---
title: Do Not Publish Full Snapshots From Selection Sync
date: 2026-05-24
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

## Guidance

Keep the two paths separate:

- Full snapshot writes happen after source/session/profile changes and before opening a pop-out.
- BroadcastChannel receive handlers apply only selection state locally.
- Do not call full snapshot publish from a selection-only receive path.

Add a regression test where `setSessionSnapshot` is mocked and assert that receiving a selection message does not call it.

## Why This Matters

Pop-out windows may start empty, hydrate late, or hold older session data. If they can overwrite the main snapshot after a selection-only message, the next new window can open with the wrong log or no log at all.

## When to Apply

- Current time, selected event, selected overlay, selected lap, or cursor synchronization.
- Any future multi-window state where small UI selections are broadcast separately from the full analysis session.
