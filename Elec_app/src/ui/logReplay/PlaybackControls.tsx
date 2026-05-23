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
      <div className="playback-controls">
        <button type="button" onClick={() => onSeek(0)}>
          처음
        </button>
        <button type="button" onClick={() => jumpToEvent(-1)}>
          이전 이벤트
        </button>
        <button
          type="button"
          disabled={duration <= 0}
          onClick={() => onPlaybackChange({ ...playback, isPlaying: !playback.isPlaying })}
        >
          {playback.isPlaying ? "일시정지" : "재생"}
        </button>
        <button type="button" onClick={() => jumpToEvent(1)}>
          다음 이벤트
        </button>
        <select
          value={playback.speed}
          onChange={(event) => onPlaybackChange({ ...playback, speed: Number(event.target.value) })}
        >
          {[0.25, 0.5, 1, 2, 4].map((speed) => (
            <option key={speed} value={speed}>
              {speed}x
            </option>
          ))}
        </select>
        <span>
          {formatTime(playback.currentTimeMs)} / {formatTime(duration)}
        </span>
      </div>
      <input
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
