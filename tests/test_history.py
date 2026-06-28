"""Tests for the bounded Irrigation History store."""

from __future__ import annotations

from custom_components.amazing_irrigation.const import HISTORY_LIMIT
from custom_components.amazing_irrigation.history import (
    IrrigationHistory,
    ObservationKind,
    build_histories,
)


def test_record_appends_and_counts():
    """Recording an Observation grows the history and tracks the last entry."""
    history = IrrigationHistory("zoneabc")
    history.record(ObservationKind.RUN_REQUEST, {"force": True})
    history.record(ObservationKind.DECISION, {"action": "water"})

    assert history.count == 2
    assert history.last is not None
    assert history.last.kind is ObservationKind.DECISION


def test_recent_is_most_recent_first_and_capped():
    """recent() returns newest-first serialised entries, optionally limited."""
    history = IrrigationHistory("zoneabc")
    for index in range(5):
        history.record(ObservationKind.RAIN_EVENT, {"i": index})

    recent = history.recent(limit=3)
    assert [entry["i"] for entry in recent] == [4, 3, 2]
    assert recent[0]["kind"] == ObservationKind.RAIN_EVENT.value
    assert "timestamp" in recent[0]


def test_history_is_bounded():
    """The ring buffer evicts the oldest entries past HISTORY_LIMIT."""
    history = IrrigationHistory("zoneabc")
    for index in range(HISTORY_LIMIT + 10):
        history.record(ObservationKind.WATERING_EVENT, {"i": index})

    assert history.count == HISTORY_LIMIT
    newest = history.recent(limit=1)[0]
    assert newest["i"] == HISTORY_LIMIT + 9


def test_listeners_fire_on_record():
    """Listeners are notified on each record and can unsubscribe."""
    history = IrrigationHistory("zoneabc")
    calls = []
    unsub = history.add_listener(lambda: calls.append(1))

    history.record(ObservationKind.DECISION)
    assert calls == [1]

    unsub()
    history.record(ObservationKind.DECISION)
    assert calls == [1]


def test_build_histories_one_per_zone():
    """build_histories produces one history keyed by each zone id."""
    histories = build_histories({"aaaa1111": {}, "bbbb2222": {}})
    assert set(histories) == {"aaaa1111", "bbbb2222"}
    assert isinstance(histories["aaaa1111"], IrrigationHistory)
