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
    ACTUATOR_LINKTAP,
    ACTUATOR_NONE,
    ACTUATOR_SCRIPT,
    ACTUATOR_SERVICE,
    ACTUATOR_SWITCH,
    ACTUATOR_TYPES,
    CONF_ACTUATOR_START_DATA,
    CONF_ACTUATOR_START_SCRIPT,
    CONF_ACTUATOR_START_SERVICE,
    CONF_ACTUATOR_STOP_DATA,
    CONF_ACTUATOR_STOP_SCRIPT,
    CONF_ACTUATOR_STOP_SERVICE,
    CONF_ACTUATOR_SWITCH,
    CONF_ACTUATOR_TYPE,
    CONF_AREA_M2,
    CONF_DEMAND_PROFILE,
    CONF_ENABLED,
    CONF_ET_SOURCE,
    CONF_FIELD_CAPACITY,
    CONF_FORECAST_AIR_HUMIDITY,
    CONF_FORECAST_AIR_TEMPERATURE,
    CONF_FORECAST_RAIN_AMOUNT,
    CONF_FORECAST_RAIN_PROBABILITY,
    CONF_GAIN_PER_LITER,
    CONF_GREENHOUSE,
    CONF_HISTORY_DAYS,
    CONF_HUMIDITY_SENSOR,
    CONF_LEARNING_ENABLED,
    CONF_LINKTAP_DEVICE,
    CONF_LINKTAP_FAILSAFE,
    CONF_LINKTAP_ID,
    CONF_LINKTAP_TOPIC,
    CONF_MAX_LITERS,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_OBSERVED_AIR_HUMIDITY,
    CONF_OBSERVED_AIR_TEMPERATURE,
    CONF_OBSERVED_RAIN_AMOUNT,
    CONF_PROTECTED_RAIN,
    CONF_RAIN_SKIP_MM,
    CONF_RAIN_SKIP_PROBABILITY,
    CONF_ROOT_DEPTH_MM,
    CONF_SAFETY_BLOCKERS,
    CONF_SCHEDULE_TIMES,
    CONF_SCHEDULE_WEEKDAYS,
    CONF_SEASON_END,
    CONF_SEASON_START,
    CONF_SOIL_TYPE,
    CONF_SOLAR_RADIATION,
    CONF_TARGET_MODE,
    CONF_TARGET_MOISTURE,
    CONF_TARGET_MOISTURE_HIGH,
    CONF_TARGET_MOISTURE_LOW,
    CONF_TEMPERATURE_SENSOR,
    CONF_VOLUME_FIELD,
    CONF_VOLUME_SENSOR,
    CONF_WATERING_SENSOR,
    CONF_WEATHER_FORECAST_ENTITY,
    CONF_WILTING_POINT,
    CONF_WIND_SPEED,
    CONF_ZONES,
    DEFAULT_HISTORY_DAYS_OPTION,
    DEFAULT_LINKTAP_FAILSAFE,
    DEFAULT_LINKTAP_TOPIC,
    DEFAULT_MAX_LITERS,
    DEFAULT_RAIN_SKIP_MM,
    DEFAULT_RAIN_SKIP_PROBABILITY,
    DEFAULT_TARGET_MOISTURE,
    DEFAULT_VOLUME_FIELD,
    DEMAND_PROFILE_OPTIONS,
    DOMAIN,
    HISTORY_DAYS_OPTIONS,
    INTEGRATION_TITLE,
    TARGET_MODE_OPTIONS,
    WEEKDAYS,
)
from .linktap import (
    async_resolve_linktap_device,
    async_resolve_linktap_from_entity,
)

# Up to three optional schedule start times are presented as individual time
# pickers (HA's TimeSelector has no multi-value mode) and mapped to/from the
# stored ``CONF_SCHEDULE_TIMES`` list of ``HH:MM`` strings.
SCHEDULE_TIME_SLOTS = ("schedule_time_1", "schedule_time_2", "schedule_time_3")
ET_SOURCE_OPTIONS = ("auto", "weather", "greenhouse")
SOIL_TYPE_OPTIONS = ("loam", "sand", "clay")


def _times_from_slots(user_input: dict[str, Any]) -> None:
    """Collapse the time-picker slots into ``CONF_SCHEDULE_TIMES`` (in place)."""
    times: list[str] = []
    for key in SCHEDULE_TIME_SLOTS:
        value = user_input.pop(key, None)
        if not value:
            continue
        parts = str(value).split(":")
        if len(parts) >= 2:
            times.append(f"{parts[0]}:{parts[1]}")
    if times:
        user_input[CONF_SCHEDULE_TIMES] = times
    else:
        user_input.pop(CONF_SCHEDULE_TIMES, None)


def _slots_from_times(record: dict[str, Any]) -> dict[str, str]:
    """Return time-picker slot suggestions for a stored zone record."""
    slots: dict[str, str] = {}
    times = record.get(CONF_SCHEDULE_TIMES) or []
    for slot_key, value in zip(SCHEDULE_TIME_SLOTS, times, strict=False):
        parts = str(value).split(":")
        if len(parts) >= 2:
            slots[slot_key] = f"{parts[0]}:{parts[1]}:00"
    return slots


def _zone_basics_schema() -> vol.Schema:
    """Build the schema for a zone's non-actuator settings.

    The Watering Actuator is configured in a dedicated follow-up step so each
    actuator type only shows its own fields.
    """
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
            vol.Optional(CONF_TARGET_MOISTURE_LOW): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=100, step=1, unit_of_measurement="%", mode="box"
                )
            ),
            vol.Optional(CONF_TARGET_MOISTURE_HIGH): selector.NumberSelector(
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
            vol.Optional(CONF_WEATHER_FORECAST_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="weather")
            ),
            vol.Optional(CONF_OBSERVED_RAIN_AMOUNT): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_OBSERVED_AIR_TEMPERATURE): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_OBSERVED_AIR_HUMIDITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_FORECAST_AIR_TEMPERATURE): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_FORECAST_AIR_HUMIDITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_WIND_SPEED): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_SOLAR_RADIATION): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_SAFETY_BLOCKERS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
            ),
            vol.Optional(CONF_FIELD_CAPACITY): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=100, step=1, unit_of_measurement="%", mode="box"
                )
            ),
            vol.Optional(CONF_WILTING_POINT): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=100, step=1, unit_of_measurement="%", mode="box"
                )
            ),
            vol.Optional(
                CONF_LEARNING_ENABLED, default=False
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_HISTORY_DAYS, default=DEFAULT_HISTORY_DAYS_OPTION
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(HISTORY_DAYS_OPTIONS),
                    translation_key="history_days",
                )
            ),
            vol.Optional(CONF_TARGET_MODE, default="auto"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(TARGET_MODE_OPTIONS), translation_key="target_mode"
                )
            ),
            vol.Optional(
                CONF_DEMAND_PROFILE, default="medium"
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(DEMAND_PROFILE_OPTIONS),
                    translation_key="demand_profile",
                )
            ),
            vol.Optional(CONF_ET_SOURCE, default="auto"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(ET_SOURCE_OPTIONS), translation_key="et_source"
                )
            ),
            vol.Optional(CONF_SOIL_TYPE, default="loam"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(SOIL_TYPE_OPTIONS), translation_key="soil_type"
                )
            ),
            vol.Optional(CONF_AREA_M2): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1,
                    max=1000.0,
                    step=0.1,
                    unit_of_measurement="m²",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_ROOT_DEPTH_MM): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=20.0,
                    max=2000.0,
                    step=10.0,
                    unit_of_measurement="mm",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_GREENHOUSE, default=False
            ): selector.BooleanSelector(),
            vol.Optional(CONF_SEASON_START): selector.TextSelector(),
            vol.Optional(CONF_SEASON_END): selector.TextSelector(),
            vol.Optional(CONF_ENABLED, default=True): selector.BooleanSelector(),
            vol.Optional(CONF_SCHEDULE_WEEKDAYS): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=WEEKDAYS,
                    multiple=True,
                    translation_key="weekday",
                )
            ),
            vol.Optional(SCHEDULE_TIME_SLOTS[0]): selector.TimeSelector(),
            vol.Optional(SCHEDULE_TIME_SLOTS[1]): selector.TimeSelector(),
            vol.Optional(SCHEDULE_TIME_SLOTS[2]): selector.TimeSelector(),
            vol.Optional(
                CONF_ACTUATOR_TYPE, default=ACTUATOR_NONE
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=ACTUATOR_TYPES, translation_key="actuator_type"
                )
            ),
        }
    )


def _greenhouse_schema() -> vol.Schema:
    """Build the schema for greenhouse-only inputs.

    These fields are collected in a dedicated step that is shown only when a
    zone is marked as a greenhouse zone, so non-greenhouse zones are not
    cluttered with rain-protection and local climate sensor inputs.
    """
    return vol.Schema(
        {
            vol.Optional(
                CONF_PROTECTED_RAIN, default=False
            ): selector.BooleanSelector(),
            vol.Optional(CONF_TEMPERATURE_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
            vol.Optional(CONF_HUMIDITY_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"])
            ),
        }
    )


def _actuator_schema(actuator_type: str) -> vol.Schema:
    """Build the schema for the selected Watering Actuator type only."""
    fields: dict[Any, Any] = {}

    if actuator_type == ACTUATOR_SWITCH:
        fields[vol.Optional(CONF_ACTUATOR_SWITCH)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="switch")
        )
    elif actuator_type == ACTUATOR_SERVICE:
        fields[vol.Optional(CONF_ACTUATOR_START_SERVICE)] = selector.TextSelector()
        fields[vol.Optional(CONF_ACTUATOR_START_DATA)] = selector.ObjectSelector()
        fields[vol.Optional(CONF_ACTUATOR_STOP_SERVICE)] = selector.TextSelector()
        fields[vol.Optional(CONF_ACTUATOR_STOP_DATA)] = selector.ObjectSelector()
        fields[
            vol.Optional(CONF_VOLUME_FIELD, default=DEFAULT_VOLUME_FIELD)
        ] = selector.TextSelector()
    elif actuator_type == ACTUATOR_SCRIPT:
        fields[vol.Optional(CONF_ACTUATOR_START_SCRIPT)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="script")
        )
        fields[vol.Optional(CONF_ACTUATOR_STOP_SCRIPT)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="script")
        )
    elif actuator_type == ACTUATOR_LINKTAP:
        fields[vol.Optional(CONF_LINKTAP_DEVICE)] = selector.DeviceSelector(
            selector.DeviceSelectorConfig(manufacturer="LinkTap")
        )
        fields[vol.Optional(CONF_LINKTAP_ID)] = selector.TextSelector()
        fields[vol.Optional(CONF_ACTUATOR_SWITCH)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="switch")
        )
        fields[
            vol.Optional(CONF_LINKTAP_TOPIC, default=DEFAULT_LINKTAP_TOPIC)
        ] = selector.TextSelector()
        fields[
            vol.Optional(CONF_LINKTAP_FAILSAFE, default=DEFAULT_LINKTAP_FAILSAFE)
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=900,
                max=21600,
                step=900,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="s",
            )
        )
        fields[
            vol.Optional(CONF_VOLUME_FIELD, default=DEFAULT_VOLUME_FIELD)
        ] = selector.TextSelector()

    # Feedback sensors apply to any actuating type.
    fields[vol.Optional(CONF_WATERING_SENSOR)] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="binary_sensor")
    )
    fields[vol.Optional(CONF_VOLUME_SENSOR)] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor")
    )
    return vol.Schema(fields)


# Actuator-detail fields cleared when a zone changes to a different actuator type.
_ACTUATOR_DETAIL_KEYS = (
    CONF_ACTUATOR_SWITCH,
    CONF_ACTUATOR_START_SERVICE,
    CONF_ACTUATOR_START_DATA,
    CONF_ACTUATOR_STOP_SERVICE,
    CONF_ACTUATOR_STOP_DATA,
    CONF_ACTUATOR_START_SCRIPT,
    CONF_ACTUATOR_STOP_SCRIPT,
    CONF_VOLUME_FIELD,
    CONF_WATERING_SENSOR,
    CONF_VOLUME_SENSOR,
    CONF_LINKTAP_DEVICE,
    CONF_LINKTAP_ID,
    CONF_LINKTAP_TOPIC,
    CONF_LINKTAP_FAILSAFE,
)


# Greenhouse-only fields cleared when a zone is no longer a greenhouse zone.
_GREENHOUSE_DETAIL_KEYS = (
    CONF_PROTECTED_RAIN,
    CONF_TEMPERATURE_SENSOR,
    CONF_HUMIDITY_SENSOR,
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
        self._zone_draft: dict[str, Any] = {}
        self._actuator_type: str = ACTUATOR_NONE
        self._actuator_suggested: dict[str, Any] = {}
        self._existing_record: dict[str, Any] = {}
        self._greenhouse_suggested: dict[str, Any] = {}

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
        """Collect a new zone's basics, then branch to the actuator step."""
        self._selected_zone_id = None
        errors: dict[str, str] = {}
        if user_input is not None:
            _times_from_slots(user_input)
            errors = _validate_zone_basics(user_input)
            if not errors:
                return await self._continue_from_basics(user_input)

        suggested = (
            {**user_input, **_slots_from_times(user_input)}
            if user_input is not None
            else {}
        )
        schema = self.add_suggested_values_to_schema(
            _zone_basics_schema(), suggested
        )
        return self.async_show_form(
            step_id="add_zone", data_schema=schema, errors=errors
        )

    async def async_step_edit_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick a zone to edit, then edit its basics and actuator."""
        zones = self._zones
        if self._selected_zone_id is None:
            if user_input is not None:
                self._selected_zone_id = user_input["zone"]
                return await self.async_step_edit_zone()
            return self.async_show_form(
                step_id="edit_zone", data_schema=_zone_picker_schema(zones)
            )

        record = zones.get(self._selected_zone_id, {})
        errors: dict[str, str] = {}
        if user_input is not None:
            _times_from_slots(user_input)
            errors = _validate_zone_basics(user_input)
            if not errors:
                return await self._continue_from_basics(user_input, existing=record)
            current = user_input
        else:
            current = record

        suggested = {**current, **_slots_from_times(current)}
        schema = self.add_suggested_values_to_schema(_zone_basics_schema(), suggested)
        return self.async_show_form(
            step_id="edit_zone", data_schema=schema, errors=errors
        )

    async def async_step_actuator(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the fields for the chosen Watering Actuator type only."""
        errors: dict[str, str] = {}
        if user_input is not None:
            resolved = self._resolve_actuator_input(user_input)
            errors = _validate_actuator_input(self._actuator_type, resolved)
            if not errors:
                record = {
                    **self._zone_draft,
                    **_clean_zone_input(resolved),
                    CONF_ACTUATOR_TYPE: self._actuator_type,
                }
                return self._persist(record)
            suggested = user_input
        else:
            suggested = self._actuator_suggested

        schema = self.add_suggested_values_to_schema(
            _actuator_schema(self._actuator_type), suggested
        )
        return self.async_show_form(
            step_id="actuator",
            data_schema=schema,
            errors=errors,
            description_placeholders={"actuator_type": self._actuator_type},
        )

    def _resolve_actuator_input(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Fill empty actuator fields from the underlying MQTT device.

        Two sources are tried, in order; any value the user typed wins:

        1. An explicit LinkTap *device* selection (LinkTap type only).
        2. The device of the chosen actuator *switch* — so a LinkTap MQTT
           switch auto-fills the watering/volume feedback sensors that live on
           the same device, for any actuator type.
        """
        merged = dict(user_input)

        if self._actuator_type == ACTUATOR_LINKTAP:
            device_id = merged.get(CONF_LINKTAP_DEVICE)
            if device_id:
                self._fill_from_resolution(
                    merged, async_resolve_linktap_device(self.hass, device_id)
                )

        switch = merged.get(CONF_ACTUATOR_SWITCH)
        if switch:
            resolution = async_resolve_linktap_from_entity(self.hass, switch)
            if resolution.watering_sensor and not merged.get(CONF_WATERING_SENSOR):
                merged[CONF_WATERING_SENSOR] = resolution.watering_sensor
            if resolution.volume_sensor and not merged.get(CONF_VOLUME_SENSOR):
                merged[CONF_VOLUME_SENSOR] = resolution.volume_sensor
            if (
                self._actuator_type == ACTUATOR_LINKTAP
                and resolution.linktap_id
                and not merged.get(CONF_LINKTAP_ID)
            ):
                merged[CONF_LINKTAP_ID] = resolution.linktap_id

        return merged

    def _fill_from_resolution(
        self, merged: dict[str, Any], resolution: Any
    ) -> None:
        """Fill empty merged fields from a LinkTap resolution (in place)."""
        derived = {
            CONF_LINKTAP_ID: resolution.linktap_id,
            CONF_ACTUATOR_SWITCH: resolution.switch,
            CONF_WATERING_SENSOR: resolution.watering_sensor,
            CONF_VOLUME_SENSOR: resolution.volume_sensor,
        }
        for key, value in derived.items():
            if value and not merged.get(key):
                merged[key] = value

    async def _continue_from_basics(
        self, basics: dict[str, Any], existing: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Store the basics, then branch to greenhouse settings or the actuator.

        Greenhouse-only inputs live on a dedicated step that appears only when
        the zone is marked as a greenhouse zone. A zone that is not (or no
        longer) a greenhouse never carries those fields, because the draft is
        rebuilt from the basics form which omits them.
        """
        self._zone_draft = _clean_zone_input(basics)
        self._actuator_type = basics.get(CONF_ACTUATOR_TYPE, ACTUATOR_NONE)
        self._existing_record = dict(existing or {})
        if basics.get(CONF_GREENHOUSE):
            self._greenhouse_suggested = {
                key: value
                for key, value in self._existing_record.items()
                if key in _GREENHOUSE_DETAIL_KEYS
            }
            return await self.async_step_greenhouse()
        return await self._continue_to_actuator()

    async def async_step_greenhouse(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect greenhouse-only inputs (shown only for greenhouse zones)."""
        if user_input is not None:
            self._zone_draft = {
                **self._zone_draft,
                **_clean_zone_input(user_input),
            }
            return await self._continue_to_actuator()

        schema = self.add_suggested_values_to_schema(
            _greenhouse_schema(), self._greenhouse_suggested
        )
        return self.async_show_form(step_id="greenhouse", data_schema=schema)

    async def _continue_to_actuator(self) -> ConfigFlowResult:
        """Finish (no actuator) or open the actuator step using the draft."""
        if self._actuator_type == ACTUATOR_NONE:
            # No actuator: drop any previously stored actuator detail fields.
            return self._persist(dict(self._zone_draft))
        self._actuator_suggested = {
            key: value
            for key, value in self._existing_record.items()
            if key in _ACTUATOR_DETAIL_KEYS
        }
        return await self.async_step_actuator()

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
    def _persist(self, record: dict[str, Any]) -> ConfigFlowResult:
        """Insert or update the drafted zone record and persist it."""
        zones = self._zones
        zone_id = self._selected_zone_id or uuid.uuid4().hex[:8]
        zones[zone_id] = record
        return self._save_zones(zones)

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


def _validate_zone_basics(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate the zone basics step; require at least one moisture sensor."""
    errors: dict[str, str] = {}
    if not user_input.get(CONF_MOISTURE_SENSORS):
        errors[CONF_MOISTURE_SENSORS] = "no_moisture_sensors"
    low = user_input.get(CONF_TARGET_MOISTURE_LOW)
    high = user_input.get(CONF_TARGET_MOISTURE_HIGH)
    if low not in (None, "") and high not in (None, "") and float(low) > float(high):
        errors[CONF_TARGET_MOISTURE_HIGH] = "target_range_invalid"
    return errors


def _validate_actuator_input(
    actuator_type: str, user_input: dict[str, Any]
) -> dict[str, str]:
    """Validate the actuator step for the selected actuator type."""
    errors: dict[str, str] = {}
    if actuator_type == ACTUATOR_LINKTAP:
        if not user_input.get(CONF_LINKTAP_ID):
            errors[CONF_LINKTAP_ID] = "linktap_requires_id_and_switch"
        if not user_input.get(CONF_ACTUATOR_SWITCH):
            errors[CONF_ACTUATOR_SWITCH] = "linktap_requires_id_and_switch"
    return errors


def _validate_zone_input(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate a complete zone record (basics + actuator) in one pass."""
    errors = _validate_zone_basics(user_input)
    errors.update(
        _validate_actuator_input(
            user_input.get(CONF_ACTUATOR_TYPE, ACTUATOR_NONE), user_input
        )
    )
    return errors


def _clean_zone_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Drop empty optional values so stored records stay tidy."""
    return {
        key: value for key, value in user_input.items() if value not in (None, "", [])
    }
