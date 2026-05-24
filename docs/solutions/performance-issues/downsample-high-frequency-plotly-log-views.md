---
title: Downsample High-Frequency Plotly Log Views
date: 2026-05-25
category: docs/solutions/performance-issues
module: MF Log Analyzer playback-linked charts
problem_type: performance_issue
component: frontend_stimulus
severity: medium
symptoms:
  - "CSV replay feels sluggish when large logs are loaded"
  - "Playback cursor updates cause Plotly views to rebuild large trace arrays many times per second"
  - "Multiple pop-out analysis windows multiply the same high-frequency rendering cost"
root_cause: async_timing
resolution_type: code_fix
tags: [plotly, playback, large-logs, downsampling, scattergl, performance]
---

# Downsample High-Frequency Plotly Log Views

## Problem

MF Log Analyzer can load real vehicle logs with tens of thousands of samples. If playback time changes several times per second while every open Plotly view receives full trace arrays, the app can feel heavy even though the analysis math is correct.

## Symptoms

- CSV replay stutters or lags after opening graph-heavy tabs.
- Time-series, Map/Lap, and Vehicle Behavior views all react to `currentTimeSec`.
- Pop-out windows make the issue more visible because each window renders its own charts.

## What Didn't Work

Only slowing the playback interval reduces update frequency, but it does not fix the underlying chart cost. If each tick still rebuilds full GPS paths or G-G sample traces, large logs remain expensive.

## Solution

Treat full-log chart data as low-frequency state and the playback cursor as high-frequency state.

- Downsample large Plotly traces to a bounded point count.
- Use `scattergl` for large point clouds and paths.
- Register a custom Plotly core with only the trace types the app uses instead of importing the full `plotly.js-dist-min` bundle.
- Preserve first and last samples so chart extents remain trustworthy.
- Keep current playback markers sourced from the full log, not the downsampled trace.
- Memoize stable path/sample traces separately from the current marker trace.

```tsx
const plottedPoints = useMemo(() => downsampleGgPoints(points), [points]);
const sampleTrace = useMemo(
  () => ggSamplesTrace(plottedPoints, plottedPoints.length < points.length ? "scattergl" : "scatter"),
  [plottedPoints, points.length]
);
const traces = useMemo(
  () => (currentPoint ? [sampleTrace, limitTrace, currentGgTrace(currentPoint)] : [sampleTrace, limitTrace]),
  [currentPoint, limitTrace, sampleTrace]
);
```

```ts
import Plotly from "plotly.js/lib/core";
import scatter from "plotly.js/lib/scatter";
import scattergl from "plotly.js/lib/scattergl";

Plotly.register([scatter, scattergl]);
```

## Why This Works

The loaded log changes rarely, but playback time changes constantly. Bounding trace size keeps Plotly work predictable, and separating stable traces from cursor markers prevents a one-point cursor movement from reallocating thousands of path or scatter points.

## Prevention

- Any view that subscribes to `currentTimeSec` should avoid rebuilding full-log arrays on every tick.
- Add synthetic large-log UI tests that assert plotted trace length stays below a fixed limit.
- Use full-resolution data for statistics, nearest-row lookup, and current markers; use downsampled data for visual background traces.
- Prefer `scattergl` once a Plotly trace crosses the bounded point threshold.
- When custom-building Plotly through Vite, define `global` as `globalThis` so browser-incompatible CommonJS dependencies do not crash lazy-loaded chart views.

## Related Issues

- [Update Leaflet Cursor Markers Without Remounting Maps](./update-leaflet-cursor-markers-without-remounting-maps.md)
- [Avoid Spread For Large Log Aggregations](./avoid-spread-for-large-log-aggregations.md)
- [Fix Responsive Chart Height Feedback Loops](../ui-bugs/fix-responsive-chart-height-feedback-loops.md)
