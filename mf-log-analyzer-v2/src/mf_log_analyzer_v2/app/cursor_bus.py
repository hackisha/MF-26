from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class CursorEvent:
    kind: Literal["playback", "hover"]
    time_sec: float | None


@dataclass
class CursorBus:
    playback_time_sec: float | None = None
    hover_time_sec: float | None = None
    _subscribers: list[Callable[[CursorEvent], None]] = field(default_factory=list, init=False, repr=False)

    def subscribe(self, callback: Callable[[CursorEvent], None]) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[CursorEvent], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def set_playback_time(self, time_sec: float) -> None:
        self.playback_time_sec = time_sec
        self._publish(CursorEvent(kind="playback", time_sec=time_sec))

    def set_hover_time(self, time_sec: float) -> None:
        self.hover_time_sec = time_sec
        self._publish(CursorEvent(kind="hover", time_sec=time_sec))

    def clear_hover_time(self) -> None:
        self.hover_time_sec = None
        self._publish(CursorEvent(kind="hover", time_sec=None))

    def _publish(self, event: CursorEvent) -> None:
        for callback in list(self._subscribers):
            callback(event)
