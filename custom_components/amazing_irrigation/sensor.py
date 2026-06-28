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

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfVolume
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
    DATA_LEARNERS,
    DATA_ZONE_STATE,
    DOMAIN,
)
from .decision import evaluate_zone
from .engine import Decision, DecisionAction
from .history import IrrigationHistory
from .learner import ZoneLearner
from .state import ZoneStateStore
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
    zone_state: ZoneStateStore | None = hass.data[DOMAIN][entry.entry_id].get(
        DATA_ZONE_STATE
    )
    learners: dict[str, ZoneLearner] = hass.data[DOMAIN][entry.entry_id].get(
        DATA_LEARNERS, {}
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
            if zone_state is not None:
                entities.append(
                    TotalVolumeSensor(entry, zone, controller, zone_state)
                )
        history = histories.get(zone_id)
        if history is not None:
            entities.append(ZoneHistorySensor(entry, zone, history))
        learner = learners.get(zone_id)
        if learner is not None:
            entities.extend(
                descriptor.build(entry, zone, learner)
                for descriptor in LEARNED_SENSORS
            )
    if zone_state is not None and controllers:
        entities.append(SystemTotalVolumeSensor(entry, controllers, zone_state))
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
        via_device=(DOMAIN, entry.entry_id),
    )


def _hub_device_info(entry: ConfigEntry) -> DeviceInfo:
    """The integration-level device that owns system-wide entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Amazing Irrigation",
        manufacturer="Amazing Irrigation",
        model="Controller",
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
            "references": self._references(),
            **decision.details,
        }

    @callback
    def _references(self) -> dict[str, object]:
        """The configured source entities this zone reads, for card surfacing.

        Exposed so the Lovelace card can list every referenced sensor (moisture,
        rain, climate and safety blockers) with its live state without the user
        having to wire each one into the card config by hand.
        """
        return {
            "moisture_sensors": list(self._zone.moisture_sensors),
            "forecast_rain_amount": self._zone.forecast_rain_amount,
            "forecast_rain_probability": self._zone.forecast_rain_probability,
            "observed_rain_amount": self._zone.observed_rain_amount,
            "temperature_sensor": self._zone.temperature_sensor,
            "humidity_sensor": self._zone.humidity_sensor,
            "safety_blockers": list(self._zone.safety_blockers),
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


class TotalVolumeSensor(SensorEntity):
    """Cumulative Total Watering Volume applied to a zone, in liters.

    Sums the measured (or, when no measurement is available, requested) volume of
    every Confirmed Watering Event. Exposed as a ``total_increasing`` sensor so
    Home Assistant's statistics can chart long-term water use per zone.
    """

    _attr_has_entity_name = True
    _attr_name = "Total Watering Volume"
    _attr_icon = "mdi:water-circle"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        entry: ConfigEntry,
        zone: ZoneConfig,
        controller: WateringController,
        zone_state: ZoneStateStore,
    ) -> None:
        """Initialise the cumulative volume sensor for a zone."""
        self._zone = zone
        self._controller = controller
        self._zone_state = zone_state
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_total_volume"
        self._attr_device_info = _zone_device_info(entry, zone)

    async def async_added_to_hass(self) -> None:
        """Refresh whenever the controller reports a Watering Event change."""
        self.async_on_remove(self._controller.add_listener(self._on_update))
        self._refresh()

    @callback
    def _on_update(self) -> None:
        """Handle a controller update."""
        self._refresh()
        self.async_write_ha_state()

    @callback
    def _refresh(self) -> None:
        """Read the cumulative total from the zone's persisted state."""
        state = self._zone_state.get(self._zone.zone_id)
        total = 0.0 if state is None else state.total_liters
        self._attr_native_value = round(total, 3)
        self._attr_extra_state_attributes = {"zone_id": self._zone.zone_id}


class SystemTotalVolumeSensor(SensorEntity):
    """Overall Total Watering Volume across every zone, in liters."""

    _attr_has_entity_name = True
    _attr_name = "Total Watering Volume"
    _attr_icon = "mdi:water-pump"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        entry: ConfigEntry,
        controllers: dict[str, WateringController],
        zone_state: ZoneStateStore,
    ) -> None:
        """Initialise the integration-wide cumulative volume sensor."""
        self._controllers = controllers
        self._zone_state = zone_state
        self._attr_unique_id = f"{entry.entry_id}_total_volume"
        self._attr_device_info = _hub_device_info(entry)

    async def async_added_to_hass(self) -> None:
        """Refresh whenever any zone's controller reports a change."""
        for controller in self._controllers.values():
            self.async_on_remove(controller.add_listener(self._on_update))
        self._refresh()

    @callback
    def _on_update(self) -> None:
        """Handle a controller update from any zone."""
        self._refresh()
        self.async_write_ha_state()

    @callback
    def _refresh(self) -> None:
        """Sum every zone's persisted Total Watering Volume."""
        total = sum(state.total_liters for state in self._zone_state.states.values())
        self._attr_native_value = round(total, 3)


class ZoneHistorySensor(SensorEntity):
    """Exposes a zone's bounded Irrigation History for explainability.

    The state is a short human-readable summary of the most recent Observation
    (e.g. "Watered 8 L", "Skipped: above target", "Rain +4 mm"); the recent
    entries and an observation count are exposed as attributes so a card can
    show *why* a zone behaved as it did.
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
        self._attr_native_value = "No activity yet" if last is None else last.summary
        self._attr_extra_state_attributes = {
            "zone_id": self._zone.zone_id,
            "last_kind": None if last is None else last.kind.value,
            "observation_count": self._history.count,
            "entries": self._history.recent(limit=20),
        }


class LearnedValueSensor(SensorEntity):
    """A single read-only learned parameter from a zone's Learned Model.

    Learned values change slowly and are written to the persisted ZoneState by
    the :class:`ZoneLearner`; this sensor mirrors one of them, refreshing when
    the learner reports an update. ``None`` until enough evidence is gathered.
    """

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        entry: ConfigEntry,
        zone: ZoneConfig,
        learner: ZoneLearner,
        *,
        key: str,
        name: str,
        icon: str,
        unit: str,
        attribute: str,
        samples_key: str | None,
    ) -> None:
        """Initialise a learned-value sensor for one parameter of a zone."""
        self._zone = zone
        self._learner = learner
        self._attribute = attribute
        self._samples_key = samples_key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_learned_{key}"
        self._attr_device_info = _zone_device_info(entry, zone)

    async def async_added_to_hass(self) -> None:
        """Refresh whenever the learner reports a model update."""
        self.async_on_remove(self._learner.add_listener(self._on_update))
        self._refresh()

    @callback
    def _on_update(self) -> None:
        """Handle a learner update."""
        self._refresh()
        self.async_write_ha_state()

    @callback
    def _refresh(self) -> None:
        """Read the learned value from the zone's persisted state."""
        state = self._learner.state
        value = None if state is None else getattr(state, self._attribute)
        self._attr_native_value = None if value is None else round(float(value), 3)
        attributes = {"zone_id": self._zone.zone_id}
        if state is not None and self._samples_key is not None:
            attributes["samples"] = state.learning_state.get(self._samples_key, 0)
        self._attr_extra_state_attributes = attributes


@dataclass(frozen=True)
class _LearnedSensorDescriptor:
    """Static description of one learned-value sensor."""

    key: str
    name: str
    icon: str
    unit: str
    attribute: str
    samples_key: str | None

    def build(
        self, entry: ConfigEntry, zone: ZoneConfig, learner: ZoneLearner
    ) -> LearnedValueSensor:
        """Instantiate the described sensor for a zone."""
        return LearnedValueSensor(
            entry,
            zone,
            learner,
            key=self.key,
            name=self.name,
            icon=self.icon,
            unit=self.unit,
            attribute=self.attribute,
            samples_key=self.samples_key,
        )


# The five learned parameters surfaced as read-only per-zone sensors.
LEARNED_SENSORS: tuple[_LearnedSensorDescriptor, ...] = (
    _LearnedSensorDescriptor(
        key="gain_per_liter",
        name="Learned Moisture Gain per Liter",
        icon="mdi:water-percent",
        unit=f"{PERCENTAGE}/L",
        attribute="learned_gain_per_liter",
        samples_key="gain_samples",
    ),
    _LearnedSensorDescriptor(
        key="drying_rate",
        name="Learned Daily Drying Rate",
        icon="mdi:weather-sunny",
        unit=f"{PERCENTAGE}/d",
        attribute="learned_drying_rate",
        samples_key="drying_samples",
    ),
    _LearnedSensorDescriptor(
        key="rain_efficiency",
        name="Learned Rain Efficiency",
        icon="mdi:weather-pouring",
        unit=f"{PERCENTAGE}/mm",
        attribute="learned_rain_efficiency",
        samples_key="rain_samples",
    ),
    _LearnedSensorDescriptor(
        key="field_capacity",
        name="Learned Field Capacity",
        icon="mdi:cup-water",
        unit=PERCENTAGE,
        attribute="learned_field_capacity",
        samples_key="capacity_samples",
    ),
    _LearnedSensorDescriptor(
        key="wilting_point",
        name="Learned Wilting Point",
        icon="mdi:flower-tulip-outline",
        unit=PERCENTAGE,
        attribute="learned_wilting_point",
        samples_key="capacity_samples",
    ),
)
