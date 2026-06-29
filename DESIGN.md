---
name: Amazing Irrigation
description: Professional soil-moisture intelligence dashboard for Home Assistant
colors:
  primary: "#03a9f4"
  primary-rgb: "3, 169, 244"
  state-active: "#03a9f4"
  success: "#43a047"
  error: "#db4437"
  warning: "#ff9800"
  text-primary: "inherit"
  text-secondary: "inherit"
  divider: "inherit"
  card-bg: "inherit"
  secondary-bg: "inherit"
typography:
  body:
    fontFamily: "inherit"
    fontSize: "inherit"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "inherit"
    fontSize: "0.8rem"
    fontWeight: 600
    lineHeight: 1.2
  metric:
    fontFamily: "inherit"
    fontSize: "1.8rem"
    fontWeight: 700
    lineHeight: 1
  small:
    fontFamily: "inherit"
    fontSize: "0.72rem"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  pill: "10px"
  full: "50%"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
components:
  zone-tile:
    backgroundColor: "{colors.card-bg}"
    rounded: "{rounded.lg}"
    padding: "16px 12px 12px"
  zone-tile-hover:
    textColor: "{colors.primary}"
  chip:
    backgroundColor: "{colors.secondary-bg}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  toggle:
    backgroundColor: "{colors.secondary-bg}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.lg}"
    padding: "2px 10px"
  toggle-active:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
  metric-card:
    backgroundColor: "{colors.secondary-bg}"
    rounded: "{rounded.md}"
    padding: "8px 6px"
  confidence-badge:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "1px 6px"
  back-button:
    backgroundColor: "transparent"
    rounded: "{rounded.full}"
    padding: "4px"
  collapsible:
    rounded: "{rounded.md}"
    padding: "10px 12px"
---

# Design System: Amazing Irrigation

## 1. Overview

**Creative North Star: "The Soil Intelligence Dashboard"**

This system renders soil-water-balance data as a confident, readable instrument panel. It inherits Home Assistant's visual vocabulary completely -- ha-card containers, CSS custom properties for theming, MDI icon set, standard interactive patterns -- and layers a domain-specific information hierarchy on top. The personality is scientific without being clinical: every data readout earns its space, every control conveys what the model is doing and why.

The system explicitly rejects generic IoT dashboards with oversized colorful gauges, decorative "smart garden" apps with leaf animations and cartoon imagery, dense spreadsheet tables with no visual hierarchy, and default HA entity lists with no grouping or context. It is not playful. It is not flashy. It is the calm readout of a system that understands your soil.

**Key Characteristics:**
- **Theme-native**: all colors reference HA CSS custom properties (`--primary-color`, `--secondary-text-color`, `--divider-color`, etc.), adapting automatically to any user theme and dark/light mode
- **Progressive disclosure**: overview tile grid answers "is everything OK?" in under 2 seconds; detail is one tap away, never forced
- **Data-dense but uncluttered**: every number shown helps the user make a decision or build confidence; no decorative metrics
- **Semantic color only**: color is reserved for state communication (active/watering, error, success), never decoration
- **Responsive within ha-card**: adapts to card widths from narrow mobile columns to wide desktop panels via CSS grid auto-fit

## 2. Colors: The Inherited Palette

Colors are not owned by this system. They are inherited from the user's Home Assistant theme via CSS custom properties, making the card a native citizen of any theme.

### Primary
- **HA Primary** (`var(--primary-color)`, fallback `#03a9f4`): accent color for active states, moisture bars, chart lines, target indicators, confidence badges. Used at full opacity for interactive elements, at 8-18% opacity for tinted backgrounds and gradient fills.
- **HA Primary RGB** (`var(--rgb-primary-color)`, fallback `3, 169, 244`): used in `rgba()` constructions for hover shadows and tinted decision banners.

### Semantic
- **Active State** (`var(--state-active-color)`, fallback to primary): pulsing animation ring, watering status text, active tile border.
- **Success** (`var(--success-color)`, fallback `#43a047`): peak moisture marker, positive water-balance terms.
- **Error** (`var(--error-color)`, fallback `#db4437`): critical theta marker, negative water-balance terms, stop button theme.
- **Badge Green** (`var(--label-badge-green)`, fallback `#4caf50`): gain terms in the water-balance grid.

### Neutral
- **Primary Text** (`var(--primary-text-color)`): headings, zone names, metric values, chart value labels.
- **Secondary Text** (`var(--secondary-text-color)`): sublabels, section labels, axis labels, status text, chip text.
- **Divider** (`var(--divider-color)`): row separators, tile borders at rest, gauge track backgrounds, chart gridlines.
- **Card Background** (`var(--card-background-color)`): tile surfaces, chart data point fills.
- **Secondary Background** (`var(--secondary-background-color)`): metric card fills, chip backgrounds, toggle resting state, term grid cells, collapsible panel hover.

### Named Rules
**The Inheritance Rule.** No color is hardcoded except fallback values. Every color token references a HA CSS custom property. If a fallback is used (e.g., `#db4437` for `--error-color`), it must match HA's documented defaults so behavior is predictable when the variable is undefined.

## 3. Typography: System Stack

**Body Font:** `inherit` (from HA's `--ha-card-header-font-family` and body cascade, typically Roboto or the user's configured font)

**Character:** The card inherits the user's chosen typeface entirely. It expresses hierarchy through weight and size alone, never through font-family variation. This is intentional: a card that imports its own display font would feel foreign inside HA's native UI.

### Hierarchy
- **Metric Display** (700, 1.8rem, line-height 1): current moisture percentage in the gauge section. The single largest text element; draws the eye on the detail view.
- **Card Header** (inherited from HA): zone card title, uses HA's standard `.card-header` styling.
- **Zone Name / Detail Name** (600, 0.8-1.0rem, line-height 1.2): tile labels and detail header. Semi-bold to distinguish from body text.
- **Section Label** (600, 0.8rem): "Predicted Trajectory", "Controls", "Schedule" headers. Secondary text color; acts as quiet signpost.
- **Body** (400, 0.82rem): info rows, schedule rows, history entries, control labels.
- **Small / Sublabel** (400, 0.72-0.75rem): chip text, legend items, prediction notes, axis labels. Often in secondary text color.
- **Micro** (in SVG: 7px): chart axis labels and value annotations, sized for the SVG coordinate space.

### Named Rules
**The No-Import Rule.** The card never imports external fonts. It inherits from HA's cascade. This ensures visual consistency with other cards on the same dashboard.

## 4. Elevation: Flat-by-Default

The system uses tonal layering, not shadows, as its primary depth mechanism. Surfaces are flat at rest. The only shadow appears as a response to interaction state:

- **Tile hover**: `0 2px 8px rgba(var(--rgb-primary-color), 0.12)` -- a subtle primary-tinted lift when hovering over a zone tile.
- **Gauge marker**: `0 1px 3px rgba(0, 0, 0, 0.2)` -- the draggable current-moisture dot on the gauge track.

Depth is otherwise conveyed through background color differentiation: `--card-background-color` for primary surfaces, `--secondary-background-color` for inset metrics and chips, `--divider-color` borders for structural separation.

### Named Rules
**The Flat-By-Default Rule.** Surfaces are flat at rest. Shadows appear only as a response to state (hover, active). This matches HA's native card behavior where ha-card itself carries the only ambient shadow.

## 5. Components

### Zone Tile
Precise and restrained. The primary interactive element on the overview grid.
- **Shape:** 12px radius, 1px solid `--divider-color` border
- **Background:** `--card-background-color`
- **Padding:** 16px 12px 12px
- **Layout:** flex column, centered, with icon (28px), name, moisture bar, and stats
- **Hover:** border transitions to `--primary-color`, subtle primary-tinted box-shadow
- **Focus:** 2px solid `--primary-color` outline, 2px offset
- **Watering state:** border color shifts to `--state-active-color`, icon tints to active, animated pulse ring
- **Skip state:** 0.7 opacity reduction

### Moisture Gauge
The centerpiece of the detail view.
- **Track:** 8px tall, 4px radius, `--divider-color` background
- **Fill:** `--primary-color`, width animated with 0.5s ease transition
- **Target band:** semi-transparent primary overlay at 15% opacity
- **Target line:** 2px wide, 14px tall, `--secondary-text-color`
- **Current marker:** 10px circle, primary fill, card-background border, subtle shadow
- **Ticks:** 0.65rem, secondary text color, flexed between 0% and 100%

### Prediction Chart
Full SVG moisture trajectory visualization.
- **Canvas:** padded SVG viewBox (32px left, 8px right, 12px top, 24px bottom)
- **Grid:** 0.5px `--divider-color` horizontal lines with Y-axis % labels (7px)
- **Target band:** `--primary-color` at 8% opacity rect
- **Target line:** dashed (4 2), 0.8px, primary at 50% opacity
- **Trajectory line:** 1.8px `--primary-color`, round joins and caps
- **Area fill:** linear gradient from 18% primary at top to 2% at bottom
- **Data points:** 2.5px circles, card-background fill, primary stroke
- **Critical marker:** 4px circle, `--error-color` ring (no fill)
- **Peak marker:** 4px circle, `--success-color` ring (no fill)
- **X-axis:** hour labels (+0h, +2h, ...) at 7px, secondary text

### Chip
- **Shape:** 10px radius (pill-adjacent)
- **Background:** `--secondary-background-color`
- **Text:** 0.72rem, `--secondary-text-color`
- **Active variant:** primary color text, semi-bold

### Toggle Button
- **Rest:** `--secondary-background-color`, `--secondary-text-color`, 1px `--divider-color` border, 12px radius
- **Active:** `--primary-color` fill and border, white text
- **Transition:** background and border-color at 0.15s

### Confidence Badge
- **Shape:** 8px radius
- **Background:** `--primary-color`
- **Text:** 0.72rem, white, semi-bold
- **Purpose:** displays model confidence percentage inline

### Collapsible Section
- **Shape:** 8px radius, 1px `--divider-color` border
- **Padding:** 10px 12px
- **Summary:** flex row with space-between, no default marker
- **Open state:** bottom border on summary for visual separation

### Info Row
- **Layout:** flex wrap, 8px gap, 8px vertical / 16px horizontal padding
- **Icon size:** 18px via `--mdc-icon-size`
- **Border:** individual rows separated by 1px `--divider-color` bottom border

### Decision Banner
- **Water variant:** tinted primary background at 8% opacity via rgba
- **Skip variant:** `--secondary-background-color`
- **Layout:** flex row with icon, bold label, and reason text
- **Typography:** 0.85rem body, 0.8rem reason in secondary color

## 6. Do's and Don'ts

### Do:
- **Do** use HA CSS custom properties for every color value; hardcode only as fallbacks.
- **Do** inherit typography from HA's cascade; express hierarchy through weight (400/500/600/700) and size alone.
- **Do** use `ha-icon` with MDI icon set for all icons; never inline raw SVGs for UI chrome.
- **Do** respect `prefers-reduced-motion: reduce` for every animation (the pulse ring degrades to static 0.5 opacity).
- **Do** add `:focus-visible` outlines on all interactive elements for keyboard navigation.
- **Do** use semantic color for state: primary for active/selected, error for critical/negative, success for peak/positive.
- **Do** keep the overview answerable in under 2 seconds -- tile grid with at-a-glance moisture bars and status indicators.
- **Do** use `font-variant-numeric: tabular-nums` for any numeric column to maintain alignment.

### Don't:
- **Don't** import external fonts or override `font-family` on any element.
- **Don't** use large colorful gauges, circular meters, or toy-like iconography (per PRODUCT.md anti-reference: "Generic IoT dashboards with large colorful gauges and toy-like icons").
- **Don't** add leaf animations, plant graphics, or cartoon nature imagery (per PRODUCT.md: "Overly decorative 'smart garden' apps with leaf animations and cartoon plants").
- **Don't** present raw entity lists without grouping, hierarchy, or context (per PRODUCT.md: "Default HA entity lists with no grouping or context").
- **Don't** use border-left/right stripes greater than 1px as colored accents on any element.
- **Don't** use gradient text (`background-clip: text`) anywhere.
- **Don't** hardcode light or dark theme values; always reference CSS custom properties that adapt to both.
- **Don't** use decorative motion or choreographed entrances; motion is for state feedback only (tile hover, bar fill, pulse ring).
- **Don't** add shadows to resting surfaces; only hover and active states earn elevation.
- **Don't** use `z-index` values above 10 within the card; the card lives inside HA's stacking context.
