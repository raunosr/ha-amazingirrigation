"""Config and options flow for the Amazing Irrigation integration.

The integration is a single hub instance. Irrigation Zones are created and
edited through this entry's *options* flow using Home Assistant entity
selectors, and stored as records under ``options[CONF_ZONES]`` keyed by a
generated ``zone_id``. This slice is observe-only: zones select moisture and
typed environmental/safety inputs but cannot actuate water.
"""

from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    ACTUATOR_NONE,
    ACTUATOR_TYPES,
    CONF_ACTUATOR_START_DATA,
    CONF_ACTUATOR_START_SCRIPT,
    CONF_ACTUATOR_START_SERVICE,
    CONF_ACTUATOR_STOP_DATA,
    CONF_ACTUATOR_STOP_SCRIPT,
    CONF_ACTUATOR_STOP_SERVICE,
    CONF_ACTUATOR_SWITCH,
    CONF_ACTUATOR_TYPE,
    CONF_FORECAST_RAIN_AMOUNT,
    CONF_FORECAST_RAIN_PROBABILITY,
    CONF_GAIN_PER_LITER,
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_OBSERVED_RAIN_AMOUNT,
    CONF_RAIN_SKIP_MM,
    CONF_RAIN_SKIP_PROBABILITY,
    CONF_SAFETY_BLOCKERS,
    CONF_SEASON_END,
    CONF_SEASON_START,
    CONF_TARGET_MOISTURE,
    CONF_VOLUME_FIELD,
    CONF_VOLUME_SENSOR,
    CONF_WATERING_SENSOR,
    CONF_ZONES,
    DEFAULT_MAX_LITERS,
    DEFAULT_RAIN_SKIP_MM,
    DEFAULT_RAIN_SKIP_PROBABILITY,
    DEFAULT_TARGET_MOISTURE,
    DEFAULT_VOLUME_FIELD,
    DOMAIN,
    INTEGRATION_TITLE,
)


def _zone_schema() -> vol.Schema:
    """Build the schema for creating or editing an Irrigation Zone."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME): selector.TextSelector(),
            vol.Required(CONF_MOISTURE_SENSORS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", multiple=True)
            ),
            vol.Optional(
                CONF_TARGET_MOISTURE, default=DEFAULT_TARGET_MOISTURE
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=100, step=1, unit_of_measurement="%", mode="box"
                )
            ),
            vol.Optional(
                CONF_MAX_LITERS, default=DEFAULT_MAX_LITERS
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=1000, step=1, unit_of_measurement="L", mode="box"
                )
            ),
            vol.Optional(CONF_GAIN_PER_LITER): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, step=0.1, unit_of_measurement="%/L", mode="box"
                )
            ),
            vol.Optional(
                CONF_RAIN_SKIP_MM, default=DEFAULT_RAIN_SKIP_MM
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, step=0.5, unit_of_measurement="mm", mode="box"
                )
            ),
            vol.Optional(
                CONF_RAIN_SKIP_PROBABILITY, default=DEFAULT_RAIN_SKIP_PROBABILITY
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=100, step=5, unit_of_measurement="%", mode="box"
                )
            ),
            vol.Optional(CONF_FORECAST_RAIN_AMOUNT): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_FORECAST_RAIN_PROBABILITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_OBSERVED_RAIN_AMOUNT): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_SAFETY_BLOCKERS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
            ),
            vol.Optional(CONF_SEASON_START): selector.TextSelector(),
            vol.Optional(CONF_SEASON_END): selector.TextSelector(),
            vol.Optional(
                CONF_ACTUATOR_TYPE, default=ACTUATOR_NONE
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=ACTUATOR_TYPES, translation_key="actuator_type"
                )
            ),
            vol.Optional(CONF_ACTUATOR_SWITCH): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch")
            ),
            vol.Optional(CONF_ACTUATOR_START_SERVICE): selector.TextSelector(),
            vol.Optional(CONF_ACTUATOR_START_DATA): selector.ObjectSelector(),
            vol.Optional(CONF_ACTUATOR_STOP_SERVICE): selector.TextSelector(),
            vol.Optional(CONF_ACTUATOR_STOP_DATA): selector.ObjectSelector(),
            vol.Optional(CONF_ACTUATOR_START_SCRIPT): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="script")
            ),
            vol.Optional(CONF_ACTUATOR_STOP_SCRIPT): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="script")
            ),
            vol.Optional(
                CONF_VOLUME_FIELD, default=DEFAULT_VOLUME_FIELD
            ): selector.TextSelector(),
            vol.Optional(CONF_WATERING_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            vol.Optional(CONF_VOLUME_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        }
    )


class AmazingIrrigationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Amazing Irrigation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the single Amazing Irrigation hub instance."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title=INTEGRATION_TITLE, data={})

        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> AmazingIrrigationOptionsFlow:
        """Return the options flow that manages Irrigation Zones."""
        return AmazingIrrigationOptionsFlow()


class AmazingIrrigationOptionsFlow(OptionsFlow):
    """Manage Irrigation Zones stored in the entry options."""

    def __init__(self) -> None:
        """Initialise transient flow state."""
        self._selected_zone_id: str | None = None

    @property
    def _zones(self) -> dict[str, dict[str, Any]]:
        """Return a copy of the stored zone records."""
        return dict(self.config_entry.options.get(CONF_ZONES, {}))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the zone management menu."""
        menu_options = ["add_zone"]
        if self._zones:
            menu_options += ["edit_zone", "remove_zone"]
        return self.async_show_menu(step_id="init", menu_options=menu_options)

    async def async_step_add_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a new Irrigation Zone."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_zone_input(user_input)
            if not errors:
                zone_id = uuid.uuid4().hex[:8]
                zones = self._zones
                zones[zone_id] = _clean_zone_input(user_input)
                return self._save_zones(zones)

        return self.async_show_form(
            step_id="add_zone", data_schema=_zone_schema(), errors=errors
        )

    async def async_step_edit_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick a zone to edit, then edit it."""
        zones = self._zones
        if self._selected_zone_id is None:
            if user_input is not None:
                self._selected_zone_id = user_input["zone"]
                return await self.async_step_edit_zone()
            return self.async_show_form(
                step_id="edit_zone", data_schema=_zone_picker_schema(zones)
            )

        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_zone_input(user_input)
            if not errors:
                zones[self._selected_zone_id] = _clean_zone_input(user_input)
                return self._save_zones(zones)
            current = user_input
        else:
            current = zones.get(self._selected_zone_id, {})

        schema = self.add_suggested_values_to_schema(_zone_schema(), current)
        return self.async_show_form(
            step_id="edit_zone", data_schema=schema, errors=errors
        )

    async def async_step_remove_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove an existing Irrigation Zone."""
        zones = self._zones
        if user_input is not None:
            zones.pop(user_input["zone"], None)
            return self._save_zones(zones)

        return self.async_show_form(
            step_id="remove_zone", data_schema=_zone_picker_schema(zones)
        )

    @callback
    def _save_zones(self, zones: dict[str, dict[str, Any]]) -> ConfigFlowResult:
        """Persist the updated zone records to the entry options."""
        options = dict(self.config_entry.options)
        options[CONF_ZONES] = zones
        return self.async_create_entry(title="", data=options)


def _zone_picker_schema(zones: dict[str, dict[str, Any]]) -> vol.Schema:
    """Build a schema for selecting an existing zone."""
    options = [
        selector.SelectOptionDict(value=zone_id, label=record.get(CONF_NAME, zone_id))
        for zone_id, record in zones.items()
    ]
    return vol.Schema(
        {
            vol.Required("zone"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options)
            )
        }
    )


def _validate_zone_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate zone input; require at least one moisture sensor."""
    errors: dict[str, str] = {}
    if not user_input.get(CONF_MOISTURE_SENSORS):
        errors[CONF_MOISTURE_SENSORS] = "no_moisture_sensors"
    return errors


def _clean_zone_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Drop empty optional values so stored records stay tidy."""
    return {
        key: value for key, value in user_input.items() if value not in (None, "", [])
    }
