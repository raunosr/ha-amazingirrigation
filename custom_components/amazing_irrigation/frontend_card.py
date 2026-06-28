"""Register the bundled Lovelace card as a frontend resource.

The integration ships its Lovelace card in the same package. Rather than asking
users to add a Lovelace resource by hand, the integration serves the bundled
JavaScript from a static path and registers it as an extra frontend module so
the ``amazing-irrigation-card`` custom card is available automatically.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DATA_CARD_REGISTERED, DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "amazing-irrigation-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILENAME}"


async def async_register_card(hass: HomeAssistant) -> None:
    """Serve and register the bundled card once per Home Assistant instance."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_CARD_REGISTERED):
        return

    # The card is a convenience; never let a frontend/http hiccup block setup.
    if getattr(hass, "http", None) is None:
        _LOGGER.debug("HTTP component unavailable; skipping card registration")
        return

    card_path = Path(__file__).parent / "frontend" / CARD_FILENAME
    if not card_path.is_file():
        _LOGGER.warning("Amazing Irrigation card bundle missing at %s", card_path)
        return

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(card_path), cache_headers=False)]
        )

        # Lazy import so this module stays importable without the frontend.
        from homeassistant.components import frontend

        frontend.add_extra_js_url(hass, CARD_URL)
    except Exception:  # noqa: BLE001 - card is optional, setup must continue
        _LOGGER.warning("Failed to register Amazing Irrigation card", exc_info=True)
        return

    domain_data[DATA_CARD_REGISTERED] = True
    _LOGGER.debug("Registered Amazing Irrigation card at %s", CARD_URL)
