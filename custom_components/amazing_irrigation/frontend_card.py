"""Register the bundled Lovelace card as a frontend resource.

The integration ships its Lovelace card in the same package. Rather than asking
users to add a Lovelace resource by hand, the integration serves the bundled
JavaScript from a static path and makes the ``amazing-irrigation-card`` /
``amazing-irrigation-overview-card`` custom cards available automatically.

Two registration mechanisms exist and they are used in order of reliability:

1. A **Lovelace resource** (storage-mode dashboards). This is the mechanism
   HACS frontend plugins use; it loads the module on every dashboard and makes
   the cards appear in the "Add card" picker. We register it with a
   ``?v=<version>`` query so a HACS update busts the frontend service-worker
   cache instead of serving a stale (or empty) module -- the usual cause of
   "Custom element not found" after an update.
2. ``frontend.add_extra_js_url`` as a fallback for YAML-mode dashboards (where
   resources are read-only) or when the Lovelace resource collection is not
   available.

The :func:`plan_resource_action` helper is pure so the dedup/update decision can
be unit tested without Home Assistant.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DATA_CARD_REGISTERED, DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "amazing-irrigation-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILENAME}"


def _strip_query(url: str) -> str:
    """Return ``url`` without its query string."""
    return url.split("?", 1)[0]


def plan_resource_action(
    items: Iterable[Mapping[str, Any]], base_url: str, versioned_url: str
) -> tuple[str, str | None, list[str]]:
    """Decide how to register our card as a Lovelace resource.

    Returns ``(action, item_id, duplicate_ids)`` where ``action`` is one of
    ``"noop"``, ``"create"`` or ``"update"``. ``duplicate_ids`` are extra
    resources pointing at our card that should be removed.
    """
    ours = [
        item for item in items if _strip_query(str(item.get("url", ""))) == base_url
    ]
    if not ours:
        return ("create", None, [])

    primary = ours[0]
    duplicate_ids = [
        str(item["id"]) for item in ours[1:] if item.get("id") is not None
    ]
    primary_id = primary.get("id")
    if primary.get("url") == versioned_url and not duplicate_ids:
        return ("noop", None, [])
    return (
        "update",
        str(primary_id) if primary_id is not None else None,
        duplicate_ids,
    )


async def _async_card_version(hass: HomeAssistant) -> str:
    """Return the integration version, used to cache-bust the card URL."""
    try:
        from homeassistant.loader import async_get_integration

        integration = await async_get_integration(hass, DOMAIN)
        return str(integration.version or "0")
    except Exception:  # noqa: BLE001 - version is only for cache-busting
        return "0"


def _resource_collection(hass: HomeAssistant) -> Any | None:
    """Return the writable (storage-mode) Lovelace resource collection, if any."""
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        return None
    resources = getattr(lovelace, "resources", None)
    if resources is None and isinstance(lovelace, dict):
        resources = lovelace.get("resources")
    if resources is None:
        return None
    # Only storage-mode collections are writable; YAML collections have no store.
    if getattr(resources, "store", None) is None:
        return None
    return resources


async def _async_register_lovelace_resource(
    hass: HomeAssistant, versioned_url: str
) -> bool:
    """Register/refresh the card as a Lovelace resource. Returns success."""
    resources = _resource_collection(hass)
    if resources is None:
        return False

    try:
        if not getattr(resources, "loaded", False):
            await resources.async_get_info()

        items = list(resources.async_items())
        action, item_id, duplicate_ids = plan_resource_action(
            items, CARD_URL, versioned_url
        )

        if action == "create":
            await resources.async_create_item(
                {"res_type": "module", "url": versioned_url}
            )
        elif action == "update" and item_id is not None:
            await resources.async_update_item(
                item_id, {"res_type": "module", "url": versioned_url}
            )
        for dup_id in duplicate_ids:
            await resources.async_delete_item(dup_id)
    except Exception:  # noqa: BLE001 - fall back to extra_js_url
        _LOGGER.warning(
            "Could not register Amazing Irrigation card as a Lovelace resource",
            exc_info=True,
        )
        return False

    return True


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

    version = await _async_card_version(hass)
    versioned_url = f"{CARD_URL}?v={version}"

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(card_path), cache_headers=False)]
        )
    except RuntimeError:
        # Already registered (e.g. an entry reload); the path stays served.
        _LOGGER.debug("Amazing Irrigation card static path already registered")
    except Exception:  # noqa: BLE001 - card is optional, setup must continue
        _LOGGER.warning("Failed to serve Amazing Irrigation card", exc_info=True)
        return

    registered = await _async_register_lovelace_resource(hass, versioned_url)
    if not registered:
        # Fallback: YAML-mode dashboards or no writable resource collection.
        try:
            from homeassistant.components import frontend

            frontend.add_extra_js_url(hass, versioned_url)
        except Exception:  # noqa: BLE001 - card is optional, setup must continue
            _LOGGER.warning(
                "Failed to register Amazing Irrigation card module", exc_info=True
            )
            return

    domain_data[DATA_CARD_REGISTERED] = True
    _LOGGER.debug("Registered Amazing Irrigation card at %s", versioned_url)
