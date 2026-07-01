"""Tests for the persistent per-zone ZoneState store (Slice 0 foundation)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.amazing_irrigation.const import (
    CONF_GAIN_PER_LITER,
    CONF_LEARNING_ENABLED,
    CONF_MAX_LITERS,
    CONF_MIN_APPLICATION,
    CONF_NAME,
    CONF_RAIN_FRACTION,
    CONF_SCHEDULE_TIMES,
    CONF_SENSOR_DEPTH_MM,
    CONF_SOIL_TYPE,
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


def test_seed_seeds_new_live_settings_from_config() -> None:
    state = seed_zone_state(
        "z1",
        {
            CONF_NAME: "Bed",
            CONF_SOIL_TYPE: "sandy",
            CONF_SENSOR_DEPTH_MM: 120,
            CONF_RAIN_FRACTION: 50,
            CONF_MIN_APPLICATION: 0.8,
        },
    )
    assert state.soil_type == "sandy"
    assert state.sensor_depth_mm == 120
    assert state.rain_fraction == 50
    assert state.min_application == 0.8


def test_live_settings_survive_serialisation_roundtrip() -> None:
    state = ZoneState(
        zone_id="z1",
        soil_type="peat_compost",
        sensor_depth_mm=200.0,
        rain_fraction=25.0,
        min_application=1.5,
    )
    restored = ZoneState.from_dict("z1", state.to_dict())
    assert restored.soil_type == "peat_compost"
    assert restored.sensor_depth_mm == 200.0
    assert restored.rain_fraction == 25.0
    assert restored.min_application == 1.5


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


async def test_reload_applies_config_learning_toggle(hass: HomeAssistant) -> None:
    """Editing the learning toggle in config takes effect on the next reload."""
    zones = {"z1": {CONF_NAME: "Bed", CONF_LEARNING_ENABLED: False}}
    store = ZoneStateStore(hass, "entry_learn")
    await store.async_load(zones)
    assert store.get("z1").learning_enabled is False

    # User enables learning in the zone config; a reload re-runs async_load.
    zones = {"z1": {CONF_NAME: "Bed", CONF_LEARNING_ENABLED: True}}
    reloaded = ZoneStateStore(hass, "entry_learn")
    await reloaded.async_load(zones)
    assert reloaded.get("z1").learning_enabled is True


async def test_reload_preserves_runtime_target_when_config_unchanged(
    hass: HomeAssistant,
) -> None:
    """A target tuned via the live entity survives reloads with no config edit."""
    zones = {"z1": {CONF_NAME: "Bed", CONF_TARGET_MOISTURE: 40}}
    store = ZoneStateStore(hass, "entry_runtime")
    await store.async_load(zones)

    # Simulate a runtime change via the number entity.
    store.get("z1").target_moisture = 55
    await store.async_save()

    reloaded = ZoneStateStore(hass, "entry_runtime")
    await reloaded.async_load(zones)
    assert reloaded.get("z1").target_moisture == 55


async def test_reload_applies_changed_config_target(hass: HomeAssistant) -> None:
    """Editing the target in config overrides the persisted runtime value."""
    zones = {"z1": {CONF_NAME: "Bed", CONF_TARGET_MOISTURE: 40}}
    store = ZoneStateStore(hass, "entry_target")
    await store.async_load(zones)
    store.get("z1").target_moisture = 55
    await store.async_save()

    zones = {"z1": {CONF_NAME: "Bed", CONF_TARGET_MOISTURE: 30}}
    reloaded = ZoneStateStore(hass, "entry_target")
    await reloaded.async_load(zones)
    assert reloaded.get("z1").target_moisture == 30


async def test_first_reload_syncs_learning_flag_without_signature(
    hass: HomeAssistant,
) -> None:
    """A persisted state from before signatures adopts the config learning flag."""
    legacy = ZoneState(zone_id="z1", learning_enabled=False, target_moisture=55)
    assert legacy.config_signature == {}
    store = ZoneStateStore(hass, "entry_legacy")
    store.states = {"z1": legacy}
    await store.async_save()

    zones = {"z1": {CONF_NAME: "Bed", CONF_LEARNING_ENABLED: True, CONF_TARGET_MOISTURE: 40}}
    reloaded = ZoneStateStore(hass, "entry_legacy")
    await reloaded.async_load(zones)
    # Boolean flag is synced from config on first reconcile ...
    assert reloaded.get("z1").learning_enabled is True
    # ... but a numeric value tuned at runtime is preserved.
    assert reloaded.get("z1").target_moisture == 55
