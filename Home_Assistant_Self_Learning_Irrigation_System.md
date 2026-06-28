# Home Assistant Self-Learning Irrigation System

## Overview

This document describes a self-learning irrigation controller for Home
Assistant. The goal is to optimize irrigation using:

-   Soil moisture sensors (one per irrigation zone)
-   Weather observations
-   Rain forecast
-   Temperature forecast
-   Precise irrigation control (liters per zone)

Instead of relying on fixed thresholds, the system continuously learns
the characteristics of each irrigation zone.

------------------------------------------------------------------------

# Objectives

The system should automatically:

1.  Learn the soil field capacity.
2.  Estimate the effective wilting point.
3.  Learn how many liters are required to increase soil moisture.
4.  Predict daily moisture loss.
5.  Account for rainfall before irrigating.
6.  Calculate the optimal irrigation volume for every zone.

------------------------------------------------------------------------

# Zone Model

Each irrigation zone maintains its own model.

## Static Parameters

-   Soil moisture sensor
-   Irrigation valve
-   Water flow (L/min)

## Learned Parameters

-   Field Capacity (FC)
-   Wilting Point (WP)
-   Moisture Gain per Liter
-   Daily Drying Model
-   Rain Efficiency

------------------------------------------------------------------------

# Learning Field Capacity

## Principle

After heavy rainfall or irrigation, excess water drains through the
soil.

The stabilized moisture value measured after drainage is considered the
Field Capacity.

## Detection

If:

-   Rain + irrigation exceeds a configurable threshold
-   Moisture stabilizes after 6--24 hours
-   Moisture decline becomes minimal

then:

FC = 95% previous FC + 5% new observation

This continuously improves the estimate.

------------------------------------------------------------------------

# Learning the Wilting Point

The true wilting point depends on soil and plant species.

Instead of allowing plants to wilt, the system estimates a safe
practical minimum.

Initial value:

-   User configurable

Learning:

-   Slowly adjust using long-term minimum healthy moisture values
-   Never decrease faster than a configurable safety limit

------------------------------------------------------------------------

# Learning Moisture Gain per Liter

For every irrigation event:

Record:

-   Moisture before irrigation
-   Irrigation volume (L)
-   Moisture 1--3 hours after irrigation

Example:

Before: 31%

Applied: 12 L

After: 39%

Gain:

8% / 12 L = 0.67% per liter

Update using exponential moving average:

NewGain = 0.95 × OldGain + 0.05 × Observation

------------------------------------------------------------------------

# Learning Rain Efficiency

Rainfall does not affect every zone equally.

For each rainfall event:

Record:

-   Rainfall (mm)
-   Moisture increase

Example:

10 mm rain

↓

+6% soil moisture

Rain efficiency becomes another learned parameter.

------------------------------------------------------------------------

# Daily Drying Model

Every night calculate:

Daily Moisture Loss = Yesterday Moisture - Today Moisture

Store together with:

-   Average temperature
-   Maximum temperature
-   Rainfall
-   Solar radiation (optional)
-   Wind speed (optional)
-   Humidity (optional)

This creates a predictive drying model.

------------------------------------------------------------------------

# Available Water

Available Water (AW):

AW = FC - WP

Current Available Water (%):

(Current Moisture - WP) / (FC - WP)

×100

Interpretation:

# 100%

Field Capacity

# 0%

Wilting Point

------------------------------------------------------------------------

# Irrigation Target

Instead of filling soil to Field Capacity every time:

Target Moisture = WP + 75--90% of Available Water

This avoids water loss due to drainage.

------------------------------------------------------------------------

# Irrigation Volume Calculation

Known:

Current Moisture

Target Moisture

Gain per Liter

Required Increase:

Target - Current

Liters Required:

Required Increase / GainPerLiter

Example:

Current: 35%

Target: 45%

Gain: 0.7% / L

Increase: 10%

Liters:

10 / 0.7

≈14 L

------------------------------------------------------------------------

# Rain Forecast Logic

Before irrigation:

If forecast rain exceeds configurable threshold (for example 5 mm):

Reduce irrigation or skip it completely.

Possible strategy:

Forecast \> 10 mm

→ Skip irrigation

Forecast 5--10 mm

→ Reduce irrigation proportionally

Forecast \< 5 mm

→ Normal irrigation

------------------------------------------------------------------------

# Home Assistant Entities

## Learned Sensors

-   sensor.zone_field_capacity
-   sensor.zone_wilting_point
-   sensor.zone_gain_per_liter
-   sensor.zone_daily_drying_rate
-   sensor.zone_available_water
-   sensor.zone_target_liters

## Configuration Helpers

-   input_number.target_available_water
-   input_number.minimum_wilting_point
-   input_number.maximum_irrigation
-   input_number.rain_skip_threshold
-   input_number.learning_rate

------------------------------------------------------------------------

# Future Improvements

Possible future enhancements include:

-   AI-based evapotranspiration prediction
-   Machine learning using historical seasons
-   Plant-specific irrigation profiles
-   Automatic seasonal calibration
-   Integration with weather radar
-   Water price optimization
-   Leak detection
-   Frost protection
-   Fertigation support

------------------------------------------------------------------------

# Expected Benefits

Compared to fixed-threshold irrigation, this approach:

-   Uses less water
-   Adapts to each irrigation zone
-   Automatically compensates for soil differences
-   Learns over time
-   Improves irrigation accuracy throughout the season
-   Requires minimal manual calibration after initial setup
