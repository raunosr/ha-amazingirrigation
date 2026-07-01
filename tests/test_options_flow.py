"""Tests for the Amazing Irrigation options flow (zone management)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amazing_irrigation.const import (
    ACTUATOR_LINKTAP,
    ACTUATOR_SWITCH,
    CONF_ACTUATOR_SWITCH,
    CONF_ACTUATOR_TYPE,
    CONF_ET_SOURCE,
    CONF_FORECAST_AIR_HUMIDITY,
    CONF_FORECAST_AIR_TEMPERATURE,
    CONF_GREENHOUSE,
    CONF_HUMIDITY_SENSOR,
    CONF_LINKTAP_DEVICE,
    CONF_LINKTAP_ID,
    CONF_MOISTURE_SENSORS,
    CONF_NAME,
    CONF_OBSERVED_AIR_HUMIDITY,
    CONF_OBSERVED_AIR_TEMPERATURE,
    CONF_PROTECTED_RAIN,
    CONF_SCHEDULE_TIMES,
    CONF_SOIL_TYPE,
    CONF_SOLAR_RADIATION,
    CONF_TARGET_MOISTURE_HIGH,
    CONF_TARGET_MOISTURE_LOW,
    CONF_TEMPERATURE_SENSOR,
    CONF_VOLUME_SENSOR,
    CONF_WATERING_SENSOR,
    CONF_WEATHER_FORECAST_ENTITY,
    CONF_WIND_SPEED,
    CONF_ZONES,
    DOMAIN,
)


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_add_zone_creates_record(hass: HomeAssistant) -> None:
    """A user can create one observe-only Irrigation Zone."""
    entry = await _setup_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_zone"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Herb Bed",
            CONF_MOISTURE_SENSORS: ["sensor.gw2000a_soil_moisture_5"],
            CONF_OBSERVED_AIR_TEMPERATURE: "sensor.outdoor_temp",
            CONF_OBSERVED_AIR_HUMIDITY: "sensor.outdoor_humidity",
            CONF_FORECAST_AIR_TEMPERATURE: "sensor.forecast_temp",
            CONF_FORECAST_AIR_HUMIDITY: "sensor.forecast_humidity",
            CONF_WEATHER_FORECAST_ENTITY: "weather.home",
            CONF_WIND_SPEED: "sensor.wind_speed",
            CONF_SOLAR_RADIATION: "sensor.solar_radiation",
            CONF_TARGET_MOISTURE_LOW: 35,
            CONF_TARGET_MOISTURE_HIGH: 45,
            CONF_ET_SOURCE: "weather",
            CONF_SOIL_TYPE: "sandy",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    zones = entry.options[CONF_ZONES]
    assert len(zones) == 1
    record = next(iter(zones.values()))
    assert record[CONF_NAME] == "Herb Bed"
    assert record[CONF_MOISTURE_SENSORS] == ["sensor.gw2000a_soil_moisture_5"]
    assert record[CONF_OBSERVED_AIR_TEMPERATURE] == "sensor.outdoor_temp"
    assert record[CONF_OBSERVED_AIR_HUMIDITY] == "sensor.outdoor_humidity"
    assert record[CONF_FORECAST_AIR_TEMPERATURE] == "sensor.forecast_temp"
    assert record[CONF_FORECAST_AIR_HUMIDITY] == "sensor.forecast_humidity"
    assert record[CONF_WEATHER_FORECAST_ENTITY] == "weather.home"
    assert record[CONF_WIND_SPEED] == "sensor.wind_speed"
    assert record[CONF_SOLAR_RADIATION] == "sensor.solar_radiation"
    assert record[CONF_TARGET_MOISTURE_LOW] == 35
    assert record[CONF_TARGET_MOISTURE_HIGH] == 45
    assert record[CONF_ET_SOURCE] == "weather"
    assert record[CONF_SOIL_TYPE] == "sandy"


async def test_add_zone_time_pickers_map_to_schedule_times(
    hass: HomeAssistant,
) -> None:
    """Time-picker slots are collapsed into the stored HH:MM schedule list."""
    entry = await _setup_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Herb Bed",
            CONF_MOISTURE_SENSORS: ["sensor.gw2000a_soil_moisture_5"],
            "schedule_time_1": "06:00:00",
            "schedule_time_3": "20:30:00",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    record = next(iter(entry.options[CONF_ZONES].values()))
    assert record[CONF_SCHEDULE_TIMES] == ["06:00", "20:30"]


async def test_add_zone_requires_a_moisture_sensor(hass: HomeAssistant) -> None:
    """A zone cannot be created without at least one moisture sensor."""
    entry = await _setup_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_NAME: "Empty", CONF_MOISTURE_SENSORS: []}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_MOISTURE_SENSORS: "no_moisture_sensors"}
    assert CONF_ZONES not in entry.options


async def test_add_zone_validates_target_range(hass: HomeAssistant) -> None:
    """The optional target moisture range must be ordered."""
    entry = await _setup_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Herb Bed",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_TARGET_MOISTURE_LOW: 55,
            CONF_TARGET_MOISTURE_HIGH: 45,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TARGET_MOISTURE_HIGH: "target_range_invalid"}
    assert CONF_ZONES not in entry.options


async def test_edit_zone_updates_record(hass: HomeAssistant) -> None:
    """A user can edit an existing Irrigation Zone."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_ZONES: {
                "abc123": {
                    CONF_NAME: "Old Name",
                    CONF_MOISTURE_SENSORS: ["sensor.a"],
                }
            }
        },
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_zone"}
    )
    # Pick the zone to edit.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"zone": "abc123"}
    )
    assert result["step_id"] == "edit_zone"
    # Submit the edited values.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "New Name",
            CONF_MOISTURE_SENSORS: ["sensor.a", "sensor.b"],
            CONF_TARGET_MOISTURE_LOW: 32,
            CONF_TARGET_MOISTURE_HIGH: 44,
            CONF_WEATHER_FORECAST_ENTITY: "weather.updated",
            CONF_ET_SOURCE: "greenhouse",
            CONF_SOIL_TYPE: "clay",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    record = entry.options[CONF_ZONES]["abc123"]
    assert record[CONF_NAME] == "New Name"
    assert record[CONF_MOISTURE_SENSORS] == ["sensor.a", "sensor.b"]
    assert record[CONF_TARGET_MOISTURE_LOW] == 32
    assert record[CONF_TARGET_MOISTURE_HIGH] == 44
    assert record[CONF_WEATHER_FORECAST_ENTITY] == "weather.updated"
    assert record[CONF_ET_SOURCE] == "greenhouse"
    assert record[CONF_SOIL_TYPE] == "clay"


async def test_add_zone_with_switch_actuator_uses_actuator_step(
    hass: HomeAssistant,
) -> None:
    """Choosing an actuator routes to a second step with only its fields."""
    entry = await _setup_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    # Basics step: pick the switch actuator type.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Bed",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_ACTUATOR_TYPE: ACTUATOR_SWITCH,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "actuator"

    # Actuator step: only the switch field is relevant.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_ACTUATOR_SWITCH: "switch.valve"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    record = next(iter(entry.options[CONF_ZONES].values()))
    assert record[CONF_ACTUATOR_TYPE] == ACTUATOR_SWITCH
    assert record[CONF_ACTUATOR_SWITCH] == "switch.valve"


async def test_add_zone_linktap_actuator_step_validates(hass: HomeAssistant) -> None:
    """The LinkTap actuator step requires both a LinkTap id and a switch."""
    entry = await _setup_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Herbs",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_ACTUATOR_TYPE: ACTUATOR_LINKTAP,
        },
    )
    assert result["step_id"] == "actuator"

    # Missing id/switch is rejected on the actuator step.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_LINKTAP_ID: "ID1"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ACTUATOR_SWITCH: "linktap_requires_id_and_switch"}

    # Providing both completes the flow.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_LINKTAP_ID: "ID1", CONF_ACTUATOR_SWITCH: "switch.linktap"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    record = next(iter(entry.options[CONF_ZONES].values()))
    assert record[CONF_ACTUATOR_TYPE] == ACTUATOR_LINKTAP
    assert record[CONF_LINKTAP_ID] == "ID1"
    assert record[CONF_ACTUATOR_SWITCH] == "switch.linktap"


async def test_add_zone_linktap_device_autofills_entities(hass: HomeAssistant) -> None:
    """Selecting a LinkTap device auto-fills the id, switch and sensors."""
    entry = await _setup_entry(hass)

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("mqtt", "1F43B22F004B1200_4")},
        manufacturer="LinkTap",
        model="V1-4Z",
    )
    ent_reg = er.async_get(hass)
    for domain, suffix, unique in (
        ("switch", "water_switch", "sw"),
        ("binary_sensor", "is_watering", "bw"),
        ("sensor", "volume", "vol"),
        ("sensor", "volume_limit", "voll"),
    ):
        ent_reg.async_get_or_create(
            domain,
            "mqtt",
            unique,
            suggested_object_id=f"1f43b22f004b1200_4_{suffix}",
            config_entry=entry,
            device_id=device.id,
        )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Cones",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_ACTUATOR_TYPE: ACTUATOR_LINKTAP,
        },
    )
    assert result["step_id"] == "actuator"

    # Only the device is selected; everything else is derived.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_LINKTAP_DEVICE: device.id}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    record = next(iter(entry.options[CONF_ZONES].values()))
    assert record[CONF_ACTUATOR_TYPE] == ACTUATOR_LINKTAP
    assert record[CONF_LINKTAP_ID] == "1F43B22F004B1200_4"
    assert record[CONF_ACTUATOR_SWITCH] == "switch.1f43b22f004b1200_4_water_switch"
    assert record[CONF_WATERING_SENSOR] == "binary_sensor.1f43b22f004b1200_4_is_watering"
    assert record[CONF_VOLUME_SENSOR] == "sensor.1f43b22f004b1200_4_volume"


async def test_switch_actuator_autodetects_feedback_sensors(
    hass: HomeAssistant,
) -> None:
    """A LinkTap MQTT switch fills the feedback sensors in the Switch type."""
    entry = await _setup_entry(hass)

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("mqtt", "1F43B22F004B1200_4")},
        manufacturer="LinkTap",
        model="V1-4Z",
    )
    ent_reg = er.async_get(hass)
    for domain, suffix, unique in (
        ("switch", "water_switch", "sw"),
        ("binary_sensor", "is_watering", "bw"),
        ("sensor", "volume", "vol"),
        ("sensor", "volume_limit", "voll"),
    ):
        ent_reg.async_get_or_create(
            domain,
            "mqtt",
            unique,
            suggested_object_id=f"1f43b22f004b1200_4_{suffix}",
            config_entry=entry,
            device_id=device.id,
        )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Cones",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_ACTUATOR_TYPE: ACTUATOR_SWITCH,
        },
    )
    assert result["step_id"] == "actuator"

    # Only the actuator switch is chosen; the feedback sensors are derived
    # from the switch's MQTT device.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_ACTUATOR_SWITCH: "switch.1f43b22f004b1200_4_water_switch"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    record = next(iter(entry.options[CONF_ZONES].values()))
    assert record[CONF_ACTUATOR_TYPE] == ACTUATOR_SWITCH
    assert record[CONF_WATERING_SENSOR] == "binary_sensor.1f43b22f004b1200_4_is_watering"
    assert record[CONF_VOLUME_SENSOR] == "sensor.1f43b22f004b1200_4_volume"


async def test_remove_zone(hass: HomeAssistant) -> None:
    """A user can remove an Irrigation Zone."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_ZONES: {
                "abc123": {CONF_NAME: "Bed", CONF_MOISTURE_SENSORS: ["sensor.a"]}
            }
        },
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"zone": "abc123"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_ZONES] == {}


async def test_add_zone_greenhouse_shows_greenhouse_step(
    hass: HomeAssistant,
) -> None:
    """Marking a zone as a greenhouse routes to the greenhouse-only step."""
    entry = await _setup_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    # Basics step: mark this zone as a greenhouse.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Tunnel",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_GREENHOUSE: True,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "greenhouse"

    # Greenhouse step: only greenhouse-only inputs are collected here.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_PROTECTED_RAIN: True,
            CONF_TEMPERATURE_SENSOR: "sensor.gh_temp",
            CONF_HUMIDITY_SENSOR: "sensor.gh_humidity",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    record = next(iter(entry.options[CONF_ZONES].values()))
    assert record[CONF_GREENHOUSE] is True
    assert record[CONF_PROTECTED_RAIN] is True
    assert record[CONF_TEMPERATURE_SENSOR] == "sensor.gh_temp"
    assert record[CONF_HUMIDITY_SENSOR] == "sensor.gh_humidity"


async def test_add_zone_non_greenhouse_skips_greenhouse_step(
    hass: HomeAssistant,
) -> None:
    """A non-greenhouse zone never sees greenhouse-only inputs."""
    entry = await _setup_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_NAME: "Outdoor", CONF_MOISTURE_SENSORS: ["sensor.a"]},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    record = next(iter(entry.options[CONF_ZONES].values()))
    assert CONF_PROTECTED_RAIN not in record
    assert CONF_TEMPERATURE_SENSOR not in record
    assert CONF_HUMIDITY_SENSOR not in record


async def test_edit_zone_disabling_greenhouse_drops_greenhouse_fields(
    hass: HomeAssistant,
) -> None:
    """Turning off greenhouse mode discards greenhouse-only inputs."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_ZONES: {
                "abc123": {
                    CONF_NAME: "Tunnel",
                    CONF_MOISTURE_SENSORS: ["sensor.a"],
                    CONF_GREENHOUSE: True,
                    CONF_PROTECTED_RAIN: True,
                    CONF_TEMPERATURE_SENSOR: "sensor.gh_temp",
                    CONF_HUMIDITY_SENSOR: "sensor.gh_humidity",
                }
            }
        },
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"zone": "abc123"}
    )
    assert result["step_id"] == "edit_zone"
    # Submit basics with greenhouse turned off; no greenhouse step follows.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Tunnel",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_GREENHOUSE: False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    record = entry.options[CONF_ZONES]["abc123"]
    assert record.get(CONF_GREENHOUSE) is False
    assert CONF_PROTECTED_RAIN not in record
    assert CONF_TEMPERATURE_SENSOR not in record
    assert CONF_HUMIDITY_SENSOR not in record


async def test_edit_zone_greenhouse_prefills_existing_sensors(
    hass: HomeAssistant,
) -> None:
    """Editing a greenhouse zone prefills its greenhouse-only inputs."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_ZONES: {
                "abc123": {
                    CONF_NAME: "Tunnel",
                    CONF_MOISTURE_SENSORS: ["sensor.a"],
                    CONF_GREENHOUSE: True,
                    CONF_PROTECTED_RAIN: True,
                    CONF_TEMPERATURE_SENSOR: "sensor.gh_temp",
                    CONF_HUMIDITY_SENSOR: "sensor.gh_humidity",
                }
            }
        },
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "edit_zone"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"zone": "abc123"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Tunnel",
            CONF_MOISTURE_SENSORS: ["sensor.a"],
            CONF_GREENHOUSE: True,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "greenhouse"

    # Keep the prefilled sensors; only change protected_rain.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_PROTECTED_RAIN: False,
            CONF_TEMPERATURE_SENSOR: "sensor.gh_temp",
            CONF_HUMIDITY_SENSOR: "sensor.gh_humidity",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    record = entry.options[CONF_ZONES]["abc123"]
    assert record[CONF_TEMPERATURE_SENSOR] == "sensor.gh_temp"
    assert record[CONF_HUMIDITY_SENSOR] == "sensor.gh_humidity"
    assert record.get(CONF_PROTECTED_RAIN) in (False, None)
