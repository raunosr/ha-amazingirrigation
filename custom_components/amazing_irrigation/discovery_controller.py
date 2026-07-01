"""Home Assistant orchestration for guided Field Capacity Discovery.

One :class:`DiscoveryController` per zone drives the workflow state machine:

``idle → awaiting_saturation → monitoring → completed | failed | cancelled``

The user starts discovery, is instructed to saturate the moisture sensor and
cover the soil, then confirms. While monitoring, a periodic timer samples the
moisture sensor and feeds the drainage curve to the Home-Assistant-free
:func:`discovery.evaluate_discovery`, which decides when to record Field Capacity
(the Drained Upper Limit) or abort. On success the measured FC is anchored into
the zone's learned model in sensor-% via the :class:`learner.ZoneLearner`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    DISCOVERY_AWAITING_SATURATION,
    DISCOVERY_CANCELLED,
    DISCOVERY_COMPLETED,
    DISCOVERY_FAILED,
    DISCOVERY_MONITORING,
    DISCOVERY_SAMPLE_INTERVAL,
    DOMAIN,
)
from .decision import read_number
from .discovery import (
    OUTCOME_ABORT,
    OUTCOME_RECORD,
    DiscoveryConfig,
    DiscoverySample,
    DiscoveryState,
    evaluate_discovery,
    instruction_for_phase,
)
from .learner import ZoneLearner
from .state import ZoneState, ZoneStateStore
from .zone import ZoneConfig, aggregate_zone_moisture

_LOGGER = logging.getLogger(__name__)


class DiscoveryController:
    """Runs the guided Field Capacity Discovery workflow for one zone."""

    def __init__(
        self,
        hass: HomeAssistant,
        zone: ZoneConfig,
        store: ZoneStateStore,
        learner: ZoneLearner | None,
        *,
        config: DiscoveryConfig | None = None,
    ) -> None:
        """Initialise the discovery controller for a zone."""
        self.hass = hass
        self.zone = zone
        self._store = store
        self._learner = learner
        self._config = config or DiscoveryConfig()
        self._samples: list[DiscoverySample] = []
        self._unsub: Callable[[], None] | None = None
        self._listeners: list[Callable[[], None]] = []

    # -- wiring ------------------------------------------------------------

    def async_start(self) -> None:
        """Resume monitoring if a persisted session was mid-drainage."""
        discovery = self._discovery()
        if discovery.phase == DISCOVERY_MONITORING:
            self._seed_current_sample()
            self._start_timer()

    def async_shutdown(self) -> None:
        """Stop the sampler without changing persisted phase (for unload)."""
        self._stop_timer()

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an update callback; returns an unsubscribe handle."""
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    # -- state helpers -----------------------------------------------------

    @property
    def state(self) -> ZoneState | None:
        """The zone's live ZoneState, or ``None`` when unknown."""
        return self._store.get(self.zone.zone_id)

    def _discovery(self) -> DiscoveryState:
        """Return the persisted DiscoveryState (defaulting to idle)."""
        state = self.state
        if state is None:
            return DiscoveryState()
        return DiscoveryState.from_dict(state.discovery)

    @property
    def discovery(self) -> DiscoveryState:
        """Public view of the current DiscoveryState for entities."""
        return self._discovery()

    @property
    def instruction(self) -> str:
        """Human-readable instruction for the current phase."""
        return instruction_for_phase(self._discovery().phase)

    def _save(self, discovery: DiscoveryState) -> None:
        """Persist a DiscoveryState onto the ZoneState and notify listeners."""
        state = self.state
        if state is None:
            return
        discovery.updated_at = dt_util.utcnow().isoformat()
        state.discovery = discovery.to_dict()
        for listener in list(self._listeners):
            listener()
        self.hass.async_create_task(self._store.async_save())

    def _notify(self, discovery: DiscoveryState, *, title_suffix: str) -> None:
        """Raise a persistent notification describing the current phase."""
        message = instruction_for_phase(discovery.phase)
        if discovery.reason:
            message = f"{message}\n\n{discovery.reason}"
        if discovery.result_fc is not None:
            message = f"{message}\n\nField Capacity: {discovery.result_fc:.1f}%"
        persistent_notification.async_create(
            self.hass,
            message,
            title=f"{self.zone.name}: Field Capacity Discovery — {title_suffix}",
            notification_id=f"{DOMAIN}_discovery_{self.zone.zone_id}",
        )

    # -- moisture ----------------------------------------------------------

    def _moisture(self) -> float | None:
        """Current canonical Zone Moisture, or ``None`` when unavailable."""
        readings = [
            read_number(self.hass, entity_id)
            for entity_id in self.zone.moisture_sensors
        ]
        return aggregate_zone_moisture(readings).value

    def _seed_current_sample(self) -> None:
        """Reset the in-memory curve to the current reading (best effort)."""
        self._samples = []
        moisture = self._moisture()
        if moisture is not None:
            self._samples.append(
                DiscoverySample(at=dt_util.utcnow(), moisture=float(moisture))
            )

    # -- timer -------------------------------------------------------------

    def _start_timer(self) -> None:
        """Begin periodic drainage sampling."""
        if self._unsub is None:
            self._unsub = async_track_time_interval(
                self.hass, self._async_sample, DISCOVERY_SAMPLE_INTERVAL
            )

    def _stop_timer(self) -> None:
        """Stop periodic drainage sampling."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    # -- transitions -------------------------------------------------------

    async def async_start_discovery(self) -> None:
        """Begin a new discovery: instruct the user to saturate and cover."""
        if not self.zone.moisture_sensors:
            return
        self._stop_timer()
        self._samples = []
        now = dt_util.utcnow().isoformat()
        discovery = DiscoveryState(
            phase=DISCOVERY_AWAITING_SATURATION,
            started_at=now,
            reason=None,
        )
        self._save(discovery)
        self._notify(discovery, title_suffix="Saturate & cover")

    async def async_confirm_saturated(self) -> None:
        """Confirm the soil is saturated and covered; begin monitoring."""
        discovery = self._discovery()
        if discovery.phase != DISCOVERY_AWAITING_SATURATION:
            return
        self._seed_current_sample()
        moisture = self._samples[-1].moisture if self._samples else None
        discovery = DiscoveryState(
            phase=DISCOVERY_MONITORING,
            started_at=discovery.started_at,
            monitor_started_at=dt_util.utcnow().isoformat(),
            peak_moisture=moisture,
            last_moisture=moisture,
            reason=None,
        )
        self._save(discovery)
        self._notify(discovery, title_suffix="Monitoring")
        self._start_timer()

    async def async_cancel_discovery(self) -> None:
        """Cancel an in-progress discovery."""
        self._stop_timer()
        self._samples = []
        discovery = self._discovery()
        discovery.phase = DISCOVERY_CANCELLED
        discovery.reason = "Cancelled by user"
        self._save(discovery)
        self._notify(discovery, title_suffix="Cancelled")

    # -- monitoring loop ---------------------------------------------------

    @callback
    def _async_sample(self, now) -> None:
        """Timer callback: sample moisture and evaluate the drainage curve."""
        try:
            self._sample_and_evaluate(now)
        except (ArithmeticError, OverflowError, TypeError, ValueError) as err:
            _LOGGER.debug("Discovery sample failed for %s: %s", self.zone.zone_id, err)

    def _sample_and_evaluate(self, now) -> None:
        """Record a sample and act on the resulting decision."""
        discovery = self._discovery()
        if discovery.phase != DISCOVERY_MONITORING:
            self._stop_timer()
            return

        moisture = self._moisture()
        if moisture is not None:
            self._samples.append(DiscoverySample(at=now, moisture=float(moisture)))
            if discovery.peak_moisture is None or moisture > discovery.peak_moisture:
                discovery.peak_moisture = float(moisture)
            discovery.last_moisture = float(moisture)

        decision = evaluate_discovery(self._samples, self._config, now=now)
        discovery.drainage_rate = decision.drainage_rate
        discovery.provisional_fc = decision.provisional_fc

        if decision.outcome == OUTCOME_RECORD and decision.field_capacity is not None:
            self._complete(discovery, decision.field_capacity, decision.reason)
            return
        if decision.outcome == OUTCOME_ABORT:
            self._abort(discovery, decision.reason)
            return
        self._save(discovery)

    def _complete(
        self, discovery: DiscoveryState, field_capacity: float, reason: str
    ) -> None:
        """Record the measured Field Capacity and finish the workflow."""
        self._stop_timer()
        self._samples = []
        applied = field_capacity
        if self._learner is not None:
            state = self._learner.apply_discovered_field_capacity(field_capacity)
            if state is not None and state.field_capacity_override is not None:
                applied = float(state.field_capacity_override)
        discovery.phase = DISCOVERY_COMPLETED
        discovery.result_fc = round(applied, 2)
        discovery.provisional_fc = round(applied, 2)
        discovery.reason = reason
        self._save(discovery)
        self._notify(discovery, title_suffix="Complete")

    def _abort(self, discovery: DiscoveryState, reason: str) -> None:
        """Abort monitoring, preserving the reason for the user."""
        self._stop_timer()
        self._samples = []
        discovery.phase = DISCOVERY_FAILED
        discovery.reason = reason
        self._save(discovery)
        self._notify(discovery, title_suffix="Failed")


def build_discovery_controllers(
    hass: HomeAssistant,
    zones: dict[str, dict],
    store: ZoneStateStore,
    learners: dict[str, ZoneLearner],
) -> dict[str, DiscoveryController]:
    """Create a DiscoveryController for each zone that has moisture sensors."""
    controllers: dict[str, DiscoveryController] = {}
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        if not zone.moisture_sensors:
            continue
        controllers[zone_id] = DiscoveryController(
            hass, zone, store, learners.get(zone_id)
        )
    return controllers
