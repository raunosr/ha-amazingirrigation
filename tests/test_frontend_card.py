"""Tests for bundled Lovelace card frontend registration."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.amazing_irrigation.const import DATA_CARD_REGISTERED, DOMAIN
from custom_components.amazing_irrigation.frontend_card import (
    CARD_URL,
    async_register_card,
    plan_resource_action,
)


class _FakeResources:
    """A minimal storage-mode Lovelace resource collection for tests."""

    def __init__(self, items: list[dict] | None = None) -> None:
        self.store = object()  # marks the collection as writable (storage mode)
        self.loaded = True
        self._items = list(items or [])
        self.created: list[dict] = []
        self.updated: list[tuple[str, dict]] = []
        self.deleted: list[str] = []
        self._next = 1

    async def async_get_info(self) -> dict:
        self.loaded = True
        return {}

    def async_items(self) -> list[dict]:
        return list(self._items)

    async def async_create_item(self, data: dict) -> dict:
        item = {"id": f"id{self._next}", **data}
        self._next += 1
        self._items.append(item)
        self.created.append(data)
        return item

    async def async_update_item(self, item_id: str, updates: dict) -> None:
        self.updated.append((item_id, updates))
        for item in self._items:
            if item.get("id") == item_id:
                item.update(updates)

    async def async_delete_item(self, item_id: str) -> None:
        self.deleted.append(item_id)
        self._items = [i for i in self._items if i.get("id") != item_id]


def _with_http(hass: HomeAssistant) -> None:
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()


# ---------------------------------------------------------------------------
# plan_resource_action (pure)
# ---------------------------------------------------------------------------


def test_plan_resource_action_creates_when_absent() -> None:
    action, item_id, dups = plan_resource_action([], CARD_URL, f"{CARD_URL}?v=1")
    assert action == "create"
    assert item_id is None
    assert dups == []


def test_plan_resource_action_noop_when_current() -> None:
    items = [{"id": "a", "url": f"{CARD_URL}?v=1"}]
    action, _item_id, dups = plan_resource_action(items, CARD_URL, f"{CARD_URL}?v=1")
    assert action == "noop"
    assert dups == []


def test_plan_resource_action_updates_stale_and_dedupes() -> None:
    items = [
        {"id": "a", "url": f"{CARD_URL}?v=0"},
        {"id": "b", "url": CARD_URL},
        {"id": "c", "url": "/other/card.js"},
    ]
    action, item_id, dups = plan_resource_action(items, CARD_URL, f"{CARD_URL}?v=2")
    assert action == "update"
    assert item_id == "a"
    assert dups == ["b"]


# ---------------------------------------------------------------------------
# async_register_card
# ---------------------------------------------------------------------------


async def test_register_card_uses_lovelace_resource(hass: HomeAssistant) -> None:
    """In storage mode the card is registered as a Lovelace resource."""
    _with_http(hass)
    fake = _FakeResources()
    hass.data["lovelace"] = SimpleNamespace(resources=fake)

    with patch("homeassistant.components.frontend.add_extra_js_url") as add_js:
        await async_register_card(hass)

    hass.http.async_register_static_paths.assert_awaited_once()
    add_js.assert_not_called()
    assert len(fake.created) == 1
    assert fake.created[0]["res_type"] == "module"
    assert fake.created[0]["url"].startswith(f"{CARD_URL}?v=")
    assert hass.data[DOMAIN][DATA_CARD_REGISTERED] is True


async def test_register_card_falls_back_to_extra_js(hass: HomeAssistant) -> None:
    """Without a writable resource collection, the module URL is added."""
    _with_http(hass)

    with patch("homeassistant.components.frontend.add_extra_js_url") as add_js:
        await async_register_card(hass)

    hass.http.async_register_static_paths.assert_awaited_once()
    add_js.assert_called_once()
    url = add_js.call_args.args[1]
    assert url.startswith(f"{CARD_URL}?v=")
    assert hass.data[DOMAIN][DATA_CARD_REGISTERED] is True


async def test_register_card_is_idempotent(hass: HomeAssistant) -> None:
    """Registration runs only once even if called again."""
    _with_http(hass)

    with patch("homeassistant.components.frontend.add_extra_js_url"):
        await async_register_card(hass)
        await async_register_card(hass)

    hass.http.async_register_static_paths.assert_awaited_once()


async def test_register_card_skips_without_http(hass: HomeAssistant) -> None:
    """Setup is never blocked when the HTTP component is unavailable."""
    hass.http = None

    await async_register_card(hass)

    assert not hass.data.get(DOMAIN, {}).get(DATA_CARD_REGISTERED)
