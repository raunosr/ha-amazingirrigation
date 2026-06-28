"""Run and Stop buttons for Amazing Irrigation zones.

Each zone gets a Run button that creates a Run Request and waters when the
decision allows. A Stop button is created only when the zone's actuator exposes
an explicit stop path, matching the requirement to hide stop when unsupported.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ZONES, DATA_CONTROLLERS, DATA_ZONE_STATE, DOMAIN
from .history_ingest import async_bootstrap_zone
from .state import ZoneStateStore
from .watering import WateringController
from .zone import ZoneConfig


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Run/Stop buttons for each configured zone."""
    controllers: dict[str, WateringController] = hass.data[DOMAIN][entry.entry_id][
        DATA_CONTROLLERS
    ]
    store: ZoneStateStore = hass.data[DOMAIN][entry.entry_id][DATA_ZONE_STATE]
    zones = entry.options.get(CONF_ZONES, {})

    entities: list[ButtonEntity] = []
    for zone_id, record in zones.items():
        controller = controllers.get(zone_id)
        if controller is None:
            continue
        zone = ZoneConfig.from_record(zone_id, record)
        entities.append(RunZoneButton(entry, zone, controller))
        entities.append(RelearnHistoryButton(hass, entry, zone, store))
        if controller.can_stop:
            entities.append(StopZoneButton(entry, zone, controller))
    async_add_entities(entities)


def _zone_device_info(entry: ConfigEntry, zone: ZoneConfig) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{zone.zone_id}")},
        name=zone.name,
        manufacturer="Amazing Irrigation",
        model="Irrigation Zone",
    )


class RunZoneButton(ButtonEntity):
    """Create a Run Request and water the zone if the decision allows."""

    _attr_has_entity_name = True
    _attr_name = "Run"
    _attr_icon = "mdi:water"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, controller: WateringController
    ) -> None:
        """Initialise the run button for a zone."""
        self._controller = controller
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_run"
        self._attr_device_info = _zone_device_info(entry, zone)

    async def async_press(self) -> None:
        """Handle a button press by running the zone through the engine."""
        await self._controller.async_run()


class StopZoneButton(ButtonEntity):
    """Stop an in-progress Watering Event (only when stop is configured)."""

    _attr_has_entity_name = True
    _attr_name = "Stop"
    _attr_icon = "mdi:stop"

    def __init__(
        self, entry: ConfigEntry, zone: ZoneConfig, controller: WateringController
    ) -> None:
        """Initialise the stop button for a zone."""
        self._controller = controller
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_stop"
        self._attr_device_info = _zone_device_info(entry, zone)

    async def async_press(self) -> None:
        """Handle a button press by stopping watering."""
        await self._controller.async_stop()


class RelearnHistoryButton(ButtonEntity):
    """Re-fit a zone's water-balance model from recorder history."""

    _attr_has_entity_name = True
    _attr_name = "Re-learn from History"
    _attr_icon = "mdi:history"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        zone: ZoneConfig,
        store: ZoneStateStore,
    ) -> None:
        """Initialise the history relearn button for a zone."""
        self._hass = hass
        self._zone = zone
        self._store = store
        self._attr_unique_id = f"{entry.entry_id}_{zone.zone_id}_relearn"
        self._attr_device_info = _zone_device_info(entry, zone)

    async def async_press(self) -> None:
        """Handle a button press by bootstrapping from recorder history."""
        await async_bootstrap_zone(self._hass, self._zone, self._store)
