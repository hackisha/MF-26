---
title: "Drive visual windows from shared playback state"
date: "2026-06-02"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.ui"
tags:
  - "playback"
  - "visualization"
  - "time-series"
  - "vehicle-model"
---

# Drive Visual Windows From Shared Playback State

## Context

Analysis windows can look correct at first render but still drift from the CSV
playback session if they do not subscribe to the shared playback cursor. This is
especially easy to miss for qualitative views such as the 3D vehicle model, and
for configurable views such as time-series graphs where the displayed channels
can change after the window has already been opened.

## Guidance

- Pass `PlaybackState` into visual windows that represent the current sample.
- Store the complete data series needed by the window, not only the first value.
- On playback cursor events, clamp the sample index and update the visible
  indicator immediately.
- Keep user-selectable graph channel IDs in application state and reapply them
  to all open windows plus newly opened windows.
- Preserve raw numeric CSV columns as selectable plot series so target-scale
  100-200 sensor logs are not reduced to a small fixed alias set.
- Expose a small observable property or label for each visual effect so tests and
  users can confirm the behavior.

## When to Apply

Use this pattern for time-series graphs, GPS maps, G-G diagrams, 3D vehicle
attitude previews, sensor cards, and future lap/segment visualizations.
