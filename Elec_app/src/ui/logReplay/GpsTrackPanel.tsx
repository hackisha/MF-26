import { useMemo } from "react";
import type { LogSample, LogSession } from "../../domain/logReplayTypes";

interface GpsTrackPanelProps {
  session: LogSession;
  currentSample: LogSample;
}

function scale(value: number, min: number, max: number, size: number): number {
  if (min === max) return size / 2;
  return ((value - min) / (max - min)) * size;
}

const MAX_GPS_POINTS = 800;

function downsample<T>(items: T[], max: number): T[] {
  if (items.length <= max) return items;
  const step = (items.length - 1) / (max - 1);
  return Array.from({ length: max }, (_, index) => items[Math.round(index * step)]);
}

function colorForSpeed(speed: number): string {
  if (!Number.isFinite(speed)) return "#38bdf8";
  if (speed < 30) return "#38bdf8";
  if (speed < 70) return "#22c55e";
  if (speed < 110) return "#facc15";
  return "#f97316";
}

export function GpsTrackPanel({ session, currentSample }: GpsTrackPanelProps) {
  const points = useMemo(
    () =>
      session.samples
        .map((sample) => ({ lat: Number(sample.values.Latitude), lon: Number(sample.values.Longitude), sample }))
        .filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lon)),
    [session.samples],
  );
  const geometry = useMemo(() => {
    if (points.length < 2) return null;
    const lats = points.map((point) => point.lat);
    const lons = points.map((point) => point.lon);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    const renderPoints = downsample(points, MAX_GPS_POINTS);
    const screenPoints = renderPoints.map((point) => ({
      x: scale(point.lon, minLon, maxLon, 500),
      y: 300 - scale(point.lat, minLat, maxLat, 300),
      speed: Number(point.sample.values.GPS_Speed_KPH ?? point.sample.values.VSS_kmh),
    }));
    return { minLat, maxLat, minLon, maxLon, screenPoints };
  }, [points]);

  if (!geometry) {
    return <section className="panel empty-panel">GPS 컬럼이 없거나 경로를 그리기에 데이터가 부족합니다.</section>;
  }
  const currentLat = Number(currentSample.values.Latitude);
  const currentLon = Number(currentSample.values.Longitude);
  const currentX = scale(currentLon, geometry.minLon, geometry.maxLon, 500);
  const currentY = 300 - scale(currentLat, geometry.minLat, geometry.maxLat, 300);
  const currentSpeed = Number(currentSample.values.GPS_Speed_KPH ?? currentSample.values.VSS_kmh);

  return (
    <section className="panel gps-panel">
      <div className="section-heading">
        <h3>GPS 경로</h3>
        <span>
          {points.length.toLocaleString()} points
          {Number.isFinite(currentSpeed) ? ` · ${currentSpeed.toFixed(1)} km/h` : ""}
        </span>
      </div>
      <svg viewBox="0 0 500 300" preserveAspectRatio="xMidYMid meet" aria-label="GPS 경로">
        {geometry.screenPoints.slice(1).map((point, index) => {
          const previous = geometry.screenPoints[index];
          return (
            <line
              key={`${previous.x}-${previous.y}-${point.x}-${point.y}`}
              x1={previous.x}
              y1={previous.y}
              x2={point.x}
              y2={point.y}
              stroke={colorForSpeed(point.speed)}
              strokeWidth="4"
              strokeLinecap="round"
            />
          );
        })}
        {Number.isFinite(currentX) && Number.isFinite(currentY) ? <circle cx={currentX} cy={currentY} r="8" fill="#facc15" /> : null}
      </svg>
    </section>
  );
}
