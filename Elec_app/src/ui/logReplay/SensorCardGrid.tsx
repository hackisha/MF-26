import type { LogSample, LogSession } from "../../domain/logReplayTypes";

interface SensorCardGridProps {
  session: LogSession;
  sample: LogSample;
  selectedKeys: string[];
  onToggleKey: (key: string) => void;
}

function formatValue(value: unknown): string {
  if (typeof value === "number") return value.toFixed(Math.abs(value) >= 100 ? 0 : 2);
  return String(value ?? "-");
}

export function SensorCardGrid({ session, sample, selectedKeys, onToggleKey }: SensorCardGridProps) {
  const available = session.sensors.filter((sensor) => sensor.type === "number" || sensor.type === "state");

  return (
    <section className="panel sensor-card-section">
      <div className="section-heading">
        <h3>주요 센서 카드</h3>
        <span>{selectedKeys.length}개 선택</span>
      </div>
      <div className="sensor-picker-row">
        {available.map((sensor) => (
          <button
            key={sensor.key}
            className={selectedKeys.includes(sensor.key) ? "chip selected" : "chip"}
            type="button"
            aria-pressed={selectedKeys.includes(sensor.key)}
            onClick={() => onToggleKey(sensor.key)}
          >
            {sensor.label}
          </button>
        ))}
      </div>
      <div className="sensor-card-grid">
        {selectedKeys.map((key) => {
          const sensor = session.sensors.find((item) => item.key === key);
          const value = sample.values[key];
          return (
            <article className="sensor-card" key={key}>
              <span>{sensor?.label ?? key}</span>
              <strong>{formatValue(value)}</strong>
              <small>{sensor?.unit ?? ""}</small>
            </article>
          );
        })}
      </div>
    </section>
  );
}
