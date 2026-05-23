import { useMemo, useState } from "react";
import { findNearestSample, limitOverlaySelection, normalizeSeries } from "../../domain/logReplayAnalysis";
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

interface TooltipState {
  left: number;
  top: number;
  timeMs: number;
}

function downsampleIndexes(length: number): number[] {
  if (length <= MAX_RENDER_POINTS) return Array.from({ length }, (_, index) => index);
  const step = (length - 1) / (MAX_RENDER_POINTS - 1);
  return Array.from({ length: MAX_RENDER_POINTS }, (_, index) => Math.round(index * step));
}

function formatValue(value: unknown): string {
  if (typeof value === "number") return value.toFixed(Math.abs(value) >= 100 ? 0 : 2);
  return String(value ?? "-");
}

export function SensorOverlayChart({
  session,
  selectedKeys,
  currentTimeMs,
  onSelectedKeysChange,
  onSeek,
}: SensorOverlayChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const numericSensors = session.sensors.filter((sensor) => sensor.type === "number" && sensor.key !== "Timestamp");
  const duration = Math.max(1, session.summary.durationMs);
  const playheadX = (currentTimeMs / duration) * 100;
  const renderIndexes = useMemo(() => downsampleIndexes(session.samples.length), [session.samples.length]);
  const tooltipSample = tooltip ? findNearestSample(session.samples, tooltip.timeMs) : undefined;
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
            aria-pressed={selectedKeys.includes(sensor.key)}
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
        data-testid="sensor-overlay-chart"
        role="slider"
        tabIndex={0}
        aria-label="오버랩 차트 재생 위치"
        aria-valuemin={0}
        aria-valuemax={Math.round(duration)}
        aria-valuenow={Math.round(currentTimeMs)}
        onKeyDown={(event) => {
          if (event.key === "ArrowLeft") onSeek(Math.max(0, currentTimeMs - 1000));
          if (event.key === "ArrowRight") onSeek(Math.min(duration, currentTimeMs + 1000));
        }}
        onMouseLeave={() => setTooltip(null)}
        onMouseMove={(event) => {
          const bounds = event.currentTarget.getBoundingClientRect();
          const ratio = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
          setTooltip({ left: ratio * 100, top: event.clientY - bounds.top, timeMs: ratio * duration });
        }}
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
        {tooltip && tooltipSample ? (
          <div className="overlay-tooltip" style={{ left: `${tooltip.left}%`, top: Math.max(8, tooltip.top - 8) }}>
            <strong>{(tooltip.timeMs / 1000).toFixed(2)}s</strong>
            {selectedKeys.map((key, index) => {
              const sensor = session.sensors.find((item) => item.key === key);
              return (
                <span key={key} style={{ color: COLORS[index] }}>
                  {sensor?.label ?? key}: {formatValue(tooltipSample.values[key])} {sensor?.unit ?? ""}
                </span>
              );
            })}
          </div>
        ) : null}
      </div>
    </section>
  );
}
