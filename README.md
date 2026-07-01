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
  bounds always win, and the soil water-balance physics is unchanged. In Automatic
  mode the card hides the manual Target Moisture and shows the derived band
  read-only, so there is only ever one live target control.
- **Soil-type presets.** Choose from five texture presets — Sandy (~20% FC),
  Standard mineral (~30%), Good garden (~40%), Peat/compost (~47%) and
  Greenhouse/potting mix (~52%) — plus a retained Clay option. Presets only seed
  the model; learned, Discovery or manual Field Capacity / Wilting Point always win.
- **Hysteresis irrigation.** A single rule drives every decision: watering starts
  once moisture drops below the band low and refills toward the band high (never
  above Field Capacity), instead of topping up on every small dip.
- **Rain fraction (0–100%).** Set how much natural rainfall reaches a zone —
  100% for open beds, 0% for greenhouses, in between for covered zones. Effective
  rainfall uses an event-based curve so light showers barely count. On hot days,
  **high**-demand zones get a heat-emergency override of the minimum-application skip.
- **Minimum application & sensor depth.** Skip negligible top-ups below a
  configurable minimum (unless a heat emergency applies), and record the moisture
  probe's installation depth (warned when much shallower than the root zone).
- **Unified selection.** Soil type, plant profile, sensor depth, rain fraction and
  minimum application are set the same way in the initial config flow, on the
  device page (auto-created Number/Select entities), and in the card.
- **Bed area & root depth (optional).** Enter a zone's area and rooting depth to seed
  irrigation/rain gains physically for faster, more accurate cold-start; learning
  refines them and manual parameters override. See *Scientific background* below.
- **History Bootstrap.** Every new zone with moisture sensors learns fast by replaying
  history at setup — over a selectable window (default 2 months), drawing on Home
  Assistant long-term statistics beyond the recorder's ~10-day raw retention. Re-run it
  any time with the per-zone **Re-learn from History** button or the
  `amazing_irrigation.relearn_from_history` service. It degrades gracefully when no
  history is available and reports how much it used and from which source.
- **Field Capacity Discovery.** A guided, human-in-the-loop calibration (FAO-56
  in-situ drainage method): you saturate the sensor and cover the soil, and the
  integration monitors the drainage curve and records **Field Capacity** when
  drainage settles — a rate-based, texture-adaptive stop (not a fixed clock). See
  [`docs/usage.md`](./docs/usage.md#field-capacity-discovery).
- **Model Insight.** A per-zone diagnostic sensor and the card section above make
  every learned parameter, its confidence, the bootstrap summary and the reasoning
  behind each decision reviewable on the device page.

See [`docs/usage.md`](./docs/usage.md) for the full field reference and
[`docs/adr/0003-physics-informed-water-balance-learning.md`](./docs/adr/0003-physics-informed-water-balance-learning.md)
for the design rationale.

## Scientific background

The model treats each zone's root zone as a single bucket of volumetric soil
moisture θ (percent) and advances it over each interval with a mass balance:

```
θ_next = θ + η_irr·L + η_rain·R − ET − drainage
```

| Term | Meaning | Units |
|------|---------|-------|
| `η_irr·L` | gain from `L` litres of irrigation | %·L⁻¹ |
| `η_rain·R` | gain from `R` mm of effective rain | %·mm⁻¹ |
| `ET` | evapotranspiration loss over the interval | % |
| `drainage` | loss above field capacity | % |

**Area / root-depth coupling (optional).** Irrigation and rain gains are the same
physics: applying a depth `D` mm raises moisture by `D / root_depth · 100`, and 1 L
over `A` m² equals `1/A` mm. So `η_rain = 100·eff/root_depth` and `η_irr = η_rain/A`
— their ratio is just the bed area. Supplying optional **Bed area** and **Root depth**
seeds both gains physically (efficiency ≈ 0.8) instead of soil-blind defaults, fixing
cold-start error; steady-state learning still overrides them.

**Evapotranspiration.** With root depth set, ET₀ uses the FAO-56 Penman-Monteith
reference equation (net radiation approximated from solar, with a temperature/humidity
fallback) scaled by a crop coefficient Kc from the demand profile (low 0.55 / med 0.85
/ high 1.1) and converted mm·day⁻¹ → %·h⁻¹ via root depth. Without root depth the
legacy VPD heuristic is used. A learned `k_et` corrects residual bias.

**Learning and confidence.** A recursive least-squares estimator with forgetting
updates the four coefficients online; per-parameter confidence comes from posterior
covariance, and a fit-based confidence tracks one-step residual RMSE so persistent
drift lowers trust. All values stay inside safe bounds (η_irr 0.01–25, η_rain 0.01–30,
Kc 0.2–1.5, root depth 20–2000 mm) and manual entries always win.

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