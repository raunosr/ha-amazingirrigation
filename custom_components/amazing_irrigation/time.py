"""Editable per-zone schedule times exposed as Time entities.

Each zone has two independent daily schedule slots. The time of each slot is a
native Time entity backed by the persisted :class:`ZoneState` store, so a user
can pick a watering time on the device page with a proper time picker and have it
take effect immediately. Whether a slot actually fires is governed by its
separate Schedule N Active switch; the scheduler reads both from the same store.
"""

from __future__ import annotations

from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ZONES, DATA_ZONE_STATE, DOMAIN
from .state import ZoneStateStore, normalize_time
from .zone import ZoneConfig


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the two per-zone schedule Time entities."""
    store: ZoneStateStore | None = hass.data[DOMAIN][entry.entry_id].get(
        DATA_ZONE_STATE
    )
    if store is None:
        return
    zones = entry.options.get(CONF_ZONES, {})
    entities: list[TimeEntity] = []
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        entities.append(
            ScheduleTime(
                entry, zone, store,
                key="schedule_1_time", name="Schedule 1 Time",
                attribute="schedule_1_time",
            )
        )
        entities.append(
            ScheduleTime(
                entry, zone, store,
                key="schedule_2_time", name="Schedule 2 Time",
                attribute="schedule_2_time",
            )
        )
    async_add_entities(entities)


def _zone_device_info(entry: ConfigEntry, zone: ZoneConfig) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{zone.zone_id}")},
        name=zone.name,
        manufacturer="Amazing Irrigation",
        model="Irrigation Zone",
        via_device=(DOMAIN, entry.entry_id),
    )


class ScheduleTime(TimeEntity):
    """One schedule slot's start time, backed by ZoneState."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:clock-time-four-outline"

    def __init__(
        self,
        entry: ConfigEntry,
        zone: ZoneConfig,
        store: ZoneStateStore,
        *,
        key: str,
        name: str,
        attribute: str,
    ) -> None:
        """Initialise a schedule-time entity for one slot of a zone."""
        self._zone = zone
        self._store = store
        self._attribute = attribute
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_{key}"
        self._attr_device_info = _zone_device_info(entry, zone)

    @property
    def native_value(self) -> dt_time | None:
        """Return the slot's stored ``HH:MM`` as a time, or None when unset."""
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return None
        normalized = normalize_time(getattr(state, self._attribute))
        if normalized is None:
            return None
        hour, minute = (int(part) for part in normalized.split(":"))
        return dt_time(hour=hour, minute=minute)

    async def async_set_value(self, value: dt_time) -> None:
        """Persist a new schedule time (minute precision) and refresh."""
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return
        setattr(state, self._attribute, f"{value.hour:02d}:{value.minute:02d}")
        await self._store.async_save()
        self.async_write_ha_state()
