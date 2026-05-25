"""Playback and cursor synchronization primitives."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Sequence


class CursorKind(str, Enum):
    PLAYBACK = "playback"
    HOVER = "hover"


@dataclass(frozen=True)
class CursorEvent:
    kind: CursorKind
    sample_index: int
    seconds: float
    channel_id: str | None = None
    value: float | None = None
    is_playing: bool = False


CursorSubscriber = Callable[[CursorEvent], None]


class CursorBus:
    def __init__(self) -> None:
        self._subscribers: list[CursorSubscriber] = []

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def subscribe(self, subscriber: CursorSubscriber) -> Callable[[], None]:
        self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

        return unsubscribe

    def publish(self, event: CursorEvent) -> None:
        for subscriber in list(self._subscribers):
            subscriber(event)

    def publish_hover(
        self,
        *,
        sample_index: int,
        seconds: float,
        channel_id: str | None = None,
        value: float | None = None,
    ) -> None:
        self.publish(
            CursorEvent(
                kind=CursorKind.HOVER,
                sample_index=sample_index,
                seconds=seconds,
                channel_id=channel_id,
                value=value,
            )
        )


class PlaybackState:
    def __init__(self, timestamps: Sequence[float], cursor_bus: CursorBus | None = None) -> None:
        if not timestamps:
            raise ValueError("timestamps must contain at least one sample")
        self._timestamps = _validated_sorted_floats("timestamps", timestamps)
        self._cursor_bus = cursor_bus or CursorBus()
        self._current_sample = 0
        self._is_playing = False

    @property
    def current_sample(self) -> int:
        return self._current_sample

    @property
    def current_seconds(self) -> float:
        return self._timestamps[self._current_sample]

    @property
    def sample_count(self) -> int:
        return len(self._timestamps)

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def subscriber_count(self) -> int:
        return self._cursor_bus.subscriber_count

    def subscribe(self, subscriber: CursorSubscriber) -> Callable[[], None]:
        return self._cursor_bus.subscribe(subscriber)

    def set_sample(self, sample_index: int) -> None:
        clamped = min(max(sample_index, 0), self.sample_count - 1)
        if clamped == self._current_sample:
            return
        self._current_sample = clamped
        self._publish_playback()

    def set_seconds(self, seconds: float) -> None:
        self.set_sample(self.sample_at_seconds(seconds))

    def sample_at_seconds(self, seconds: float) -> int:
        insertion_index = bisect_left(self._timestamps, seconds)
        if insertion_index <= 0:
            return 0
        if insertion_index >= self.sample_count:
            return self.sample_count - 1

        before_index = insertion_index - 1
        after_index = insertion_index
        before_delta = abs(self._timestamps[before_index] - seconds)
        after_delta = abs(self._timestamps[after_index] - seconds)
        return before_index if before_delta <= after_delta else after_index

    def seconds_at(self, sample_index: int) -> float:
        clamped = min(max(sample_index, 0), self.sample_count - 1)
        return self._timestamps[clamped]

    def publish_hover(
        self,
        *,
        sample_index: int,
        channel_id: str | None = None,
        value: float | None = None,
    ) -> None:
        self._cursor_bus.publish_hover(
            sample_index=min(max(sample_index, 0), self.sample_count - 1),
            seconds=self.seconds_at(sample_index),
            channel_id=channel_id,
            value=value,
        )

    def step(self, delta_samples: int) -> None:
        self.set_sample(self._current_sample + delta_samples)

    def play(self) -> None:
        if self._is_playing:
            return
        self._is_playing = True
        self._publish_playback()

    def pause(self) -> None:
        if not self._is_playing:
            return
        self._is_playing = False
        self._publish_playback()

    def _publish_playback(self) -> None:
        self._cursor_bus.publish(
            CursorEvent(
                kind=CursorKind.PLAYBACK,
                sample_index=self._current_sample,
                seconds=self.current_seconds,
                is_playing=self._is_playing,
            )
        )


def _validated_sorted_floats(name: str, values: Sequence[float]) -> list[float]:
    output = [float(value) for value in values]
    if any(left > right for left, right in zip(output, output[1:])):
        raise ValueError(f"{name} must be sorted in ascending time order")
    return output
