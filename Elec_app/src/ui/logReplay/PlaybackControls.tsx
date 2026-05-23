import { Pause, Play, RotateCcw, SkipBack, SkipForward } from "lucide-react";
import type { LogEvent, LogSession, PlaybackState } from "../../domain/logReplayTypes";

interface PlaybackControlsProps {
  session: LogSession;
  playback: PlaybackState;
  events: LogEvent[];
  onPlaybackChange: (next: PlaybackState) => void;
  onSeek: (timeMs: number) => void;
}

function formatTime(ms: number): string {
  const totalSeconds = Math.max(0, ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds - minutes * 60;
  return `${minutes}:${seconds.toFixed(1).padStart(4, "0")}`;
}

export function PlaybackControls({ session, playback, events, onPlaybackChange, onSeek }: PlaybackControlsProps) {
  const duration = session.summary.durationMs;
  const rangeMax = Math.max(1, duration);

  function jumpToEvent(direction: -1 | 1) {
    const sorted = [...events].sort((a, b) => a.timeMs - b.timeMs);
    const target =
      direction > 0
        ? sorted.find((event) => event.timeMs > playback.currentTimeMs)
        : sorted.reverse().find((event) => event.timeMs < playback.currentTimeMs);
    if (target) onSeek(target.timeMs);
  }

  return (
    <section className="panel playback-panel">
      <div className="playback-panel__header">
        <div>
          <h2>재생 컨트롤</h2>
          <p>
            {formatTime(playback.currentTimeMs)} / {formatTime(duration)}
          </p>
        </div>
        <span>{playback.speed}x</span>
      </div>
      <div className="playback-controls">
        <button type="button" aria-label="처음으로 이동" onClick={() => onSeek(0)}>
          <RotateCcw size={17} />
        </button>
        <button type="button" aria-label="이전 이벤트" onClick={() => jumpToEvent(-1)}>
          <SkipBack size={17} />
        </button>
        <button
          type="button"
          aria-label={playback.isPlaying ? "일시정지" : "재생"}
          disabled={duration <= 0}
          onClick={() => onPlaybackChange({ ...playback, isPlaying: !playback.isPlaying })}
        >
          {playback.isPlaying ? <Pause size={17} /> : <Play size={17} />}
        </button>
        <button type="button" aria-label="다음 이벤트" onClick={() => jumpToEvent(1)}>
          <SkipForward size={17} />
        </button>
        <select
          aria-label="재생 속도"
          value={playback.speed}
          onChange={(event) => onPlaybackChange({ ...playback, speed: Number(event.target.value) })}
        >
          {[0.25, 0.5, 1, 2, 4].map((speed) => (
            <option key={speed} value={speed}>
              {speed}x
            </option>
          ))}
        </select>
      </div>
      <input
        aria-label="재생 위치"
        className="playback-range"
        type="range"
        min={0}
        max={rangeMax}
        value={Math.min(playback.currentTimeMs, duration)}
        disabled={duration <= 0}
        onChange={(event) => onSeek(Math.min(Number(event.target.value), duration))}
      />
    </section>
  );
}
