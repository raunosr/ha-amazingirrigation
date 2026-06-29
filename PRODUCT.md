# Product

## Register

product

## Users

Home automation enthusiasts who manage garden and greenhouse irrigation through Home Assistant. 50/50 split between quick phone glances ("is everything healthy?") and detailed desktop sessions (configuring zones, reviewing model predictions, adjusting targets). They are technically literate, familiar with HA conventions, and expect data-dense interfaces that respect their time.

## Product Purpose

A professional irrigation monitoring and control surface for Home Assistant. Shows zone health at a glance, enables drill-down into predictive soil-water-balance models, and provides confident controls for manual intervention. Success: the user trusts the system is making good decisions without needing to micromanage.

## Brand Personality

Confident, scientific, calm. The interface communicates "this system understands your soil" — not flashy, not playful, not utilitarian to the point of being clinical. It earns trust through clarity of information and precision of controls.

## Anti-references

- Generic IoT dashboards with large colorful gauges and toy-like icons
- Overly decorative "smart garden" apps with leaf animations and cartoon plants
- Dense spreadsheet-style tables with no visual hierarchy
- Default HA entity lists with no grouping or context

## Design Principles

1. **Trust through transparency** — Show the reasoning behind every decision. The user should understand why a zone was skipped or watered without digging.
2. **Glance, then dive** — The overview answers "is everything OK?" in under 2 seconds. Detail is one tap away, never forced.
3. **Respect the ecosystem** — Follow HA patterns (ha-card, CSS custom properties, more-info dialogs). The card should feel native, not foreign.
4. **Data earns its space** — Every number shown must help the user make a decision or build confidence. No decorative metrics.
5. **Calm confidence** — The system is smart; the UI reflects that by being measured, not anxious. Active states are clear, idle states are quiet.

## Accessibility & Inclusion

Follow Home Assistant's standard guidelines (inherits HA's theme system, respects `prefers-reduced-motion`, uses semantic HTML where Lit allows). Minimum WCAG AA contrast ratios. All interactive elements keyboard-accessible via HA's standard card interaction model.
