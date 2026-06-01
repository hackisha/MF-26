---
title: "Keep playback time independent from sample index"
date: "2026-05-25"
track: "knowledge"
category: "conventions"
problem_type: "convention"
component: "tooling"
severity: "medium"
module: "mflog_proto.playback"
tags:
  - "playback"
  - "time-series"
  - "csv"
  - "qt"
---

# Keep Playback Time Independent From Sample Index

## Context

MF-LOG-ANALYZER uses one shared playback clock for time-series graphs, GPS, G-G diagrams, sensor cards, and event markers. A tempting implementation is to store only the current sample index and derive the current time from that sample's timestamp. That breaks smooth playback when the timer advances by less than one sample interval.

## Guidance

Store `currentTimeMs` as its own clamped playback value, and separately track the nearest sample index for value lookup. Seeking by sample should update both fields to the exact sample timestamp; seeking by time should preserve the requested millisecond position and only use nearest-sample lookup for current sensor values.

```python
def set_time_ms(self, time_ms: int) -> None:
    clamped = min(max(int(time_ms), start_ms), self.total_time_ms)
    self._current_sample = self.sample_at_seconds(clamped / 1000)
    self._current_time_ms = clamped
    self._publish_playback()
```

Playback timer code should add elapsed wall-clock time to `currentTimeMs`, not to a timestamp derived from the currently selected sample.

## Why This Matters

With 100 ms sample spacing and a 33 ms UI timer, deriving time from the nearest sample can snap `33 ms` back to `0 ms` every tick. The UI appears frozen at 1x or slower speeds even though the timer is firing. Keeping an unsnapped playback clock lets the vertical graph cursor move smoothly while sensor cards still show the nearest row's values.

## When to Apply

Apply this whenever implementing playback, seek bars, synchronized graph cursors, event marker jumps, keyboard seek, or persisted playback position. Tests should cover a time between samples, such as `set_time_ms(33)` on `[0.0, 0.1, 0.2]`, and verify both the preserved time and the nearest sample index.
