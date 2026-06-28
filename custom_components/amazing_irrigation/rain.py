"""Observed Rain Event watcher feeding Irrigation History.

Forecast rain influences Irrigation Decisions; *observed* rain is independent
evidence used to explain why soil moisture rose without watering (and, later,
to learn rain efficiency). This watcher records a Rain Event whenever a zone's
Observed Rain Amount sensor increases, so the bounded Irrigation History shows
real rainfall alongside Decisions and Watering Events.
"""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .decision import read_number
from .history import IrrigationHistory, ObservationKind
from .zone import ZoneConfig


class RainWatcher:
    """Records a Rain Event when a zone's Observed Rain Amount rises."""

    def __init__(
        self, hass: HomeAssistant, entity_id: str, history: IrrigationHistory
    ) -> None:
        """Initialise the watcher for one zone's observed-rain sensor."""
        self.hass = hass
        self.entity_id = entity_id
        self.history = history
        self._baseline: float | None = read_number(hass, entity_id)
        self._unsub: Callable[[], None] | None = None

    def async_start(self) -> None:
        """Begin tracking the observed-rain sensor."""
        if self._unsub is None:
            self._unsub = async_track_state_change_event(
                self.hass, [self.entity_id], self._handle_change
            )

    def async_stop(self) -> None:
        """Stop tracking the observed-rain sensor."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_change(self, event: Event) -> None:
        """Record a Rain Event when the observed amount increases."""
        current = read_number(self.hass, self.entity_id)
        if current is None:
            return
        # A reset to a lower value (e.g. a daily counter rollover) just rebases.
        if self._baseline is None or current < self._baseline:
            self._baseline = current
            return
        if current > self._baseline:
            self.history.record(
                ObservationKind.RAIN_EVENT,
                {
                    "observed_rain_amount": round(current, 2),
                    "delta_mm": round(current - self._baseline, 2),
                },
            )
            self._baseline = current


def build_rain_watchers(
    hass: HomeAssistant,
    zones: dict[str, dict],
    histories: dict[str, IrrigationHistory],
) -> list[RainWatcher]:
    """Create a RainWatcher for each zone with an Observed Rain Amount sensor."""
    watchers: list[RainWatcher] = []
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        history = histories.get(zone_id)
        if zone.observed_rain_amount and history is not None:
            watchers.append(
                RainWatcher(hass, zone.observed_rain_amount, history)
            )
    return watchers
