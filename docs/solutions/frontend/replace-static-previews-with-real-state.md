---
title: "Replace static UI previews before shipping feature screens"
date: 2026-05-23
category: frontend
problem_type: ui_regression
component: Elec_app log replay
tags:
  - react
  - testing-library
  - preview-ui
  - tdd
---

# Replace static UI previews before shipping feature screens

## Problem

The log replay redesign initially kept a static preview component in the real feature tab. It showed sample data such as `test_run_0523.csv` and `MF-26 Replay`, which made the app look populated even before the user uploaded a CSV.

## Symptoms

- The feature screen contains hard-coded sample file names or sample telemetry values.
- Real upload controls are visually secondary to mock content.
- Tests cannot reliably distinguish empty state from loaded state.

## Solution

Add a UI test that fails when static preview data remains in the real feature screen:

```tsx
expect(screen.getByLabelText("CSV 로그 파일")).toBeInTheDocument();
expect(screen.queryByText("test_run_0523.csv")).not.toBeInTheDocument();
expect(screen.queryByText("MF-26 Replay")).not.toBeInTheDocument();
```

Then remove the preview component and render only state-driven UI from the real session, playback, and analysis data.

## Prevention

When a design preview graduates into implementation, rename or remove the preview component before wiring the route. Empty states should show real upload/import actions, not sample telemetry.

