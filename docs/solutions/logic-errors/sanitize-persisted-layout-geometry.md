---
title: Sanitize Persisted Layout Geometry
date: 2026-05-24
category: docs/solutions/logic-errors
module: MF Log Analyzer workspace presets
problem_type: logic_error
component: frontend_workspace
severity: medium
applies_when:
  - "Loading user-editable layout or preset data from localStorage"
  - "Converting persisted numeric fields into CSS grid coordinates"
  - "Normalizing imported workspace, dashboard, or panel layouts"
tags: [workspace, presets, localstorage, validation, layout]
---

# Sanitize Persisted Layout Geometry

## Context

The Workspace preset feature stores panel `x`, `y`, `width`, and `height` in `localStorage`. During review, missing or malformed numeric fields could flow through `Number(...)` and `Math.floor(...)` as `NaN`, then become invalid CSS grid coordinates.

## Guidance

Treat persisted layout JSON as untrusted input. Before clamping grid coordinates, convert each field through a finite-number guard with explicit defaults:

```ts
function finiteInteger(value: unknown, fallback: number): number {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? Math.floor(numberValue) : fallback;
}
```

Use safe defaults for missing width and height, then clamp `x` and `y` after the final panel size is known so panels cannot escape the grid.

## Why This Matters

TypeScript types do not protect data coming back from `localStorage`, imported JSON, or future user-edited preset files. Without finite-number guards, a single malformed preset can silently generate `NaN` styles and make the workspace look broken.

## When to Apply

- Workspace and dashboard layout presets.
- Imported/exported UI configuration.
- Any code path that maps persisted numeric configuration directly into CSS, chart ranges, canvas dimensions, or grid placement.
