# Amazing Irrigation — setup and usage

This guide covers installation, configuring an Irrigation Zone, the watering
actuator adapters (generic and LinkTap/MQTT), scheduling, Safety Blockers,
greenhouse zones, the services, and migration warnings.

For migrating an existing Home Assistant setup, also read
[`migration.md`](./migration.md).

## Installation

### HACS (custom repository)

Until this repository is published to the default HACS store, add it as a
**custom repository**:

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/raunosr/ha-amazingirrigation` with category
   **Integration**.
3. Install **Amazing Irrigation** and restart Home Assistant.

The integration installs into `custom_components/amazing_irrigation/` and bundles
its Lovelace card — no separate frontend/plugin resource is required.

### Manual

Copy `custom_components/amazing_irrigation/` into your Home Assistant
`config/custom_components/` directory and restart.

### Add the integration

After restart, go to **Settings → Devices & Services → Add Integration →
Amazing Irrigation**. Then add Irrigation Zones through the integration's
**Configure** (options) flow.

## Configuring an Irrigation Zone

Each zone is configured through Home Assistant config/options flows using entity
selectors. The integration is the single source of truth for zone configuration;
the Lovelace card only displays and controls it.

### Core fields

| Field | Purpose |
| --- | --- |
| Name | Zone name; also the device name and the prefix of generated entity ids. |
| Enabled | Master enable for scheduled/automatic decisions. |
| Moisture sensors | One or more soil moisture sensors. **Zone Moisture** defaults to the *minimum* valid reading. If some sensors are unavailable it uses the remaining valid ones (degraded); it fails closed only when no valid reading exists. |
| Target moisture | Decision target (`%`). Watering is recommended only when Zone Moisture is below target. |
| Max liters | Hard cap on Watering Volume per run. |
| Gain per liter | Estimated moisture `%` gained per liter; used to size the recommended volume. |

### Rain inputs (typed)

Rain inputs are typed rather than arbitrary entities:

| Field | Purpose |
| --- | --- |
| Forecast rain amount | Used to skip/reduce Run Requests (mm). |
| Forecast rain probability | Used with the probability threshold to skip (`%`). |
| Observed rain amount | Drives Rain Events / learning; independent of forecast. |
| Rain skip mm | Skip threshold for forecast rain amount. |
| Rain skip probability | Skip threshold for forecast rain probability. |

### Safety, season and learning

| Field | Purpose |
| --- | --- |
| Safety blockers | Binary sensors that block watering when `on`. **Unavailable blockers block by default** (fail closed). The skip reason is recorded. |
| Season start / end | Optional active watering season; out-of-season zones never run. |
| Field capacity / wilting point | Advanced per-zone calibration that explains Target Available Water and learning. |
| Target moisture low / high | Optional **Target Range** for Predictive Control. When set, the controller keeps predicted moisture within `[low, high]`; when unset, a band is derived from the single Target Moisture (unchanged behaviour). |
| ET source | Which climate inputs drive Evapotranspiration: `auto` (greenhouse sensors for greenhouse zones, otherwise weather), `weather`, or `greenhouse`. |
| Soil type | Prior preset (`loam`, `sand`, `clay`) used to seed a new or freshly bootstrapped Learned Model. |
| Learning enabled | Per-zone toggle. When on, Amazing Irrigation learns a physics-informed **Soil Water Balance** (Irrigation Efficiency, Rain Efficiency, an Evapotranspiration coefficient, a Drainage rate, and bounded Field Capacity / Wilting Point — each with a Model Confidence) and uses it for **Predictive Control**, always bounded by safety limits with any manual value winning. When off, observations are still collected but never change decisions. |
| History to learn from | Lookback window for the **History Bootstrap** (`2 weeks` / `1 month` / `2 months` / `3 months`, default `2 months`). Beyond the recorder's ~10-day raw retention this draws on Home Assistant long-term statistics. |

#### Climate inputs (evapotranspiration)

For accurate Evapotranspiration, configure the optional climate inputs. All are
optional — absent inputs degrade gracefully and the model falls back to a
conservative default loss.

| Field | Purpose |
| --- | --- |
| Observed air temperature / humidity | Local measured climate driving ET (e.g. weather station, greenhouse sensor). |
| Forecast air temperature / humidity | Predicted climate used by Predictive Control over the horizon. |
| Wind speed | Optional; increases modelled ET. |
| Solar radiation | Optional; increases modelled ET. |

The Learned Model is exposed as read-only **Learned …** sensors per zone
(`sensor.<zone>_learned_moisture_gain_per_liter` — Irrigation Efficiency,
`…_learned_daily_drying_rate`, `…_learned_rain_efficiency`,
`…_learned_et_coefficient`, `…_learned_drainage_rate`,
`…_learned_field_capacity`, `…_learned_wilting_point`, and
`…_model_confidence`), plus a **Model Insight** diagnostic sensor
(`sensor.<zone>_model_insight`) whose attributes carry every parameter with its
confidence, the History Bootstrap summary, and the water-balance breakdown,
predicted trajectory and chosen liters behind the latest decision. All are
surfaced on the zone card. Each shows `learning…` until enough evidence is
gathered.

### Greenhouse zones

A Greenhouse Zone is a subtype of Irrigation Zone:

| Field | Purpose |
| --- | --- |
| Greenhouse | Marks the zone as a protected environment. |
| Protected rain | When enabled, rain never skips/reduces watering (effective rain is treated as 0). All other rules still apply. |
| Temperature / humidity sensor | Optional protected-environment context shown on the zone. |

## Watering actuator setup

The **Watering Actuator** is the only place hardware specifics live. After
choosing an `actuator_type` on the zone basics step, a dedicated **Watering
Actuator** step shows only the fields for that type (so you never see switch,
service, script and LinkTap fields all at once):

### `switch`

Set **Actuator switch** to a `switch`/`input_boolean` entity. The zone turns it
on to water and off to stop.

### `service`

Set **Start service** (e.g. `valve.open_valve`) and optional **Start data**
(JSON). Optionally set **Stop service** / **Stop data** to enable stopping.
Without a stop path, the card hides the Stop control.

### `script`

Set **Start script** and optionally **Stop script**. Use this to wrap an
existing watering script.

### `linktap` (LinkTap over MQTT)

First-class adapter reproducing a LinkTap volume-based watering script. The
easiest setup is to **select the LinkTap device** — the integration then
auto-fills the LinkTap id (exact case, from the device), the water switch, the
watering-state binary sensor and the volume sensor from that device's entities:

| Field | Purpose |
| --- | --- |
| LinkTap device | Select the `by LinkTap` device. Auto-fills the fields below. |
| LinkTap id | Auto-filled from the device; optional manual override. |
| Actuator switch | Auto-filled (`*_water_switch`); optional override. |
| LinkTap topic | MQTT config topic; defaults to `/homeassistant/config_from_ha`. |
| LinkTap failsafe | Failsafe duration in seconds (LinkTap range 900–21600, step 900). |

Provide a device **or** enter a LinkTap id and switch manually. The watering and
volume feedback sensors are also auto-filled from the device when present.

The adapter publishes the volume limit and failsafe to the MQTT topic, then turns
on the configured switch — i.e. **the integration performs the LinkTap watering
script for you**, so no separate Home Assistant script is required. (An optional
standalone script for manual testing is in
[`examples/linktap-water-by-volume.yaml`](./examples/linktap-water-by-volume.yaml).)

### Feedback (recommended)

| Field | Purpose |
| --- | --- |
| Watering sensor | Binary sensor that is `on` while watering; confirms Watering Events. |
| Volume sensor | Cumulative/last volume sensor for reporting. |

> **Auto-detection.** Leave both feedback sensors blank — for *any* actuator
> type — and the integration derives them from the device of the chosen
> actuator switch: the `_is_watering` binary sensor and the cumulative
> `_volume` sensor (never `_volume_limit`). This works whenever the switch is a
> LinkTap MQTT entity. Anything you select manually overrides auto-detection.

> Actuator command success is treated as a *request* only. When feedback is
> configured, Watering Events are confirmed from the watering-state/volume
> sensors.

## Scheduling

Each zone has **two independent daily schedule slots**, editable live from the
device page (and the zone card) as native entities — no options-flow reload:

- **Schedule 1 / Schedule 2 Time** (`time.<zone>_schedule_1_time`,
  `…_schedule_2_time`) — pick each slot's start time with a time picker.
- **Schedule 1 / Schedule 2 Active** (`switch.<zone>_schedule_1_active`,
  `…_schedule_2_active`) — toggle each slot on or off independently.
- **Defaults:** a fresh zone has Schedule 1 = **21:00** and **active**, and
  Schedule 2 = 21:00 but **inactive**, so it waters once each evening until you
  change it. The scheduler fires only the **active** slots.
- **Schedule weekdays** — tokens `mon`…`sun` (options flow). An empty set means
  *every day*.
- Disabled and out-of-season zones are skipped.

Editing these native entities is the live source of truth; the options-flow
schedule fields only seed their initial values. Target Moisture, Max Liters per
Run, Zone Enabled and Learning Enabled are likewise exposed as native
`number` / `switch` entities so they can be changed without an options reload.

External Home Assistant automations may also create Run Requests by calling
`amazing_irrigation.run_zone`. Keep such automations thin (schedule trigger →
service call); the integration owns the skip/reduce/water decision.

## Services

| Service | Purpose |
| --- | --- |
| `amazing_irrigation.evaluate_zone` | Create a Run Request and return the Irrigation Decision **without** watering. Optional `force` bypasses soft checks (still respects Safety Blockers). |
| `amazing_irrigation.run_zone` | Create a Run Request that waters through the actuator when the decision allows. Optional `force`. |
| `amazing_irrigation.stop_zone` | Stop an in-progress Watering Event (only zones with a configured stop path). |
| `amazing_irrigation.relearn_from_history` | Re-run the **History Bootstrap** for the targeted zones: replay recorder history through the Soil Water Balance estimator to (re)initialise the Learned Model. Returns how many intervals/days were used, or notes when history was insufficient. |

Normal manual UI runs use the same decision engine. **Force Water** bypasses soft
checks (moisture above target, rain, etc.) but never bypasses hard Safety
Blockers.

## Learning, prediction and explainability

When Learning is enabled, each zone learns a physics-informed **Soil Water
Balance** and uses it for **Predictive Control**:

- **Predictive Control.** Instead of only covering the current deficit, the
  controller simulates the model forward over a forecast horizon to the next
  active schedule slot and applies only the liters needed to keep predicted Zone
  Moisture inside the **Target Range** without exceeding Field Capacity —
  minimizing overwatering, drainage and unnecessary runs. When the model or a
  forecast is unavailable it falls back to the rule-based decision.
- **History Bootstrap.** Every new zone with moisture sensors is bootstrapped at
  setup (no need to enable live learning first) by replaying history (moisture,
  rain, climate, and irrigation taken from recorded Watering Events or inferred
  from unexplained moisture rises). The lookback window is selectable per zone
  (**2 weeks / 1 month / 2 months / 3 months**, default **2 months**); reaching
  beyond the recorder's ~10-day raw retention uses Home Assistant **long-term
  statistics** (hourly means kept ~1 year for `state_class: measurement`
  sensors). Re-run it any time with the per-zone **Re-learn from History** button
  (`button.<zone>_re_learn_from_history`) or the
  `amazing_irrigation.relearn_from_history` service (its `days` defaults to the
  zone's window). It degrades gracefully when history is unavailable and reports
  how much it used and from which source.
- **Model Insight.** The `sensor.<zone>_model_insight` diagnostic sensor and the
  card's **"Why this decision"** section make every conclusion reviewable: each
  learned parameter with its **Model Confidence**, the bootstrap summary
  ("bootstrapped from N of M requested days · K intervals · source"), and the
  water-balance term breakdown, predicted
  soil-moisture trajectory and chosen liters behind the latest Irrigation
  Decision.

Manual values always override learned ones, and every learned value stays inside
safe bounds. See
[`docs/adr/0003-physics-informed-water-balance-learning.md`](./adr/0003-physics-informed-water-balance-learning.md)
for the design rationale.

## Lovelace cards

The integration auto-registers two cards (no manual resource setup):

- `custom:amazing-irrigation-card` — single-zone detail/control.
- `custom:amazing-irrigation-overview-card` — compact multi-zone overview.

They are registered as a Lovelace resource automatically, so they appear in the
dashboard **Add card** picker as *Amazing Irrigation Zone* and *Amazing
Irrigation Overview*.

Both cards ship a **visual editor** — no YAML required. When you add or edit a
card, the UI shows entity pickers:

- *Zone card:* pick the required **Decision sensor**
  (`sensor.<zone>_irrigation_decision`) plus optional soil-moisture, status,
  and history sensors, and an optional display name.
- *Overview card:* set an optional title, then **+ Add zone** / **Remove** rows,
  each selecting that zone's Decision sensor (and optional sensors).

You can still switch to **Show code editor** for raw YAML if you prefer.

The zone card surfaces the whole zone at a glance, discovering the zone's
sibling entities from the Decision sensor (no extra config needed):

- **Settings** — Target Moisture and Max Liters per Run (click to edit), plus
  Zone Enabled / Learning Enabled toggles.
- **Schedule** — both daily slots with their time and an independent Active
  toggle each.
- **Learned model** — the five learned parameters, shown as `learning…` until
  enough evidence is gathered.
- **Sensors** — every referenced source (moisture sensors, rain
  forecast/observed, climate, safety blockers) with its live state.
- **Total water** — cumulative Total Watering Volume for the zone.

Click any row to open Home Assistant's more-info dialog and edit the value.

> **After updating via HACS:** the resource URL is cache-busted per version, but
> if the cards still show a loading spinner or "Custom element not found",
> hard-refresh the browser (Ctrl/Cmd+Shift+R) once to clear the frontend
> service-worker cache. A Home Assistant restart after the update is also
> recommended so the resource is (re)registered.

See the README for the card YAML and
[`examples/test-dashboard.yaml`](./examples/test-dashboard.yaml) for a
non-destructive validation view.

## Migration warnings

- Disable each old per-zone automation **before** enabling/scheduling the same
  zone here, so two systems never control one valve.
- Validate one zone first using the test dashboard before broader migration.
- See [`migration.md`](./migration.md) for the full entity mapping.

## Security

Never commit Home Assistant secrets, tokens, backups, `.storage` files or
runtime databases. See [`../SECURITY.md`](../SECURITY.md).

## Translations / i18n

English is the baseline (`custom_components/amazing_irrigation/strings.json` and
`translations/en.json`). Additional languages can be added as
`translations/<lang>.json`.
