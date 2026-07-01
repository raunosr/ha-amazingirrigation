"""Editable per-zone tunables exposed as Number entities.

Target Moisture and Max Liters per run are live tunables a user can change from
the device page without reloading the integration. They are backed by the
persisted :class:`ZoneState` store (the live source of truth); the config-entry
options only seed their initial values. Changes take effect immediately for the
decision engine and scheduler, which read the same store.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ZONES, DATA_ZONE_STATE, DOMAIN
from .state import ZoneState, ZoneStateStore, params_from_state
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
        entities.append(SensorDepthNumber(entry, zone, store))
        entities.append(RainFractionNumber(entry, zone, store))
        entities.append(MinApplicationNumber(entry, zone, store))
        entities.append(FieldCapacityNumber(entry, zone, store))
        entities.append(WiltingPointNumber(entry, zone, store))
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

    @property
    def available(self) -> bool:
        """Inactive while the zone derives its target automatically.

        In Automatic mode the target band comes from the plant profile and
        field capacity, so this manual value is ignored. Marking it unavailable
        makes that clear on the device page instead of showing a number that
        silently has no effect.
        """
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return False
        return (state.target_mode or "").strip().lower() != "auto"


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


class SensorDepthNumber(_ZoneStateNumber):
    """The installation depth of the soil-moisture probe."""

    _attr_name = "Sensor Depth"
    _attr_icon = "mdi:ruler"
    _attr_native_unit_of_measurement = UnitOfLength.MILLIMETERS
    _attr_native_min_value = 0.0
    _attr_native_max_value = 1500.0
    _attr_native_step = 10.0
    _attribute = "sensor_depth_mm"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the Sensor Depth number for a zone."""
        super().__init__(entry, zone, store)
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_sensor_depth_mm"


class RainFractionNumber(_ZoneStateNumber):
    """How much natural rainfall reaches this zone (0–100%)."""

    _attr_name = "Rain Fraction"
    _attr_icon = "mdi:weather-rainy"
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 5.0
    _attribute = "rain_fraction"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the Rain Fraction number for a zone."""
        super().__init__(entry, zone, store)
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_rain_fraction"


class MinApplicationNumber(_ZoneStateNumber):
    """The minimum watering amount below which a run is skipped."""

    _attr_name = "Minimum Application"
    _attr_icon = "mdi:water-minus"
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 0.1
    _attribute = "min_application"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the Minimum Application number for a zone."""
        super().__init__(entry, zone, store)
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_min_application"


class _SoilAnchorNumber(_ZoneStateNumber):
    """A trusted manual soil-calibration anchor (Field Capacity / Wilting Point).

    The box shows the value currently in use: the manual override when pinned,
    otherwise the effective learned/soil value so the user sees a sensible
    starting point. Setting a value pins it (wins over learning everywhere);
    setting ``0`` clears the override back to auto.
    """

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0
    _param: str

    def _effective(self, state: ZoneState) -> float | None:
        """Return the effective (used) FC/WP for the zone, or ``None``."""
        params = params_from_state(
            state,
            soil_type=state.soil_type or self._zone.soil_type,
            area_m2=self._zone.area_m2,
            root_depth_mm=self._zone.root_depth_mm,
            demand_profile=state.demand_profile or self._zone.demand_profile,
        )
        if params is None:
            return None
        return round(float(getattr(params, self._param)), 1)

    @property
    def native_value(self) -> float | None:
        """Return the pinned override, else the effective learned/soil value."""
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return None
        override = getattr(state, self._attribute)
        if override is not None and float(override) > 0.0:
            return round(float(override), 1)
        return self._effective(state)

    async def async_set_native_value(self, value: float) -> None:
        """Pin the anchor, or clear it back to auto when set to 0."""
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return
        setattr(state, self._attribute, float(value) if value and value > 0.0 else None)
        await self._store.async_save()
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose whether the anchor is pinned and the underlying auto value."""
        state = self._store.get(self._zone.zone_id)
        if state is None:
            return {}
        override = getattr(state, self._attribute)
        pinned = override is not None and float(override) > 0.0
        return {"manual_override": pinned, "auto_value": self._effective(state)}


class FieldCapacityNumber(_SoilAnchorNumber):
    """The moisture level at field capacity (band ceiling). 0 = auto."""

    _attr_name = "Field Capacity"
    _attr_icon = "mdi:water-percent"
    _param = "field_capacity"
    _attribute = "field_capacity_override"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the Field Capacity anchor for a zone."""
        super().__init__(entry, zone, store)
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_field_capacity"


class WiltingPointNumber(_SoilAnchorNumber):
    """The moisture level at the wilting point (band floor). 0 = auto."""

    _attr_name = "Wilting Point"
    _attr_icon = "mdi:water-off"
    _param = "wilting_point"
    _attribute = "wilting_point_override"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the Wilting Point anchor for a zone."""
        super().__init__(entry, zone, store)
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_wilting_point"
