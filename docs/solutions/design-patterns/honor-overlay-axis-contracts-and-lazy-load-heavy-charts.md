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
  - "Rendering empty-state views that can later become loaded chart views"
tags: [charts, plotly, lazy-loading, overlays, axes, react-hooks]
---

# Honor Overlay Axis Contracts And Lazy Load Heavy Charts

## Context

Task 9 added configurable time-series overlays for MF Log Analyzer. Review caught repeatable risks: `separateAxes` presets were drawn on a single native-unit axis, Plotly was statically imported into the initial dashboard bundle, generated free axes could overlap the plot domain, and an empty-state render path returned before later hooks.

## Guidance

When a preset mode is named as a behavior contract, implement that contract directly or rename it before shipping. For mixed-unit overlays, `separateAxes` means every trace gets a valid Plotly axis id and the layout defines the matching axis key:

```tsx
trace 0 -> yaxis: "y"  -> layout.yaxis
trace 1 -> yaxis: "y2" -> layout.yaxis2
trace 2 -> yaxis: "y3" -> layout.yaxis3
```

Axis titles should include the channel display name and unit so mixed RPM, pressure, and temperature traces are readable without guessing.

Heavy charting libraries should sit behind the narrowest useful lazy boundary. In this app, `Layout` lazy-loads `TimeSeriesView`, and `TimeSeriesView` owns the Plotly factory import, so Summary and Diagnostics do not pay the Plotly cost at startup.

When a component can render empty first and loaded later, keep hook order stable. Either call hooks unconditionally with null guards, or split the loaded graph into a child component whose hooks only exist while that child is mounted.

Free overlay axes need two linked calculations: reserve x-axis domain padding, then place added free axes outside that domain. For a three-channel overlay, the primary left axis sits at the domain start, so an added left axis must be less than `xaxis.domain[0]`, not equal to it.

## Why This Matters

Analysis dashboards are trusted because labels and plots match. A single axis for mixed units can make a valid data trace look dangerous or harmless by accident. Separately, loading Plotly in the first app chunk makes every user pay for graphing even when they only inspect summaries or diagnostics.

## When to Apply

- Use this pattern when overlay presets mix channels with different units.
- Add trace/layout tests for axis id mapping whenever graph configuration is generated dynamically.
- Use a lazy tab/view boundary when a dependency is large and only needed for one dashboard view.
- Add a render-transition test for lazy tab content that starts as an empty state and later receives data.
- Test generated free-axis positions against `xaxis.domain` so labels and tick marks do not stack on the plot boundary.

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

For React hook stability, prefer this shape when the outer view has empty states:

```tsx
export function TimeSeriesView() {
  const session = useSessionStore((state) => state.session);
  if (!session) return <EmptyState />;

  return <LoadedTimeSeriesView session={session} />;
}

function LoadedTimeSeriesView({ session }: { session: AnalysisSession }) {
  const traces = useMemo(() => buildTraces(session), [session]);
  return <Plot data={traces} />;
}
```
