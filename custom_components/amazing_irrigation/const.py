"""Constants for the Amazing Irrigation integration."""

from __future__ import annotations

DOMAIN = "amazing_irrigation"

# Title shown for the single integration config entry.
INTEGRATION_TITLE = "Amazing Irrigation"

# Options key holding the mapping of zone_id -> zone configuration record.
CONF_ZONES = "zones"

# Per-zone configuration keys.
CONF_ZONE_ID = "zone_id"
CONF_NAME = "name"
CONF_MOISTURE_SENSORS = "moisture_sensors"
CONF_FORECAST_RAIN_AMOUNT = "forecast_rain_amount"
CONF_FORECAST_RAIN_PROBABILITY = "forecast_rain_probability"
CONF_OBSERVED_RAIN_AMOUNT = "observed_rain_amount"
CONF_SAFETY_BLOCKERS = "safety_blockers"

# Decision-tuning keys (used by the Irrigation Decision engine).
CONF_TARGET_MOISTURE = "target_moisture"
CONF_MAX_LITERS = "max_liters"
CONF_GAIN_PER_LITER = "gain_per_liter"
CONF_RAIN_SKIP_MM = "rain_skip_mm"
CONF_RAIN_SKIP_PROBABILITY = "rain_skip_probability"
CONF_SEASON_START = "season_start"
CONF_SEASON_END = "season_end"

# Per-zone enablement and built-in scheduling keys.
CONF_ENABLED = "enabled"
CONF_SCHEDULE_WEEKDAYS = "schedule_weekdays"
CONF_SCHEDULE_TIMES = "schedule_times"

# Weekday tokens used by zone schedules (Monday = index 0).
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# hass.data[DOMAIN][entry_id] sub-key holding the IrrigationScheduler.
DATA_SCHEDULER = "scheduler"

# Defaults for decision-tuning values.
DEFAULT_TARGET_MOISTURE = 40.0
DEFAULT_MAX_LITERS = 30.0
DEFAULT_RAIN_SKIP_MM = 3.0
DEFAULT_RAIN_SKIP_PROBABILITY = 60.0

# Services.
SERVICE_EVALUATE_ZONE = "evaluate_zone"
SERVICE_RUN_ZONE = "run_zone"
SERVICE_STOP_ZONE = "stop_zone"

# Event fired when a Run Request is evaluated into an Irrigation Decision.
EVENT_DECISION = "amazing_irrigation_decision"

# Event fired when a Watering Event changes state (commanded/confirmed/...).
EVENT_WATERING = "amazing_irrigation_watering"

# hass.data[DOMAIN][entry_id] sub-key holding decision sensor entities by id.
DATA_DECISION_ENTITIES = "decision_entities"

# hass.data[DOMAIN][entry_id] sub-key holding WateringController by zone_id.
DATA_CONTROLLERS = "controllers"

# Watering Actuator config keys.
CONF_ACTUATOR_TYPE = "actuator_type"
CONF_ACTUATOR_SWITCH = "actuator_switch"
CONF_ACTUATOR_START_SERVICE = "actuator_start_service"
CONF_ACTUATOR_START_DATA = "actuator_start_data"
CONF_ACTUATOR_STOP_SERVICE = "actuator_stop_service"
CONF_ACTUATOR_STOP_DATA = "actuator_stop_data"
CONF_ACTUATOR_START_SCRIPT = "actuator_start_script"
CONF_ACTUATOR_STOP_SCRIPT = "actuator_stop_script"
CONF_VOLUME_FIELD = "volume_field"
CONF_WATERING_SENSOR = "watering_sensor"
CONF_VOLUME_SENSOR = "volume_sensor"

# LinkTap/MQTT actuator config keys.
CONF_LINKTAP_TOPIC = "linktap_topic"
CONF_LINKTAP_ID = "linktap_id"
CONF_LINKTAP_FAILSAFE = "linktap_failsafe"

# Actuator types.
ACTUATOR_NONE = "none"
ACTUATOR_SWITCH = "switch"
ACTUATOR_SERVICE = "service"
ACTUATOR_SCRIPT = "script"
ACTUATOR_LINKTAP = "linktap"
ACTUATOR_TYPES = [
    ACTUATOR_NONE,
    ACTUATOR_SWITCH,
    ACTUATOR_SERVICE,
    ACTUATOR_SCRIPT,
    ACTUATOR_LINKTAP,
]

# Default variable/field name used to inject the bounded Watering Volume.
DEFAULT_VOLUME_FIELD = "volume"

# LinkTap defaults matching the current MQTT script pattern.
DEFAULT_LINKTAP_TOPIC = "/homeassistant/config_from_ha"
DEFAULT_LINKTAP_FAILSAFE = 3600
