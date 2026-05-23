import { summarizeLog } from "../domain/summary";
import { useSessionStore } from "../state/sessionStore";
import { SeverityBadge } from "./SeverityBadge";

const visibleCriticalEventLimit = 5;

function formatMetric(value: number | null, suffix = "", fractionDigits = 0): string {
  if (value === null) return "n/a";
  return `${value.toFixed(fractionDigits)}${suffix}`;
}

export function SummaryView() {
  const session = useSessionStore((state) => state.session);
  if (!session) return <section className="empty-state">Open a CSV to see the run summary.</section>;

  const summary = summarizeLog(session.log, session.events);
  const criticalEvents = session.events.filter((event) => event.severity === "critical");
  const visibleCriticalEvents = criticalEvents.slice(0, visibleCriticalEventLimit);
  const remainingCriticalEventCount = criticalEvents.length - visibleCriticalEvents.length;

  return (
    <section className="view-grid">
      <div className="panel">
        <h2>Run Summary</h2>
        <div className="metric-grid" aria-label="Run metrics">
          <Metric label="Duration" value={`${summary.durationSec.toFixed(2)} s`} />
          <Metric label="Max Speed" value={formatMetric(summary.maxSpeedKph, " km/h")} />
          <Metric label="Max RPM" value={formatMetric(summary.maxRpm)} />
          <Metric label="Max Corrected G" value={formatMetric(summary.maxCorrectedG, " g", 2)} />
          <Metric label="Max EOT_IN" value={formatMetric(summary.maxEotInC, " C")} />
          <Metric label="Min Oil Pressure" value={formatMetric(summary.minOilPressureBar, " bar", 1)} />
          <Metric label="Warning Events" value={summary.warningEventCount.toLocaleString()} />
          <Metric label="Critical Events" value={summary.criticalEventCount.toLocaleString()} />
        </div>
      </div>
      <div className="panel">
        <h2>Critical Events</h2>
        {criticalEvents.length === 0 ? (
          <p className="muted">No critical events detected.</p>
        ) : (
          <>
            <ul className="event-list">
              {visibleCriticalEvents.map((event) => (
                <li key={event.id}>
                  <SeverityBadge severity={event.severity} />
                  <span>{event.name}</span>
                  <span>{event.startSec.toFixed(2)} s</span>
                </li>
              ))}
            </ul>
            {remainingCriticalEventCount > 0 && (
              <p className="muted event-overflow-note">
                {remainingCriticalEventCount.toLocaleString()} more critical events not shown.
              </p>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
