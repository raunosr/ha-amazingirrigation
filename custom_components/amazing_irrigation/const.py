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

# Defaults for decision-tuning values.
DEFAULT_TARGET_MOISTURE = 40.0
DEFAULT_MAX_LITERS = 30.0
DEFAULT_RAIN_SKIP_MM = 3.0
DEFAULT_RAIN_SKIP_PROBABILITY = 60.0

# Services.
SERVICE_EVALUATE_ZONE = "evaluate_zone"

# Event fired when a Run Request is evaluated into an Irrigation Decision.
EVENT_DECISION = "amazing_irrigation_decision"

# hass.data[DOMAIN][entry_id] sub-key holding decision sensor entities by id.
DATA_DECISION_ENTITIES = "decision_entities"
