"""Constants for the Amazing Irrigation integration."""

from __future__ import annotations

from datetime import timedelta

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
CONF_WEATHER_FORECAST_ENTITY = "weather_forecast_entity"
CONF_OBSERVED_RAIN_AMOUNT = "observed_rain_amount"
CONF_SAFETY_BLOCKERS = "safety_blockers"

# Decision-tuning keys (used by the Irrigation Decision engine).
CONF_TARGET_MOISTURE = "target_moisture"
CONF_TARGET_MOISTURE_LOW = "target_moisture_low"
CONF_TARGET_MOISTURE_HIGH = "target_moisture_high"
CONF_MAX_LITERS = "max_liters"
CONF_GAIN_PER_LITER = "gain_per_liter"
CONF_RAIN_SKIP_MM = "rain_skip_mm"
CONF_RAIN_SKIP_PROBABILITY = "rain_skip_probability"
CONF_SEASON_START = "season_start"
CONF_SEASON_END = "season_end"
CONF_ET_SOURCE = "et_source"
CONF_SOIL_TYPE = "soil_type"

# Depth (mm) at which the moisture sensor is installed. Diagnostic only: a sensor
# much shallower than the root zone over-reports drying and can over-trigger.
CONF_SENSOR_DEPTH_MM = "sensor_depth_mm"

# Continuous rain influence (0-100 %) replacing the binary protected-rain flag.
# 100 = fully exposed (outdoor), 0 = fully protected (greenhouse), values between
# for covered zones. Applied to effective rainfall in the decision engine.
CONF_RAIN_FRACTION = "rain_fraction"

# Smallest worthwhile application per run. Below this the run is skipped unless a
# heat emergency overrides it. Stored in liters (mm converted via area_m2).
CONF_MIN_APPLICATION = "min_application"

# Optional physical zone geometry: irrigated area (m^2) and effective root-zone
# depth (mm). When provided they seed physical eta priors and couple irrigation
# and rain efficiency (eta_rain ~= eta_irr * area). Both are optional.
CONF_AREA_M2 = "area_m2"
CONF_ROOT_DEPTH_MM = "root_depth_mm"

# Advanced per-zone calibration keys (visible, manually set in this slice).
CONF_FIELD_CAPACITY = "field_capacity"
CONF_WILTING_POINT = "wilting_point"
CONF_LEARNING_ENABLED = "learning_enabled"
CONF_HISTORY_DAYS = "history_days"
CONF_DEMAND_PROFILE = "demand_profile"
CONF_TARGET_MODE = "target_mode"

# Lookback window options (days) for the history bootstrap selector.
HISTORY_DAYS_OPTIONS = ("14", "30", "60", "90")
DEFAULT_HISTORY_DAYS_OPTION = "60"

# Plant water-demand profile + target-moisture mode selector options.
DEMAND_PROFILE_OPTIONS = ("low", "medium", "high")
TARGET_MODE_OPTIONS = ("auto", "manual")

# Soil-type presets shown in the config flow and the SELECT entity. The first
# five mirror the guided soil table (Sandy 20 %, Standard mineral 30 %, Good
# garden 40 %, Peat/compost 47 %, Greenhouse/potting 52 % field capacity);
# ``clay`` is retained for backward compatibility with pre-0.18 zones.
SOIL_TYPE_OPTIONS = (
    "sandy",
    "standard_mineral",
    "good_garden",
    "peat_compost",
    "potting_mix",
    "clay",
)
DEFAULT_SOIL_TYPE = "good_garden"

# Migration of legacy soil-type keys (pre-0.18) onto the new preset set.
SOIL_TYPE_MIGRATION = {
    "sand": "sandy",
    "loam": "good_garden",
    "clay": "clay",
}

# Greenhouse Zone keys (a zone subtype with protected-environment context).
CONF_GREENHOUSE = "greenhouse"
CONF_PROTECTED_RAIN = "protected_rain"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"

# Optional ET / climate inputs for the physics-based soil model.
CONF_OBSERVED_AIR_TEMPERATURE = "observed_air_temperature"
CONF_OBSERVED_AIR_HUMIDITY = "observed_air_humidity"
CONF_FORECAST_AIR_TEMPERATURE = "forecast_air_temperature"
CONF_FORECAST_AIR_HUMIDITY = "forecast_air_humidity"
CONF_WIND_SPEED = "wind_speed"
CONF_SOLAR_RADIATION = "solar_radiation"

# Bounded Irrigation History size kept per zone for explainability.
HISTORY_LIMIT = 50

# hass.data[DOMAIN][entry_id] sub-key holding IrrigationHistory by zone_id.
DATA_HISTORY = "history"

# hass.data[DOMAIN][entry_id] sub-key holding the RainWatcher list.
DATA_RAIN_WATCHERS = "rain_watchers"

# hass.data[DOMAIN][entry_id] sub-key holding the WeatherForecastProvider.
DATA_WEATHER_PROVIDER = "weather_provider"

# hass.data[DOMAIN] sub-key holding cached weather forecast series by entity id.
DATA_WEATHER_FORECAST = "weather_forecast"

# How often weather forecast series are refreshed from Home Assistant.
WEATHER_FORECAST_REFRESH_INTERVAL = timedelta(minutes=30)

# hass.data[DOMAIN] flag marking the Lovelace card frontend resource registered.
DATA_CARD_REGISTERED = "card_registered"

# Per-zone enablement and built-in scheduling keys.
CONF_ENABLED = "enabled"
CONF_SCHEDULE_WEEKDAYS = "schedule_weekdays"
CONF_SCHEDULE_TIMES = "schedule_times"

# Default evening watering time used when a zone has no configured schedule.
DEFAULT_SCHEDULE_TIME = "21:00"

# Persistent ZoneState store (live tunables, learned params, cumulative volume).
STORAGE_VERSION = 1

# hass.data[DOMAIN][entry_id] sub-key holding the ZoneStateStore.
DATA_ZONE_STATE = "zone_state"

# hass.data[DOMAIN][entry_id] sub-key holding ZoneLearner objects by zone_id.
DATA_LEARNERS = "learners"

# Weekday tokens used by zone schedules (Monday = index 0).
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# hass.data[DOMAIN][entry_id] sub-key holding the IrrigationScheduler.
DATA_SCHEDULER = "scheduler"

# Defaults for decision-tuning values.
DEFAULT_TARGET_MOISTURE = 40.0
DEFAULT_MAX_LITERS = 30.0
DEFAULT_RAIN_SKIP_MM = 3.0
DEFAULT_RAIN_SKIP_PROBABILITY = 60.0

# Default continuous rain influence (fully exposed) and greenhouse override.
DEFAULT_RAIN_FRACTION = 100.0
GREENHOUSE_RAIN_FRACTION = 0.0

# Default smallest worthwhile application per run, in liters. Matches the legacy
# hard-coded ``MIN_EFFECTIVE_LITERS`` so behaviour is unchanged until edited.
DEFAULT_MIN_APPLICATION = 0.1

# Heat-emergency override thresholds. A ``high`` demand zone that is below its
# trigger will water even below ``min_application`` when air temperature or vapour
# pressure deficit exceed these limits.
HEAT_EMERGENCY_TEMP_C = 32.0
HEAT_EMERGENCY_VPD_KPA = 2.2

# Default effective root-zone depth (mm) used when area is set without a depth.
DEFAULT_ROOT_DEPTH_MM = 200.0

# Services.
SERVICE_EVALUATE_ZONE = "evaluate_zone"
SERVICE_RUN_ZONE = "run_zone"
SERVICE_STOP_ZONE = "stop_zone"
SERVICE_RELEARN_FROM_HISTORY = "relearn_from_history"
SERVICE_START_DISCOVERY = "start_field_capacity_discovery"

# hass.data[DOMAIN][entry_id] sub-key holding DiscoveryController by zone_id.
DATA_DISCOVERY = "discovery"

# Guided Field Capacity Discovery phases (persisted in ZoneState.discovery).
DISCOVERY_IDLE = "idle"
DISCOVERY_AWAITING_SATURATION = "awaiting_saturation"
DISCOVERY_MONITORING = "monitoring"
DISCOVERY_COMPLETED = "completed"
DISCOVERY_FAILED = "failed"
DISCOVERY_CANCELLED = "cancelled"

# Field Capacity Discovery tuning defaults. The stop criterion is a drainage-rate
# knee (FAO-56 Drained Upper Limit), not a fixed clock: FC is recorded once the
# moisture drop rate falls below a threshold that is relative to the initial
# post-saturation drainage rate (texture-adaptive) with a small absolute floor,
# bounded by a minimum wait (ignore the early transient plateau) and a maximum
# wait (graceful fallback). Values are in sensor moisture-% space.
DISCOVERY_SAMPLE_INTERVAL = timedelta(minutes=10)
DISCOVERY_MIN_WAIT_HOURS = 12.0
DISCOVERY_MAX_WAIT_HOURS = 48.0
DISCOVERY_STABILITY_WINDOW_HOURS = 2.0
DISCOVERY_RATE_RELATIVE_STOP = 0.12
DISCOVERY_RATE_ABS_FLOOR = 0.2
DISCOVERY_RISE_ABORT_DELTA = 3.0

# Event fired when a Run Request is evaluated into an Irrigation Decision.
EVENT_DECISION = "amazing_irrigation_decision"

# Event fired when a Watering Event changes state (commanded/confirmed/...).
EVENT_WATERING = "amazing_irrigation_watering"

# hass.data[DOMAIN][entry_id] sub-key holding decision sensor entities by id.
DATA_DECISION_ENTITIES = "decision_entities"

# hass.data[DOMAIN][entry_id] sub-key holding Model Insight sensors by zone_id.
DATA_MODEL_INSIGHT_ENTITIES = "model_insight_entities"

# hass.data[DOMAIN][entry_id] sub-key holding Target Range sensors by zone_id.
DATA_TARGET_RANGE_ENTITIES = "target_range_entities"

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
CONF_LINKTAP_DEVICE = "linktap_device"

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
