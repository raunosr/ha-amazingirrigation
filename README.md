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
- **Physics-informed and predictive.** A learned **Soil Water Balance** model and
  **Predictive Control** apply only the liters needed to keep a zone inside its
  **Target Range** over the forecast horizon, and a **History Bootstrap** learns it
  fast from recorder history. Every conclusion is reviewable on the device page.

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
(Irrigation Efficiency, Evapotranspiration coefficient, Rain Efficiency, Drainage
rate, Field Capacity, Wilting Point) and every referenced sensor — all discovered
from the decision sensor, no extra config. A **Model Insight / "Why this decision"**
section explains the latest Irrigation Decision: the water-balance breakdown, the
predicted soil-moisture trajectory, each learned parameter with its Model
Confidence, and "learned from N days" when a History Bootstrap has run. It exposes
Run, Force Water, and Stop controls; Stop appears only when the backend reports a
stoppable run. The card never stores zone configuration — the integration remains
the source of truth.

## Learning and predictive control

When Learning is enabled, each zone learns a physics-informed **Soil Water Balance**
— Irrigation Efficiency, Rain Efficiency, an Evapotranspiration coefficient and a
Drainage rate, plus bounded Field Capacity / Wilting Point — using a recursive
estimator that also reports a **Model Confidence** per parameter. Manual values
always override learned ones, and every value stays inside safe bounds.

- **Climate inputs.** For accurate Evapotranspiration, configure the optional
  observed/forecast air temperature and humidity (and optional wind and solar)
  inputs on each zone. Greenhouse zones can use their local temperature/humidity
  sensors instead via the **ET source** setting.
- **Target Range.** Set an optional low/high moisture band; **Predictive Control**
  simulates the model forward to the next active schedule slot and applies only the
  liters needed to keep predicted moisture in range without exceeding Field Capacity.
  A zone with only a single Target Moisture keeps working unchanged.
- **Plant Water Demand profiles.** Pick Low / Medium / High instead of an exact
  species. In **Automatic** target mode the model derives the Target Range from
  learned Wilting Point / Field Capacity and the profile (with an automatic
  hot-day margin); **Manual** keeps your fixed Target Moisture. Explicit low/high
  bounds always win, and the soil water-balance physics is unchanged.
- **History Bootstrap.** Every new zone with moisture sensors learns fast by replaying
  history at setup — over a selectable window (default 2 months), drawing on Home
  Assistant long-term statistics beyond the recorder's ~10-day raw retention. Re-run it
  any time with the per-zone **Re-learn from History** button or the
  `amazing_irrigation.relearn_from_history` service. It degrades gracefully when no
  history is available and reports how much it used and from which source.
- **Model Insight.** A per-zone diagnostic sensor and the card section above make
  every learned parameter, its confidence, the bootstrap summary and the reasoning
  behind each decision reviewable on the device page.

See [`docs/usage.md`](./docs/usage.md) for the full field reference and
[`docs/adr/0003-physics-informed-water-balance-learning.md`](./docs/adr/0003-physics-informed-water-balance-learning.md)
for the design rationale.

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