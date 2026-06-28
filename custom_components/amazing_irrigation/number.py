"""Editable per-zone tunables exposed as Number entities.

Target Moisture and Max Liters per run are live tunables a user can change from
the device page without reloading the integration. They are backed by the
persisted :class:`ZoneState` store (the live source of truth); the config-entry
options only seed their initial values. Changes take effect immediately for the
decision engine and scheduler, which read the same store.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ZONES, DATA_ZONE_STATE, DOMAIN
from .state import ZoneStateStore
from .zone import ZoneConfig


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up per-zone tunable Number entities."""
    store: ZoneStateStore | None = hass.data[DOMAIN][entry.entry_id].get(
        DATA_ZONE_STATE
    )
    if store is None:
        return
    zones = entry.options.get(CONF_ZONES, {})
    entities: list[NumberEntity] = []
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        entities.append(TargetMoistureNumber(entry, zone, store))
        entities.append(MaxLitersNumber(entry, zone, store))
    async_add_entities(entities)


def _zone_device_info(entry: ConfigEntry, zone: ZoneConfig) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{zone.zone_id}")},
        name=zone.name,
        manufacturer="Amazing Irrigation",
        model="Irrigation Zone",
        via_device=(DOMAIN, entry.entry_id),
    )


class _ZoneStateNumber(NumberEntity):
    """Base for a Number that reads/writes one ZoneState field."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX
    _attribute: str

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the tunable for a zone."""
        self._zone = zone
        self._store = store
        self._attr_device_info = _zone_device_info(entry, zone)

    @property
    def native_value(self) -> float | None:
        """Return the current value from the zone's persisted state."""
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return None
        return getattr(state, self._attribute)

    async def async_set_native_value(self, value: float) -> None:
        """Persist a new value and refresh the entity."""
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return
        setattr(state, self._attribute, float(value))
        await self._store.async_save()
        self.async_write_ha_state()


class TargetMoistureNumber(_ZoneStateNumber):
    """The moisture level a zone waters towards."""

    _attr_name = "Target Moisture"
    _attr_icon = "mdi:target"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0
    _attribute = "target_moisture"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the Target Moisture number for a zone."""
        super().__init__(entry, zone, store)
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_target_moisture"


class MaxLitersNumber(_ZoneStateNumber):
    """The safety cap on the Watering Volume of a single run."""

    _attr_name = "Max Liters per Run"
    _attr_icon = "mdi:cup-water"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_native_min_value = 0.0
    _attr_native_max_value = 500.0
    _attr_native_step = 0.5
    _attribute = "max_liters"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the Max Liters number for a zone."""
        super().__init__(entry, zone, store)
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_max_liters"
