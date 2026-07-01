"""Editable per-zone preset selectors exposed as Select entities.

Soil Type and Plant Profile are live tunables a user can change from the device
page (or card) without reloading the integration. They are backed by the
persisted :class:`ZoneState` store — the same live source of truth the config
flow seeds — so the config flow, the device page and the card all present the
identical option set from one source (:mod:`.const`).

Changing the soil type only re-seeds the physics prior for zones whose field
capacity / wilting point are neither manually overridden nor confidently
learned; a good learned model is preserved automatically by
``params_from_state`` (it falls back to the prior only for missing values).
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ZONES,
    DATA_ZONE_STATE,
    DEMAND_PROFILE_OPTIONS,
    DOMAIN,
    SOIL_TYPE_OPTIONS,
)
from .state import ZoneStateStore
from .zone import ZoneConfig


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up per-zone preset Select entities."""
    store: ZoneStateStore | None = hass.data[DOMAIN][entry.entry_id].get(
        DATA_ZONE_STATE
    )
    if store is None:
        return
    zones = entry.options.get(CONF_ZONES, {})
    entities: list[SelectEntity] = []
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        entities.append(SoilTypeSelect(entry, zone, store))
        entities.append(PlantProfileSelect(entry, zone, store))
    async_add_entities(entities)


def _zone_device_info(entry: ConfigEntry, zone: ZoneConfig) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{zone.zone_id}")},
        name=zone.name,
        manufacturer="Amazing Irrigation",
        model="Irrigation Zone",
        via_device=(DOMAIN, entry.entry_id),
    )


class _ZoneStateSelect(SelectEntity):
    """Base for a Select that reads/writes one ZoneState field."""

    _attr_has_entity_name = True
    _attribute: str

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the selector for a zone."""
        self._zone = zone
        self._store = store
        self._attr_device_info = _zone_device_info(entry, zone)

    @property
    def current_option(self) -> str | None:
        """Return the current value from the zone's persisted state."""
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return None
        value = getattr(state, self._attribute)
        return value if value in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        """Persist a new value and refresh the entity."""
        if option not in self._attr_options:
            return
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return
        setattr(state, self._attribute, option)
        await self._store.async_save()
        self.async_write_ha_state()


class SoilTypeSelect(_ZoneStateSelect):
    """The soil preset that seeds the zone's physics prior."""

    _attr_name = "Soil Type"
    _attr_icon = "mdi:shovel"
    _attr_translation_key = "soil_type"
    _attr_options = list(SOIL_TYPE_OPTIONS)
    _attribute = "soil_type"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the Soil Type select for a zone."""
        super().__init__(entry, zone, store)
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_soil_type"


class PlantProfileSelect(_ZoneStateSelect):
    """The plant water-demand profile driving the hysteresis band."""

    _attr_name = "Plant Profile"
    _attr_icon = "mdi:sprout"
    _attr_translation_key = "demand_profile"
    _attr_options = list(DEMAND_PROFILE_OPTIONS)
    _attribute = "demand_profile"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the Plant Profile select for a zone."""
        super().__init__(entry, zone, store)
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_plant_profile"
