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

## Development

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements_test.txt
pytest
```

## Security

Never commit Home Assistant secrets, tokens, backups, `.storage` files or runtime
databases. See [`SECURITY.md`](./SECURITY.md).
