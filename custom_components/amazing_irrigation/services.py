"""Services for Amazing Irrigation.

- ``amazing_irrigation.evaluate_zone``: create a Run Request for Irrigation
  Decision sensors and return the explained Decision without watering.
- ``amazing_irrigation.run_zone`` / ``stop_zone``: create a Run Request that
  actually waters (or stop watering) for the targeted zones via their generic
  Watering Actuator.

Zones are targeted by any of their entities or by their device; the matching
:class:`WateringController` is resolved through the entity/device registries.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_ZONES,
    DATA_CONTROLLERS,
    DATA_DECISION_ENTITIES,
    DATA_ZONE_STATE,
    DOMAIN,
    EVENT_DECISION,
    SERVICE_EVALUATE_ZONE,
    SERVICE_RELEARN_FROM_HISTORY,
    SERVICE_RUN_ZONE,
    SERVICE_STOP_ZONE,
)
from .history_ingest import DEFAULT_HISTORY_DAYS, async_bootstrap_zone
from .watering import WateringController
from .zone import ZoneConfig

_EVALUATE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Optional("force", default=False): cv.boolean,
    }
)

_RUN_SCHEMA = vol.Schema(
    {
        vol.Optional("entity_id"): cv.entity_ids,
        vol.Optional("device_id"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("force", default=False): cv.boolean,
    }
)

_STOP_SCHEMA = vol.Schema(
    {
        vol.Optional("entity_id"): cv.entity_ids,
        vol.Optional("device_id"): vol.All(cv.ensure_list, [cv.string]),
    }
)

_RELEARN_SCHEMA = vol.Schema(
    {
        vol.Optional("entity_id"): cv.entity_ids,
        vol.Optional("device_id"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("days", default=DEFAULT_HISTORY_DAYS): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=365)
        ),
    }
)


def _all_decision_entities(hass: HomeAssistant) -> dict[str, Any]:
    """Collect decision sensor entities across all integration entries."""
    entities: dict[str, Any] = {}
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if isinstance(entry_data, dict):
            entities.update(entry_data.get(DATA_DECISION_ENTITIES, {}))
    return entities


def _controller_for_device_id(
    hass: HomeAssistant, device_id: str
) -> WateringController | None:
    """Resolve a zone device to its WateringController."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for domain, identifier in device.identifiers:
        if domain != DOMAIN or "_" not in identifier:
            continue
        entry_id, _, zone_id = identifier.rpartition("_")
        controllers = (
            hass.data.get(DOMAIN, {}).get(entry_id, {}).get(DATA_CONTROLLERS, {})
        )
        controller = controllers.get(zone_id)
        if controller is not None:
            return controller
    return None


def _resolve_controllers(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, WateringController]:
    """Resolve all controllers referenced by a call's entity/device targets."""
    found: dict[str, WateringController] = {}

    entity_reg = er.async_get(hass)
    for entity_id in call.data.get("entity_id", []):
        entry = entity_reg.async_get(entity_id)
        if entry is None or entry.device_id is None:
            continue
        controller = _controller_for_device_id(hass, entry.device_id)
        if controller is not None:
            found[controller.zone.zone_id] = controller

    for device_id in call.data.get("device_id", []):
        controller = _controller_for_device_id(hass, device_id)
        if controller is not None:
            found[controller.zone.zone_id] = controller

    return found


def _zone_target_for_device_id(
    hass: HomeAssistant, device_id: str
) -> tuple[str, str] | None:
    """Resolve a zone device id to ``(entry_id, zone_id)``."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for domain, identifier in device.identifiers:
        if domain != DOMAIN or "_" not in identifier:
            continue
        entry_id, _, zone_id = identifier.rpartition("_")
        entry_data = hass.data.get(DOMAIN, {}).get(entry_id)
        if isinstance(entry_data, dict):
            return (entry_id, zone_id)
    return None


def _resolve_zone_targets(
    hass: HomeAssistant, call: ServiceCall
) -> dict[tuple[str, str], ZoneConfig]:
    """Resolve service entity/device targets to configured zones."""
    found: dict[tuple[str, str], ZoneConfig] = {}
    entity_reg = er.async_get(hass)
    device_ids: list[str] = list(call.data.get("device_id", []))
    for entity_id in call.data.get("entity_id", []):
        entry = entity_reg.async_get(entity_id)
        if entry is not None and entry.device_id is not None:
            device_ids.append(entry.device_id)

    for device_id in device_ids:
        target = _zone_target_for_device_id(hass, device_id)
        if target is None:
            continue
        entry_id, zone_id = target
        config_entry = hass.config_entries.async_get_entry(entry_id)
        if config_entry is None:
            continue
        record = config_entry.options.get(CONF_ZONES, {}).get(zone_id)
        if record is None:
            continue
        found[(entry_id, zone_id)] = ZoneConfig.from_record(zone_id, record)
    return found


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


async def _async_run_zone(call: ServiceCall) -> dict[str, Any]:
    """Handle ``amazing_irrigation.run_zone``."""
    hass = call.hass
    force = call.data["force"]
    results: list[dict[str, Any]] = []
    for controller in _resolve_controllers(hass, call).values():
        event = await controller.async_run(force=force)
        results.append(
            {
                "zone_id": controller.zone.zone_id,
                "status": event.status.value,
                "requested_liters": round(event.requested_liters, 2),
                "confirmed": event.confirmed,
                "reason": event.reason,
            }
        )
    return {"results": results}


async def _async_stop_zone(call: ServiceCall) -> dict[str, Any]:
    """Handle ``amazing_irrigation.stop_zone``."""
    hass = call.hass
    results: list[dict[str, Any]] = []
    for controller in _resolve_controllers(hass, call).values():
        event = await controller.async_stop()
        results.append(
            {"zone_id": controller.zone.zone_id, "status": event.status.value}
        )
    return {"results": results}


async def _async_relearn_from_history(call: ServiceCall) -> dict[str, Any]:
    """Handle ``amazing_irrigation.relearn_from_history``."""
    hass = call.hass
    days = call.data["days"]
    results: list[dict[str, Any]] = []
    for (entry_id, zone_id), zone in _resolve_zone_targets(hass, call).items():
        store = hass.data.get(DOMAIN, {}).get(entry_id, {}).get(DATA_ZONE_STATE)
        if store is None:
            results.append(
                {
                    "zone_id": zone_id,
                    "intervals_used": 0,
                    "days_span": 0.0,
                    "summary": "No zone state store available",
                }
            )
            continue
        result = await async_bootstrap_zone(hass, zone, store, days=days)
        if result is None:
            results.append(
                {
                    "zone_id": zone_id,
                    "intervals_used": 0,
                    "days_span": 0.0,
                    "summary": "No recorder history available",
                }
            )
            continue
        results.append(
            {
                "zone_id": zone_id,
                "intervals_used": result.intervals_used,
                "days_span": round(result.days_span, 2),
                "summary": result.summary,
            }
        )
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
    hass.services.async_register(
        DOMAIN,
        SERVICE_RUN_ZONE,
        _async_run_zone,
        schema=_RUN_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_ZONE,
        _async_stop_zone,
        schema=_STOP_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RELEARN_FROM_HISTORY,
        _async_relearn_from_history,
        schema=_RELEARN_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove integration services."""
    hass.services.async_remove(DOMAIN, SERVICE_EVALUATE_ZONE)
    hass.services.async_remove(DOMAIN, SERVICE_RUN_ZONE)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_ZONE)
    hass.services.async_remove(DOMAIN, SERVICE_RELEARN_FROM_HISTORY)
