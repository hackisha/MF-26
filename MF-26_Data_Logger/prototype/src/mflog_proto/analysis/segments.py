"""Time-range segment summaries for log analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class AnalysisSegment:
    name: str
    start_ms: int
    end_ms: int

    def normalized(self) -> AnalysisSegment:
        start = min(self.start_ms, self.end_ms)
        end = max(self.start_ms, self.end_ms)
        return AnalysisSegment(self.name, start, end)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AnalysisSegment:
        return cls(
            name=str(data.get("name", "Segment")),
            start_ms=int(data.get("start_ms", 0)),
            end_ms=int(data.get("end_ms", 0)),
        )


@dataclass(frozen=True)
class SegmentSummary:
    name: str
    start_ms: int
    end_ms: int
    duration_ms: int
    row_count: int
    average_speed: float | None
    max_speed: float | None
    min_rpm: float | None
    max_rpm: float | None
    average_tps: float | None
    max_abs_ax: float | None
    max_abs_ay: float | None
    min_battery_voltage: float | None


def compute_segment_summary(
    segment: AnalysisSegment,
    timestamps_seconds: Sequence[float],
    sensors: Mapping[str, Sequence[float | None]],
) -> SegmentSummary:
    normalized = segment.normalized()
    times_ms = np.asarray(timestamps_seconds, dtype=float) * 1000.0
    mask = (times_ms >= normalized.start_ms) & (times_ms <= normalized.end_ms)

    def channel_stat(
        names: tuple[str, ...],
        reducer: Callable[[np.ndarray], float],
    ) -> float | None:
        values: Sequence[float | None] | None = None
        for name in names:
            if name in sensors:
                values = sensors[name]
                break
        if values is None:
            return None

        selected = np.asarray(values, dtype=float)[mask]
        if selected.size == 0:
            return None
        finite = selected[np.isfinite(selected)]
        if finite.size == 0:
            return None
        return float(reducer(finite))

    return SegmentSummary(
        name=normalized.name,
        start_ms=normalized.start_ms,
        end_ms=normalized.end_ms,
        duration_ms=normalized.end_ms - normalized.start_ms,
        row_count=int(np.count_nonzero(mask)),
        average_speed=channel_stat(("VSS / GPS speed", "GPS speed", "VSS"), np.mean),
        max_speed=channel_stat(("VSS / GPS speed", "GPS speed", "VSS"), np.max),
        min_rpm=channel_stat(("RPM",), np.min),
        max_rpm=channel_stat(("RPM",), np.max),
        average_tps=channel_stat(("TPS", "TPS_percent"), np.mean),
        max_abs_ax=channel_stat(("ax", "AX_CORRECTED_G"), lambda values: np.max(np.abs(values))),
        max_abs_ay=channel_stat(("ay", "AY_CORRECTED_G"), lambda values: np.max(np.abs(values))),
        min_battery_voltage=channel_stat(("Battery voltage",), np.min),
    )
