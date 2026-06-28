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
| Learning enabled | Per-zone toggle. v1 collects observations and supports manual/visible calibration; automatic learning updates are gated behind this toggle. |

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

> Actuator command success is treated as a *request* only. When feedback is
> configured, Watering Events are confirmed from the watering-state/volume
> sensors.

## Scheduling

v1 ships simple per-zone scheduling:

- **Schedule weekdays** — tokens `mon`…`sun`. An empty set means *every day*.
- **Schedule times** — up to three start times, each picked with a time picker.
- A zone with no start times is never auto-scheduled; manual and Force runs still
  work.
- Disabled and out-of-season zones are skipped.

External Home Assistant automations may also create Run Requests by calling
`amazing_irrigation.run_zone`. Keep such automations thin (schedule trigger →
service call); the integration owns the skip/reduce/water decision.

## Services

| Service | Purpose |
| --- | --- |
| `amazing_irrigation.evaluate_zone` | Create a Run Request and return the Irrigation Decision **without** watering. Optional `force` bypasses soft checks (still respects Safety Blockers). |
| `amazing_irrigation.run_zone` | Create a Run Request that waters through the actuator when the decision allows. Optional `force`. |
| `amazing_irrigation.stop_zone` | Stop an in-progress Watering Event (only zones with a configured stop path). |

Normal manual UI runs use the same decision engine. **Force Water** bypasses soft
checks (moisture above target, rain, etc.) but never bypasses hard Safety
Blockers.

## Lovelace cards

The integration auto-registers two cards (no manual resource setup):

- `custom:amazing-irrigation-card` — single-zone detail/control.
- `custom:amazing-irrigation-overview-card` — compact multi-zone overview.

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
