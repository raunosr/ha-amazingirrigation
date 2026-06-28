"""Live capture of learning samples feeding a zone's Learned Model.

This is the Home-Assistant-aware glue around the pure :mod:`learning` maths. One
:class:`ZoneLearner` per Irrigation Zone watches the zone's moisture sensors and
listens for Watering Events, turning what it sees into bounded learning samples:

- a Confirmed Watering Event captures the moisture *before* watering and the
  litres applied; the next moisture observation provides the *after* value, which
  yields a **Moisture Gain per Liter** sample;
- a rise in Observed Rain between observations yields a **Rain Efficiency** sample;
- an unexplained moisture decline over time yields a **Daily Drying Rate** sample;
- every observation nudges the bounded **Field Capacity** / **Wilting Point**
  envelope.

The learner only ever writes the persisted :class:`ZoneState`; the decision engine
consumes the learned values (bounded, manual override winning) elsewhere. All
arithmetic lives in :mod:`learning` so it can be unit-tested without Home
Assistant.
"""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import EVENT_WATERING
from .decision import read_number
from .learning import (
    update_capacity,
    update_drying,
    update_gain,
    update_rain_efficiency,
)
from .state import ZoneStateStore
from .zone import ZoneConfig, aggregate_zone_moisture


class ZoneLearner:
    """Captures bounded learning samples for one zone from live state."""

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

    @property
    def state(self):  # noqa: ANN201 - ZoneState | None, avoid an import cycle
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

    @callback
    def _handle_watering(self, event: Event) -> None:
        """Capture before-moisture and litres around a Watering Event."""
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
            liters = measured if measured is not None else requested
            bookkeeping["pending_liters"] = liters
        state.learning_state = bookkeeping

    @callback
    def _handle_moisture(self, event: Event) -> None:
        """Turn a moisture observation into the appropriate learning sample."""
        state = self.state
        if state is None:
            return
        moisture = self._moisture()
        now = dt_util.utcnow()
        bookkeeping = dict(state.learning_state)

        # Field Capacity / Wilting Point envelope updates on every observation.
        fc, wp, bookkeeping = update_capacity(
            state.learned_field_capacity,
            state.learned_wilting_point,
            bookkeeping,
            moisture,
        )
        state.learned_field_capacity = fc
        state.learned_wilting_point = wp

        pending_before = bookkeeping.get("pending_before")
        pending_liters = bookkeeping.get("pending_liters")
        rain_now = self._observed_rain()
        rain_last = bookkeeping.get("rain_last")
        last_moisture = bookkeeping.get("last_moisture")
        last_time = bookkeeping.get("last_time")

        if pending_before is not None and pending_liters is not None:
            # The moisture rise since watering started attributes to that volume.
            gain, bookkeeping = update_gain(
                state.learned_gain_per_liter,
                bookkeeping,
                pending_before,
                moisture,
                pending_liters,
            )
            state.learned_gain_per_liter = gain
            bookkeeping.pop("pending_before", None)
            bookkeeping.pop("pending_liters", None)
        elif (
            rain_now is not None
            and rain_last is not None
            and rain_now > rain_last
            and last_moisture is not None
        ):
            eff, bookkeeping = update_rain_efficiency(
                state.learned_rain_efficiency,
                bookkeeping,
                last_moisture,
                moisture,
                rain_now - rain_last,
            )
            state.learned_rain_efficiency = eff
        elif last_moisture is not None and last_time:
            previous = dt_util.parse_datetime(last_time)
            if previous is not None:
                hours = (now - previous).total_seconds() / 3600.0
                rate, bookkeeping = update_drying(
                    state.learned_drying_rate,
                    bookkeeping,
                    last_moisture,
                    moisture,
                    hours,
                )
                state.learned_drying_rate = rate

        bookkeeping["last_moisture"] = moisture
        bookkeeping["last_time"] = now.isoformat()
        bookkeeping["rain_last"] = rain_now
        state.learning_state = bookkeeping

        for listener in list(self._listeners):
            listener()
        self.hass.async_create_task(self._store.async_save())


def build_learners(
    hass: HomeAssistant, zones: dict[str, dict], store: ZoneStateStore
) -> dict[str, ZoneLearner]:
    """Create a ZoneLearner for each configured zone."""
    learners: dict[str, ZoneLearner] = {}
    for zone_id, record in zones.items():
        zone = ZoneConfig.from_record(zone_id, record)
        learners[zone_id] = ZoneLearner(hass, zone, store)
    return learners
