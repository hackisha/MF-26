import type { LogEvent, LogSample, LogSession } from "../../domain/logReplayTypes";

interface LogDashboardProps {
  session: LogSession;
  sample: LogSample;
  selectedKeys: string[];
  events: LogEvent[];
  currentTimeMs: number;
}

function display(value: unknown): string {
  return typeof value === "number" ? value.toFixed(Math.abs(value) >= 100 ? 0 : 2) : String(value ?? "-");
}

export function LogDashboard({ session, sample, selectedKeys, events, currentTimeMs }: LogDashboardProps) {
  const rpm = Number(sample.values.RPM ?? 0);
  const speed = Number(sample.values.VSS_kmh ?? sample.values.GPS_Speed_KPH ?? 0);
  const gear = sample.values.Gear ?? "-";
  const warningCount = events.filter((event) => event.timeMs <= currentTimeMs && event.severity !== "info").length;
  const cards = selectedKeys
    .map((key) => ({ key, sensor: session.sensors.find((sensor) => sensor.key === key), value: sample.values[key] }))
    .filter((item) => item.sensor);

  return (
    <section className="emu-dashboard" aria-label="로그 대시보드">
      <div className="emu-dashboard__top">
        <div>
          <strong>MUZIL LOGGER</strong>
          <span>{session.fileName}</span>
        </div>
        <div className="emu-dashboard__time">{(currentTimeMs / 1000).toFixed(2)}s</div>
      </div>
      <div className="emu-dashboard__core">
        <div className="emu-dashboard__gear">{gear}</div>
        <div className="emu-dashboard__rpm">
          <span>RPM</span>
          <strong>{display(rpm)}</strong>
          <div className="emu-rpm-track">
            <span style={{ width: `${Math.min(100, (rpm / 12000) * 100)}%` }} />
          </div>
        </div>
        <div className="emu-dashboard__speed">
          <span>SPEED</span>
          <strong>{display(speed)}</strong>
          <small>km/h</small>
        </div>
      </div>
      <div className="emu-dashboard__cards">
        {cards.slice(0, 8).map(({ key, sensor, value }) => (
          <article key={key}>
            <span>{sensor?.label}</span>
            <strong>{display(value)}</strong>
            <small>{sensor?.unit}</small>
          </article>
        ))}
      </div>
      <div className={warningCount > 0 ? "emu-dashboard__alarm active" : "emu-dashboard__alarm"}>
        <span>WARNINGS</span>
        <strong>{warningCount}</strong>
      </div>
    </section>
  );
}
