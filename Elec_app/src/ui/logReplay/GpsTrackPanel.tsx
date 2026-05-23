import { useMemo } from "react";
import { projectGpsTrack } from "../../domain/gpsProjection";
import type { GpsConfig } from "../../domain/logSettingsTypes";
import type { LogSample, LogSession } from "../../domain/logReplayTypes";

interface GpsTrackPanelProps {
  session: LogSession;
  currentSample: LogSample;
  gpsConfig: GpsConfig;
}

const MAX_GPS_POINTS = 800;

function scale(value: number, min: number, max: number, size: number): number {
  if (min === max) return size / 2;
  return ((value - min) / (max - min)) * size;
}

function downsample<T>(items: T[], max: number): T[] {
  if (items.length <= max) return items;
  const step = (items.length - 1) / (max - 1);
  return Array.from({ length: max }, (_, index) => items[Math.round(index * step)]);
}

function colorForSpeed(speed: number): string {
  if (!Number.isFinite(speed)) return "#2563eb";
  if (speed < 30) return "#22c55e";
  if (speed < 70) return "#16a34a";
  if (speed < 110) return "#f59e0b";
  return "#dc2626";
}

export function GpsTrackPanel({ session, currentSample, gpsConfig }: GpsTrackPanelProps) {
  const projected = useMemo(() => projectGpsTrack(session.samples, gpsConfig), [gpsConfig, session.samples]);
  const renderPoints = useMemo(() => downsample(projected.points, MAX_GPS_POINTS), [projected.points]);

  if (projected.points.length < 2) {
    return <section className="panel empty-panel">GPS 컬럼이 없거나 경로를 그리기에 데이터가 부족합니다.</section>;
  }

  const currentProjected = projected.points.reduce((closest, point) => {
    return Math.abs(point.sample.timeMs - currentSample.timeMs) < Math.abs(closest.sample.timeMs - currentSample.timeMs) ? point : closest;
  }, projected.points[0]);
  const currentX = currentProjected ? scale(currentProjected.xMeters, projected.bounds.minX, projected.bounds.maxX, 500) : Number.NaN;
  const currentY = currentProjected ? 300 - scale(currentProjected.yMeters, projected.bounds.minY, projected.bounds.maxY, 300) : Number.NaN;
  const currentSpeed = Number(currentSample.values[gpsConfig.speedKey] ?? currentSample.values.VSS_kmh);

  return (
    <section className="panel gps-panel">
      <div className="section-heading">
        <h3>GPS 궤적</h3>
        <span>
          {projected.points.length.toLocaleString()} points
          {Number.isFinite(currentSpeed) ? ` · ${currentSpeed.toFixed(1)} km/h` : ""}
        </span>
      </div>
      <svg viewBox="0 0 500 300" preserveAspectRatio="xMidYMid meet" aria-label="GPS 궤적">
        {renderPoints.slice(1).map((point, index) => {
          const previous = renderPoints[index];
          const x1 = scale(previous.xMeters, projected.bounds.minX, projected.bounds.maxX, 500);
          const y1 = 300 - scale(previous.yMeters, projected.bounds.minY, projected.bounds.maxY, 300);
          const x2 = scale(point.xMeters, projected.bounds.minX, projected.bounds.maxX, 500);
          const y2 = 300 - scale(point.yMeters, projected.bounds.minY, projected.bounds.maxY, 300);
          return (
            <line
              key={`${previous.sample.rowIndex}-${point.sample.rowIndex}`}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={colorForSpeed(point.speed)}
              strokeWidth="4"
              strokeLinecap="round"
            />
          );
        })}
        {Number.isFinite(currentX) && Number.isFinite(currentY) ? <circle cx={currentX} cy={currentY} r="8" fill="#f59e0b" /> : null}
      </svg>
    </section>
  );
}
