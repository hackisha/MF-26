---
title: "Keep reference overlays above analysis data"
date: "2026-05-26"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.ui"
tags:
  - "visualization"
  - "g-g-diagram"
  - "adxl345"
  - "pyqtgraph"
---

# Keep Reference Overlays Above Analysis Data

## Context

The G-G diagram's 1 G limit circle was visible before CSV upload but became hard to see after loading a real log. The reference circle still existed, but the uploaded point cloud and raw acceleration scale visually buried it.

## Guidance

Reference overlays such as limit circles, thresholds, current-time cursors, event bands, and map routes should have explicit z-order above dense data layers. For pyqtgraph items, set `zValue()` deliberately instead of relying on insertion order.

```python
map_tile_item.setZValue(-10)
route_background_item.setZValue(0)
cloud_item.setZValue(5)
limit_circle_item.setZValue(10)
current_item.setZValue(20)
```

Analysis views must also consume the corrected or derived standard channel when the SRS defines one. For ADXL345 acceleration, G-G should read `AX_CORRECTED_G` / `AY_CORRECTED_G`, not raw `ax_g` / `ay_g`.

When settings affect different layers, refresh only the impacted layer. For example, time-series line style changes should not trigger GPS map tile reloads; reload the tile only when the map background toggle or GPS track changes.

## Why This Matters

Dense real CSV data changes axis ranges, point density, and visual stacking. A reference marker that is fine in an empty or demo view can disappear in the real workflow unless its layer order and channel source are explicit.

## When to Apply

Apply this to G-G diagrams, time-series cursor lines, threshold bands, event markers, GPS route/current-position layers, and any analysis view where reference geometry explains how to interpret the data.
