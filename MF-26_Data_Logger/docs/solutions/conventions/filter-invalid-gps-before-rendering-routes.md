---
title: "Filter invalid GPS samples before rendering routes"
date: "2026-05-26"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.ui"
tags:
  - "gps"
  - "visualization"
  - "pyqtgraph"
  - "csv"
---

# Filter Invalid GPS Samples Before Rendering Routes

## Context

Some EMU logger files contain startup GPS rows with `Latitude=0`, `Longitude=0`,
and `Satellites=0` before a real fix is available. Rendering those samples as a
normal route creates a diagonal line from `(0, 0)` to the real track and makes the
GPS map look broken.

## Guidance

Treat GPS rows as invalid before plotting when:

- latitude or longitude is missing or non-finite
- latitude is outside `[-90, 90]`
- longitude is outside `[-180, 180]`
- latitude and longitude are both effectively zero

Keep the playback index aligned by storing `None` for invalid samples, but pass
`NaN` gaps into pyqtgraph route arrays so the line is visually broken instead of
connected across bad data.

## Why This Matters

GPS startup/dropout rows are common in real logs. If plotting code only checks
that numbers parse, one bad sample can dominate the view range and hide the
actual driving line.

## When to Apply

Use this rule for GPS maps, route previews, lap overlays, and any future export
that connects location samples as a continuous path.
