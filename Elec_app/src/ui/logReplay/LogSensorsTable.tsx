import { useMemo, useState } from "react";
import type { LogSample, LogSession } from "../../domain/logReplayTypes";

interface LogSensorsTableProps {
  session: LogSession;
  sample: LogSample;
}

export function LogSensorsTable({ session, sample }: LogSensorsTableProps) {
  const [query, setQuery] = useState("");
  const sensors = useMemo(() => {
    const lower = query.trim().toLowerCase();
    return session.sensors
      .filter((sensor) => sensor.key !== "Timestamp")
      .filter((sensor) => !lower || sensor.key.toLowerCase().includes(lower) || sensor.label.toLowerCase().includes(lower));
  }, [query, session.sensors]);

  return (
    <section className="panel log-sensors-panel">
      <div className="section-heading">
        <h3>전체 센서</h3>
        <span>{sensors.length.toLocaleString()}개</span>
      </div>
      <label className="field">
        검색
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="RPM, Oil, adu..." />
      </label>
      <div className="log-sensor-table">
        <div className="log-sensor-table__head">
          <span>센서</span>
          <span>값</span>
          <span>단위</span>
          <span>타입</span>
        </div>
        {sensors.map((sensor) => (
          <div key={sensor.key}>
            <strong>{sensor.label}</strong>
            <span>{String(sample.values[sensor.key] ?? "-")}</span>
            <span>{sensor.unit ?? ""}</span>
            <span>{sensor.type}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
