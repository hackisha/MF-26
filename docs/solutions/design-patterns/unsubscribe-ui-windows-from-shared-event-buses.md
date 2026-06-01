---
title: Unsubscribe UI Windows From Shared Event Buses
date: 2026-06-01
category: docs/solutions/design-patterns
module: mf-log-analyzer-v2/ui/time_series_window.py
problem_type: design_pattern
component: ui_lifecycle
severity: medium
applies_when:
  - "A Qt widget subscribes to a shared application event bus"
  - "Floating or dockable analysis windows can be opened and closed repeatedly"
tags: [qt, event-bus, lifecycle, memory-leak, desktop-ui]
---

# Unsubscribe UI Windows From Shared Event Buses

## Context

The MF Log Analyzer v2 time-series window subscribed its bound method to `CursorBus`. Code review caught that closing the window did not remove the callback, so the bus could keep the widget alive and keep sending stale cursor updates.

## Guidance

When a UI object subscribes to a shared application bus, provide a matching unsubscribe path and test the window lifecycle. The unsubscribe path should be safe to call more than once.

For Qt widgets, cover both common paths:

- `closeEvent`, for normal user-initiated close.
- destruction or deferred deletion, for `deleteLater()` and parent-owned cleanup.

## Why This Matters

MF Log Analyzer is designed around floating and dockable analysis windows. Leaked subscribers would accumulate as users open and close graphs, maps, and vehicle-behavior windows. That can cause memory leaks, stale updates, duplicate rendering work, and crashes when callbacks touch deleted UI objects.

## When to Apply

Use this pattern for shared buses such as playback cursor, hover cursor, selected lap, loaded log, selected preset, or language/theme changes.

## Example

```python
self._cursor_callback = self._handle_cursor_event
self.cursor_bus.subscribe(self._cursor_callback)

def closeEvent(self, event):
    self.cursor_bus.unsubscribe(self._cursor_callback)
    super().closeEvent(event)
```

The bus should also make `unsubscribe` idempotent so double cleanup is harmless.

## Related

- mf-log-analyzer-v2/src/mf_log_analyzer_v2/app/cursor_bus.py
- mf-log-analyzer-v2/src/mf_log_analyzer_v2/ui/time_series_window.py
