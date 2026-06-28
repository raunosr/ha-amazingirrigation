"""Tests for the persistent per-zone ZoneState store (Slice 0 foundation)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.amazing_irrigation.const import (
    CONF_GAIN_PER_LITER,
    CONF_MAX_LITERS,
    CONF_NAME,
    CONF_SCHEDULE_TIMES,
    CONF_TARGET_MOISTURE,
    DEFAULT_SCHEDULE_TIME,
)
from custom_components.amazing_irrigation.state import (
    ZoneState,
    ZoneStateStore,
    apply_model_to_state,
    clamp_percent,
    normalize_time,
    params_from_state,
    seed_zone_state,
)
from custom_components.amazing_irrigation.waterbalance import WaterBalanceParams


def test_clamp_percent_bounds() -> None:
    assert clamp_percent(None) is None
    assert clamp_percent(-5) == 0.0
    assert clamp_percent(150) == 100.0
    assert clamp_percent(42.5) == 42.5


def test_normalize_time_valid_and_invalid() -> None:
    assert normalize_time("9:5") == "09:05"
    assert normalize_time("21:00") == "21:00"
    assert normalize_time("21:00:00") == "21:00"
    assert normalize_time("25:00") is None
    assert normalize_time("nonsense") is None
    assert normalize_time(None) is None


def test_seed_defaults_to_single_evening_schedule() -> None:
    state = seed_zone_state("z1", {CONF_NAME: "Bed"})
    assert state.schedule_1_time == DEFAULT_SCHEDULE_TIME
    assert state.schedule_1_active is True
    assert state.schedule_2_time == DEFAULT_SCHEDULE_TIME
    assert state.schedule_2_active is False
    assert state.active_schedule_times() == [DEFAULT_SCHEDULE_TIME]


def test_seed_uses_configured_tunables_and_two_times() -> None:
    state = seed_zone_state(
        "z1",
        {
            CONF_NAME: "Bed",
            CONF_TARGET_MOISTURE: 35,
            CONF_MAX_LITERS: 12,
            CONF_GAIN_PER_LITER: 1.5,
            CONF_SCHEDULE_TIMES: ["06:30", "20:15"],
        },
    )
    assert state.target_moisture == 35
    assert state.max_liters == 12
    assert state.learned_gain_per_liter == 1.5
    assert state.schedule_1_time == "06:30"
    assert state.schedule_1_active is True
    assert state.schedule_2_time == "20:15"
    assert state.schedule_2_active is True
    assert state.active_schedule_times() == ["06:30", "20:15"]


def test_active_schedule_times_ignores_inactive_slot() -> None:
    state = ZoneState(
        zone_id="z1",
        schedule_1_time="06:00",
        schedule_1_active=True,
        schedule_2_time="20:00",
        schedule_2_active=False,
    )
    assert state.active_schedule_times() == ["06:00"]


def test_roundtrip_serialisation_ignores_unknown_keys() -> None:
    explanation = {"mode": "predictive", "chosen_liters": 1.25}
    state = ZoneState(
        zone_id="z1",
        target_moisture=40,
        total_liters=12.5,
        decision_explanation=explanation,
    )
    data = state.to_dict()
    data["some_future_key"] = "ignored"
    restored = ZoneState.from_dict("z1", data)
    assert restored.target_moisture == 40
    assert restored.total_liters == 12.5
    assert restored.decision_explanation == explanation


def test_apply_model_to_state_persists_model_and_legacy_mirrors() -> None:
    state = ZoneState(zone_id="z1")
    params = WaterBalanceParams(1.8, 1.1, 0.5, 0.12, 48.0, 16.0)
    confidence = {"eta_irr": 0.8, "eta_rain": 0.6, "k_et": 0.4, "drain_rate": 0.2}
    covariance = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 2.0, 0.0, 0.0],
        [0.0, 0.0, 3.0, 0.0],
        [0.0, 0.0, 0.0, 4.0],
    ]

    result = apply_model_to_state(
        state,
        params,
        confidence,
        covariance=covariance,
        updated="2026-06-28T20:00:00+00:00",
    )

    assert result is state
    assert state.model_params == {
        "eta_irr": 1.8,
        "eta_rain": 1.1,
        "k_et": 0.5,
        "drain_rate": 0.12,
        "field_capacity": 48.0,
        "wilting_point": 16.0,
    }
    assert state.model_confidence == confidence
    assert state.model_covariance == covariance
    assert state.model_updated == "2026-06-28T20:00:00+00:00"
    assert state.learned_gain_per_liter == 1.8
    assert state.learned_rain_efficiency == 1.1
    assert state.learned_drying_rate == 0.48
    assert state.learned_field_capacity == 48.0
    assert state.learned_wilting_point == 16.0


def test_params_from_state_round_trips_model_params() -> None:
    state = ZoneState(zone_id="z1")
    params = WaterBalanceParams(1.7, 1.2, 0.7, 0.09, 47.0, 15.0)
    apply_model_to_state(state, params, {"eta_irr": 0.5})

    restored = params_from_state(state)

    assert restored == params


def test_params_from_state_falls_back_to_legacy_mirrors() -> None:
    state = ZoneState(
        zone_id="z1",
        learned_gain_per_liter=2.0,
        learned_rain_efficiency=1.5,
        learned_drying_rate=1.92,
        learned_field_capacity=52.0,
        learned_wilting_point=20.0,
    )

    restored = params_from_state(state)

    assert restored.eta_irr == 2.0
    assert restored.eta_rain == 1.5
    assert restored.k_et == 2.0
    assert restored.field_capacity == 52.0
    assert restored.wilting_point == 20.0


def test_from_dict_loads_old_records_without_model_fields() -> None:
    restored = ZoneState.from_dict(
        "z1",
        {
            "target_moisture": 40,
            "learned_gain_per_liter": 1.4,
            "learning_state": {"gain_samples": 2},
        },
    )

    assert restored.model_params is None
    assert restored.model_covariance is None
    assert restored.model_confidence is None
    assert restored.bootstrapped_days is None
    assert restored.model_updated is None
    assert restored.decision_explanation is None
    assert restored.learned_gain_per_liter == 1.4


async def test_store_seeds_then_persists_and_reloads(hass: HomeAssistant) -> None:
    zones = {"z1": {CONF_NAME: "Bed", CONF_TARGET_MOISTURE: 40}}

    store = ZoneStateStore(hass, "entry1")
    await store.async_load(zones)
    assert store.get("z1") is not None
    assert store.get("z1").target_moisture == 40

    # Mutate and persist a learned value + volume.
    store.get("z1").total_liters = 7.0
    store.get("z1").learned_gain_per_liter = 2.0
    await store.async_save()

    # A fresh store for the same entry should reload the persisted values.
    reloaded = ZoneStateStore(hass, "entry1")
    await reloaded.async_load(zones)
    assert reloaded.get("z1").total_liters == 7.0
    assert reloaded.get("z1").learned_gain_per_liter == 2.0


async def test_store_drops_removed_zone_and_seeds_new(hass: HomeAssistant) -> None:
    store = ZoneStateStore(hass, "entry2")
    await store.async_load({"old": {CONF_NAME: "Old"}})
    assert store.get("old") is not None

    await store.async_load({"new": {CONF_NAME: "New"}})
    assert store.get("old") is None
    assert store.get("new") is not None
