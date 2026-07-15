---
title: "Include data fingerprints in render cache keys"
date: "2026-05-25"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.data.downsample"
tags:
  - "graph-cache"
  - "downsampling"
  - "rendering"
---

# Include Data Fingerprints In Render Cache Keys

## Context

Graph render caches often key on channel, visible range, pixel width, strategy, and source count. That is not enough when the same channel and range can be recalculated after calibration, unit conversion, filtering, or derived-channel changes.

## Guidance

Cache keys for downsampled or render-ready graph data should include a fingerprint of the actual x/y values, or an equivalent upstream data revision ID. Range and count identify the view shape, not the data content.

```python
key = (
    channel_id,
    visible_range,
    pixel_width,
    strategy,
    len(x),
    series_digest(x),
    series_digest(y),
)
```

Add regression tests where the range and source count stay the same but an interior x or y value changes. The cache must not reuse the old result in that case.

## Why This Matters

Stale render caches are subtle. The graph may keep showing an old calibration, old filter result, or old derived channel even though the data layer changed correctly. This is especially risky in MF-LOG-ANALYZER because graph output may be used for cooling, DBW, voltage, or safety decisions.

## When to Apply

Apply this to graph caches, analysis-result caches, report image caches, and any cache where the same channel/range can be recomputed from different calibration, unit, filter, or derived-channel inputs.
