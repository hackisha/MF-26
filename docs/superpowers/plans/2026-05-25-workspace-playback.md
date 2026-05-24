# Workspace Playback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add shared CSV playback controls to Workspace and make plotted panels indicate the current replay position.

**Architecture:** Extract playback transport and current-sample readout helpers from `PlaybackView` into reusable UI. `WorkspaceView` renders the transport as a compact top rail while analysis panels consume the existing global `currentTimeSec`.

**Tech Stack:** React, Zustand session store, Plotly, Leaflet, Vitest, Playwright.

---

### Task 1: Reusable Playback Controls

**Files:**
- Create: `src/ui/PlaybackControls.tsx`
- Modify: `src/ui/PlaybackView.tsx`
- Test: `tests/ui/playbackView.test.tsx`

- [x] Write a failing test that expects playback controls to still seek, step, and play through `PlaybackView`.
- [x] Move transport state and current sample metrics into `PlaybackControls`.
- [x] Keep the current sample value table in `PlaybackView`.
- [x] Run `npm.cmd test -- tests/ui/playbackView.test.tsx`.

### Task 2: Workspace Shared Playback Rail

**Files:**
- Modify: `src/ui/WorkspaceView.tsx`
- Modify: `src/domain/workspacePresets.ts`
- Test: `tests/ui/workspaceView.test.tsx`
- Modify: `src/styles.css`

- [x] Write a failing test that expects Workspace to render shared playback controls and update `currentTimeSec`.
- [x] Render `PlaybackControls` in Workspace above the panel grid.
- [x] Remove default playback panels from built-in Workspace presets.
- [x] Add compact Workspace rail styles following the existing dashboard visual language.

### Task 3: Current-Time Plot Indicators

**Files:**
- Modify: `src/ui/TimeSeriesView.tsx`
- Modify: `src/ui/MapLapView.tsx`
- Test: `tests/ui/timeSeriesView.test.tsx`
- Test: `tests/ui/mapLapView.test.tsx`

- [x] Write failing tests for a current-time vertical cursor in Time-Series Plotly layout.
- [x] Write failing tests for a current coordinate marker in Map/Lap Plotly traces.
- [x] Add indicator traces/layout shapes derived from `currentTimeSec`.
- [x] Run focused UI tests.

### Task 4: Verification

**Files:**
- Test-only.

- [x] Run `npm.cmd run lint`.
- [x] Run `npm.cmd test`.
- [x] Run `npm.cmd run build`.
- [x] Run the relevant Playwright smoke tests.
