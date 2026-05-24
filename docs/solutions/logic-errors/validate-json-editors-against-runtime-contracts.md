---
title: Validate JSON Editors Against Runtime Contracts
date: 2026-05-24
category: docs/solutions/logic-errors
module: MF Log Analyzer settings
problem_type: logic_error
component: frontend_settings
severity: medium
applies_when:
  - "Exposing advanced JSON editors for runtime configuration"
  - "Casting parsed JSON to TypeScript domain types"
  - "Applying user-edited profiles before running analysis"
tags: [settings, validation, json, profiles]
---

# Validate JSON Editors Against Runtime Contracts

## Context

Task 12 exposed an advanced profile JSON editor. Review caught that checking only `id` and "is object" still allowed malformed-but-valid JSON to be saved, such as broken calibration, overlay, or rule shapes. Those edits could later crash charts or event detection, or silently produce `NaN` analysis values.

## Guidance

Before casting parsed JSON to a domain type, validate the runtime contracts used by downstream code:

- Channels must include source columns, calibration, visibility, and display fields.
- Calibration must match the union exactly: `identity`, `invert`, or `scaleOffset` with finite `scale` and `offset`.
- Overlay presets must include `channelIds` and a known mode.
- Threshold rules must include valid `all`/`any` condition arrays, severity, duration, and view ids.

Wrap the apply/rebuild call in `try/catch` and display errors in the settings view. Add regression tests for malformed valid JSON, not only invalid JSON syntax.

## Why This Matters

TypeScript types do not protect data after `JSON.parse`. A raw editor can persist shapes that compile locally but fail later in a different tab or workflow. Validation should happen at the boundary where untyped JSON enters the app.

## When to Apply

- Profile JSON editors.
- Future import/export flows for profiles, rule packs, overlays, or calibration presets.
- Any settings screen that casts parsed JSON directly into runtime state.
