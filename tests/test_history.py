"""Tests for the bounded Irrigation History store."""

from __future__ import annotations

from custom_components.amazing_irrigation.const import HISTORY_LIMIT
from custom_components.amazing_irrigation.history import (
    IrrigationHistory,
    Observation,
    ObservationKind,
    build_histories,
    summarize_observation,
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


def test_summary_watering_event_confirmed_uses_measured():
    """A confirmed Watering Event reads as a watered amount in liters."""
    obs = Observation(
        ObservationKind.WATERING_EVENT,
        {"status": "confirmed", "requested_liters": 8.0, "measured_liters": 7.5,
         "confirmed": True},
    )
    assert obs.summary == "Watered 7.5 L"


def test_summary_watering_event_falls_back_to_requested():
    """Without a measured volume the requested liters are shown."""
    obs = Observation(
        ObservationKind.WATERING_EVENT,
        {"status": "confirmed", "requested_liters": 8.0, "measured_liters": None,
         "confirmed": True},
    )
    assert obs.summary == "Watered 8 L"


def test_summary_decision_skip_is_human_readable():
    """A skip Decision explains the reason in plain language."""
    obs = Observation(
        ObservationKind.DECISION,
        {"action": "skip", "reason": "above_target", "recommended_liters": 0.0},
    )
    assert obs.summary == "Skipped: above target"


def test_summary_decision_reduce_includes_reason():
    """A reduce Decision shows the reduced liters and reason."""
    obs = Observation(
        ObservationKind.DECISION,
        {"action": "reduce", "reason": "rain_reduce", "recommended_liters": 4.0},
    )
    assert obs.summary == "Reduced to 4 L (rain expected)"


def test_summary_rain_event_shows_delta():
    """A Rain Event reads as a signed millimetre delta."""
    obs = Observation(
        ObservationKind.RAIN_EVENT, {"observed_rain_amount": 12.0, "delta_mm": 4.0}
    )
    assert obs.summary == "Rain +4 mm"


def test_summary_run_request_variants():
    """Run Requests distinguish manual and busy states."""
    manual = Observation(ObservationKind.RUN_REQUEST, {"force": True})
    busy = Observation(ObservationKind.RUN_REQUEST, {"zone_locked": True})
    assert manual.summary == "Run requested (manual)"
    assert busy.summary == "Run requested (actuator busy)"


def test_summarize_observation_matches_property():
    """The module function and the convenience property agree."""
    obs = Observation(ObservationKind.DECISION, {"action": "water",
                                                 "recommended_liters": 6.0})
    assert summarize_observation(obs) == obs.summary == "Watering 6 L"


def test_as_dict_includes_summary():
    """Serialised entries carry the human-readable summary for the card."""
    obs = Observation(ObservationKind.WATERING_EVENT,
                      {"status": "skipped", "requested_liters": 0.0})
    assert obs.as_dict()["summary"] == "Watering skipped"
