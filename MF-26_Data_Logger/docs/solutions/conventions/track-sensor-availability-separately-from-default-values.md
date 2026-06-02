---
title: "Track sensor availability separately from default display values"
date: "2026-06-03"
track: "knowledge"
category: "conventions"
problem_type: "convention"
module: "mflog_proto.ui"
component: "development_workflow"
severity: "medium"
tags:
  - "sensor-availability"
  - "csv-loading"
  - "vehicle-dynamics"
  - "missing-data"
---

# Track Sensor Availability Separately From Default Display Values

## Context

MF-LOG-ANALYZER keeps stable UI sensor keys such as `AX_CORRECTED_G`,
`AY_CORRECTED_G`, and `steering angle` even when a loaded CSV does not contain
those channels. That is useful for playback cards and window construction, but
it becomes unsafe when analytical summaries treat those placeholder arrays as
real measurements.

## Guidance

When a view computes engineering metrics, pass both:

- the numeric series used for display and plotting
- an explicit set of channels that were actually present or derived from the CSV

Do not infer availability from the existence of a key in `sensor_series`.
Placeholder zero arrays should make UI construction stable, not imply the log
measured that channel.

```python
summary = compute_dynamics_summary(
    timestamps_seconds=timestamps,
    sensors=self.sensor_series,
    available_channels=self.available_sensor_channels,
)
```

Metric code should return `None`/unavailable for missing inputs, so the UI can
display `-` instead of a plausible-looking `0.000 G`.

## Why This Matters

For vehicle dynamics work, a real `0.000 G` sample and a missing accelerometer
column mean very different things. If missing inputs are silently converted to
zero, engineers can mistake an incomplete CSV for a valid low-load run, and
derived metrics such as G utilization, yaw response ratio, or handling balance
become misleading.

## When to Apply

Apply this whenever adding session-level summaries, derived analysis windows,
quality badges, export metrics, or report fields. Tests should cover both a
CSV that contains the alias-backed channel and a minimal CSV that omits the
channel but still creates the standard UI keys.
