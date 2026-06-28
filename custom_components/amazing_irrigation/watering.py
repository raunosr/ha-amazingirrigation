"""Watering controller: turn an Irrigation Decision into a Watering Event.

The controller bounds the requested Watering Volume by the zone's safety limit
*before* any actuator call, executes the generic actuator, and tracks whether
the command became a Confirmed Watering Event. Command success alone is never
treated as confirmed flow — confirmation requires configured feedback (a
watering binary sensor turning on, or a cumulative volume sensor increasing).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .actuator import (
    ActuatorConfig,
    async_execute_all,
    build_start_calls,
    build_stop_calls,
)
from .const import EVENT_WATERING
from .decision import evaluate_zone, read_number
from .engine import Decision
from .history import IrrigationHistory, ObservationKind
from .state import ZoneStateStore
from .zone import ZoneConfig


class WateringStatus(StrEnum):
    """Lifecycle of a Watering Event."""

    IDLE = "idle"
    SKIPPED = "skipped"
    NO_ACTUATOR = "no_actuator"
    COMMANDED = "commanded"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class WateringEvent:
    """The outcome of a Run Request that reached the actuator stage."""

    status: WateringStatus
    requested_liters: float = 0.0
    measured_liters: float | None = None
    reason: str | None = None
    timestamp: str = field(default_factory=lambda: dt_util.utcnow().isoformat())

    @property
    def confirmed(self) -> bool:
        """Whether this event represents confirmed water flow."""
        return self.status is WateringStatus.CONFIRMED


def bound_volume(requested_liters: float, max_liters: float) -> float:
    """Clamp a requested Watering Volume to the zone's safety limits."""
    return max(0.0, min(requested_liters, max_liters))


class WateringController:
    """Owns a single zone's Watering Events and actuator interaction."""

    def __init__(
        self,
        hass: HomeAssistant,
        zone: ZoneConfig,
        actuator: ActuatorConfig,
        history: IrrigationHistory | None = None,
        zone_state_store: ZoneStateStore | None = None,
    ) -> None:
        """Initialise the controller for one zone."""
        self.hass = hass
        self.zone = zone
        self.actuator = actuator
        self.history = history
        self._zone_state_store = zone_state_store
        self.last_event = WateringEvent(WateringStatus.IDLE)
        self._listeners: list[Callable[[], None]] = []
        self._active = False
        self._confirmed_once = False
        self._unsub: Callable[[], None] | None = None
        self._volume_baseline: float | None = None
        # Liters already added to the zone's Total Watering Volume for the
        # current Watering Event, so a single event is never counted twice.
        self._accounted_liters = 0.0

    @property
    def zone_state(self):  # noqa: ANN201 - ZoneState | None, avoid import cycle in hint
        """The zone's live ZoneState, or None when no store is wired."""
        if self._zone_state_store is None:
            return None
        return self._zone_state_store.get(self.zone.zone_id)

    @property
    def is_watering(self) -> bool:
        """Whether the zone is currently watering."""
        return self._active

    @property
    def can_stop(self) -> bool:
        """Whether an explicit stop path exists for this zone."""
        return self.actuator.can_stop

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an entity update callback; returns an unsubscribe handle."""
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    @callback
    def _set_event(self, event: WateringEvent) -> None:
        """Store the latest event, notify listeners, and fire a bus event."""
        self.last_event = event
        for listener in list(self._listeners):
            listener()
        self.hass.bus.async_fire(
            EVENT_WATERING,
            {
                "zone_id": self.zone.zone_id,
                "status": event.status.value,
                "requested_liters": event.requested_liters,
                "measured_liters": event.measured_liters,
                "confirmed": event.confirmed,
                "reason": event.reason,
            },
        )
        # Skipped Run Requests are recorded as Decisions, not Watering Events.
        if self.history is not None and event.status is not WateringStatus.SKIPPED:
            self.history.record(
                ObservationKind.WATERING_EVENT,
                {
                    "status": event.status.value,
                    "requested_liters": round(event.requested_liters, 2),
                    "measured_liters": (
                        None
                        if event.measured_liters is None
                        else round(event.measured_liters, 2)
                    ),
                    "confirmed": event.confirmed,
                    "reason": event.reason,
                },
            )

    @callback
    def _record_decision(
        self, decision: Decision, *, force: bool, zone_locked: bool
    ) -> None:
        """Capture a Run Request and its Irrigation Decision in history."""
        if self.history is None:
            return
        self.history.record(
            ObservationKind.RUN_REQUEST, {"force": force, "zone_locked": zone_locked}
        )
        self.history.record(
            ObservationKind.DECISION,
            {
                "action": decision.action.value,
                "reason": decision.reason.value,
                "recommended_liters": round(decision.recommended_liters, 2),
                "degraded": decision.degraded,
            },
        )

    @callback
    def _account_volume(self, event_total: float) -> None:
        """Add this event's water to the zone's cumulative Total Watering Volume.

        ``event_total`` is the best-known total liters applied for the *current*
        Watering Event. Only the delta beyond what has already been counted for
        this event is added, so repeated confirmation/finalisation callbacks
        never double-count, while a volume sensor revealing a larger final delta
        still tops the total up.
        """
        state = self.zone_state
        if state is None:
            return
        delta = event_total - self._accounted_liters
        if delta <= 0:
            return
        self._accounted_liters = event_total
        state.total_liters = round(state.total_liters + delta, 3)
        # Notify listeners so the Total Watering Volume sensors pick up the new
        # cumulative value (accounting runs after the event is set).
        for listener in list(self._listeners):
            listener()
        if self._zone_state_store is not None:
            self.hass.async_create_task(self._zone_state_store.async_save())

    @callback
    def _event_volume(self) -> float:
        """Best-known liters applied for the current event (measured or requested)."""
        if self.last_event.measured_liters is not None:
            return self.last_event.measured_liters
        return self.last_event.requested_liters

    async def async_run(
        self, *, force: bool = False, zone_locked: bool = False
    ) -> WateringEvent:
        """Evaluate a Run Request and, if it would water, actuate it."""
        # Skip overlapping Run Requests for a zone that is already watering;
        # never re-actuate or re-subscribe while a Watering Event is live.
        if self._active:
            return WateringEvent(
                WateringStatus.COMMANDED,
                requested_liters=self.last_event.requested_liters,
                measured_liters=self.last_event.measured_liters,
                reason="already_watering",
            )

        decision: Decision = evaluate_zone(
            self.hass,
            self.zone,
            force=force,
            zone_locked=zone_locked,
            state=self.zone_state,
        )
        self._record_decision(decision, force=force, zone_locked=zone_locked)

        if not decision.will_water:
            event = WateringEvent(
                WateringStatus.SKIPPED, reason=decision.reason.value
            )
            self._set_event(event)
            return event

        # Bound the Watering Volume by safety limits BEFORE any actuator call.
        volume = bound_volume(decision.recommended_liters, self.zone.max_liters)

        start_call = build_start_calls(self.actuator, volume)
        if not start_call:
            event = WateringEvent(
                WateringStatus.NO_ACTUATOR, requested_liters=volume
            )
            self._set_event(event)
            return event

        if self.actuator.volume_sensor:
            self._volume_baseline = read_number(self.hass, self.actuator.volume_sensor)

        try:
            await async_execute_all(self.hass, start_call)
        except Exception as err:  # noqa: BLE001 - record any actuator failure
            event = WateringEvent(
                WateringStatus.FAILED, requested_liters=volume, reason=str(err)
            )
            self._set_event(event)
            return event

        self._active = True
        self._confirmed_once = False
        self._accounted_liters = 0.0
        # Command succeeded: COMMANDED, not yet confirmed. Subscribe to feedback.
        event = WateringEvent(WateringStatus.COMMANDED, requested_liters=volume)
        self._set_event(event)
        self._subscribe_feedback()
        self._check_confirmation()
        return self.last_event

    def _subscribe_feedback(self) -> None:
        """Watch confirmation feedback entities while watering."""
        tracked = [
            entity_id
            for entity_id in (
                self.actuator.watering_sensor,
                self.actuator.volume_sensor,
            )
            if entity_id
        ]
        if tracked:
            if self._unsub is not None:
                self._unsub()
                self._unsub = None
            self._unsub = async_track_state_change_event(
                self.hass, tracked, self._handle_feedback
            )

    @callback
    def _handle_feedback(self, event: Event) -> None:
        """React to confirmation feedback changes."""
        # A watering binary sensor reading "off" only means the Watering Event
        # finished if it was previously confirmed "on"; before confirmation it
        # is simply the pre-flow state and must not finalize a just-started run.
        if self.actuator.watering_sensor and self._confirmed_once:
            changed = event.data.get("entity_id")
            if changed == self.actuator.watering_sensor:
                state = self.hass.states.get(self.actuator.watering_sensor)
                if state is not None and state.state == "off" and self._active:
                    self._finalize()
                    return
        self._check_confirmation()

    @callback
    def _check_confirmation(self) -> None:
        """Promote COMMANDED to CONFIRMED when feedback shows real flow."""
        if not self._active or self.last_event.status is WateringStatus.CONFIRMED:
            return

        confirmed = False
        measured = self.last_event.measured_liters

        if self.actuator.watering_sensor:
            state = self.hass.states.get(self.actuator.watering_sensor)
            if state is not None and state.state == "on":
                confirmed = True

        if self.actuator.volume_sensor and self._volume_baseline is not None:
            current = read_number(self.hass, self.actuator.volume_sensor)
            if current is not None and current > self._volume_baseline:
                confirmed = True
                measured = current - self._volume_baseline

        if confirmed:
            self._confirmed_once = True
            self._set_event(
                WateringEvent(
                    WateringStatus.CONFIRMED,
                    requested_liters=self.last_event.requested_liters,
                    measured_liters=measured,
                )
            )
            self._account_volume(self._event_volume())

    @callback
    def _finalize(self) -> None:
        """Mark the active watering as finished (keeps confirmed status)."""
        measured = self.last_event.measured_liters
        if self.actuator.volume_sensor and self._volume_baseline is not None:
            current = read_number(self.hass, self.actuator.volume_sensor)
            if current is not None:
                measured = max(0.0, current - self._volume_baseline)
        was_confirmed = self._confirmed_once
        self._teardown()
        self._set_event(
            WateringEvent(
                self.last_event.status,
                requested_liters=self.last_event.requested_liters,
                measured_liters=measured,
            )
        )
        # Top up the cumulative total with any volume the sensor revealed after
        # the initial confirmation. Only confirmed flow contributes.
        if was_confirmed:
            self._account_volume(self._event_volume())

    def _teardown(self) -> None:
        """Stop tracking feedback."""
        self._active = False
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    def teardown(self) -> None:
        """Release any live feedback subscription (entry unload/reload)."""
        self._teardown()

    async def async_stop(self) -> WateringEvent:
        """Stop watering if a stop path is configured."""
        stop_call = build_stop_calls(self.actuator)
        if not stop_call:
            return self.last_event

        measured = self.last_event.measured_liters
        if self.actuator.volume_sensor and self._volume_baseline is not None:
            current = read_number(self.hass, self.actuator.volume_sensor)
            if current is not None:
                measured = max(0.0, current - self._volume_baseline)
        was_confirmed = self._confirmed_once

        try:
            await async_execute_all(self.hass, stop_call)
        except Exception as err:  # noqa: BLE001 - record any actuator failure
            event = WateringEvent(
                WateringStatus.FAILED,
                requested_liters=self.last_event.requested_liters,
                reason=str(err),
            )
            self._set_event(event)
            return event

        self._teardown()
        event = WateringEvent(
            WateringStatus.STOPPED,
            requested_liters=self.last_event.requested_liters,
            measured_liters=measured,
        )
        self._set_event(event)
        if was_confirmed:
            self._account_volume(self._event_volume())
        return event


def build_controllers(
    hass: HomeAssistant,
    zones: dict[str, dict],
    histories: dict[str, IrrigationHistory] | None = None,
    zone_state_store: ZoneStateStore | None = None,
) -> dict[str, WateringController]:
    """Create a WateringController for each configured zone."""
    histories = histories or {}
    controllers: dict[str, WateringController] = {}
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        actuator = ActuatorConfig.from_record(record)
        controllers[zone_id] = WateringController(
            hass, zone, actuator, histories.get(zone_id), zone_state_store
        )
    return controllers


# Re-exported for convenience.
__all__ = [
    "WateringController",
    "WateringEvent",
    "WateringStatus",
    "bound_volume",
    "build_controllers",
]
