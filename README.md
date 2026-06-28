# Amazing Irrigation

A generic Home Assistant custom integration and Lovelace card for moisture-based,
weather-aware irrigation. Each **Irrigation Zone** selects its own moisture sensor(s),
watering actuator, rain inputs and safety limits, so the same integration works across
many setups (LinkTap over MQTT today, other hardware later).

> Status: early development. See the [implementation issues](https://github.com/raunosr/ha-amazingirrigation/issues)
> for the roadmap. This package is built as thin vertical slices.

## Key ideas

- **Integration owns the watering decision.** Schedules only create *Run Requests*;
  the integration decides whether to skip, reduce or water and records why.
- **Liters first.** Watering is modelled in liters; duration is an actuator fallback.
- **Fail safe.** Watering fails closed when moisture or actuator safety is unknown.
- **One source of truth.** Zone configuration lives in the integration; the Lovelace
  card only displays and controls.

See [`CONTEXT.md`](./CONTEXT.md) for the domain glossary and
[`docs/adr/`](./docs/adr) for architecture decisions.

## Installation (HACS)

This repository is structured for HACS. Until it is published to the default store you
can add it as a **custom repository** (category: Integration), then install
**Amazing Irrigation** and restart Home Assistant.

After installing, add the integration from **Settings → Devices & Services → Add
Integration → Amazing Irrigation**.

For full setup details — zone configuration, actuator adapters (switch, service,
script, LinkTap/MQTT), scheduling, Safety Blockers, greenhouse zones, and the
services — see [`docs/usage.md`](./docs/usage.md).

## Lovelace card

The integration bundles a Lovelace card (`amazing-irrigation-card`) and registers
it automatically — no manual resource setup is required. Add it to a dashboard
to display and control a single Irrigation Zone:

```yaml
type: custom:amazing-irrigation-card
name: Herb Bed
decision_entity: sensor.herb_bed_irrigation_decision
moisture_entity: sensor.herb_bed_zone_moisture
status_entity: sensor.herb_bed_watering_status
history_entity: sensor.herb_bed_irrigation_history
```

Only `decision_entity` is required; the other entities enrich the display. The
card shows Zone Moisture, target, recommended Watering Volume, cumulative Total
Watering Volume, the latest Irrigation Decision and recent Irrigation History,
and surfaces the zone's settings, both schedule slots, its Learned Model
(Moisture Gain per Liter, Daily Drying Rate, Rain Efficiency, Field Capacity,
Wilting Point) and every referenced sensor — all discovered from the decision
sensor, no extra config. It exposes Run, Force Water, and Stop controls; Stop
appears only when the backend reports a stoppable run. The card never stores
zone configuration — the integration remains the source of truth.

## Development

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements_test.txt
pytest
```

The Lovelace card lives in `frontend/` (Lit + TypeScript). Build the bundle into
the integration package with:

```bash
cd frontend
npm install
npm run test     # vitest unit tests
npm run build    # emits custom_components/amazing_irrigation/frontend/amazing-irrigation-card.js
```

## Migration from an existing setup

Migrating an existing Home Assistant irrigation setup (e.g. Ecowitt soil moisture
with LinkTap-over-MQTT)? See [`docs/migration.md`](./docs/migration.md) for an
entity mapping, the rule that old per-zone automations must be disabled before
enabling the same zone here, and a non-destructive
[test dashboard](./docs/examples/test-dashboard.yaml) for validating one zone
first.

## Security

Never commit Home Assistant secrets, tokens, backups, `.storage` files or runtime
databases. See [`SECURITY.md`](./SECURITY.md).