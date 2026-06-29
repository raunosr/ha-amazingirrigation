---
timestamp: 2026-06-29T09-56-09Z
slug: frontend-src-amazing-irrigation-overview-card-ts
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Loading spinner and feedback on Run/Force just added; toggle switches have no pending/confirmation state |
| 2 | Match System / Real World | 4 | Domain language is precise: moisture %, liters, target bands, soil science terms used fluently |
| 3 | User Control and Freedom | 3 | Back button works; no undo for Run/Force actions; toggle switches fire instantly with no confirmation |
| 4 | Consistency and Standards | 3 | Follows HA ha-card patterns; custom toggles differ from native ha-switch appearance |
| 5 | Error Prevention | 2 | No confirmation dialog for Force water (destructive/override action); Run/Stop are equal visual weight |
| 6 | Recognition Rather Than Recall | 3 | Zone tiles show live moisture + target; detail view shows everything; history entries lack timestamps |
| 7 | Flexibility and Efficiency | 2 | No keyboard shortcuts; no quick-actions from overview tiles; must drill in for every operation |
| 8 | Aesthetic and Minimalist Design | 3 | Clean layout; prediction chart is dense but earned; water balance terms grid could overwhelm on smaller zones |
| 9 | Error Recovery | 2 | Action feedback shows "Service call failed" with no retry or detail; no explanation of why a run was rejected |
| 10 | Help and Documentation | 1 | No tooltips, no inline help, no explanation of what "Force" does vs "Run", no legend for decision banners |
| **Total** | | **26/40** | **Solid foundation, clear gaps in error handling, help, and efficiency** |

## Anti-Patterns Verdict

**LLM assessment**: This does NOT look AI-generated. The card has a clear domain-specific identity -- soil moisture gauges, prediction trajectories, water balance breakdowns. The overview tile grid uses varied status classes (watering pulse, skip, pending-water) rather than identical card clones. The SVG prediction chart is hand-crafted with purpose-built markers. No side-stripe borders, no gradient text, no glassmorphism, no hero-metric template. The design is restrained and functional, which is correct for an HA custom card that must coexist with the user's existing dashboard theme.

**Deterministic scan**: 22 findings across 2 files.
- 2x `layout-transition` (warning): `transition: width` on gauge-fill and tile-bar-fill bars. These animate the moisture bar fill on state updates -- a standard HA progress-bar pattern. **False positive**: the bars are absolutely positioned fills inside a fixed-size track; the `width` change does not trigger reflow of surrounding content.
- 8x `design-system-radius` (advisory): Values 1px, 2px, 3px, 4px used in gauge markers, confidence bars, and prediction chart elements. These are sub-component details (dot markers, thin bar fills) where the DESIGN.md 8px/12px scale would be too large. **Contextually valid**: these are precision UI elements, not card-level rounding drift.
- 12x `design-system-color` (advisory): `#fff` (5x), `rgba(0,0,0,0.2)` (1x), `rgba(255,255,255,0.08)` (1x), `#4caf50` (3x), `#f44336` (2x). All are CSS fallbacks for HA custom properties (`--card-background-color`, `--success-color`, `--error-color`) or SVG fill values that inherit from the HA theme context. **False positive**: these are defensive fallbacks, not palette drift.

## Overall Impression

A competent irrigation dashboard card that takes its domain seriously. The two-level architecture (overview grid -> detail drill-down) is the right structure. The prediction chart is the standout element -- genuinely useful. The biggest missed opportunity is that the card is **operationally silent**: actions happen with minimal feedback, errors are opaque, and there is no help surface for the user who doesn't already understand what "Force" means or why their run was skipped.

## What's Working

1. **Overview tile grid with live moisture bars**: Each zone is a scannable tile showing moisture-vs-target at a glance. The pulse animation on watering zones and the status-class color coding (watering/skip/pending) provide immediate system status without text.

2. **Prediction SVG chart**: The time-slotted trajectory with target band shading, critical/peak markers, gradient fill, and water balance terms breakdown is genuinely informative. It shows the model's thinking, not just its conclusion. This is the card's signature element.

3. **Progressive disclosure via `<details>` sections**: Model Insight, Sensors, and History are collapsed by default, keeping the detail view focused on the moisture gauge + decision banner + prediction. The user can dig deeper without being overwhelmed.

## Priority Issues

**[P1] Action buttons lack confirmation for destructive operations**
- **Why it matters**: "Force" overrides the model's decision and delivers water regardless of conditions. A mis-tap on mobile could waste water or overwater a zone. There is no visual distinction between "Run" (respect the model) and "Force" (override the model) beyond the label text. No confirmation step exists.
- **Fix**: Add a two-tap confirm pattern for Force: first tap changes the button to "Confirm Force?" with a warning color; second tap executes. Or use a native HA confirmation dialog. Make Force visually distinct from Run (different color weight, not just label).
- **Suggested command**: `/impeccable harden`

**[P2] No inline help or explanatory text for domain-specific concepts**
- **Why it matters**: New users won't understand what "Force" does vs "Run", what "target band" means, what the decision banner colors signify, or how to interpret the prediction chart markers. The card assumes expert knowledge.
- **Fix**: Add `title` attributes (tooltips) on: Force button ("Override model decision and water now"), decision banner labels, prediction chart legend items, confidence badges. Add a small "?" icon on the prediction section header that expands a one-line explanation.
- **Suggested command**: `/impeccable clarify`

**[P2] Error feedback is opaque and unrecoverable**
- **Why it matters**: When `_callZoneService` fails, the user sees "Service call failed" with no detail, no retry button, and no guidance. The feedback auto-clears after 4 seconds, which may be too fast to read if the user wasn't watching.
- **Fix**: Include the error reason from the rejected promise (HA returns structured error messages). Add a retry affordance. Extend the auto-clear timeout on errors to 8 seconds, or keep the error visible until dismissed.
- **Suggested command**: `/impeccable harden`

**[P2] History entries lack temporal context**
- **Why it matters**: History shows "Decision: water (reason)" but not when it happened. The user cannot correlate events with time without opening HA's native history panel.
- **Fix**: Add relative timestamps ("2h ago", "yesterday") to each history entry using `Date.now()` minus the entry timestamp. The data model likely includes timestamps in the history attributes.
- **Suggested command**: `/impeccable clarify`

**[P3] No quick actions from overview tiles**
- **Why it matters**: The user must tap a tile, wait for the detail view, scroll to the bottom, then tap Run. For a 6-zone system, running all zones is 18+ taps. Power users managing daily irrigation will feel this friction.
- **Fix**: Add a long-press or secondary action on overview tiles (a small play icon in the tile corner that triggers Run directly). Or add a "Run All" button to the overview header.
- **Suggested command**: `/impeccable craft "quick-run from overview tiles"`

## Persona Red Flags

**Alex (Power User, manages 8+ zones daily)**:
No keyboard shortcuts. No "Run All" or batch operations. Must drill into each zone individually to trigger runs. Force button is same visual weight as Run -- Alex might fat-finger Force when meaning Run on mobile. Toggle switches fire instantly with no undo, which is fine for Alex but risky for accidental taps.

**Jordan (First-Timer, just installed the integration)**:
No onboarding state when zones have no data yet. What does the card show when `moisture` is null, `decision` is null, and `predictedTrajectory` is empty? Jordan sees a tile with "--" values, drills in, sees an empty moisture gauge, no prediction, no decision banner, and three buttons (Run, Force, Stop) with no explanation. Jordan will click Force "to see if it works" because the label is more action-oriented than Run.

**Sam (Non-technical homeowner)**:
Decision banner says "skip" with a reason like "predicted_sufficient_moisture". Underscore-separated model internals leak into the UI via `view.decisionReason.replace(/_/g, " ")` -- this converts to "predicted sufficient moisture" but the phrasing is still model-speak, not human language. "Soil moisture is on track -- no watering needed" would be immediately clear.

## Minor Observations

- Custom `<button class="toggle">` elements should use HA's native `<ha-switch>` for visual consistency with the rest of the dashboard
- The gauge tick labels use `position: absolute` with `left: N%` but have no `transform: translateX(-50%)`, meaning tick labels at non-zero/non-100 positions may appear off-center
- `_toggleSwitch` fires immediately with no pending/feedback state (unlike the newly improved Run/Force buttons)
- The overview card title uses `font-size: 1.1rem` while HA cards typically use `font-size: 1.25rem` for card headers
- Water balance terms grid may need horizontal scroll or collapse on narrow cards with many terms

## Questions to Consider

- What should the card show for a brand-new zone with no historical data? Is there an onboarding state?
- Should "Force" require confirmation? It overrides the ML model's decision -- that feels like a destructive action.
- Would a "Run All Zones" button on the overview save meaningful daily friction?
