---
title: Keep Playback Engines Outside Tab Panels
date: 2026-05-25
category: docs/solutions/logic-errors
module: MF Log Analyzer CSV playback
problem_type: logic_error
component: frontend_stimulus
severity: medium
symptoms:
  - "Dragging the playback timeline updates linked views"
  - "Pressing Play stops updating linked views after leaving the CSV Playback tab"
  - "Pop-out or analysis views can show stale playback cursor positions"
root_cause: scope_issue
resolution_type: code_fix
tags: [playback, tabs, react, zustand, cursor-sync]
---

# Keep Playback Engines Outside Tab Panels

## Problem

MF Log Analyzer originally owned the playback interval inside the `CSV Playback` tab controls. Manual seeking worked because it wrote `currentTimeSec` immediately, but Play stopped advancing once the tab panel unmounted.

## Symptoms

- Timeline dragging moved the Time-Series cursor correctly.
- Pressing Play and then viewing another analysis tab left the cursor stationary.
- The bug looked like a chart sync issue, but the real playback clock had stopped.

## What Didn't Work

Only forcing Plotly to redraw the cursor fixes manual cursor rendering, but it does not keep time advancing. The playback interval must outlive the visible controls.

## Solution

Store playback state in the shared session store and mount a small playback ticker at the app shell level.

```tsx
export function PlaybackTicker() {
  const isPlaybackPlaying = useSessionStore((state) => state.isPlaybackPlaying);
  const playbackSpeed = useSessionStore((state) => state.playbackSpeed);

  useEffect(() => {
    if (!isPlaybackPlaying) return;
    const intervalId = window.setInterval(() => {
      // Advance currentTimeSec and publish normal selection sync.
    }, tickMs);
    return () => window.clearInterval(intervalId);
  }, [isPlaybackPlaying, playbackSpeed]);

  return null;
}
```

The visible controls only start, pause, stop, seek, and change speed. They do not own the clock.

## Why This Works

Tabs are view state; playback is session state. Moving the timer to the app shell keeps the clock alive while users inspect Time-Series, Vehicle Behavior, Map/Lap, or pop-out windows. Existing `currentTimeSec` sync can then keep analysis views aligned.

## Prevention

- Long-running intervals for shared session behavior should be mounted above tab panels and route-specific views.
- Add a test that starts playback, unmounts the controls by switching tabs, advances timers, and asserts `currentTimeSec` still changes.
- Keep controls stateless where possible: buttons should update shared state, not own domain clocks.

## Related Issues

- [Downsample High-Frequency Plotly Log Views](../performance-issues/downsample-high-frequency-plotly-log-views.md)
- [Do Not Publish Full Snapshots From Selection Sync](./do-not-publish-full-snapshots-from-selection-sync.md)
