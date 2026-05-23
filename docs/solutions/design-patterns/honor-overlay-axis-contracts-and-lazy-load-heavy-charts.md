---
title: Honor Overlay Axis Contracts And Lazy Load Heavy Charts
date: 2026-05-24
category: docs/solutions/design-patterns
module: MF Log Analyzer time-series view
problem_type: design_pattern
component: frontend_stimulus
severity: medium
applies_when:
  - "Adding graph presets whose names imply a concrete plotting contract"
  - "Mixing sensor channels with different units in one overlay"
  - "Using heavy visualization libraries behind dashboard tabs"
tags: [charts, plotly, lazy-loading, overlays, axes]
---

# Honor Overlay Axis Contracts And Lazy Load Heavy Charts

## Context

Task 9 added configurable time-series overlays for MF Log Analyzer. Review caught two repeatable risks: `separateAxes` presets were drawn on a single native-unit axis, and Plotly was statically imported into the initial dashboard bundle.

## Guidance

When a preset mode is named as a behavior contract, implement that contract directly or rename it before shipping. For mixed-unit overlays, `separateAxes` means every trace gets a valid Plotly axis id and the layout defines the matching axis key:

```tsx
trace 0 -> yaxis: "y"  -> layout.yaxis
trace 1 -> yaxis: "y2" -> layout.yaxis2
trace 2 -> yaxis: "y3" -> layout.yaxis3
```

Axis titles should include the channel display name and unit so mixed RPM, pressure, and temperature traces are readable without guessing.

Heavy charting libraries should sit behind the narrowest useful lazy boundary. In this app, `Layout` lazy-loads `TimeSeriesView`, and `TimeSeriesView` owns the Plotly factory import, so Summary and Diagnostics do not pay the Plotly cost at startup.

## Why This Matters

Analysis dashboards are trusted because labels and plots match. A single axis for mixed units can make a valid data trace look dangerous or harmless by accident. Separately, loading Plotly in the first app chunk makes every user pay for graphing even when they only inspect summaries or diagnostics.

## When to Apply

- Use this pattern when overlay presets mix channels with different units.
- Add trace/layout tests for axis id mapping whenever graph configuration is generated dynamically.
- Use a lazy tab/view boundary when a dependency is large and only needed for one dashboard view.

## Examples

Avoid this for mixed-unit presets:

```tsx
const traces = channels.map((channel) => ({
  name: channel.displayName,
  y: channel.values
}));
```

Prefer explicit trace and layout pairing:

```tsx
const traceAxisId = index === 0 ? "y" : `y${index + 1}`;
const layoutAxisKey = index === 0 ? "yaxis" : `yaxis${index + 1}`;
```

Then test both sides of the generated contract: trace `yaxis` values and matching layout axis definitions.
