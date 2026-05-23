---
title: "Scope SVG panel selectors around icon components"
date: 2026-05-23
category: frontend
problem_type: ui_regression
component: Elec_app log replay preview
tags:
  - css
  - svg
  - lucide-react
  - visual-qa
---

# Scope SVG panel selectors around icon components

## Problem

The log replay preview used panel-level CSS such as `.telemetry-map-panel svg` to size GPS and G-G diagrams. That selector also matched small `lucide-react` icons in the same panels, so the icons expanded into large chart-sized SVGs.

## Symptoms

- A heading icon appears as a huge graphic inside the panel.
- The panel height becomes unexpectedly large.
- Full-page screenshots may show awkward stitched or repeated-looking regions because the page is much taller than expected.

## Solution

Scope chart styling to the direct SVG child that represents the visualization:

```css
.telemetry-map-panel > svg,
.telemetry-gg-panel > svg {
  height: 210px;
  min-height: 0;
  border-radius: 8px;
  background: #091118;
}
```

Avoid broad descendants like `.panel svg` or `.telemetry-map-panel svg` when a component contains both visualization SVGs and icon SVGs.

## Prevention

When using icon libraries next to custom SVG charts, use one of these patterns:

- Target the chart with a direct-child selector.
- Add a dedicated chart class, such as `.telemetry-map-chart`.
- Verify with a browser screenshot after styling SVG-heavy UI.

