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
        self._current_time_ms = round(self._timestamps[0] * 1000)
        self._is_playing = False
        self._playback_speed = 1.0

    @property
    def current_sample(self) -> int:
        return self._current_sample

    @property
    def current_seconds(self) -> float:
        return self._current_time_ms / 1000

    @property
    def current_time_ms(self) -> int:
        return self._current_time_ms

    @property
    def total_time_ms(self) -> int:
        return round(self._timestamps[-1] * 1000)

    @property
    def sample_count(self) -> int:
        return len(self._timestamps)

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def playback_speed(self) -> float:
        return self._playback_speed

    @property
    def subscriber_count(self) -> int:
        return self._cursor_bus.subscriber_count

    def subscribe(self, subscriber: CursorSubscriber) -> Callable[[], None]:
        return self._cursor_bus.subscribe(subscriber)

    def set_sample(self, sample_index: int) -> None:
        clamped = min(max(sample_index, 0), self.sample_count - 1)
        time_ms = round(self._timestamps[clamped] * 1000)
        if clamped == self._current_sample and time_ms == self._current_time_ms:
            return
        self._current_sample = clamped
        self._current_time_ms = time_ms
        self._publish_playback()

    def set_seconds(self, seconds: float) -> None:
        self.set_time_ms(round(seconds * 1000))

    def set_time_ms(self, time_ms: int) -> None:
        clamped = min(max(int(time_ms), round(self._timestamps[0] * 1000)), self.total_time_ms)
        sample_index = self.sample_at_seconds(clamped / 1000)
        if sample_index == self._current_sample and clamped == self._current_time_ms:
            return
        self._current_sample = sample_index
        self._current_time_ms = clamped
        self._publish_playback()

    def set_speed(self, speed: float) -> None:
        if speed <= 0:
            raise ValueError("speed must be positive")
        self._playback_speed = float(speed)
        self._publish_playback()

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
