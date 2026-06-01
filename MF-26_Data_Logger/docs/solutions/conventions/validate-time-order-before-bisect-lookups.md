---
title: "Validate time order before bisect lookups"
date: "2026-05-25"
track: "knowledge"
category: "conventions"
problem_type: "best_practice"
module: "mflog_proto.playback"
tags:
  - "time-series"
  - "playback"
  - "pyqtgraph"
  - "bisect"
---

# Validate Time Order Before Bisect Lookups

## Context

MF-LOG-ANALYZER uses time-based cursor lookup for playback and graph hover. During the P7 prototype review, `bisect_left()` was introduced for efficient nearest-sample selection, but the first version accepted arbitrary timestamp sequences. That would silently return wrong samples if a CSV import, channel transform, or filtered graph series became unsorted.

## Guidance

Treat sorted time as an explicit API contract at the boundary where playback state or renderable series are created. Validate the input once, fail with a clear `ValueError`, and then keep the fast lookup code simple.

```python
def _validated_sorted_floats(name: str, values: Sequence[float]) -> list[float]:
    output = [float(value) for value in values]
    if any(left > right for left, right in zip(output, output[1:])):
        raise ValueError(f"{name} must be sorted in ascending time order")
    return output
```

Use the same rule for graph series x-values before hover lookup or downsampling:

```python
def _require_sorted_x_values(channel_id: str, x_values: Sequence[float]) -> None:
    if any(left > right for left, right in zip(x_values, x_values[1:])):
        raise ValueError(f"x values for {channel_id} must be sorted in ascending time order")
```

## Why This Matters

`bisect_left()` is fast enough for large logs, but it is only correct on sorted sequences. A wrong cursor position is especially hard to diagnose because the UI still moves smoothly while showing the wrong sample. For 300k-row, 100-200 sensor logs, catching ordering drift at load or series construction is safer than debugging graph/video/playback desynchronization later.

## When to Apply

Apply this whenever adding time-based lookup, hover nearest-point selection, playback seek, visible-range slicing, downsampling windows, or cache-key range lookup. If a transform intentionally changes row order, either sort before exposing the data or carry an explicit sample-index mapping.

## Example Tests

```python
def test_playback_state_requires_sorted_timestamps():
    with pytest.raises(ValueError, match="timestamps must be sorted"):
        PlaybackState(timestamps=[0.0, 0.2, 0.1])


def test_time_series_window_requires_sorted_series_x_values(qtbot):
    playback = PlaybackState(timestamps=[0.0, 0.1, 0.2])
    window = TimeSeriesWindow(playback_state=playback)
    qtbot.addWidget(window)

    with pytest.raises(ValueError, match="RPM.*sorted"):
        window.set_series({"RPM": ([0.0, 0.2, 0.1], [1000.0, 3000.0, 2000.0])})
```
