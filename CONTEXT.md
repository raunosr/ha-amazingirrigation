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
