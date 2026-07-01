"""Tests for guided Field Capacity Discovery.

The pure-logic tests exercise :func:`evaluate_discovery` against synthetic
drainage curves (settling, still-draining, max-wait fallback, re-wetting abort,
rail rejection). The integration tests drive the Home Assistant controller,
buttons, sensor and service through a real config entry.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    ACTUATOR_SWITCH,
    CONF_ACTUATOR_SWITCH,
    CONF_ACTUATOR_TYPE,
    CONF_LEARNING_ENABLED,
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_TARGET_MOISTURE,
    CONF_ZONES,
    DATA_DISCOVERY,
    DATA_ZONE_STATE,
    DISCOVERY_AWAITING_SATURATION,
    DISCOVERY_CANCELLED,
    DISCOVERY_COMPLETED,
    DISCOVERY_FAILED,
    DISCOVERY_IDLE,
    DISCOVERY_MONITORING,
    DOMAIN,
    SERVICE_START_DISCOVERY,
)
from custom_components.amazing_irrigation.discovery import (
    OUTCOME_ABORT,
    OUTCOME_CONTINUE,
    OUTCOME_RECORD,
    DiscoveryConfig,
    DiscoverySample,
    DiscoveryState,
    evaluate_discovery,
    instruction_for_phase,
)
from custom_components.amazing_irrigation.estimator import JointEstimator

_BASE = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)


def _curve(peak: float, fc: float, tau: float, hours: int, step: float = 1.0):
    """Build an exponential drainage curve toward ``fc`` from ``peak``."""
    samples = []
    t = 0.0
    while t <= hours + 1e-9:
        moisture = fc + (peak - fc) * math.exp(-t / tau)
        samples.append(DiscoverySample(at=_BASE + timedelta(hours=t), moisture=moisture))
        t += step
    return samples


def _now(samples: list[DiscoverySample]) -> datetime:
    return samples[-1].at


# --- pure logic -------------------------------------------------------------


def test_records_fc_after_drainage_settles() -> None:
    """A settled drainage curve past the min wait records FC near the asymptote."""
    samples = _curve(peak=60.0, fc=40.0, tau=3.0, hours=14)
    decision = evaluate_discovery(samples, DiscoveryConfig(), now=_now(samples))
    assert decision.outcome == OUTCOME_RECORD
    assert decision.field_capacity == pytest.approx(40.0, abs=1.0)


def test_continue_before_min_wait() -> None:
    """Even a flat curve keeps waiting until the minimum wait elapses."""
    samples = _curve(peak=60.0, fc=40.0, tau=3.0, hours=6)
    decision = evaluate_discovery(samples, DiscoveryConfig(), now=_now(samples))
    assert decision.outcome == OUTCOME_CONTINUE
    assert decision.field_capacity is None


def test_continue_while_actively_draining() -> None:
    """Past the min wait but still draining fast -> keep monitoring."""
    samples = _curve(peak=80.0, fc=30.0, tau=20.0, hours=14)
    decision = evaluate_discovery(samples, DiscoveryConfig(), now=_now(samples))
    assert decision.outcome == OUTCOME_CONTINUE
    assert decision.drainage_rate is not None and decision.drainage_rate > 0.3


def test_max_wait_fallback_records() -> None:
    """A never-settling curve records FC at the maximum wait as a fallback."""
    samples = _curve(peak=80.0, fc=30.0, tau=40.0, hours=48)
    decision = evaluate_discovery(samples, DiscoveryConfig(), now=_now(samples))
    assert decision.outcome == OUTCOME_RECORD
    assert "Maximum wait" in decision.reason
    assert decision.field_capacity is not None


def test_abort_on_moisture_rise() -> None:
    """Moisture climbing back up mid-test aborts (rain / leak / cover failed)."""
    samples = _curve(peak=60.0, fc=45.0, tau=3.0, hours=6)
    samples.append(DiscoverySample(at=_BASE + timedelta(hours=7), moisture=58.0))
    decision = evaluate_discovery(samples, DiscoveryConfig(), now=_now(samples))
    assert decision.outcome == OUTCOME_ABORT
    assert "rose" in decision.reason.lower()


def test_rail_readings_are_rejected() -> None:
    """All-rail (0/100) curves yield no valid data and keep waiting."""
    samples = [
        DiscoverySample(at=_BASE + timedelta(hours=t), moisture=100.0)
        for t in range(0, 15)
    ]
    decision = evaluate_discovery(samples, DiscoveryConfig(), now=_now(samples))
    assert decision.outcome == OUTCOME_CONTINUE
    assert decision.provisional_fc is None


def test_rail_readings_are_filtered_but_curve_still_records() -> None:
    """Interspersed rail readings are dropped without breaking the decision."""
    samples = _curve(peak=60.0, fc=40.0, tau=3.0, hours=14)
    samples.insert(5, DiscoverySample(at=_BASE + timedelta(hours=4.5), moisture=0.0))
    samples.insert(9, DiscoverySample(at=_BASE + timedelta(hours=8.5), moisture=100.0))
    decision = evaluate_discovery(samples, DiscoveryConfig(), now=_now(samples))
    assert decision.outcome == OUTCOME_RECORD
    assert decision.field_capacity == pytest.approx(40.0, abs=1.0)


def test_relative_threshold_is_texture_adaptive() -> None:
    """A fast-draining (sandy) curve settles and records within the window."""
    samples = _curve(peak=50.0, fc=25.0, tau=1.5, hours=13)
    decision = evaluate_discovery(samples, DiscoveryConfig(), now=_now(samples))
    assert decision.outcome == OUTCOME_RECORD
    assert decision.field_capacity == pytest.approx(25.0, abs=1.5)


def test_discovery_state_round_trip() -> None:
    """DiscoveryState serialises and rebuilds, ignoring unknown keys."""
    state = DiscoveryState(phase=DISCOVERY_MONITORING, peak_moisture=60.0)
    data = state.to_dict()
    data["unexpected"] = "ignored"
    rebuilt = DiscoveryState.from_dict(data)
    assert rebuilt.phase == DISCOVERY_MONITORING
    assert rebuilt.peak_moisture == 60.0
    assert DiscoveryState.from_dict(None).phase == DISCOVERY_IDLE


def test_instruction_for_phase_covers_all_phases() -> None:
    """Every phase maps to a non-empty human instruction."""
    for phase in (
        DISCOVERY_IDLE,
        DISCOVERY_AWAITING_SATURATION,
        DISCOVERY_MONITORING,
        DISCOVERY_COMPLETED,
        DISCOVERY_FAILED,
        DISCOVERY_CANCELLED,
    ):
        assert instruction_for_phase(phase)


# --- estimator write-back ---------------------------------------------------


def test_estimator_seed_field_capacity_sets_fc_only() -> None:
    """Seeding FC moves the envelope high without disturbing wilting point."""
    estimator = JointEstimator()
    wp_before = estimator.params.wilting_point
    estimator.seed_field_capacity(58.0)
    assert estimator.params.field_capacity == pytest.approx(58.0, abs=0.01)
    assert estimator.params.wilting_point == pytest.approx(wp_before, abs=0.01)


def test_estimator_manual_override_wins_over_discovery() -> None:
    """A manual field-capacity override is not overwritten by a discovery seed."""
    estimator = JointEstimator()
    estimator.set_override("field_capacity", 30.0)
    estimator.seed_field_capacity(58.0)
    assert estimator.params.field_capacity == pytest.approx(30.0, abs=0.01)


# --- integration ------------------------------------------------------------

_ZONE = {
    CONF_NAME: "Herb Bed",
    CONF_MOISTURE_SENSORS: ["sensor.a"],
    CONF_TARGET_MOISTURE: 40,
    CONF_MAX_LITERS: 30,
    CONF_ACTUATOR_TYPE: ACTUATOR_SWITCH,
    CONF_ACTUATOR_SWITCH: "switch.valve",
    CONF_LEARNING_ENABLED: True,
}


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={CONF_ZONES: {"abc123": _ZONE}},
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _controller(hass: HomeAssistant, entry: MockConfigEntry):
    return hass.data[DOMAIN][entry.entry_id][DATA_DISCOVERY]["abc123"]


def _state(hass: HomeAssistant, entry: MockConfigEntry):
    return hass.data[DOMAIN][entry.entry_id][DATA_ZONE_STATE].get("abc123")


async def test_workflow_transitions_and_records(hass: HomeAssistant) -> None:
    """Start -> confirm -> monitored drainage records FC into the learned model."""
    hass.states.async_set("sensor.a", "60.0")
    entry = await _setup(hass)
    controller = _controller(hass, entry)

    await controller.async_start_discovery()
    await hass.async_block_till_done()
    assert controller.discovery.phase == DISCOVERY_AWAITING_SATURATION

    await controller.async_confirm_saturated()
    await hass.async_block_till_done()
    assert controller.discovery.phase == DISCOVERY_MONITORING

    # Shrink the waits so a short synthetic curve can settle and record. The
    # minimum wait must stay above zero so the initial flat seed pair does not
    # record instantly (mirroring the 12 h production floor).
    controller._config = DiscoveryConfig(  # noqa: SLF001 - test seam
        min_wait_hours=3.5,
        max_wait_hours=100.0,
        stability_window_hours=1.5,
        rate_relative_stop=0.12,
        rate_abs_floor=0.2,
    )
    base = dt_util.utcnow()
    for i, moisture in enumerate([60.0, 50.0, 45.0, 42.0, 41.0, 41.0, 41.0]):
        hass.states.async_set("sensor.a", str(moisture))
        await hass.async_block_till_done()
        controller._async_sample(base + timedelta(hours=i))  # noqa: SLF001 - test seam
        await hass.async_block_till_done()

    assert controller.discovery.phase == DISCOVERY_COMPLETED
    assert controller.discovery.result_fc == pytest.approx(41.0, abs=1.0)
    state = _state(hass, entry)
    assert state.learned_field_capacity == pytest.approx(41.0, abs=1.0)


async def test_cancel_returns_to_cancelled(hass: HomeAssistant) -> None:
    """Cancelling an in-progress discovery stops monitoring."""
    hass.states.async_set("sensor.a", "55.0")
    entry = await _setup(hass)
    controller = _controller(hass, entry)

    await controller.async_start_discovery()
    await controller.async_confirm_saturated()
    await hass.async_block_till_done()
    await controller.async_cancel_discovery()
    await hass.async_block_till_done()

    assert controller.discovery.phase == DISCOVERY_CANCELLED


async def test_abort_on_rewetting(hass: HomeAssistant) -> None:
    """A moisture rise during monitoring fails the discovery."""
    hass.states.async_set("sensor.a", "60.0")
    entry = await _setup(hass)
    controller = _controller(hass, entry)

    await controller.async_start_discovery()
    await controller.async_confirm_saturated()
    await hass.async_block_till_done()

    base = dt_util.utcnow()
    for i, moisture in enumerate([60.0, 55.0, 50.0, 62.0]):
        hass.states.async_set("sensor.a", str(moisture))
        await hass.async_block_till_done()
        controller._async_sample(base + timedelta(hours=i))  # noqa: SLF001 - test seam
        await hass.async_block_till_done()

    assert controller.discovery.phase == DISCOVERY_FAILED
    assert "rose" in (controller.discovery.reason or "").lower()


async def test_service_starts_discovery(hass: HomeAssistant) -> None:
    """The start_field_capacity_discovery service advances the workflow."""
    hass.states.async_set("sensor.a", "50.0")
    entry = await _setup(hass)
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_abc123_discovery_status"
    )
    assert entity_id is not None

    device_entry = next(
        entry_id
        for entry_id in registry.entities
        if registry.entities[entry_id].unique_id
        == f"{entry.entry_id}_abc123_discovery_status"
    )
    device_id = registry.entities[device_entry].device_id
    await hass.services.async_call(
        DOMAIN,
        SERVICE_START_DISCOVERY,
        {"device_id": [device_id]},
        blocking=True,
    )
    await hass.async_block_till_done()

    controller = _controller(hass, entry)
    assert controller.discovery.phase == DISCOVERY_AWAITING_SATURATION
    assert hass.states.get(entity_id).state == DISCOVERY_AWAITING_SATURATION


async def test_discovery_buttons_are_created(hass: HomeAssistant) -> None:
    """The three discovery buttons are registered for a moisture-sensor zone."""
    hass.states.async_set("sensor.a", "50.0")
    entry = await _setup(hass)
    registry = er.async_get(hass)
    for suffix in ("discovery_start", "discovery_confirm", "discovery_cancel"):
        assert registry.async_get_entity_id(
            "button", DOMAIN, f"{entry.entry_id}_abc123_{suffix}"
        )
