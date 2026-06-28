"""Read-only sensors for Amazing Irrigation.

This observe-only slice exposes, per Irrigation Zone:

- a **Zone Moisture** sensor that reduces the zone's soil moisture sensors to a
  single canonical value (minimum valid reading); and
- an **Irrigation Decision** sensor that runs the pure decision engine against
  the zone's live inputs and shows whether a Run Request would skip, reduce, or
  water, with an explicit reason.

Neither sensor actuates water; watering arrives in later slices.
"""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_ZONES, DATA_DECISION_ENTITIES, DOMAIN
from .decision import evaluate_zone
from .engine import Decision, DecisionAction
from .zone import ZoneConfig, aggregate_zone_moisture


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up per-zone read-only sensors."""
    zones = entry.options.get(CONF_ZONES, {})
    entities: list[SensorEntity] = []
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        entities.append(ZoneMoistureSensor(entry, zone))
        entities.append(IrrigationDecisionSensor(entry, zone))
    async_add_entities(entities)


def _read_moisture(hass: HomeAssistant, entity_id: str) -> float | None:
    """Return a numeric moisture reading, or None when unavailable."""
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable", "", None):
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


def _zone_device_info(entry: ConfigEntry, zone: ZoneConfig) -> DeviceInfo:
    """Shared device for all of a zone's entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{zone.zone_id}")},
        name=zone.name,
        manufacturer="Amazing Irrigation",
        model="Irrigation Zone",
    )


class ZoneMoistureSensor(SensorEntity):
    """A canonical Zone Moisture value derived from a zone's sensors."""

    _attr_has_entity_name = True
    _attr_name = "Zone Moisture"
    _attr_device_class = SensorDeviceClass.MOISTURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, entry: ConfigEntry, zone: ZoneConfig) -> None:
        """Initialise the sensor for a single zone."""
        self._zone = zone
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_zone_moisture"
        self._attr_device_info = _zone_device_info(entry, zone)

    async def async_added_to_hass(self) -> None:
        """Subscribe to the source moisture sensors and compute initial state."""
        if self._zone.moisture_sensors:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    self._zone.moisture_sensors,
                    self._handle_source_update,
                )
            )
        self._recalculate()

    @callback
    def _handle_source_update(self, event: Event) -> None:
        """Recompute when any source moisture sensor changes."""
        self._recalculate()
        self.async_write_ha_state()

    @callback
    def _recalculate(self) -> None:
        """Recompute Zone Moisture from the current source readings."""
        readings = [
            _read_moisture(self.hass, entity_id)
            for entity_id in self._zone.moisture_sensors
        ]
        result = aggregate_zone_moisture(readings)
        self._attr_native_value = result.value
        self._attr_available = result.available
        self._attr_extra_state_attributes = {
            "zone_id": self._zone.zone_id,
            "degraded": result.degraded,
            "sensors_used": result.used,
            "sensors_configured": result.configured,
            "source_sensors": self._zone.moisture_sensors,
            "forecast_rain_amount": self._zone.forecast_rain_amount,
            "forecast_rain_probability": self._zone.forecast_rain_probability,
            "observed_rain_amount": self._zone.observed_rain_amount,
            "safety_blockers": self._zone.safety_blockers,
        }


class IrrigationDecisionSensor(SensorEntity):
    """Shows what a Run Request would decide right now for a zone."""

    _attr_has_entity_name = True
    _attr_name = "Irrigation Decision"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:water-pump"
    _attr_options = [action.value for action in DecisionAction]

    def __init__(self, entry: ConfigEntry, zone: ZoneConfig) -> None:
        """Initialise the decision sensor for a single zone."""
        self._entry = entry
        self._zone = zone
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_decision"
        self._attr_device_info = _zone_device_info(entry, zone)

    @property
    def _tracked_entities(self) -> list[str]:
        """All live entities whose changes affect this zone's decision."""
        tracked = list(self._zone.moisture_sensors)
        tracked += self._zone.safety_blockers
        for entity_id in (
            self._zone.forecast_rain_amount,
            self._zone.forecast_rain_probability,
            self._zone.observed_rain_amount,
        ):
            if entity_id:
                tracked.append(entity_id)
        return tracked

    async def async_added_to_hass(self) -> None:
        """Register with the entry, subscribe to inputs, compute initial state."""
        store = self.hass.data[DOMAIN][self._entry.entry_id].setdefault(
            DATA_DECISION_ENTITIES, {}
        )
        store[self.entity_id] = self

        tracked = self._tracked_entities
        if tracked:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, tracked, self._handle_source_update
                )
            )
        # Set initial state without writing; HA writes it when the entity is added.
        self._store(self._compute())

    async def async_will_remove_from_hass(self) -> None:
        """Deregister from the entry's lookup table."""
        store = (
            self.hass.data.get(DOMAIN, {})
            .get(self._entry.entry_id, {})
            .get(DATA_DECISION_ENTITIES, {})
        )
        store.pop(self.entity_id, None)

    @callback
    def _handle_source_update(self, event: Event) -> None:
        """Re-evaluate the live (non-forced) decision when any input changes."""
        self.evaluate(write=True)

    def _compute(self, *, force: bool = False) -> Decision:
        """Compute a Decision without mutating entity state."""
        return evaluate_zone(self.hass, self._zone, force=force)

    @callback
    def _store(self, decision: Decision) -> None:
        """Reflect a Decision on this entity's attributes (no state write)."""
        self._attr_native_value = decision.action.value
        self._attr_extra_state_attributes = {
            "zone_id": self._zone.zone_id,
            "reason": decision.reason.value,
            "recommended_liters": round(decision.recommended_liters, 2),
            "degraded": decision.degraded,
            "target_moisture": self._zone.target_moisture,
            "max_liters": self._zone.max_liters,
            **decision.details,
        }

    @callback
    def evaluate(self, *, force: bool = False, write: bool = True) -> Decision:
        """Run the engine; persist the result only when ``write`` is true.

        A forced evaluation (Force Water) is computed for the caller's response
        but is deliberately not persisted, so the sensor keeps showing the live,
        non-forced decision rather than getting stuck on a one-shot ``forced``.
        """
        decision = self._compute(force=force)
        if write:
            self._store(decision)
            self.async_write_ha_state()
        return decision
