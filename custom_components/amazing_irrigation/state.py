"""Persistent per-zone live state for Amazing Irrigation.

The config entry's options describe how a zone is *set up*. Once running, a zone
also has **live tunables** the user can change from the device page (Target
Moisture, Max Liters, whether the zone and its learning are enabled, and two
schedule slots), plus values the integration **learns** over time and a running
**Total Watering Volume**. Persisting those in the config entry would force a
full reload on every slider drag, so they live here instead, in a small
``homeassistant.helpers.storage.Store`` keyed by zone.

The pure helpers (seeding, bounds, (de)serialisation) take plain dicts so they
can be unit-tested without Home Assistant; only :class:`ZoneStateStore` touches
the Store I/O. Initial values seed from the config-entry options the first time a
zone is seen; thereafter this store is the live source of truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DEFAULT_MAX_LITERS,
    DEFAULT_SCHEDULE_TIME,
    DOMAIN,
    STORAGE_VERSION,
)
from .zone import ZoneConfig

# Storage key suffix; the full key is scoped per config entry so multiple
# entries (should they ever exist) never share learned state.
STORAGE_KEY_FORMAT = f"{DOMAIN}.{{entry_id}}.zone_state"


def clamp_percent(value: float | None) -> float | None:
    """Clamp a moisture-style percentage to ``[0, 100]`` (``None`` passes through)."""
    if value is None:
        return None
    return max(0.0, min(100.0, float(value)))


def normalize_time(value: str | None) -> str | None:
    """Return a valid ``HH:MM`` string, or ``None`` when unparseable."""
    if not value:
        return None
    parts = str(value).strip().split(":")
    if len(parts) < 2:
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"
    return None


@dataclass
class ZoneState:
    """A single zone's persisted, live-editable state.

    ``schedule_1``/``schedule_2`` are the two independently toggleable schedule
    slots surfaced as native entities. Learned values are ``None`` until the
    learning engine has enough evidence. ``total_liters`` is the cumulative
    Confirmed Watering Volume applied to the zone.
    """

    zone_id: str
    # Live tunables (seeded from the config-entry options).
    target_moisture: float | None = None
    max_liters: float = DEFAULT_MAX_LITERS
    enabled: bool = True
    learning_enabled: bool = False
    # Two schedule slots, each independently active.
    schedule_1_time: str | None = DEFAULT_SCHEDULE_TIME
    schedule_1_active: bool = True
    schedule_2_time: str | None = DEFAULT_SCHEDULE_TIME
    schedule_2_active: bool = False
    # Learned parameters (filled by the learning engine over time).
    learned_gain_per_liter: float | None = None
    learned_drying_rate: float | None = None
    learned_rain_efficiency: float | None = None
    learned_field_capacity: float | None = None
    learned_wilting_point: float | None = None
    # Cumulative Total Watering Volume in liters.
    total_liters: float = 0.0
    # Opaque bookkeeping for the learning engine (EMA counters, last samples).
    learning_state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise for the Store."""
        return asdict(self)

    @classmethod
    def from_dict(cls, zone_id: str, data: dict[str, Any]) -> ZoneState:
        """Rebuild from a persisted record, ignoring unknown keys."""
        known = {f for f in cls.__dataclass_fields__ if f != "zone_id"}
        kwargs = {key: value for key, value in data.items() if key in known}
        return cls(zone_id=zone_id, **kwargs)

    def active_schedule_times(self) -> list[str]:
        """Sorted, de-duplicated ``HH:MM`` times of the active schedule slots."""
        out: set[str] = set()
        for value, active in (
            (self.schedule_1_time, self.schedule_1_active),
            (self.schedule_2_time, self.schedule_2_active),
        ):
            normalized = normalize_time(value)
            if active and normalized is not None:
                out.add(normalized)
        return sorted(out)


def seed_zone_state(zone_id: str, record: dict[str, Any]) -> ZoneState:
    """Build a zone's initial state from its config-entry options record.

    Schedule slots seed from any existing configured times (first two), each
    active where a time exists. With no configured times, the zone defaults to a
    single evening watering at :data:`DEFAULT_SCHEDULE_TIME` (slot 1 active, slot
    2 present but inactive).
    """
    zone = ZoneConfig.from_record(zone_id, record)
    state = ZoneState(
        zone_id=zone_id,
        target_moisture=clamp_percent(zone.target_moisture),
        max_liters=max(0.0, zone.max_liters),
        enabled=zone.enabled,
        learning_enabled=zone.learning_enabled,
        learned_gain_per_liter=zone.gain_per_liter,
        learned_field_capacity=zone.field_capacity,
        learned_wilting_point=zone.wilting_point,
    )

    configured = [normalize_time(value) for value in zone.schedule_times]
    configured = [value for value in configured if value is not None]
    if configured:
        state.schedule_1_time = configured[0]
        state.schedule_1_active = True
        if len(configured) > 1:
            state.schedule_2_time = configured[1]
            state.schedule_2_active = True
        else:
            state.schedule_2_time = configured[0]
            state.schedule_2_active = False
    return state


class ZoneStateStore:
    """Loads, holds and persists every zone's :class:`ZoneState`."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialise the Store for one config entry."""
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_FORMAT.format(entry_id=entry_id)
        )
        self.states: dict[str, ZoneState] = {}

    async def async_load(self, zones: dict[str, dict]) -> None:
        """Load persisted state and seed any zone seen for the first time.

        Zones removed from the configuration are dropped; new zones seed from
        their options record. The merged result is persisted so the on-disk shape
        always matches the current set of zones.
        """
        raw = await self._store.async_load() or {}
        persisted = raw.get("zones", {}) if isinstance(raw, dict) else {}

        states: dict[str, ZoneState] = {}
        for zone_id, record in zones.items():
            if zone_id in persisted:
                states[zone_id] = ZoneState.from_dict(zone_id, persisted[zone_id])
            else:
                states[zone_id] = seed_zone_state(zone_id, record)
        self.states = states
        await self.async_save()

    async def async_save(self) -> None:
        """Persist the current state for every zone."""
        await self._store.async_save(
            {"zones": {zone_id: state.to_dict() for zone_id, state in self.states.items()}}
        )

    def get(self, zone_id: str) -> ZoneState | None:
        """Return a zone's live state, or ``None`` when unknown."""
        return self.states.get(zone_id)
