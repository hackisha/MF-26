"""Event review state for playback markers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class EventReviewState(str, Enum):
    UNREVIEWED = "unreviewed"
    CONFIRMED = "confirmed"
    IGNORED = "ignored"


@dataclass(frozen=True)
class EventReview:
    name: str
    time_ms: int
    severity: str
    sensor: str
    value: float
    condition: str
    state: EventReviewState = EventReviewState.UNREVIEWED
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "time_ms": self.time_ms,
            "severity": self.severity,
            "sensor": self.sensor,
            "value": self.value,
            "condition": self.condition,
            "state": self.state.value,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EventReview:
        state_value = str(data.get("state", EventReviewState.UNREVIEWED.value))
        try:
            state = EventReviewState(state_value)
        except ValueError:
            state = EventReviewState.UNREVIEWED

        return cls(
            name=str(data.get("name", "")),
            time_ms=int(data.get("time_ms", 0)),
            severity=str(data.get("severity", "info")),
            sensor=str(data.get("sensor", "")),
            value=float(data.get("value", 0.0)),
            condition=str(data.get("condition", "")),
            state=state,
            note=str(data.get("note", "")),
        )


def build_event_reviews(events: Iterable[Mapping[str, Any]]) -> tuple[EventReview, ...]:
    return tuple(EventReview.from_dict(event) for event in events)
