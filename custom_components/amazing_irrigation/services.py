"""Services for Amazing Irrigation.

Exposes ``amazing_irrigation.evaluate_zone``: create a Run Request for one or
more Irrigation Decision sensors, recompute the Decision, fire an event, and
return the explained result. This slice is observe-only, so evaluating never
actuates water.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

from .const import (
    DATA_DECISION_ENTITIES,
    DOMAIN,
    EVENT_DECISION,
    SERVICE_EVALUATE_ZONE,
)

_EVALUATE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Optional("force", default=False): cv.boolean,
    }
)


def _all_decision_entities(hass: HomeAssistant) -> dict[str, Any]:
    """Collect decision sensor entities across all integration entries."""
    entities: dict[str, Any] = {}
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if isinstance(entry_data, dict):
            entities.update(entry_data.get(DATA_DECISION_ENTITIES, {}))
    return entities


async def _async_evaluate_zone(call: ServiceCall) -> dict[str, Any]:
    """Handle ``amazing_irrigation.evaluate_zone``."""
    hass = call.hass
    force = call.data["force"]
    available = _all_decision_entities(hass)

    results: list[dict[str, Any]] = []
    for entity_id in call.data["entity_id"]:
        entity = available.get(entity_id)
        if entity is None:
            continue
        # A forced evaluation is computed for the response/event but not
        # persisted, so the sensor keeps showing the live, non-forced decision.
        decision = entity.evaluate(force=force, write=not force)
        result = {
            "entity_id": entity_id,
            "zone_id": entity._zone.zone_id,  # noqa: SLF001 - trusted internal access
            "action": decision.action.value,
            "reason": decision.reason.value,
            "recommended_liters": round(decision.recommended_liters, 2),
            "degraded": decision.degraded,
        }
        results.append(result)
        hass.bus.async_fire(EVENT_DECISION, result)

    return {"results": results}


def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_EVALUATE_ZONE):
        return
    hass.services.async_register(
        DOMAIN,
        SERVICE_EVALUATE_ZONE,
        _async_evaluate_zone,
        schema=_EVALUATE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove integration services."""
    hass.services.async_remove(DOMAIN, SERVICE_EVALUATE_ZONE)
