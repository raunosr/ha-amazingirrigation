"""Tests for bundled Lovelace card frontend registration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.amazing_irrigation.const import DATA_CARD_REGISTERED, DOMAIN
from custom_components.amazing_irrigation.frontend_card import (
    CARD_URL,
    async_register_card,
)


async def test_register_card_serves_and_adds_module(hass: HomeAssistant) -> None:
    """The card bundle is served and registered as an extra frontend module."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    with patch(
        "homeassistant.components.frontend.add_extra_js_url"
    ) as add_js:
        await async_register_card(hass)

    hass.http.async_register_static_paths.assert_awaited_once()
    paths = hass.http.async_register_static_paths.await_args.args[0]
    assert paths[0].url_path == CARD_URL
    add_js.assert_called_once_with(hass, CARD_URL)
    assert hass.data[DOMAIN][DATA_CARD_REGISTERED] is True


async def test_register_card_is_idempotent(hass: HomeAssistant) -> None:
    """Registration runs only once even if called again."""
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()

    with patch("homeassistant.components.frontend.add_extra_js_url"):
        await async_register_card(hass)
        await async_register_card(hass)

    hass.http.async_register_static_paths.assert_awaited_once()


async def test_register_card_skips_without_http(hass: HomeAssistant) -> None:
    """Setup is never blocked when the HTTP component is unavailable."""
    hass.http = None

    await async_register_card(hass)

    assert not hass.data.get(DOMAIN, {}).get(DATA_CARD_REGISTERED)
