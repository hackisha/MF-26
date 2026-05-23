import type { LogEvent, LogSession } from "../../domain/logReplayTypes";

interface EventStripProps {
  session: LogSession;
  events: LogEvent[];
  currentTimeMs: number;
  onSeek: (timeMs: number) => void;
}

export function EventStrip({ session, events, currentTimeMs, onSeek }: EventStripProps) {
  const duration = Math.max(1, session.summary.durationMs);

  return (
    <section className="panel event-strip-panel">
      <div className="section-heading">
        <h3>이벤트/이상 감지</h3>
        <span>{events.length}개</span>
      </div>
      <div className="event-strip">
        <div className="playhead-line" style={{ left: `${(currentTimeMs / duration) * 100}%` }} />
        {events.map((event) => (
          <button
            key={event.id}
            className={`event-marker ${event.severity}`}
            type="button"
            style={{ left: `${(event.timeMs / duration) * 100}%` }}
            title={event.description}
            onClick={() => onSeek(event.timeMs)}
          >
            {event.label}
          </button>
        ))}
      </div>
      <div className="event-list">
        {events.slice(0, 8).map((event) => (
          <button key={event.id} type="button" onClick={() => onSeek(event.timeMs)}>
            <strong>{event.label}</strong>
            <span>{(event.timeMs / 1000).toFixed(2)}s</span>
            <small>{event.description}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
