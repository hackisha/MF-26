---
title: Plan Pop-Out Views With Shared Session State
date: 2026-05-24
category: docs/solutions/design-patterns
module: MF Log Analyzer planning
problem_type: design_pattern
component: development_workflow
severity: low
applies_when:
  - "Planning desktop analytics apps with tabs that can open as separate windows"
  - "Designing multi-window views that must follow the same selected data, time, event, or filter"
tags: [desktop-apps, popout-views, shared-state, planning]
---

# Plan Pop-Out Views With Shared Session State

## Context

During MF Log Analyzer planning, the first implementation plan treated pop-out views as a UI/window feature. Self-review caught the gap: opening a second window is not enough for an analytics app if the user expects map, graph, and vehicle-behavior views to track the same log session.

## Guidance

When planning pop-out views, explicitly include the state-sharing mechanism in the implementation tasks. The plan should answer:

- How a new window receives the currently loaded log/session.
- How selected time, event, segment, lap, and overlay preset synchronize after the window opens.
- Which state is snapshotted once and which state is broadcast continuously.
- What happens when no log is loaded.

For MF Log Analyzer, the plan now uses two mechanisms:

- Electron IPC stores a session snapshot before opening a pop-out window.
- `BroadcastChannel` syncs lightweight selection state such as current time, selected event, and selected overlay.

## Why This Matters

Without this check, a plan can appear to satisfy "open view in new window" while producing a detached, empty, or stale analysis window. That breaks the core workflow for comparing a map, G-G diagram, and time-series graph side by side.

## When to Apply

- Multi-window desktop apps.
- Analytics tools where several views inspect one dataset.
- Any feature described as pop-out, detached, docked, or second-window view.

## Examples

Weak plan item:

```text
Add a pop-out button that opens the current tab in a new window.
```

Better plan item:

```text
Before opening the pop-out, publish the current analysis session snapshot through the desktop shell. On window mount, hydrate from that snapshot. Use a cross-window channel to broadcast current time, selected event, and overlay changes.
```

## Related

- docs/superpowers/plans/2026-05-24-mf-log-analyzer.md
