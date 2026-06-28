# Amazing Irrigation

Amazing Irrigation manages automatic watering for independently controlled plant or bed areas in Home Assistant.

## Language

**Irrigation Zone**:
An independently monitored and watered plant, bed, greenhouse, or garden section with its own moisture signal and watering control.
_Avoid_: Area, zone

**Greenhouse Zone**:
An Irrigation Zone inside a greenhouse, where protected conditions may make temperature, humidity, and rain exposure different from outdoor zones.
_Avoid_: Greenhouse

**Zone Moisture**:
The single moisture value used to decide whether an Irrigation Zone needs water, even when the zone has more than one physical moisture sensor.
_Avoid_: Soil moisture sensor value, probe value

**Run Request**:
A request for Amazing Irrigation to evaluate whether an Irrigation Zone should be watered.
_Avoid_: Run, trigger

**Force Water**:
An explicit user action to water an Irrigation Zone while bypassing soft checks such as moisture target or forecast rain.
_Avoid_: Manual run, override

**Irrigation Decision**:
The outcome of evaluating a Run Request for an Irrigation Zone, such as skip, reduce, or water.
_Avoid_: Status, result

**Rain Event**:
Observed rainfall that may affect an Irrigation Zone's learned moisture model.
_Avoid_: Forecast, rain status

**Forecast Rain**:
Predicted rainfall used to decide whether a Run Request should be skipped, reduced, or allowed.
_Avoid_: Rain Event

**Forecast Rain Amount**:
The predicted quantity of rain for the decision window, measured in millimeters.
_Avoid_: Rain forecast sensor

**Forecast Rain Probability**:
The predicted likelihood of rain for the decision window, expressed as a percentage.
_Avoid_: Rain chance sensor

**Observed Rain Amount**:
The measured quantity of rain that has already fallen, measured in millimeters.
_Avoid_: Rain sensor

**Watering Event**:
An actual application of water to an Irrigation Zone.
_Avoid_: Run, irrigation

**Confirmed Watering Event**:
A Watering Event backed by actuator feedback such as watering state, volume increase, or another configured confirmation signal.
_Avoid_: Successful command

**Irrigation History**:
The chronological record of Run Requests, Irrigation Decisions, Rain Events, and Watering Events for an Irrigation Zone.
_Avoid_: Recorder history, chart history

**Watering Volume**:
The amount of water applied or recommended for an Irrigation Zone, measured in liters.
_Avoid_: Duration, watering amount

**Watering Actuator**:
The controllable device, service, or script that applies water to an Irrigation Zone.
_Avoid_: Valve, switch, watering device

**Safety Blocker**:
A configured condition that prevents watering when active, such as leak detection, unavailable water supply, pump fault, or freezing risk.
_Avoid_: Error sensor, lockout

**Target Moisture**:
A direct moisture percentage that an Irrigation Zone should reach before watering is considered unnecessary.
_Avoid_: Moisture threshold

**Target Available Water**:
A target expressed as a percentage between Wilting Point and Field Capacity for an Irrigation Zone.
_Avoid_: Smart target, learned target

**Field Capacity**:
The moisture level an Irrigation Zone settles to after excess water has drained.
_Avoid_: Maximum moisture

**Wilting Point**:
The practical lower moisture boundary below which an Irrigation Zone should not be allowed to dry.
_Avoid_: Minimum moisture, dry limit

**Learned Recommendation**:
A watering recommendation derived from historical moisture, rain, and Watering Events, bounded by user-defined safety limits.
_Avoid_: AI decision, automatic target

**Zone State**:
The per-zone persisted store holding live-editable tunables (target moisture, max liters, enabled, learning, and the two schedule slots), the Learned Model, and cumulative volume. It is the live source of truth that the scheduler and Irrigation Decision read; the config-entry options only seed its initial values.
_Avoid_: Settings, config

**Learned Model**:
The Soil Water Balance values Amazing Irrigation learns for an Irrigation Zone over time — Irrigation Efficiency, Rain Efficiency, the Evapotranspiration coefficient, the Drainage rate, and bounded Field Capacity / Wilting Point estimates, each with a Model Confidence — stored in the Zone State and used only when Learning is enabled, always bounded by safety limits and overridden by any manual value.
_Avoid_: AI model, profile

**Moisture Gain per Liter**:
The rise in Zone Moisture observed per liter applied during a Confirmed Watering Event, learned as a bounded moving average.
_Avoid_: Absorption rate

**Daily Drying Rate**:
The decline in Zone Moisture per day observed between Watering Events, learned as a bounded moving average.
_Avoid_: Evaporation, drying model

**Rain Efficiency**:
The rise in Zone Moisture observed per millimeter of Observed Rain, learned as a bounded moving average.
_Avoid_: Rain factor

**Total Watering Volume**:
The cumulative liters applied to an Irrigation Zone (or across the whole system) by every Confirmed Watering Event, exposed as a total-increasing sensor.
_Avoid_: Water usage, consumption

**Soil Water Balance**:
The physics-informed model that advances Zone Moisture over time by adding Irrigation Efficiency and Rain Efficiency gains and subtracting Evapotranspiration and Drainage losses, bounded by Field Capacity and Wilting Point. It is the basis of the Learned Model and Predictive Control.
_Avoid_: Bucket model, water model

**Irrigation Efficiency**:
The rise in Zone Moisture per liter applied, learned jointly by the Soil Water Balance estimator. The model-based successor to Moisture Gain per Liter.
_Avoid_: Absorption rate

**Evapotranspiration**:
The modelled loss of Zone Moisture to the air over time, driven by temperature and humidity (and optional wind and solar inputs), scaled by a learned coefficient. The physics-based successor to Daily Drying Rate.
_Avoid_: Evaporation, drying

**Drainage**:
The modelled loss of Zone Moisture once it rises above Field Capacity, learned as a bounded drainage rate.
_Avoid_: Runoff, leakage

**Target Range**:
A configurable low/high Zone Moisture band the Predictive Control keeps a zone within, instead of a single Target Moisture point. Backward-compatible: a zone with only a Target Moisture derives a band from it.
_Avoid_: Target band, moisture window

**Predictive Control**:
Deciding watering by simulating the Soil Water Balance forward over a forecast horizon to the next active schedule slot and applying only the minimum liters needed to keep predicted Zone Moisture inside the Target Range, without exceeding Field Capacity.
_Avoid_: Forecasting, smart control

**Model Confidence**:
A per-parameter and overall measure, derived from the estimator's covariance, of how certain the Learned Model is about each coefficient of the Soil Water Balance.
_Avoid_: Accuracy, certainty score

**History Bootstrap**:
Initialising a zone's Learned Model quickly by replaying history (moisture, rain, climate and irrigation events) through the Soil Water Balance estimator, run once at setup for any zone with moisture sensors and on demand. The lookback window is selectable per zone (default 2 months) and draws on Home Assistant long-term statistics beyond the recorder's short raw retention. It degrades gracefully and reports how much history it used and from which source.
_Avoid_: Backfill, training run

**Model Insight**:
The diagnostic sensor and card section that make every conclusion reviewable: learned parameters with Model Confidence, the History Bootstrap summary, and the water-balance breakdown, predicted trajectory and chosen liters behind the latest Irrigation Decision.
_Avoid_: Debug info, model dump

