"""Editable per-zone toggles exposed as Switch entities.

Four switches per zone are backed by the persisted :class:`ZoneState` store and
take effect immediately (no config-entry reload):

- **Zone Enabled** — whether the zone may water at all.
- **Learning Enabled** — whether the Learned Model feeds the decision engine.
- **Schedule 1 Active** / **Schedule 2 Active** — independently toggle each of the
  two daily schedule slots; the scheduler fires only the active slots.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up per-zone toggle Switch entities."""
    store: ZoneStateStore | None = hass.data[DOMAIN][entry.entry_id].get(
        DATA_ZONE_STATE
    )
    if store is None:
        return
    zones = entry.options.get(CONF_ZONES, {})
    entities: list[SwitchEntity] = []
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        entities.append(
            ZoneToggleSwitch(
                entry, zone, store,
                key="enabled", name="Zone Enabled", icon="mdi:sprinkler-variant",
                attribute="enabled",
            )
        )
        entities.append(
            ZoneToggleSwitch(
                entry, zone, store,
                key="learning_enabled", name="Learning Enabled",
                icon="mdi:school-outline", attribute="learning_enabled",
            )
        )
        entities.append(
            ZoneToggleSwitch(
                entry, zone, store,
                key="schedule_1_active", name="Schedule 1 Active",
                icon="mdi:calendar-clock", attribute="schedule_1_active",
            )
        )
        entities.append(
            ZoneToggleSwitch(
                entry, zone, store,
                key="schedule_2_active", name="Schedule 2 Active",
                icon="mdi:calendar-clock-outline", attribute="schedule_2_active",
            )
        )
        entities.append(AutoTargetSwitch(entry, zone, store))
    async_add_entities(entities)


def _zone_device_info(entry: ConfigEntry, zone: ZoneConfig) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{zone.zone_id}")},
        name=zone.name,
        manufacturer="Amazing Irrigation",
        model="Irrigation Zone",
        via_device=(DOMAIN, entry.entry_id),
    )


class ZoneToggleSwitch(SwitchEntity):
    """A boolean ZoneState field surfaced as a live switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        zone: ZoneConfig,
        store: ZoneStateStore,
        *,
        key: str,
        name: str,
        icon: str,
        attribute: str,
    ) -> None:
        """Initialise a toggle for one ZoneState boolean field."""
        self._zone = zone
        self._store = store
        self._attribute = attribute
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_{key}"
        self._attr_device_info = _zone_device_info(entry, zone)

    @property
    def is_on(self) -> bool | None:
        """Return the current boolean from the zone's persisted state."""
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return None
        return bool(getattr(state, self._attribute))

    async def async_turn_on(self, **kwargs) -> None:  # noqa: ANN003
        """Set the field true and persist."""
        await self._set(True)

    async def async_turn_off(self, **kwargs) -> None:  # noqa: ANN003
        """Set the field false and persist."""
        await self._set(False)

    async def _set(self, value: bool) -> None:
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return
        setattr(state, self._attribute, value)
        await self._store.async_save()
        self.async_write_ha_state()


class AutoTargetSwitch(SwitchEntity):
    """Target moisture mode toggle: on = Automatic, off = Manual.

    Automatic lets the model own the target band (from learned WP/FC and the
    demand profile); Manual keeps the user's fixed Target Moisture.
    """

    _attr_has_entity_name = True
    _attr_name = "Target · Automatic"
    _attr_icon = "mdi:target"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the automatic-target toggle for a zone."""
        self._zone = zone
        self._store = store
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_target_mode"
        self._attr_device_info = _zone_device_info(entry, zone)

    @property
    def is_on(self) -> bool | None:
        """Return True when the zone's target mode is Automatic."""
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return None
        return state.target_mode == "auto"

    async def async_turn_on(self, **kwargs) -> None:  # noqa: ANN003
        """Switch to Automatic target mode."""
        await self._set("auto")

    async def async_turn_off(self, **kwargs) -> None:  # noqa: ANN003
        """Switch to Manual target mode."""
        await self._set("manual")

    async def _set(self, mode: str) -> None:
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return
        state.target_mode = mode
        await self._store.async_save()
        self.async_write_ha_state()
