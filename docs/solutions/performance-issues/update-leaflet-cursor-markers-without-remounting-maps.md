---
title: Update Leaflet Cursor Markers Without Remounting Maps
date: 2026-05-25
category: docs/solutions/performance-issues
module: MF Log Analyzer Map/Lap playback
problem_type: performance_issue
component: frontend_stimulus
severity: medium
symptoms:
  - "Playback cursor updates cause the online map effect to rerun many times per second"
  - "Leaflet tile layers and map instances can be recreated while only the current position marker changed"
root_cause: async_timing
resolution_type: code_fix
tags: [leaflet, playback, map, performance, react-effects]
---

# Update Leaflet Cursor Markers Without Remounting Maps

## Problem

Map/Lap needs to show the current CSV playback position on both the offline Plotly path and the online Leaflet map. A naive React effect dependency on `currentPoint` makes the online map tear down and rebuild whenever playback advances.

## Symptoms

- During replay, `currentTimeSec` can update every playback tick.
- If `currentPoint` is part of the Leaflet map initialization effect dependencies, each tick removes and recreates the map, tile layer, path, and fixed markers.
- The user only expects one marker to move, but the implementation asks Leaflet to rebuild the whole map.

## What Didn't Work

Putting `currentPoint` directly in the map initialization effect is simple, but it ties a high-frequency cursor update to low-frequency map setup. That is acceptable for tests with one render, but expensive during actual playback.

## Solution

Keep map setup dependent on the GPS point set, then store the Leaflet map, module, and current marker in refs. Update only the cursor marker when `currentPoint` changes.

```tsx
const currentMarkerRef = useRef<CircleMarker | null>(null);
const leafletRef = useRef<Awaited<typeof import("leaflet")> | null>(null);
const mapRef = useRef<LeafletMap | null>(null);

function drawCurrentMarker(point: CoordinatePoint | null) {
  const L = leafletRef.current;
  const map = mapRef.current;

  currentMarkerRef.current?.remove();
  currentMarkerRef.current = null;
  if (!L || !map || !point) return;

  currentMarkerRef.current = L.circleMarker([point.latitude, point.longitude], markerOptions).addTo(map);
}

useEffect(() => {
  // Create map, tile layer, path, and fixed start/end markers from points.
}, [points]);

useEffect(() => {
  drawCurrentMarker(currentPoint);
}, [currentPoint]);
```

## Why This Works

The GPS path and tile layer are stable for a loaded log, while the playback cursor is intentionally high frequency. Separating those lifecycles lets React update the small mutable Leaflet overlay without triggering map disposal, network tile reloads, or layout churn.

## Prevention

- Treat playback cursors, hover positions, and selected samples as high-frequency state.
- Keep expensive visualization initialization effects dependent on stable data only.
- For Leaflet overlays, store mutable markers/layers in refs and update or replace those layers independently from the base map.
- Add tests for the output data marker in pure render tests, then use code review to check that online map effects do not depend on the high-frequency cursor unless they only update a small layer.

## Related Issues

- [Fix Responsive Chart Height Feedback Loops](../ui-bugs/fix-responsive-chart-height-feedback-loops.md)
- [Do Not Publish Full Snapshots From Selection Sync](../logic-errors/do-not-publish-full-snapshots-from-selection-sync.md)
