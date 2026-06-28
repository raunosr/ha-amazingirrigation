# Migrating the current Kastelu setup to Amazing Irrigation

This guide maps the existing Home Assistant *Kastelu* irrigation setup
(Ecowitt soil moisture + LinkTap-over-MQTT, driven by four per-zone automations
and `script.taplinker_water_by_volume_2`) onto Amazing Irrigation zones, and
describes a **non-destructive** way to validate one zone before migrating the
rest.

> ⚠️ **Human validation required.** This document is a migration plan, not an
> automated cut-over. Configure the new zones, validate one zone end-to-end
> using the test dashboard below, and only then disable the old automations and
> migrate the remaining zones one at a time.

## 1. Current zones and their entities

The four existing zones map to these real entities. Targets are the existing
`input_number` helpers (current values shown in parentheses).

| Zone | Soil moisture | Target moisture helper | Target volume helper | LinkTap id |
| --- | --- | --- | --- | --- |
| Taka-Altaat | `sensor.gw2000a_soil_moisture_2` | `input_number.kastelu_taka_altaat_target_moisture` (40 %) | `input_number.kastelu_taka_altaat_target_volume_l` (30 L) | `1F43B22F004B1200_3` |
| Kartiomarjakuuset | `sensor.gw2000a_soil_moisture_3` | `input_number.kastelu_kartiomarjakuuset_target_moisture` (41 %) | `input_number.kastelu_kartiomarjakuuset_target_volume_l` (10 L) | `1F43B22F004B1200_4` |
| Etuallas | `sensor.gw2000a_soil_moisture_4` | `input_number.kastelu_etuallas_target_moisture` (52 %) | `input_number.kastelu_etuallas_target_volume_l` (10 L) | `EBED822C004B1200` |
| Kukkakäytävä / Yrtit | `sensor.gw2000a_soil_moisture_5` | `input_number.kastelu_yrtit_target_moisture` (41 %) | `input_number.kastelu_yrtit_target_volume_l` (50 L) | `1F43B22F004B1200_1` |

### LinkTap feedback and control entities

Each LinkTap exposes a consistent set of entities derived from its id (lower
cased). For `1F43B22F004B1200_3` (Taka-Altaat):

| Purpose | Entity |
| --- | --- |
| Watering feedback (confirms flow) | `binary_sensor.1f43b22f004b1200_3_is_watering` |
| Cumulative volume (confirms flow) | `sensor.1f43b22f004b1200_3_volume` |
| Water switch (start/stop) | `switch.1f43b22f004b1200_3_water_switch` |

Substitute the matching LinkTap id for the other zones, e.g.
`binary_sensor.ebed822c004b1200_is_watering`, `sensor.ebed822c004b1200_volume`,
`switch.ebed822c004b1200_water_switch` for Etuallas.

### Rain inputs

The old automations skip on a rain forecast. Map these to the per-zone
**Forecast Rain Amount** / **Forecast Rain Probability** fields:

- Forecast Rain Probability: `input_number.saa_sateen_todennakoisyys`
- Forecast Rain Amount: the numeric source the old automations compared
  (`automation.saa_sademaara_tanaan`); pick whichever numeric sensor/helper
  holds today's forecast rain in mm.
- Rain skip thresholds in the old automations: ~10 mm for most zones, 5 mm for
  Kukkakäytävä, with probability > 70–75 %. Set **Rain skip threshold (mm)** and
  **Forecast rain probability threshold (%)** per zone to match.

## 2. Actuator configuration (LinkTap / MQTT)

Configure each zone's **Watering Actuator** as **LinkTap (MQTT)** with:

- LinkTap id: the id from the table above (e.g. `1F43B22F004B1200_3`).
- MQTT topic: `/homeassistant/config_from_ha` (the integration default).
- Actuator switch: the zone's `switch.<id>_water_switch`.
- Failsafe duration: `3600` s (the existing default; range 900–21600).
- Watering feedback sensor: `binary_sensor.<id>_is_watering`.
- Cumulative volume sensor: `sensor.<id>_volume`.

This reproduces `script.taplinker_water_by_volume_2`: publish the volume limit,
publish the failsafe duration, then turn the switch on — with the switch called
last so a failed publish never opens the valve.

## 3. Migration order (non-destructive first)

1. **Add the integration** and create one zone — start with a non-critical zone
   such as **Kukkakäytävä / Yrtit**. Use the entity mapping above.
2. **Validate with the test dashboard** (section 4) while the old automation for
   that zone is still in place. The new zone's Irrigation Decision sensor and
   the card are read-only until you press Run, so observing them changes
   nothing.
3. **Disable the old automation _before_ enabling control for the same zone.**
   For each migrated zone you **must** turn off its old per-zone `Kastelu`
   automation before you enable scheduling or run the zone from Amazing
   Irrigation — otherwise both systems could open the same valve.
   - Taka-Altaat: `automation.kastelu_taka_altaat_volume_based`
   - Kartiomarjakuuset: `automation.kastelu_kartiomarjakuuset_by_volume`
   - Etuallas: `automation.kastelu_etuallas_by_volume`
   - Kukkakäytävä / Yrtit: `automation.kastelu_yrtit_by_volume`
4. **Enable scheduling / control** for the migrated zone in Amazing Irrigation.
5. **Repeat one zone at a time.** Keep the old dashboard and helpers in place
   until every zone is validated, then retire them.

> Generic installs do not assume these legacy automations exist; this section
> applies only when migrating from the current Kastelu setup.

## 4. Non-destructive test dashboard

Add the example view in
[`examples/test-dashboard.yaml`](./examples/test-dashboard.yaml) as a **new
dashboard view**. It reads only the new Amazing Irrigation entities and never
touches the old cards. Pressing **Run** uses the same decision engine as the
schedule, and **Stop** appears only when the zone is actually watering — so you
can validate decisions safely, watering only when you choose to.

The card and overview entity ids follow the zone name you choose, e.g. a zone
named *Kukkakäytävä* produces `sensor.kukkakaytava_irrigation_decision`,
`sensor.kukkakaytava_zone_moisture`, `sensor.kukkakaytava_watering_status` and
`sensor.kukkakaytava_irrigation_history`. Adjust the example entity ids to match
your zone names.
