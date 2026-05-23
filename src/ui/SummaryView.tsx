import { summarizeLog } from "../domain/summary";
import { useSessionStore } from "../state/sessionStore";
import { SeverityBadge } from "./SeverityBadge";

function formatMetric(value: number | null, suffix = "", fractionDigits = 0): string {
  if (value === null) return "n/a";
  return `${value.toFixed(fractionDigits)}${suffix}`;
}

export function SummaryView() {
  const session = useSessionStore((state) => state.session);
  if (!session) return <section className="empty-state">Open a CSV to see the run summary.</section>;

  const summary = summarizeLog(session.log, session.events);
  const criticalEvents = session.events.filter((event) => event.severity === "critical");

  return (
    <section className="view-grid">
      <div className="panel metric-grid" aria-label="Run metrics">
        <Metric label="Duration" value={`${summary.durationSec.toFixed(2)} s`} />
        <Metric label="Max Speed" value={formatMetric(summary.maxSpeedKph, " km/h")} />
        <Metric label="Max RPM" value={formatMetric(summary.maxRpm)} />
        <Metric label="Max Corrected G" value={formatMetric(summary.maxCorrectedG, " g", 2)} />
        <Metric label="Max EOT_IN" value={formatMetric(summary.maxEotInC, " C")} />
        <Metric label="Min Oil Pressure" value={formatMetric(summary.minOilPressureBar, " bar", 1)} />
      </div>
      <div className="panel">
        <h2>Critical Events</h2>
        {criticalEvents.length === 0 ? (
          <p className="muted">No critical events detected.</p>
        ) : (
          <ul className="event-list">
            {criticalEvents.map((event) => (
              <li key={event.id}>
                <SeverityBadge severity={event.severity} />
                <span>{event.name}</span>
                <span>{event.startSec.toFixed(2)} s</span>
              </li>
            ))}
          </ul>
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
