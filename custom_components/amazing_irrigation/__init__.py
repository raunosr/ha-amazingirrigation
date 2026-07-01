"""The Amazing Irrigation integration.

This module wires the single integration config entry into Home Assistant.
The shell deliberately controls no water: no platforms are forwarded and no
watering services are registered yet. Later slices add zones, a decision
engine, actuators, scheduling and services on top of this base.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ZONES,
    DATA_CONTROLLERS,
    DATA_DISCOVERY,
    DATA_HISTORY,
    DATA_LEARNERS,
    DATA_RAIN_WATCHERS,
    DATA_SCHEDULER,
    DATA_WEATHER_FORECAST,
    DATA_WEATHER_PROVIDER,
    DATA_ZONE_STATE,
    DOMAIN,
)
from .discovery_controller import build_discovery_controllers
from .frontend_card import async_register_card
from .history import build_histories
from .history_ingest import async_bootstrap_zone
from .learner import build_learners
from .rain import build_rain_watchers
from .scheduler import build_scheduler
from .services import async_setup_services, async_unload_services
from .state import ZoneStateStore
from .watering import build_controllers
from .weather_forecast import build_weather_provider
from .zone import ZoneConfig

_LOGGER = logging.getLogger(__name__)

# Sensors observe; buttons run/stop; number/switch/time edit live tunables.
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.TIME,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Amazing Irrigation from a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault(DATA_WEATHER_FORECAST, {})
    zones = entry.options.get(CONF_ZONES, {})
    zone_state = ZoneStateStore(hass, entry.entry_id)
    await zone_state.async_load(zones)
    histories = build_histories(zones)
    controllers = build_controllers(hass, zones, histories, zone_state)
    scheduler = build_scheduler(hass, controllers, entry.options, zone_state)
    rain_watchers = build_rain_watchers(hass, zones, histories)
    weather_provider = build_weather_provider(hass, zones)
    learners = build_learners(hass, zones, zone_state)
    discovery = build_discovery_controllers(hass, zones, zone_state, learners)
    domain_data[entry.entry_id] = {
        DATA_CONTROLLERS: controllers,
        DATA_SCHEDULER: scheduler,
        DATA_HISTORY: histories,
        DATA_RAIN_WATCHERS: rain_watchers,
        DATA_WEATHER_PROVIDER: weather_provider,
        DATA_ZONE_STATE: zone_state,
        DATA_LEARNERS: learners,
        DATA_DISCOVERY: discovery,
    }

    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async_setup_services(hass)
    await async_register_card(hass)
    scheduler.async_start()
    for watcher in rain_watchers:
        watcher.async_start()
    await weather_provider.async_start()
    for learner in learners.values():
        learner.async_start()
    for discovery_controller in discovery.values():
        discovery_controller.async_start()
    hass.async_create_task(_async_bootstrap_missing_models(hass, zones, zone_state))

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.debug("Amazing Irrigation entry %s set up", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry, PLATFORMS
        )
    else:
        unload_ok = True

    if unload_ok:
        domain_data = hass.data.get(DOMAIN, {})
        entry_data = domain_data.pop(entry.entry_id, None)
        if entry_data:
            scheduler = entry_data.get(DATA_SCHEDULER)
            if scheduler is not None:
                scheduler.async_stop()
            for watcher in entry_data.get(DATA_RAIN_WATCHERS, []):
                watcher.async_stop()
            weather_provider = entry_data.get(DATA_WEATHER_PROVIDER)
            if weather_provider is not None:
                weather_provider.async_stop()
            for learner in entry_data.get(DATA_LEARNERS, {}).values():
                learner.async_stop()
            for discovery_controller in entry_data.get(DATA_DISCOVERY, {}).values():
                discovery_controller.async_shutdown()
            for controller in entry_data.get(DATA_CONTROLLERS, {}).values():
                controller.teardown()
        # Entry data is keyed by entry_id; ignore domain-level caches/flags.
        if not any(
            key != DATA_WEATHER_FORECAST and isinstance(value, dict)
            for key, value in domain_data.items()
        ):
            async_unload_services(hass)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_bootstrap_missing_models(
    hass: HomeAssistant, zones: dict[str, dict], zone_state: ZoneStateStore
) -> None:
    """Best-effort non-blocking history bootstrap for newly configured zones.

    Runs once per zone that has moisture sensors but no model or bootstrap yet,
    independent of whether live learning is enabled, so a useful prior exists
    right after first configuration. The ``bootstrapped_days`` (success) and
    ``bootstrap_attempted`` (any completed attempt, including unsuccessful fits)
    markers prevent re-running the costly recorder fetch on every reload, e.g.
    when the user edits a zone's configuration. The manual Bootstrap button and
    service bypass this guard to force a re-run on demand.
    """
    for zone_id, record in zones.items():
        state = zone_state.get(zone_id)
        if (
            state is None
            or state.model_params is not None
            or state.bootstrapped_days is not None
            or state.bootstrap_attempted is not None
        ):
            continue
        zone = ZoneConfig.from_record(zone_id, record)
        if not zone.moisture_sensors:
            continue
        try:
            await async_bootstrap_zone(hass, zone, zone_state)
        except Exception as err:  # noqa: BLE001 - setup must not fail on history
            _LOGGER.debug("History bootstrap skipped for %s: %s", zone_id, err)
