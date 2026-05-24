---
title: Do Not Publish Full Snapshots From Selection Sync
date: 2026-05-24
last_updated: 2026-05-24
category: docs/solutions/logic-errors
module: MF Log Analyzer pop-out windows
problem_type: logic_error
component: cross_window_state
severity: medium
applies_when:
  - "Synchronizing lightweight selection state between windows"
  - "Maintaining an authoritative session snapshot for pop-out hydration"
  - "Using BroadcastChannel alongside Electron IPC snapshot storage"
tags: [electron, broadcastchannel, snapshots, popout]
---

# Do Not Publish Full Snapshots From Selection Sync

## Context

Task 13 added pop-out windows with two state paths: full session snapshots through Electron IPC and lightweight selection sync through `BroadcastChannel`. Review caught that a window receiving only selection state could publish its entire local snapshot back to Electron, overwriting the authoritative snapshot with stale or empty session data.

Later CSV playback work exposed the same boundary from the other direction: `currentTimeSec` can change many times per second while replaying a log. Publishing a full CSV/session snapshot on every cursor tick makes playback heavy and can make a new-window action fail before the app even attempts to open the pop-out.

## Guidance

Keep the two paths separate:

- Full snapshot writes happen after source/session/profile changes and before opening a pop-out.
- BroadcastChannel receive handlers apply only selection state locally.
- Do not call full snapshot publish from a selection-only receive path.
- Do not call full snapshot publish from high-frequency local cursor changes such as playback ticks.
- Treat the pre-pop-out snapshot publish as best effort; if it fails, still try to open the window and surface the actual window-opening error separately.

Add a regression test where `setSessionSnapshot` is mocked and assert that receiving a selection message does not call it.

Add a second regression test for playback/time-cursor setters: call `setCurrentTimeSec`, flush the microtask queue, and assert that `setSessionSnapshot` was not called. Keep a separate pop-out button test where `setSessionSnapshot` rejects but the desktop `popout(route)` API is still invoked.

## Why This Matters

Pop-out windows may start empty, hydrate late, or hold older session data. If they can overwrite the main snapshot after a selection-only message, the next new window can open with the wrong log or no log at all.

Full session snapshots can also be large because they include parsed CSV data. High-frequency cursor updates should stay on the lightweight sync path so playback remains responsive and IPC snapshot failures do not block the primary user action.

## When to Apply

- Current time, selected event, selected overlay, selected lap, or cursor synchronization.
- Any future multi-window state where small UI selections are broadcast separately from the full analysis session.
