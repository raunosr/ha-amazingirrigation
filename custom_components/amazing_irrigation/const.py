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
