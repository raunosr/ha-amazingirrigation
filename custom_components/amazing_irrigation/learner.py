"""Live capture of moisture intervals feeding a zone's water-balance model.

One :class:`ZoneLearner` per Irrigation Zone watches moisture sensors and Watering
Events.  Consecutive moisture observations become one joint estimator update with
irrigation, rain, ET climate, and drainage all attributed together by
``JointEstimator``.  The learner only writes the persisted :class:`ZoneState`;
the decision engine consumes the mirrored learned values elsewhere.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import EVENT_WATERING
from .decision import read_number
from .estimator import JointEstimator
from .state import (
    ZoneState,
    ZoneStateStore,
    apply_model_to_state,
    params_from_state,
)
from .waterbalance import Climate, default_params
from .zone import ZoneConfig, aggregate_zone_moisture


class ZoneLearner:
    """Captures bounded water-balance intervals for one zone from live state."""

    def __init__(
        self, hass: HomeAssistant, zone: ZoneConfig, store: ZoneStateStore
    ) -> None:
        """Initialise the learner for one zone."""
        self.hass = hass
        self.zone = zone
        self._store = store
        self._unsub_moisture: Callable[[], None] | None = None
        self._unsub_event: Callable[[], None] | None = None
        self._listeners: list[Callable[[], None]] = []
        self._estimator: JointEstimator | None = None

    @property
    def state(self) -> ZoneState | None:
        """The zone's live ZoneState, or None when unknown."""
        return self._store.get(self.zone.zone_id)

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an update callback; returns an unsubscribe handle."""
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    def async_start(self) -> None:
        """Begin watching moisture sensors and Watering Events."""
        if self.zone.moisture_sensors and self._unsub_moisture is None:
            self._unsub_moisture = async_track_state_change_event(
                self.hass, self.zone.moisture_sensors, self._handle_moisture
            )
        if self._unsub_event is None:
            self._unsub_event = self.hass.bus.async_listen(
                EVENT_WATERING, self._handle_watering
            )
        # Seed the baseline so the first observation has something to compare to.
        state = self.state
        if state is not None:
            self._ensure_estimator(state)
            bookkeeping = dict(state.learning_state)
            bookkeeping.setdefault("last_moisture", self._moisture())
            bookkeeping.setdefault("last_time", dt_util.utcnow().isoformat())
            bookkeeping.setdefault("rain_last", self._observed_rain())
            state.learning_state = bookkeeping

    def async_stop(self) -> None:
        """Stop watching live state."""
        if self._unsub_moisture is not None:
            self._unsub_moisture()
            self._unsub_moisture = None
        if self._unsub_event is not None:
            self._unsub_event()
            self._unsub_event = None

    def _moisture(self) -> float | None:
        """Current canonical Zone Moisture, or None when unavailable."""
        readings = [
            read_number(self.hass, entity_id)
            for entity_id in self.zone.moisture_sensors
        ]
        return aggregate_zone_moisture(readings).value

    def _observed_rain(self) -> float | None:
        """Current Observed Rain Amount, or None when not configured."""
        return read_number(self.hass, self.zone.observed_rain_amount)

    def _climate(self) -> Climate | None:
        """Current ET climate inputs for the estimator, if any are available."""
        prefer_greenhouse = (
            self.zone.et_source == "greenhouse"
            or (self.zone.et_source == "auto" and self.zone.greenhouse)
        )
        if prefer_greenhouse:
            temperature_entity = (
                self.zone.temperature_sensor or self.zone.observed_air_temperature
            )
            humidity_entity = self.zone.humidity_sensor or self.zone.observed_air_humidity
        else:
            temperature_entity = self.zone.observed_air_temperature
            humidity_entity = self.zone.observed_air_humidity
        climate = Climate(
            air_temp_c=read_number(self.hass, temperature_entity),
            air_humidity_pct=read_number(self.hass, humidity_entity),
            wind_ms=read_number(self.hass, self.zone.wind_speed),
            solar=read_number(self.hass, self.zone.solar_radiation),
        )
        if (
            climate.air_temp_c is None
            and climate.air_humidity_pct is None
            and climate.wind_ms is None
            and climate.solar is None
        ):
            return None
        return climate

    def _ensure_estimator(self, state: ZoneState) -> JointEstimator:
        """Create the per-zone estimator from persisted params/covariance."""
        if self._estimator is None:
            prior = params_from_state(
                state,
                soil_type=self.zone.soil_type,
                area_m2=self.zone.area_m2,
                root_depth_mm=self.zone.root_depth_mm,
                demand_profile=self.zone.demand_profile,
            ) or default_params(
                self.zone.soil_type,
                area_m2=self.zone.area_m2,
                root_depth_mm=self.zone.root_depth_mm,
                demand_profile=self.zone.demand_profile,
            )
            self._estimator = JointEstimator(
                prior_params=prior,
                prior_cov=state.model_covariance,
            )
        self._apply_overrides(self._estimator)
        return self._estimator

    def _apply_overrides(self, estimator: JointEstimator) -> None:
        """Apply manual zone settings that must always win over learning.

        Field-capacity / wilting-point anchors are read from the live ZoneState
        override (set via the device number, Discovery or the config flow) so a
        runtime edit re-anchors the estimator, falling back to the static config
        value only when no live override is set.
        """
        if self.zone.gain_per_liter is not None:
            estimator.set_override("eta_irr", self.zone.gain_per_liter)
        field_capacity = self._anchor("field_capacity_override", self.zone.field_capacity)
        if field_capacity is not None:
            estimator.set_override("field_capacity", field_capacity)
        wilting_point = self._anchor("wilting_point_override", self.zone.wilting_point)
        if wilting_point is not None:
            estimator.set_override("wilting_point", wilting_point)

    def _anchor(self, attr: str, config_value: float | None) -> float | None:
        """Return the live positive override for ``attr`` else the config value."""
        state = self.state
        if state is not None:
            override = self._finite(getattr(state, attr, None))
            if override is not None and override > 0.0:
                return override
        return config_value

    @staticmethod
    def _finite(value: object) -> float | None:
        """Return a finite float, or ``None``."""
        try:
            result = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        return result if math.isfinite(result) else None

    @staticmethod
    def _count(bookkeeping: dict, key: str) -> int:
        """Read a non-negative sample counter from bookkeeping."""
        try:
            return max(0, int(bookkeeping.get(key, 0)))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _hours_between(last_time: object, now) -> float | None:
        """Return interval length in hours, or ``None`` when invalid."""
        if not last_time:
            return None
        previous = dt_util.parse_datetime(str(last_time))
        if previous is None:
            return None
        hours = (now - previous).total_seconds() / 3600.0
        return hours if math.isfinite(hours) and hours > 0.0 else None

    def apply_discovered_field_capacity(self, field_capacity: float) -> ZoneState | None:
        """Anchor FC from a guided-discovery drainage measurement, then persist.

        Writes the measured Drained Upper Limit as the zone's trusted manual
        ``field_capacity_override`` so it survives further learning, seeds the
        live estimator's moisture-envelope high to the same value, and mirrors
        the updated model into the persisted ZoneState. Returns the updated
        state, or ``None`` when unavailable.
        """
        state = self.state
        if state is None:
            return None
        state.field_capacity_override = field_capacity
        estimator = self._ensure_estimator(state)
        estimator.seed_field_capacity(field_capacity)
        self._persist_model(state, dt_util.utcnow().isoformat())
        return state

    def _persist_model(self, state: ZoneState, updated: str) -> None:
        """Mirror estimator output into ZoneState and schedule persistence."""
        if self._estimator is None:
            return
        apply_model_to_state(
            state,
            self._estimator.params,
            self._estimator.confidence,
            covariance=self._estimator.covariance.tolist(),
            updated=updated,
        )
        for listener in list(self._listeners):
            listener()
        self.hass.async_create_task(self._store.async_save())

    @callback
    def _handle_watering(self, event: Event) -> None:
        """Capture before-moisture and litres around a Watering Event."""
        try:
            if event.data.get("zone_id") != self.zone.zone_id:
                return
            state = self.state
            if state is None:
                return
            bookkeeping = dict(state.learning_state)
            status = event.data.get("status")
            if status == "commanded":
                bookkeeping["pending_before"] = self._moisture()
            elif status == "confirmed":
                measured = event.data.get("measured_liters")
                requested = event.data.get("requested_liters")
                liters = self._finite(measured if measured is not None else requested)
                if liters is not None and liters > 0.0:
                    current = self._finite(bookkeeping.get("pending_liters")) or 0.0
                    bookkeeping["pending_liters"] = current + liters
            state.learning_state = bookkeeping
        except (ArithmeticError, OverflowError, TypeError, ValueError):
            return

    @callback
    def _handle_moisture(self, event: Event) -> None:
        """Turn a moisture observation into one joint estimator interval."""
        try:
            self._handle_moisture_safe()
        except (ArithmeticError, OverflowError, TypeError, ValueError):
            return

    def _handle_moisture_safe(self) -> None:
        """Implementation of moisture handling with callback-safe callers."""
        state = self.state
        if state is None:
            return
        moisture = self._finite(self._moisture())
        now = dt_util.utcnow()
        bookkeeping = dict(state.learning_state)
        estimator = self._ensure_estimator(state)

        last_moisture = self._finite(bookkeeping.get("last_moisture"))
        hours = self._hours_between(bookkeeping.get("last_time"), now)
        liters = self._finite(bookkeeping.get("pending_liters")) or 0.0
        rain_now = self._finite(self._observed_rain())
        rain_last = self._finite(bookkeeping.get("rain_last"))
        rain_mm = (
            max(0.0, rain_now - rain_last)
            if rain_now is not None and rain_last is not None
            else 0.0
        )

        ran_update = False
        if (
            state.learning_enabled
            and moisture is not None
            and last_moisture is not None
            and hours is not None
        ):
            estimator.update(
                theta_start=last_moisture,
                theta_end=moisture,
                dt=hours,
                liters=liters,
                rain_mm=rain_mm,
                climate=self._climate(),
                protected_rain=self.zone.protected_rain,
            )
            ran_update = True
            if liters > 0.0:
                bookkeeping["gain_samples"] = self._count(
                    bookkeeping, "gain_samples"
                ) + 1
            if rain_mm > 0.0 and not self.zone.protected_rain:
                bookkeeping["rain_samples"] = self._count(
                    bookkeeping, "rain_samples"
                ) + 1
            bookkeeping["drying_samples"] = self._count(
                bookkeeping, "drying_samples"
            ) + 1

        if moisture is not None and not ran_update:
            estimator.observe_moisture(moisture, dt_hours=hours or 0.0)
        if moisture is not None:
            bookkeeping["capacity_samples"] = self._count(
                bookkeeping, "capacity_samples"
            ) + 1

        if moisture is not None:
            bookkeeping["last_moisture"] = moisture
        bookkeeping["last_time"] = now.isoformat()
        bookkeeping["rain_last"] = rain_now
        bookkeeping.pop("pending_before", None)
        bookkeeping.pop("pending_liters", None)
        state.learning_state = bookkeeping
        self._persist_model(state, now.isoformat())


def build_learners(
    hass: HomeAssistant, zones: dict[str, dict], store: ZoneStateStore
) -> dict[str, ZoneLearner]:
    """Create a ZoneLearner for each configured zone."""
    learners: dict[str, ZoneLearner] = {}
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        learners[zone_id] = ZoneLearner(hass, zone, store)
    return learners
