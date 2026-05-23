import { useMemo } from "react";
import { limitOverlaySelection, normalizeSeries } from "../../domain/logReplayAnalysis";
import type { LogSession } from "../../domain/logReplayTypes";

interface SensorOverlayChartProps {
  session: LogSession;
  selectedKeys: string[];
  currentTimeMs: number;
  onSelectedKeysChange: (keys: string[]) => void;
  onSeek: (timeMs: number) => void;
}

const COLORS = ["#4cc9f0", "#ffc300", "#f72585", "#22c55e"];
const MAX_RENDER_POINTS = 900;

function downsampleIndexes(length: number): number[] {
  if (length <= MAX_RENDER_POINTS) return Array.from({ length }, (_, index) => index);
  const step = (length - 1) / (MAX_RENDER_POINTS - 1);
  return Array.from({ length: MAX_RENDER_POINTS }, (_, index) => Math.round(index * step));
}

export function SensorOverlayChart({
  session,
  selectedKeys,
  currentTimeMs,
  onSelectedKeysChange,
  onSeek,
}: SensorOverlayChartProps) {
  const numericSensors = session.sensors.filter((sensor) => sensor.type === "number" && sensor.key !== "Timestamp");
  const duration = Math.max(1, session.summary.durationMs);
  const playheadX = (currentTimeMs / duration) * 100;
  const renderIndexes = useMemo(() => downsampleIndexes(session.samples.length), [session.samples.length]);
  const paths = useMemo(() => {
    return Object.fromEntries(
      selectedKeys.map((key) => {
        const values = session.samples.map((sample) => Number(sample.values[key]));
        const normalized = normalizeSeries(values);
        const path = renderIndexes
          .map((sampleIndex, pathIndex) => {
            const sample = session.samples[sampleIndex];
            const x = (sample.timeMs / duration) * 800;
            const y = 220 - normalized[sampleIndex] * 190;
            return `${pathIndex === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
          })
          .join(" ");
        return [key, path];
      }),
    );
  }, [duration, renderIndexes, selectedKeys, session.samples]);

  return (
    <section className="panel overlay-panel">
      <div className="section-heading">
        <h3>센서 오버랩</h3>
        <span>최대 4개</span>
      </div>
      <div className="sensor-picker-row">
        {numericSensors.map((sensor) => (
          <button
            key={sensor.key}
            className={selectedKeys.includes(sensor.key) ? "chip selected" : "chip"}
            type="button"
            onClick={() => onSelectedKeysChange(limitOverlaySelection(selectedKeys, sensor.key))}
          >
            {sensor.label}
          </button>
        ))}
      </div>
      <div className="overlay-legend">
        {selectedKeys.map((key, index) => (
          <span key={key} style={{ color: COLORS[index] }}>
            {session.sensors.find((sensor) => sensor.key === key)?.label ?? key}
          </span>
        ))}
      </div>
      <div
        className="overlay-chart"
        onClick={(event) => {
          const bounds = event.currentTarget.getBoundingClientRect();
          onSeek(((event.clientX - bounds.left) / bounds.width) * duration);
        }}
      >
        <svg viewBox="0 0 800 240" preserveAspectRatio="none" aria-label="선택 센서 오버랩 그래프">
          {[0, 1, 2, 3].map((line) => (
            <line key={line} x1="0" x2="800" y1={30 + line * 55} y2={30 + line * 55} className="chart-grid" />
          ))}
          {selectedKeys.map((key, index) => (
            <path key={key} d={paths[key]} fill="none" stroke={COLORS[index]} strokeWidth="4" />
          ))}
        </svg>
        <div className="playhead-line" style={{ left: `${playheadX}%` }} />
      </div>
    </section>
  );
}
