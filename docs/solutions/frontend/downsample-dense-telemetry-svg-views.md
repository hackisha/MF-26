---
title: "Downsample dense telemetry SVG views"
date: 2026-05-24
category: frontend
problem_type: performance_issue
component: Elec_app log replay analysis
tags:
  - react
  - svg
  - telemetry
  - performance
  - testing-library
---

# Downsample dense telemetry SVG views

## Problem

A dense telemetry overview can pass ordinary render tests while still creating thousands of SVG nodes for real CSV logs. In the log replay analysis view, GPS paths and G-G scatter points were initially rendered from every sample in `session.samples`, which would make playback expensive on full driving logs.

## Symptoms

- Playback or seeking causes the whole analysis view to re-render frequently.
- SVG charts map every CSV row to a `<line>`, `<circle>`, or path coordinate.
- Small fixture tests pass because they only use a few rows.
- Missing sensors can appear as flat midline charts if normalization returns placeholder values.

## Solution

Limit visual density before rendering SVG elements, while keeping the full dataset available for calculations such as nearest-current-sample lookup:

```tsx
const MAX_GPS_POINTS = 800;
const MAX_GG_POINTS = 900;

function downsample<T>(items: T[], max: number): T[] {
  if (items.length <= max) return items;
  const step = (items.length - 1) / (max - 1);
  return Array.from({ length: max }, (_, index) => items[Math.round(index * step)]);
}
```

For strip charts, downsample indexes used for the rendered path and memoize paths so the playhead can move without rebuilding every series:

```tsx
const renderIndexes = useMemo(() => downsampleIndexes(session.samples.length, MAX_STRIP_POINTS), [session.samples.length]);
const paths = useMemo(
  () => visibleSeries.map((item) => ({ ...item, path: seriesPath(session, item.key, width, height, renderIndexes) })),
  [renderIndexes, session, visibleSeries],
);
```

Filter out missing numeric series before drawing. If a panel has no valid data, show an explicit empty state rather than a fake flat chart:

```tsx
const visibleSeries = series.filter((item) => hasNumericData(session, item.key));

if (!visibleSeries.length) {
  return <div className="analysis-empty">표시할 숫자 센서가 없습니다.</div>;
}
```

Add tests with a large synthetic session so the performance guard is covered:

```tsx
expect(container.querySelectorAll(".analysis-gps-line").length).toBeLessThanOrEqual(799);
expect(container.querySelectorAll(".analysis-gg-dot").length).toBeLessThanOrEqual(900);
```

## Prevention

Whenever a telemetry or log UI renders one SVG element per sample, add a test fixture with thousands of rows and assert an upper bound on rendered nodes. Also test missing-column input so absent sensors cannot be mistaken for real flat data.
