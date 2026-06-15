from __future__ import annotations

from dataclasses import dataclass

from mf_log_analyzer_v2.core.models import LogTable


@dataclass
class PlaybackSession:
    log: LogTable
    current_time_sec: float = 0.0
    is_playing: bool = False
    playback_speed: float = 1.0

    def __post_init__(self) -> None:
        self.current_time_sec = self.log.time_range[0]

    def seek(self, time_sec: float) -> None:
        start_time, end_time = self.log.time_range
        self.current_time_sec = min(max(time_sec, start_time), end_time)

    def play(self) -> None:
        self.is_playing = True

    def pause(self) -> None:
        self.is_playing = False

    def tick(self, delta_sec: float) -> None:
        if not self.is_playing:
            return

        self.seek(self.current_time_sec + (delta_sec * self.playback_speed))
        if self.current_time_sec >= self.log.time_range[1]:
            self.is_playing = False
