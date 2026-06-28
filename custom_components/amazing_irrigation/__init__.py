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
    DATA_HISTORY,
    DATA_LEARNERS,
    DATA_RAIN_WATCHERS,
    DATA_SCHEDULER,
    DATA_ZONE_STATE,
    DOMAIN,
)
from .frontend_card import async_register_card
from .history import build_histories
from .learner import build_learners
from .rain import build_rain_watchers
from .scheduler import build_scheduler
from .services import async_setup_services, async_unload_services
from .state import ZoneStateStore
from .watering import build_controllers

_LOGGER = logging.getLogger(__name__)

# Sensors observe; buttons run/stop watering through the generic actuator.
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Amazing Irrigation from a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    zones = entry.options.get(CONF_ZONES, {})
    zone_state = ZoneStateStore(hass, entry.entry_id)
    await zone_state.async_load(zones)
    histories = build_histories(zones)
    controllers = build_controllers(hass, zones, histories, zone_state)
    scheduler = build_scheduler(hass, controllers, entry.options)
    rain_watchers = build_rain_watchers(hass, zones, histories)
    learners = build_learners(hass, zones, zone_state)
    domain_data[entry.entry_id] = {
        DATA_CONTROLLERS: controllers,
        DATA_SCHEDULER: scheduler,
        DATA_HISTORY: histories,
        DATA_RAIN_WATCHERS: rain_watchers,
        DATA_ZONE_STATE: zone_state,
        DATA_LEARNERS: learners,
    }

    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async_setup_services(hass)
    await async_register_card(hass)
    scheduler.async_start()
    for watcher in rain_watchers:
        watcher.async_start()
    for learner in learners.values():
        learner.async_start()

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
            for learner in entry_data.get(DATA_LEARNERS, {}).values():
                learner.async_stop()
            for controller in entry_data.get(DATA_CONTROLLERS, {}).values():
                controller.teardown()
        # Only entry data is stored as a dict; ignore the card-registered flag
        # when deciding whether any config entries remain.
        if not any(isinstance(value, dict) for value in domain_data.values()):
            async_unload_services(hass)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
