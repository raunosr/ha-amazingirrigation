"""Resolve a LinkTap-over-MQTT device into the entities a zone needs.

LinkTap devices (the ``by LinkTap`` MQTT devices) expose every entity under a
stable, id-prefixed naming scheme, and the device registry keeps the exact-case
LinkTap id in its identifiers. Selecting the *device* therefore gives us
everything the LinkTap Watering Actuator needs without the user hunting for
individual entities.

The :func:`resolve_linktap_device` helper here is pure (it takes the already
gathered identifiers and entity ids) so it can be unit tested without Home
Assistant. :func:`async_resolve_linktap_device` is the thin runtime wrapper that
reads the device and entity registries.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class LinkTapResolution:
    """The entities and id derived from a selected LinkTap device."""

    linktap_id: str | None = None
    switch: str | None = None
    watering_sensor: str | None = None
    volume_sensor: str | None = None


def _object_id(entity_id: str) -> str:
    """Return the part of an entity id after the domain."""
    return entity_id.partition(".")[2]


def resolve_linktap_device(
    identifiers: Iterable[tuple[str, str]],
    entity_ids: Iterable[str],
) -> LinkTapResolution:
    """Derive the LinkTap id and entities from a device's registry data.

    ``identifiers`` are the device registry identifiers (e.g.
    ``[("mqtt", "1F43B22F004B1200_4")]``); ``entity_ids`` are the entity ids
    belonging to the device. Matching is suffix based so it works regardless of
    the LinkTap id, and the exact-case id is preferred from the identifiers.
    """
    entity_ids = list(entity_ids)

    switch = next(
        (e for e in entity_ids if e.startswith("switch.") and e.endswith("_water_switch")),
        None,
    )
    watering_sensor = next(
        (
            e
            for e in entity_ids
            if e.startswith("binary_sensor.") and e.endswith("_is_watering")
        ),
        None,
    )
    # ``_volume`` only — never ``_volume_limit``.
    volume_sensor = next(
        (
            e
            for e in entity_ids
            if e.startswith("sensor.") and e.endswith("_volume")
        ),
        None,
    )

    # The lowercased entity object-id prefix, used to pick the matching
    # (exact-case) identifier value.
    prefix = ""
    if switch is not None:
        prefix = _object_id(switch)[: -len("_water_switch")]

    linktap_id: str | None = None
    identifier_values = [value for _, value in identifiers if value]
    for value in identifier_values:
        if prefix and value.lower() == prefix:
            linktap_id = value
            break
    if linktap_id is None and identifier_values:
        linktap_id = identifier_values[0]
    if linktap_id is None and prefix:
        linktap_id = prefix

    return LinkTapResolution(
        linktap_id=linktap_id,
        switch=switch,
        watering_sensor=watering_sensor,
        volume_sensor=volume_sensor,
    )


def async_resolve_linktap_device(hass, device_id: str) -> LinkTapResolution:
    """Resolve a LinkTap device id into its id and entities at runtime."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return LinkTapResolution()

    entity_ids = [
        entry.entity_id
        for entry in er.async_entries_for_device(
            er.async_get(hass), device_id, include_disabled_entities=True
        )
    ]
    return resolve_linktap_device(device.identifiers, entity_ids)


def async_resolve_linktap_from_entity(hass, entity_id: str) -> LinkTapResolution:
    """Resolve the LinkTap entities from a sibling entity (e.g. the switch).

    The actuator switch a user picks usually belongs to the LinkTap MQTT
    device, so its device gives us the matching watering/volume feedback
    sensors without the user hunting for them individually.
    """
    from homeassistant.helpers import entity_registry as er

    entry = er.async_get(hass).async_get(entity_id)
    if entry is None or entry.device_id is None:
        return LinkTapResolution()
    return async_resolve_linktap_device(hass, entry.device_id)
