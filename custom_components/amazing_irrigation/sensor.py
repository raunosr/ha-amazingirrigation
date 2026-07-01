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

import math
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
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .calibration import available_water_fraction
from .const import (
    CONF_ZONES,
    DATA_CONTROLLERS,
    DATA_DECISION_ENTITIES,
    DATA_DISCOVERY,
    DATA_HISTORY,
    DATA_LEARNERS,
    DATA_MODEL_INSIGHT_ENTITIES,
    DATA_TARGET_RANGE_ENTITIES,
    DATA_ZONE_STATE,
    DEMAND_PROFILE_OPTIONS,
    DISCOVERY_AWAITING_SATURATION,
    DISCOVERY_CANCELLED,
    DISCOVERY_COMPLETED,
    DISCOVERY_FAILED,
    DISCOVERY_IDLE,
    DISCOVERY_MAX_WAIT_HOURS,
    DISCOVERY_MIN_WAIT_HOURS,
    DISCOVERY_MONITORING,
    DOMAIN,
    SOIL_TYPE_OPTIONS,
)
from .decision import evaluate_zone
from .discovery_controller import DiscoveryController
from .engine import Decision, DecisionAction, DecisionReason
from .history import IrrigationHistory
from .learner import ZoneLearner
from .state import ZoneStateStore, params_from_state
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
    discovery: dict[str, DiscoveryController] = hass.data[DOMAIN][entry.entry_id].get(
        DATA_DISCOVERY, {}
    )
    zones = entry.options.get(CONF_ZONES, {})
    entities: list[SensorEntity] = []
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        entities.append(ZoneMoistureSensor(entry, zone))
        entities.append(IrrigationDecisionSensor(entry, zone))
        entities.append(TargetRangeSensor(entry, zone))
        discovery_controller = discovery.get(zone_id)
        if discovery_controller is not None:
            entities.append(
                DiscoveryStatusSensor(entry, zone, discovery_controller)
            )
        learner = learners.get(zone_id)
        if zone_state is not None:
            entities.append(ModelInsightSensor(entry, zone, zone_state, learner))
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
            self._zone.weather_forecast_entity,
            self._zone.observed_rain_amount,
            self._zone.temperature_sensor,
            self._zone.humidity_sensor,
            self._zone.observed_air_temperature,
            self._zone.observed_air_humidity,
            self._zone.forecast_air_temperature,
            self._zone.forecast_air_humidity,
            self._zone.wind_speed,
            self._zone.solar_radiation,
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
        return evaluate_zone(
            self.hass, self._zone, force=force, state=self._zone_state()
        )

    def _zone_state(self):
        """Return the persisted live ZoneState for this decision, if available."""
        store = self._zone_state_store()
        if store is None:
            return None
        return store.get(self._zone.zone_id)

    def _zone_state_store(self) -> ZoneStateStore | None:
        """Return the ZoneStateStore for this entry, if available."""
        store: ZoneStateStore | None = self.hass.data[DOMAIN][self._entry.entry_id].get(
            DATA_ZONE_STATE
        )
        return store

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
        self._persist_decision_explanation(decision.details.get("explanation"))
        current = self._current_moisture()
        available = available_water_fraction(
            current, self._zone.wilting_point, self._zone.field_capacity
        )
        live = self._zone_state()
        target_mode = live.target_mode if live else self._zone.target_mode
        demand_profile = live.demand_profile if live else self._zone.demand_profile
        soil_type = live.soil_type if live else self._zone.soil_type
        sensor_depth_mm = (
            live.sensor_depth_mm if live else self._zone.sensor_depth_mm
        )
        rain_fraction = live.rain_fraction if live else self._zone.rain_fraction
        min_application = (
            live.min_application if live else self._zone.min_application
        )
        root_depth_mm = self._zone.root_depth_mm
        sensor_depth_shallow = bool(
            sensor_depth_mm is not None
            and root_depth_mm
            and sensor_depth_mm < 0.5 * root_depth_mm
        )
        target_moisture = (
            live.target_moisture
            if live and live.target_moisture is not None
            else self._zone.target_moisture
        )
        band_low = _finite_float(decision.details.get("target_band_low"))
        band_high = _finite_float(decision.details.get("target_band_high"))
        band_fc = _finite_float(decision.details.get("band_field_capacity"))
        summary = _decision_summary(decision, current, band_low, band_high)
        fc_override = _finite_float(live.field_capacity_override) if live else None
        wp_override = _finite_float(live.wilting_point_override) if live else None
        fc_anchored = fc_override is not None and fc_override > 0.0
        wp_anchored = wp_override is not None and wp_override > 0.0
        effective = (
            params_from_state(
                live,
                soil_type=soil_type,
                area_m2=self._zone.area_m2,
                root_depth_mm=root_depth_mm,
                demand_profile=demand_profile,
            )
            if live is not None
            else None
        )
        effective_fc = (
            round(effective.field_capacity, 1)
            if effective is not None
            else self._zone.field_capacity
        )
        effective_wp = (
            round(effective.wilting_point, 1)
            if effective is not None
            else self._zone.wilting_point
        )
        self._attr_extra_state_attributes = {
            "zone_id": self._zone.zone_id,
            "reason": decision.reason.value,
            "summary": summary,
            "recommended_liters": round(decision.recommended_liters, 2),
            "degraded": decision.degraded,
            "target_moisture": target_moisture,
            "target_mode": target_mode,
            "demand_profile": demand_profile,
            "demand_profile_options": list(DEMAND_PROFILE_OPTIONS),
            "soil_type": soil_type,
            "soil_type_options": list(SOIL_TYPE_OPTIONS),
            "sensor_depth_mm": sensor_depth_mm,
            "sensor_depth_shallow": sensor_depth_shallow,
            "rain_fraction": rain_fraction,
            "min_application": min_application,
            "max_liters": self._zone.max_liters,
            "field_capacity": effective_fc,
            "wilting_point": effective_wp,
            "field_capacity_override": fc_override if fc_anchored else None,
            "wilting_point_override": wp_override if wp_anchored else None,
            "field_capacity_anchored": fc_anchored,
            "wilting_point_anchored": wp_anchored,
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
        self._notify_target_range(
            band_low,
            band_high,
            band_fc,
            target_mode,
            demand_profile,
            fc_anchored,
            wp_anchored,
        )

    @callback
    def _notify_target_range(
        self,
        low: float | None,
        high: float | None,
        field_capacity: float | None,
        mode: str | None,
        profile: str | None,
        fc_anchored: bool = False,
        wp_anchored: bool = False,
    ) -> None:
        """Push the active target band to the per-zone Target Range sensor."""
        entity = (
            self.hass.data[DOMAIN][self._entry.entry_id]
            .get(DATA_TARGET_RANGE_ENTITIES, {})
            .get(self._zone.zone_id)
        )
        if entity is not None:
            entity.update_band(
                low, high, field_capacity, mode, profile, fc_anchored, wp_anchored
            )

    @callback
    def _persist_decision_explanation(self, explanation: dict | None) -> None:
        """Persist the latest structured decision explanation on ZoneState."""
        store = self._zone_state_store()
        if store is None:
            return
        state = store.get(self._zone.zone_id)
        if state is None:
            return
        state.decision_explanation = explanation
        self._notify_model_insight()
        self.hass.async_create_task(store.async_save())

    @callback
    def _notify_model_insight(self) -> None:
        """Refresh the per-zone Model Insight sensor after a decision changes."""
        entity = (
            self.hass.data[DOMAIN][self._entry.entry_id]
            .get(DATA_MODEL_INSIGHT_ENTITIES, {})
            .get(self._zone.zone_id)
        )
        if entity is not None:
            entity.refresh_from_state(write=True)

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
            "weather_forecast_entity": self._zone.weather_forecast_entity,
            "observed_rain_amount": self._zone.observed_rain_amount,
            "temperature_sensor": self._zone.temperature_sensor,
            "humidity_sensor": self._zone.humidity_sensor,
            "observed_air_temperature": self._zone.observed_air_temperature,
            "observed_air_humidity": self._zone.observed_air_humidity,
            "forecast_air_temperature": self._zone.forecast_air_temperature,
            "forecast_air_humidity": self._zone.forecast_air_humidity,
            "wind_speed": self._zone.wind_speed,
            "solar_radiation": self._zone.solar_radiation,
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


_ACTION_LABELS = {
    DecisionAction.SKIP: "Skip",
    DecisionAction.REDUCE: "Reduce",
    DecisionAction.WATER: "Water",
}


def _anchor_note(fc_anchored: bool, wp_anchored: bool) -> str | None:
    """Return a short note naming the manually anchored soil calibration."""
    if fc_anchored and wp_anchored:
        return "manual field capacity & wilting point"
    if fc_anchored:
        return "manual field capacity"
    if wp_anchored:
        return "manual wilting point"
    return None


def _decision_summary(
    decision: Decision,
    moisture: float | None,
    band_low: float | None,
    band_high: float | None,
) -> str:
    """Build a plain-language, one-line explanation of the live decision.

    Turns the terse action + reason enum into a human sentence that names the
    active target band and the current moisture, so the meaning is clear on the
    device page and dashboards without the user knowing the internal model.
    """
    reason = decision.reason
    m = None if moisture is None else round(moisture)
    band = (
        f"{round(band_low)}\u2013{round(band_high)}%"
        if band_low is not None and band_high is not None
        else None
    )
    liters = round(decision.recommended_liters, 1)

    if reason == DecisionReason.SAFETY_BLOCKER:
        return "Skip \u2014 a safety blocker is active"
    if reason == DecisionReason.DISABLED:
        return "Skip \u2014 zone is disabled"
    if reason == DecisionReason.OUT_OF_SEASON:
        return "Skip \u2014 outside the watering season"
    if reason == DecisionReason.MOISTURE_UNAVAILABLE:
        return "Skip \u2014 no moisture reading available"
    if reason == DecisionReason.ZONE_LOCKED:
        return "Skip \u2014 zone is busy watering"
    if reason == DecisionReason.NO_TARGET:
        return "Skip \u2014 no target moisture is set"
    if reason == DecisionReason.FORCED:
        return f"Water {liters} L \u2014 forced run"
    if reason in (DecisionReason.ABOVE_TARGET, DecisionReason.PREDICTIVE_HOLD):
        if m is not None and band is not None:
            return f"Skip \u2014 moisture {m}% is within target {band}"
        return "Skip \u2014 moisture is on target"
    if reason == DecisionReason.RAIN_SUFFICIENT:
        return "Skip \u2014 rain is enough to reach the target"
    if reason == DecisionReason.RAIN_REDUCE:
        return f"Reduce to {liters} L \u2014 rain covers part of the need"
    if reason == DecisionReason.BELOW_MIN:
        return "Skip \u2014 needed amount is below the minimum application"
    if reason in (DecisionReason.BELOW_TARGET, DecisionReason.PREDICTIVE_WATER):
        if m is not None and band is not None:
            return f"Water {liters} L \u2014 moisture {m}% is below target {band}"
        return f"Water {liters} L \u2014 below target"
    label = _ACTION_LABELS.get(decision.action, decision.action.value.title())
    return f"{label} \u2014 {reason.value.replace('_', ' ')}"


class TargetRangeSensor(SensorEntity):
    """Human-readable active target band for a zone (e.g. ``33\u201358%``).

    Answers the question "what is this zone watering towards right now?" on any
    surface \u2014 the device page, dashboards and automations \u2014 without the user
    needing to know how the band is derived from soil, field capacity and the
    plant profile. The value is pushed by the Irrigation Decision sensor, which
    computes the band on every input change.
    """

    _attr_has_entity_name = True
    _attr_name = "Target Range"
    _attr_icon = "mdi:target-variant"

    def __init__(self, entry: ConfigEntry, zone: ZoneConfig) -> None:
        """Initialise the target range sensor for a single zone."""
        self._entry = entry
        self._zone = zone
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_target_range"
        self._attr_device_info = _zone_device_info(entry, zone)
        self._attr_native_value = None
        self._attr_extra_state_attributes = {"zone_id": zone.zone_id}

    async def async_added_to_hass(self) -> None:
        """Register so the decision sensor can push band updates here."""
        store = self.hass.data[DOMAIN][self._entry.entry_id].setdefault(
            DATA_TARGET_RANGE_ENTITIES, {}
        )
        store[self._zone.zone_id] = self
        # Seed from the decision sensor's latest attributes if it is already up.
        decisions = self.hass.data[DOMAIN][self._entry.entry_id].get(
            DATA_DECISION_ENTITIES, {}
        )
        decision = next(
            (
                entity
                for entity in decisions.values()
                if getattr(entity, "_zone", None) is not None
                and entity._zone.zone_id == self._zone.zone_id
            ),
            None,
        )
        if decision is not None:
            attrs = decision.extra_state_attributes or {}
            self.update_band(
                _finite_float(attrs.get("target_band_low")),
                _finite_float(attrs.get("target_band_high")),
                _finite_float(attrs.get("band_field_capacity")),
                attrs.get("target_mode"),
                attrs.get("demand_profile"),
                bool(attrs.get("field_capacity_anchored")),
                bool(attrs.get("wilting_point_anchored")),
                write=False,
            )

    async def async_will_remove_from_hass(self) -> None:
        """Deregister from the entry's lookup table."""
        store = (
            self.hass.data.get(DOMAIN, {})
            .get(self._entry.entry_id, {})
            .get(DATA_TARGET_RANGE_ENTITIES, {})
        )
        store.pop(self._zone.zone_id, None)

    @callback
    def update_band(
        self,
        low: float | None,
        high: float | None,
        field_capacity: float | None,
        mode: str | None,
        profile: str | None,
        fc_anchored: bool = False,
        wp_anchored: bool = False,
        *,
        write: bool = True,
    ) -> None:
        """Reflect the active band; keep the last value when none is available.

        Some decision paths (disabled, safety-blocked, no moisture) return before
        a band is computed. In those cases the previously known range is retained
        so the sensor keeps answering "what is the target" instead of blanking.
        """
        if low is None or high is None:
            if write:
                self.async_write_ha_state()
            return
        auto = (mode or "").strip().lower() == "auto"
        if auto:
            source = f"{profile} plant profile" if profile else "plant profile"
        else:
            source = "manual target"
        anchor = _anchor_note(fc_anchored, wp_anchored)
        if anchor:
            source = f"{source} \u00b7 {anchor}"
        self._attr_native_value = f"{round(low)}\u2013{round(high)}%"
        self._attr_extra_state_attributes = {
            "zone_id": self._zone.zone_id,
            "start_watering_below": round(low),
            "refill_to": round(high),
            "field_capacity_cap": (
                None if field_capacity is None else round(field_capacity)
            ),
            "field_capacity_anchored": fc_anchored,
            "wilting_point_anchored": wp_anchored,
            "mode": "automatic" if auto else "manual",
            "source": source,
        }
        if write:
            self.async_write_ha_state()


@dataclass(frozen=True)
class _ModelParameterDescriptor:
    """Friendly metadata for one water-balance model parameter."""

    key: str
    label: str
    unit: str | None


MODEL_PARAMETER_DESCRIPTORS: tuple[_ModelParameterDescriptor, ...] = (
    _ModelParameterDescriptor("eta_irr", "Irrigation Efficiency", f"{PERCENTAGE}/L"),
    _ModelParameterDescriptor("eta_rain", "Rain Efficiency", f"{PERCENTAGE}/mm"),
    _ModelParameterDescriptor("k_et", "ET Coefficient", None),
    _ModelParameterDescriptor("drain_rate", "Drainage Rate", "1/h"),
    _ModelParameterDescriptor("field_capacity", "Field Capacity", PERCENTAGE),
    _ModelParameterDescriptor("wilting_point", "Wilting Point", PERCENTAGE),
)


class ModelInsightSensor(SensorEntity):
    """Diagnostic explainability surface for one zone's water-balance model."""

    _attr_has_entity_name = True
    _attr_name = "Model Insight"
    _attr_icon = "mdi:brain"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        entry: ConfigEntry,
        zone: ZoneConfig,
        store: ZoneStateStore,
        learner: ZoneLearner | None,
    ) -> None:
        """Initialise the model insight sensor for a zone."""
        self._entry = entry
        self._zone = zone
        self._store = store
        self._learner = learner
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_model_insight"
        self._attr_device_info = _zone_device_info(entry, zone)

    async def async_added_to_hass(self) -> None:
        """Register with the entry and refresh when learning updates."""
        store = self.hass.data[DOMAIN][self._entry.entry_id].setdefault(
            DATA_MODEL_INSIGHT_ENTITIES, {}
        )
        store[self._zone.zone_id] = self
        if self._learner is not None:
            self.async_on_remove(self._learner.add_listener(self._on_update))
        self.refresh_from_state(write=False)

    async def async_will_remove_from_hass(self) -> None:
        """Deregister from the entry's lookup table."""
        store = (
            self.hass.data.get(DOMAIN, {})
            .get(self._entry.entry_id, {})
            .get(DATA_MODEL_INSIGHT_ENTITIES, {})
        )
        store.pop(self._zone.zone_id, None)

    @callback
    def _on_update(self) -> None:
        """Handle a model update."""
        self.refresh_from_state(write=True)

    @callback
    def refresh_from_state(self, *, write: bool) -> None:
        """Read the latest ZoneState into the diagnostic sensor."""
        state = self._store.get(self._zone.zone_id)
        attrs = self._attributes(state)
        self._attr_native_value = self._status(state, attrs["overall_confidence"])
        self._attr_extra_state_attributes = attrs
        if write:
            self.async_write_ha_state()

    def _attributes(self, state) -> dict[str, object]:  # noqa: ANN001 - ZoneState
        """Build the full explainability attribute payload."""
        params = state.model_params if state is not None else None
        confidence = state.model_confidence if state is not None else None
        params = params if isinstance(params, dict) else {}
        confidence = confidence if isinstance(confidence, dict) else {}
        parameter_rows = self._parameter_rows(params, confidence)
        overall = _overall_confidence(confidence)
        days = _finite_float(state.bootstrapped_days) if state is not None else None
        intervals = (
            int(state.bootstrap_intervals)
            if state is not None and state.bootstrap_intervals is not None
            else None
        )
        requested = (
            int(state.bootstrap_requested_days)
            if state is not None and state.bootstrap_requested_days is not None
            else None
        )
        source = (
            state.bootstrap_source
            if state is not None and isinstance(state.bootstrap_source, str)
            else None
        )
        explanation = (
            state.decision_explanation
            if state is not None and isinstance(state.decision_explanation, dict)
            else None
        )
        attrs: dict[str, object] = {
            "zone_id": self._zone.zone_id,
            "parameters": parameter_rows,
            "confidence": {
                key: float(value)
                for key, value in confidence.items()
                if _is_finite_number(value)
            },
            "overall_confidence": overall,
            "bootstrapped_days": days,
            "bootstrap_intervals": intervals,
            "bootstrap_requested_days": requested,
            "bootstrap_source": source,
            "bootstrap_summary": _bootstrap_summary(days, intervals, requested, source),
            "decision_explanation": explanation,
            "water_balance_terms": _dict_attr(explanation, "terms"),
            "predicted_trajectory": _list_attr(explanation, "predicted_trajectory"),
            "horizon_hours": _number_attr(explanation, "horizon_hours"),
            "chosen_liters": _number_attr(explanation, "chosen_liters"),
            "predicted_critical_theta": _predicted_critical_theta(explanation),
            "predicted_peak_theta": _number_attr(explanation, "predicted_peak_theta"),
            "model_updated": None if state is None else state.model_updated,
            "total_liters": 0.0 if state is None else round(state.total_liters, 3),
        }
        return attrs

    def _parameter_rows(
        self, params: dict[str, object], confidence: dict[str, object]
    ) -> dict[str, dict[str, object]]:
        """Return friendly parameter metadata and values keyed by model code."""
        rows: dict[str, dict[str, object]] = {}
        for descriptor in MODEL_PARAMETER_DESCRIPTORS:
            value = _finite_float(params.get(descriptor.key))
            conf = _finite_float(confidence.get(descriptor.key))
            rows[descriptor.key] = {
                "name": descriptor.label,
                "value": None if value is None else round(value, 6),
                "unit": descriptor.unit,
                "confidence": None if conf is None else max(0.0, min(1.0, conf)),
            }
        return rows

    @staticmethod
    def _status(state, overall: float | None) -> str:  # noqa: ANN001 - ZoneState
        """Short state for the sensor row."""
        if state is None:
            return "no model"
        if isinstance(state.model_params, dict) and state.model_params:
            if overall is not None:
                return f"{round(overall * 100)}% confidence"
            return "model available"
        if state.bootstrapped_days is not None:
            return "bootstrapped"
        if state.learning_enabled:
            return "learning"
        return "no model"


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


class DiscoveryStatusSensor(SensorEntity):
    """Reflects a zone's guided Field Capacity Discovery workflow state."""

    _attr_has_entity_name = True
    _attr_name = "Field Capacity Discovery"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:water-percent"
    _attr_options = [
        DISCOVERY_IDLE,
        DISCOVERY_AWAITING_SATURATION,
        DISCOVERY_MONITORING,
        DISCOVERY_COMPLETED,
        DISCOVERY_FAILED,
        DISCOVERY_CANCELLED,
    ]

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, controller: DiscoveryController
    ) -> None:
        """Initialise the discovery status sensor for a zone."""
        self._zone = zone
        self._controller = controller
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_discovery_status"
        self._attr_device_info = _zone_device_info(entry, zone)

    async def async_added_to_hass(self) -> None:
        """Subscribe to the controller's updates."""
        self.async_on_remove(self._controller.add_listener(self._on_update))
        self._refresh()

    @callback
    def _on_update(self) -> None:
        """Handle a controller update."""
        self._refresh()
        self.async_write_ha_state()

    @staticmethod
    def _elapsed_hours(started_at: str | None) -> float | None:
        """Hours since ``started_at`` (ISO string), or ``None``."""
        if not started_at:
            return None
        started = dt_util.parse_datetime(started_at)
        if started is None:
            return None
        return round((dt_util.utcnow() - started).total_seconds() / 3600.0, 2)

    @callback
    def _refresh(self) -> None:
        """Read the controller's discovery state into entity attributes."""
        discovery = self._controller.discovery
        self._attr_native_value = discovery.phase
        self._attr_extra_state_attributes = {
            "zone_id": self._zone.zone_id,
            "instruction": self._controller.instruction,
            "elapsed_hours": self._elapsed_hours(discovery.monitor_started_at),
            "current_moisture": discovery.last_moisture,
            "saturation_peak": discovery.peak_moisture,
            "drainage_rate_pct_per_h": (
                None
                if discovery.drainage_rate is None
                else round(discovery.drainage_rate, 3)
            ),
            "provisional_field_capacity": discovery.provisional_fc,
            "field_capacity": discovery.result_fc,
            "min_wait_hours": DISCOVERY_MIN_WAIT_HOURS,
            "max_wait_hours": DISCOVERY_MAX_WAIT_HOURS,
            "reason": discovery.reason,
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
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        entry: ConfigEntry,
        zone: ZoneConfig,
        learner: ZoneLearner,
        *,
        key: str,
        name: str,
        icon: str,
        unit: str | None,
        attribute: str | None,
        samples_key: str | None,
        dict_attribute: str | None = None,
        dict_key: str | None = None,
        average_dict: bool = False,
        scale: float = 1.0,
    ) -> None:
        """Initialise a learned-value sensor for one parameter of a zone."""
        self._zone = zone
        self._learner = learner
        self._attribute = attribute
        self._samples_key = samples_key
        self._dict_attribute = dict_attribute
        self._dict_key = dict_key
        self._average_dict = average_dict
        self._scale = scale
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
        value = None if state is None else self._read_value(state)
        self._attr_available = value is not None
        self._attr_native_value = None if value is None else round(float(value), 3)
        attributes = {"zone_id": self._zone.zone_id}
        if state is not None and self._samples_key is not None:
            attributes["samples"] = state.learning_state.get(self._samples_key, 0)
        self._attr_extra_state_attributes = attributes

    def _read_value(self, state) -> float | None:  # noqa: ANN001 - ZoneState import cycle
        """Read either a direct ZoneState attribute or a dict-backed model value."""
        if self._dict_attribute is not None:
            source = getattr(state, self._dict_attribute, None)
            if not isinstance(source, dict):
                return None
            if self._average_dict:
                values = [
                    float(value)
                    for value in source.values()
                    if _is_finite_number(value)
                ]
                if not values:
                    return None
                return sum(values) / len(values) * self._scale
            value = source.get(self._dict_key)
        elif self._attribute is not None:
            value = getattr(state, self._attribute)
        else:
            return None
        if not _is_finite_number(value):
            return None
        return float(value) * self._scale


@dataclass(frozen=True)
class _LearnedSensorDescriptor:
    """Static description of one learned-value sensor."""

    key: str
    name: str
    icon: str
    unit: str | None
    attribute: str | None
    samples_key: str | None
    dict_attribute: str | None = None
    dict_key: str | None = None
    average_dict: bool = False
    scale: float = 1.0

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
            dict_attribute=self.dict_attribute,
            dict_key=self.dict_key,
            average_dict=self.average_dict,
            scale=self.scale,
        )


def _is_finite_number(value: object) -> bool:
    """Whether ``value`` can be exposed as a finite numeric sensor state."""
    try:
        return math.isfinite(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def _finite_float(value: object) -> float | None:
    """Return a finite float, or None."""
    if not _is_finite_number(value):
        return None
    return float(value)  # type: ignore[arg-type]


def _overall_confidence(confidence: dict[str, object]) -> float | None:
    """Average finite confidence values."""
    values = [
        max(0.0, min(1.0, float(value)))
        for value in confidence.values()
        if _is_finite_number(value)
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _bootstrap_summary(
    days: float | None,
    intervals: int | None = None,
    requested: int | None = None,
    source: str | None = None,
) -> str | None:
    """Human-readable bootstrap summary for the UI."""
    if days is None:
        return None
    span = f"{days:g} of {requested} requested" if requested else f"{days:g}"
    summary = f"Bootstrapped from {span} days"
    if intervals:
        summary += f" \u00b7 {intervals} intervals"
    if source:
        summary += f" \u00b7 {source}"
    return summary


def _dict_attr(source: dict | None, key: str) -> dict | None:
    """Return a nested dict attribute from a decision explanation."""
    value = source.get(key) if source is not None else None
    return value if isinstance(value, dict) else None


def _list_attr(source: dict | None, key: str) -> list | None:
    """Return a nested list attribute from a decision explanation."""
    value = source.get(key) if source is not None else None
    return value if isinstance(value, list) else None


def _number_attr(source: dict | None, key: str) -> float | None:
    """Return a finite numeric attribute from a decision explanation."""
    value = source.get(key) if source is not None else None
    return _finite_float(value)


def _predicted_critical_theta(explanation: dict | None) -> float | None:
    """Return the most useful predicted critical moisture value."""
    if explanation is None:
        return None
    return _number_attr(
        explanation, "predicted_critical_theta_with_water"
    ) or _number_attr(explanation, "predicted_critical_theta_without_water")


# The learned parameters surfaced as read-only per-zone sensors.
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
    _LearnedSensorDescriptor(
        key="drainage_rate",
        name="Learned Drainage Rate",
        icon="mdi:water-percent",
        unit="1/h",
        attribute=None,
        samples_key=None,
        dict_attribute="model_params",
        dict_key="drain_rate",
    ),
    _LearnedSensorDescriptor(
        key="et_coefficient",
        name="Learned ET Coefficient",
        icon="mdi:weather-sunny",
        unit=None,
        attribute=None,
        samples_key=None,
        dict_attribute="model_params",
        dict_key="k_et",
    ),
    _LearnedSensorDescriptor(
        key="model_confidence",
        name="Model Confidence",
        icon="mdi:gauge",
        unit=PERCENTAGE,
        attribute=None,
        samples_key=None,
        dict_attribute="model_confidence",
        average_dict=True,
        scale=100.0,
    ),
)
