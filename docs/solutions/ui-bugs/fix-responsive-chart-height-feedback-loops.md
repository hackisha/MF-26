---
title: Fix Responsive Chart Height Feedback Loops
date: 2026-05-24
category: docs/solutions/ui-bugs
module: MF Log Analyzer responsive chart panels
problem_type: ui_bug
component: frontend_stimulus
severity: medium
symptoms:
  - "React Three Fiber canvas panels repeatedly grow or shrink after render"
  - "Plotly or map panels change height while the user is only observing the screen"
  - "Workspace panels with scrollable bodies can inherit unstable chart heights"
root_cause: logic_error
resolution_type: code_fix
tags: [css, plotly, threejs, resize, layout]
---

# Fix Responsive Chart Height Feedback Loops

## Problem

MF Log Analyzer's vehicle behavior model could keep changing height after the tab rendered. The GPS plot was also vulnerable to the same class of issue because responsive visualization components were placed in containers that defined only minimum heights.

## Symptoms

- The 3D vehicle model area drifts vertically after opening the Vehicle Behavior tab.
- Responsive Plotly or map regions can recalculate against a changing parent size.
- In workspace panels, nested analysis views can make the panel body feel unstable instead of scrollable.

## What Didn't Work

Using `min-height` alone gives the component a lower bound, not a stable measurement. Plotly `useResizeHandler` and React Three Fiber's canvas observe their parent dimensions, so an auto-height parent can feed the child's measured size back into the next parent layout pass.

## Solution

Give responsive chart and canvas containers explicit heights, then allow their internal content to scroll or fit inside that fixed area.

```css
.behavior-model-shell {
  grid-template-rows: minmax(0, 1fr) auto;
  height: min(58vh, 560px);
  min-height: 0;
}

.behavior-canvas {
  height: 100%;
  min-height: 0;
}
```

Workspace overrides should also use explicit panel-local heights:

```css
.workspace-panel-body .behavior-model-shell,
.workspace-panel-body .map-lap-plot,
.workspace-panel-body .leaflet-map {
  height: 340px;
  min-height: 0;
}
```

## Why This Works

The visualization library can still react to window and panel width changes, but its parent height is no longer derived from the visualization's own rendered size. `minmax(0, 1fr)` and `min-height: 0` also prevent grid children from forcing their parent taller than the intended panel slot.

## Prevention

When embedding Plotly, Leaflet, or React Three Fiber in a dashboard, avoid auto-height wrappers unless the component is genuinely content-sized. Add a browser regression test that samples `getBoundingClientRect().height` several times after render and fails if the drift is more than a couple of pixels.
