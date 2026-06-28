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

from .calibration import available_water_fraction
from .const import (
    CONF_ZONES,
    DATA_CONTROLLERS,
    DATA_DECISION_ENTITIES,
    DATA_HISTORY,
    DOMAIN,
)
from .decision import evaluate_zone
from .engine import Decision, DecisionAction
from .history import IrrigationHistory
from .watering import WateringController, WateringStatus
from .zone import ZoneConfig, aggregate_zone_moisture


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up per-zone read-only sensors."""
    controllers: dict[str, WateringController] = hass.data[DOMAIN][entry.entry_id][
        DATA_CONTROLLERS
    ]
    histories: dict[str, IrrigationHistory] = hass.data[DOMAIN][entry.entry_id].get(
        DATA_HISTORY, {}
    )
    zones = entry.options.get(CONF_ZONES, {})
    entities: list[SensorEntity] = []
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        entities.append(ZoneMoistureSensor(entry, zone))
        entities.append(IrrigationDecisionSensor(entry, zone))
        controller = controllers.get(zone_id)
        if controller is not None:
            entities.append(WateringStatusSensor(entry, zone, controller))
        history = histories.get(zone_id)
        if history is not None:
            entities.append(ZoneHistorySensor(entry, zone, history))
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
            self._zone.temperature_sensor,
            self._zone.humidity_sensor,
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
    def _current_moisture(self) -> float | None:
        """Current canonical Zone Moisture from the live source sensors."""
        readings = [
            _read_moisture(self.hass, entity_id)
            for entity_id in self._zone.moisture_sensors
        ]
        return aggregate_zone_moisture(readings).value

    @callback
    def _store(self, decision: Decision) -> None:
        """Reflect a Decision on this entity's attributes (no state write)."""
        self._attr_native_value = decision.action.value
        current = self._current_moisture()
        available = available_water_fraction(
            current, self._zone.wilting_point, self._zone.field_capacity
        )
        self._attr_extra_state_attributes = {
            "zone_id": self._zone.zone_id,
            "reason": decision.reason.value,
            "recommended_liters": round(decision.recommended_liters, 2),
            "degraded": decision.degraded,
            "target_moisture": self._zone.target_moisture,
            "max_liters": self._zone.max_liters,
            "field_capacity": self._zone.field_capacity,
            "wilting_point": self._zone.wilting_point,
            "available_water": (
                None if available is None else round(available, 3)
            ),
            "learning_enabled": self._zone.learning_enabled,
            "greenhouse": self._zone.greenhouse,
            "protected_rain": self._zone.protected_rain,
            "temperature": _read_moisture(self.hass, self._zone.temperature_sensor)
            if self._zone.temperature_sensor
            else None,
            "humidity": _read_moisture(self.hass, self._zone.humidity_sensor)
            if self._zone.humidity_sensor
            else None,
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


class WateringStatusSensor(SensorEntity):
    """Reflects a zone's latest Watering Event status and volume."""

    _attr_has_entity_name = True
    _attr_name = "Watering Status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:sprinkler"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, controller: WateringController
    ) -> None:
        """Initialise the watering status sensor for a zone."""
        self._zone = zone
        self._controller = controller
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_watering_status"
        self._attr_device_info = _zone_device_info(entry, zone)
        self._attr_options = [status.value for status in WateringStatus]

    async def async_added_to_hass(self) -> None:
        """Subscribe to the controller's updates."""
        self.async_on_remove(self._controller.add_listener(self._on_update))
        self._refresh()

    @callback
    def _on_update(self) -> None:
        """Handle a controller update."""
        self._refresh()
        self.async_write_ha_state()

    @callback
    def _refresh(self) -> None:
        """Read the controller's latest event into entity attributes."""
        event = self._controller.last_event
        self._attr_native_value = event.status.value
        self._attr_extra_state_attributes = {
            "zone_id": self._zone.zone_id,
            "confirmed": event.confirmed,
            "requested_liters": round(event.requested_liters, 2),
            "measured_liters": (
                None
                if event.measured_liters is None
                else round(event.measured_liters, 2)
            ),
            "is_watering": self._controller.is_watering,
            "can_stop": self._controller.can_stop,
            "reason": event.reason,
        }


class ZoneHistorySensor(SensorEntity):
    """Exposes a zone's bounded Irrigation History for explainability.

    The state is the number of recorded Observations; the most recent entries
    (Run Requests, Decisions, Rain Events, Watering Events) are exposed as
    attributes so a card can show *why* a zone behaved as it did.
    """

    _attr_has_entity_name = True
    _attr_name = "Irrigation History"
    _attr_icon = "mdi:history"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, history: IrrigationHistory
    ) -> None:
        """Initialise the history sensor for a zone."""
        self._zone = zone
        self._history = history
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_history"
        self._attr_device_info = _zone_device_info(entry, zone)

    async def async_added_to_hass(self) -> None:
        """Subscribe to history updates."""
        self.async_on_remove(self._history.add_listener(self._on_update))
        self._refresh()

    @callback
    def _on_update(self) -> None:
        """Handle a new Observation."""
        self._refresh()
        self.async_write_ha_state()

    @callback
    def _refresh(self) -> None:
        """Read the latest history into entity state and attributes."""
        last = self._history.last
        self._attr_native_value = self._history.count
        self._attr_extra_state_attributes = {
            "zone_id": self._zone.zone_id,
            "last_kind": None if last is None else last.kind.value,
            "entries": self._history.recent(limit=20),
        }
