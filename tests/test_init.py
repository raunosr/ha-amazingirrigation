"""Tests for setup and teardown of the Amazing Irrigation integration shell."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import DOMAIN


async def test_setup_and_unload_entry(hass: HomeAssistant) -> None:
    """The shell entry should load and unload cleanly."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_shell_loads_no_platforms(hass: HomeAssistant) -> None:
    """The shell must not control water: no platforms are forwarded."""
    from custom_components.amazing_irrigation import PLATFORMS

    assert PLATFORMS == []
