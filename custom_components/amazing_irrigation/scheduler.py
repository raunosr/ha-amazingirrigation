"""Built-in per-zone scheduling that creates Run Requests.

The scheduler is deliberately thin: it only decides *when* to create a Run
Request for a zone. It never owns the skip/reduce/water outcome — that always
stays with the Irrigation Decision engine via ``WateringController.async_run``.

A zone schedule has enabled weekdays and one or more ``HH:MM`` start times. A
zone with no start times is never scheduled (manual/Force runs still work). An
empty weekday set means "every day". Disabled zones and out-of-season zones are
filtered here, but the decision engine independently reports the matching skip
reason if such a zone is run by any other path.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from .const import (
    CONF_ZONES,
    WEEKDAYS,
)
from .state import ZoneStateStore
from .watering import WateringController
from .zone import ZoneConfig


def parse_weekdays(values: list[str] | None) -> set[int]:
    """Parse weekday tokens (``mon``..``sun``) into indices (Monday = 0).

    An empty or missing list means every weekday is enabled.
    """
    if not values:
        return set(range(7))
    out: set[int] = set()
    for value in values:
        token = str(value).strip().lower()[:3]
        if token in WEEKDAYS:
            out.add(WEEKDAYS.index(token))
    return out


def parse_times(values: list[str] | None) -> list[tuple[int, int]]:
    """Parse ``HH:MM`` start times into sorted, de-duplicated (hour, minute)."""
    times: set[tuple[int, int]] = set()
    for value in values or []:
        parts = str(value).strip().split(":")
        if len(parts) < 2:
            continue
        try:
            hour, minute = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            times.add((hour, minute))
    return sorted(times)


@dataclass(frozen=True)
class ZoneSchedule:
    """A single zone's parsed schedule.

    ``weekdays`` always comes from the config-entry options. ``enabled`` and
    ``times`` here are the *seed* values from options; at fire time the scheduler
    prefers the live :class:`ZoneState` (the source of truth for the two
    independently toggleable schedule slots and the zone-enabled switch).
    """

    zone_id: str
    enabled: bool
    weekdays: set[int]
    times: list[tuple[int, int]]

    @classmethod
    def from_zone(cls, zone: ZoneConfig) -> ZoneSchedule:
        """Build a ZoneSchedule from a ZoneConfig."""
        return cls(
            zone_id=zone.zone_id,
            enabled=zone.enabled,
            weekdays=parse_weekdays(zone.schedule_weekdays),
            times=parse_times(zone.schedule_times),
        )

    def weekday_allowed(self, weekday: int) -> bool:
        """Whether this schedule may run on the given weekday."""
        return weekday in self.weekdays

    def is_due(
        self,
        weekday: int,
        hour: int,
        minute: int,
        *,
        enabled: bool | None = None,
        times: list[tuple[int, int]] | None = None,
    ) -> bool:
        """Whether this schedule should create a Run Request at this moment.

        ``enabled`` and ``times`` override the seeded values when the live
        ZoneState is available, so slot toggles and time edits take effect
        without a config-entry reload.
        """
        effective_enabled = self.enabled if enabled is None else enabled
        effective_times = self.times if times is None else times
        if not effective_enabled or not effective_times:
            return False
        if weekday not in self.weekdays:
            return False
        return (hour, minute) in effective_times


def another_zone_watering(
    controllers: dict[str, WateringController], current_zone_id: str
) -> bool:
    """Whether any zone other than ``current_zone_id`` is currently watering."""
    return any(
        zone_id != current_zone_id and controller.is_watering
        for zone_id, controller in controllers.items()
    )


class IrrigationScheduler:
    """Fires due zone schedules, creating Run Requests via controllers."""

    def __init__(
        self,
        hass: HomeAssistant,
        controllers: dict[str, WateringController],
        zones: dict[str, dict],
        zone_state_store: ZoneStateStore | None = None,
    ) -> None:
        """Initialise the scheduler from stored zone records."""
        self.hass = hass
        self.controllers = controllers
        self._zone_state_store = zone_state_store
        self.schedules = [
            ZoneSchedule.from_zone(ZoneConfig.from_record(zone_id, record))
            for zone_id, record in zones.items()
        ]
        self._unsub: Callable[[], None] | None = None
        self._stopped = False
        self._task = None
        # Tracks the last local date each (zone_id, time) fired so a wall-clock
        # repeat (e.g. DST fall-back) cannot water a zone twice in one day.
        self._last_fired: dict[tuple[str, tuple[int, int]], date] = {}

    def _live_schedule(
        self, schedule: ZoneSchedule
    ) -> tuple[bool, list[tuple[int, int]]]:
        """Resolve a zone's live (enabled, times), preferring its ZoneState."""
        if self._zone_state_store is None:
            return schedule.enabled, schedule.times
        state = self._zone_state_store.get(schedule.zone_id)
        if state is None:
            return schedule.enabled, schedule.times
        return state.enabled, parse_times(state.active_schedule_times())

    def async_start(self) -> None:
        """Begin tracking the minute boundary for due schedules."""
        # With a live ZoneState store a zone may gain active slots after start,
        # so subscribe whenever a store is present rather than only when the
        # seeded config already had times.
        has_seeded_times = any(s.times for s in self.schedules)
        if self._unsub is not None or not (
            has_seeded_times or self._zone_state_store is not None
        ):
            return
        self._stopped = False
        self._unsub = async_track_time_change(
            self.hass, self._handle_time, second=0
        )

    def async_stop(self) -> None:
        """Stop tracking time changes and cancel any in-flight run."""
        self._stopped = True
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        if self._task is not None and not self._task.done():
            self._task.cancel()
            self._task = None

    @callback
    def _handle_time(self, now) -> None:  # noqa: ANN001 - HA passes a datetime
        """Run every zone whose schedule is due at ``now``."""
        if self._stopped:
            return
        self._task = self.hass.async_create_task(self._run_due(now))

    async def _run_due(self, now) -> None:  # noqa: ANN001 - HA datetime
        """Create Run Requests for all due zones, honouring the global lock."""
        if self._stopped:
            return
        today = now.date()
        weekday, hour, minute = now.weekday(), now.hour, now.minute
        for schedule in self.schedules:
            enabled, times = self._live_schedule(schedule)
            if not schedule.is_due(
                weekday, hour, minute, enabled=enabled, times=times
            ):
                continue
            key = (schedule.zone_id, (hour, minute))
            if self._last_fired.get(key) == today:
                continue
            self._last_fired[key] = today
            controller = self.controllers.get(schedule.zone_id)
            if controller is None:
                continue
            if self._stopped:
                return
            zone_locked = another_zone_watering(self.controllers, schedule.zone_id)
            await controller.async_run(zone_locked=zone_locked)


def build_scheduler(
    hass: HomeAssistant,
    controllers: dict[str, WateringController],
    options: dict,
    zone_state_store: ZoneStateStore | None = None,
) -> IrrigationScheduler:
    """Create an IrrigationScheduler from the entry options."""
    return IrrigationScheduler(
        hass, controllers, options.get(CONF_ZONES, {}), zone_state_store
    )
