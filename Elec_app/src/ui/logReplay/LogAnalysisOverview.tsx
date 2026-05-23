import { useMemo, type KeyboardEvent } from "react";
import { projectGpsTrack } from "../../domain/gpsProjection";
import type { LogReplaySettings } from "../../domain/logSettingsTypes";
import type { LogSample, LogSession } from "../../domain/logReplayTypes";

interface LogAnalysisOverviewProps {
  session: LogSession;
  currentSample: LogSample;
  settings: LogReplaySettings;
  currentTimeMs: number;
  onSeek: (timeMs: number) => void;
}

interface SeriesSpec {
  key: string;
  label: string;
  color: string;
}

const SERIES_COLORS = ["#1d4ed8", "#dc2626", "#16a34a", "#7c3aed"];
const MAX_STRIP_POINTS = 700;
const MAX_GPS_POINTS = 800;
const MAX_GG_POINTS = 900;

function numberValue(sample: LogSample, key: string): number | undefined {
  const value = sample.values[key];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function formatValue(value: unknown): string {
  if (typeof value === "number") return value.toFixed(Math.abs(value) >= 100 ? 0 : 2);
  return String(value ?? "-");
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function normalize(values: Array<number | undefined>): number[] {
  const finite = values.filter((value): value is number => value !== undefined && Number.isFinite(value));
  if (finite.length === 0) return [];
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (min === max) return values.map(() => 0.5);
  return values.map((value) => (value === undefined ? 0.5 : (value - min) / (max - min)));
}

function downsample<T>(items: T[], max: number): T[] {
  if (items.length <= max) return items;
  const step = (items.length - 1) / (max - 1);
  return Array.from({ length: max }, (_, index) => items[Math.round(index * step)]);
}

function downsampleIndexes(length: number, max: number): number[] {
  if (length <= max) return Array.from({ length }, (_, index) => index);
  const step = (length - 1) / (max - 1);
  return Array.from({ length: max }, (_, index) => Math.round(index * step));
}

function hasNumericData(session: LogSession, key: string): boolean {
  return session.samples.some((sample) => numberValue(sample, key) !== undefined);
}

function pickColumn(session: LogSession, candidates: string[]): string | undefined {
  return candidates.find((key) => session.columns.includes(key));
}

function seriesPath(session: LogSession, key: string, width: number, height: number, renderIndexes: number[]): string {
  const values = normalize(session.samples.map((sample) => numberValue(sample, key)));
  if (values.length === 0) return "";
  const duration = Math.max(1, session.summary.durationMs);
  return renderIndexes
    .map((sampleIndex, pathIndex) => {
      const sample = session.samples[sampleIndex];
      const x = (sample.timeMs / duration) * width;
      const y = height - values[sampleIndex] * (height - 10) - 5;
      return `${pathIndex === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function AnalysisPanel({
  title,
  unit,
  session,
  currentTimeMs,
  series,
  onSeek,
}: {
  title: string;
  unit?: string;
  session: LogSession;
  currentTimeMs: number;
  series: SeriesSpec[];
  onSeek: (timeMs: number) => void;
}) {
  const width = 520;
  const height = 96;
  const duration = Math.max(1, session.summary.durationMs);
  const playheadX = clamp((currentTimeMs / duration) * width, 0, width);
  const seriesSignature = series.map((item) => `${item.key}:${item.label}:${item.color}`).join("|");
  const visibleSeries = useMemo(() => series.filter((item) => hasNumericData(session, item.key)), [seriesSignature, session]);
  const renderIndexes = useMemo(() => downsampleIndexes(session.samples.length, MAX_STRIP_POINTS), [session.samples.length]);
  const paths = useMemo(
    () =>
      visibleSeries.map((item) => ({
        ...item,
        path: seriesPath(session, item.key, width, height, renderIndexes),
      })),
    [renderIndexes, session, visibleSeries],
  );

  function seekByRatio(ratio: number) {
    onSeek(clamp(ratio, 0, 1) * duration);
  }

  function handleKeyDown(event: KeyboardEvent<SVGSVGElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      onSeek(Math.max(0, currentTimeMs - 1000));
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      onSeek(Math.min(duration, currentTimeMs + 1000));
    }
    if (event.key === "Home") {
      event.preventDefault();
      onSeek(0);
    }
    if (event.key === "End") {
      event.preventDefault();
      onSeek(duration);
    }
  }

  return (
    <section className="analysis-panel analysis-panel--strip">
      <div className="analysis-panel__head">
        <h3>{title}</h3>
        <span>{unit ?? "time series"}</span>
      </div>
      {visibleSeries.length ? (
        <svg
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="none"
          role="slider"
          tabIndex={0}
          aria-label={`${title} 재생 위치`}
          aria-valuemin={0}
          aria-valuemax={Math.round(duration)}
          aria-valuenow={Math.round(currentTimeMs)}
          onKeyDown={handleKeyDown}
          onClick={(event) => {
            const bounds = event.currentTarget.getBoundingClientRect();
            seekByRatio((event.clientX - bounds.left) / bounds.width);
          }}
        >
          {[0, 1, 2].map((line) => (
            <line key={line} x1="0" x2={width} y1={18 + line * 28} y2={18 + line * 28} className="analysis-grid-line" />
          ))}
          {paths.map((item) => (
            <path key={item.key} d={item.path} className="analysis-series-line" stroke={item.color} />
          ))}
          <line aria-label="현재 재생 위치" x1={playheadX} x2={playheadX} y1="0" y2={height} className="analysis-playhead" />
        </svg>
      ) : (
        <div className="analysis-empty">표시할 숫자 센서가 없습니다.</div>
      )}
      <div className="analysis-legend">
        {visibleSeries.map((item) => (
          <span key={item.key} style={{ color: item.color }}>
            {item.label}
          </span>
        ))}
      </div>
    </section>
  );
}

function GpsOverviewPanel({ session, currentSample, settings }: LogAnalysisOverviewProps) {
  const projected = useMemo(() => projectGpsTrack(session.samples, settings.gps), [session.samples, settings.gps]);
  const renderPoints = useMemo(() => downsample(projected.points, MAX_GPS_POINTS), [projected.points]);
  const bounds = projected.bounds;
  const current = useMemo(
    () =>
      projected.points.length
        ? projected.points.reduce((closest, point) => {
            return Math.abs(point.sample.timeMs - currentSample.timeMs) < Math.abs(closest.sample.timeMs - currentSample.timeMs) ? point : closest;
          }, projected.points[0])
        : undefined,
    [currentSample.timeMs, projected.points],
  );

  function x(value: number): number {
    return bounds.widthMeters <= 1 ? 260 : ((value - bounds.minX) / bounds.widthMeters) * 520;
  }

  function y(value: number): number {
    return bounds.heightMeters <= 1 ? 150 : 300 - ((value - bounds.minY) / bounds.heightMeters) * 300;
  }

  return (
    <section className="analysis-panel analysis-panel--gps">
      <div className="analysis-panel__head">
        <h3>GPS 궤적</h3>
        <span>{projected.points.length.toLocaleString()} points</span>
      </div>
      {projected.points.length >= 2 ? (
        <svg viewBox="0 0 520 300" preserveAspectRatio="xMidYMid meet">
          {renderPoints.slice(1).map((point, index) => {
            const previous = renderPoints[index];
            return (
              <line
                key={`${previous.sample.rowIndex}-${point.sample.rowIndex}`}
                x1={x(previous.xMeters)}
                y1={y(previous.yMeters)}
                x2={x(point.xMeters)}
                y2={y(point.yMeters)}
                className="analysis-gps-line"
              />
            );
          })}
          <circle cx={x(projected.points[0].xMeters)} cy={y(projected.points[0].yMeters)} r="5" className="analysis-start-dot" />
          {current ? <circle cx={x(current.xMeters)} cy={y(current.yMeters)} r="7" className="analysis-current-dot" /> : null}
        </svg>
      ) : (
        <div className="analysis-empty">GPS 데이터가 부족합니다.</div>
      )}
    </section>
  );
}

function adjustedLinearPair(sample: LogSample, settings: LogReplaySettings): [number, number] {
  let ax = numberValue(sample, settings.accel.linear.xKey) ?? 0;
  let ay = numberValue(sample, settings.accel.linear.yKey) ?? 0;
  if (settings.accel.linear.swapXY) [ax, ay] = [ay, ax];
  if (settings.accel.linear.invertX) ax *= -1;
  if (settings.accel.linear.invertY) ay *= -1;
  return [ax, ay];
}

function GGOverviewPanel({ session, currentSample, settings }: LogAnalysisOverviewProps) {
  const xKey = settings.accel.linear.xKey;
  const yKey = settings.accel.linear.yKey;
  const hasAccel = hasNumericData(session, xKey) && hasNumericData(session, yKey);
  const points = useMemo(() => {
    const validSamples = session.samples.filter((sample) => numberValue(sample, xKey) !== undefined && numberValue(sample, yKey) !== undefined);
    return downsample(validSamples, MAX_GG_POINTS).map((sample) => {
      const [ax, ay] = adjustedLinearPair(sample, settings);
      return { ax, ay, rowIndex: sample.rowIndex };
    });
  }, [session.samples, settings, xKey, yKey]);
  const [currentAx, currentAy] = adjustedLinearPair(currentSample, settings);
  const toX = (ay: number) => 170 + clamp(ay, -3, 3) * 52;
  const toY = (ax: number) => 170 - clamp(ax, -2.5, 2.5) * 56;

  return (
    <section className="analysis-panel analysis-panel--gg">
      <div className="analysis-panel__head">
        <h3>G-G 다이어그램</h3>
        <span>{xKey} / {yKey}</span>
      </div>
      {hasAccel ? (
        <svg viewBox="0 0 340 340" aria-label="G-G 다이어그램">
          <circle cx="170" cy="170" r="78" className="analysis-gg-ring" />
          <circle cx="170" cy="170" r="156" className="analysis-gg-limit" />
          <line x1="0" x2="340" y1="170" y2="170" className="analysis-axis-line" />
          <line x1="170" x2="170" y1="0" y2="340" className="analysis-axis-line" />
          {points.map((point) => (
            <circle key={point.rowIndex} cx={toX(point.ay)} cy={toY(point.ax)} r="1.5" className="analysis-gg-dot" />
          ))}
          <circle cx={toX(currentAy)} cy={toY(currentAx)} r="8" className="analysis-current-dot" />
        </svg>
      ) : (
        <div className="analysis-empty">G-G에 필요한 선형 가속도 데이터가 없습니다.</div>
      )}
    </section>
  );
}

export function LogAnalysisOverview(props: LogAnalysisOverviewProps) {
  const { session, currentSample, settings, currentTimeMs, onSeek } = props;
  const speedKey = pickColumn(session, ["GPS_Speed_KPH", "VSS_kmh", "VSS_kph"]);
  const vssKey = pickColumn(session, ["VSS_kmh", "VSS_kph", "GPS_Speed_KPH"]);
  const rpmKey = pickColumn(session, ["RPM"]);
  const gearKey = pickColumn(session, ["Gear"]);
  const batteryKey = pickColumn(session, ["Batt_V"]);
  const currentSpeed = speedKey ? numberValue(currentSample, speedKey) : undefined;
  const gearText = gearKey ? `${formatValue(currentSample.values[gearKey])}단` : "기어 없음";
  const batteryText = batteryKey ? `${formatValue(currentSample.values[batteryKey])}V` : "배터리 없음";
  const speedText = currentSpeed !== undefined ? `${formatValue(currentSpeed)}kph` : "속도 없음";

  return (
    <section className="analysis-overview" data-testid="analysis-overview">
      <div className="analysis-overview__left">
        <GpsOverviewPanel {...props} />
        <AnalysisPanel
          title="GPS 속도"
          unit="kph"
          session={session}
          currentTimeMs={currentTimeMs}
          onSeek={onSeek}
          series={speedKey ? [{ key: speedKey, label: speedKey, color: "#22c55e" }] : []}
        />
        <GGOverviewPanel {...props} />
      </div>
      <div className="analysis-overview__right">
        <AnalysisPanel
          title="가속도"
          unit="g"
          session={session}
          currentTimeMs={currentTimeMs}
          onSeek={onSeek}
          series={[
            { key: settings.accel.linear.xKey, label: "G ax", color: SERIES_COLORS[0] },
            { key: settings.accel.linear.yKey, label: "G ay", color: SERIES_COLORS[1] },
          ]}
        />
        <AnalysisPanel
          title="RPM / VSS"
          unit="normalized"
          session={session}
          currentTimeMs={currentTimeMs}
          onSeek={onSeek}
          series={[
            ...(rpmKey ? [{ key: rpmKey, label: "RPM", color: SERIES_COLORS[0] }] : []),
            ...(vssKey ? [{ key: vssKey, label: "VSS", color: SERIES_COLORS[1] }] : []),
          ]}
        />
        <AnalysisPanel
          title="Roll rate"
          unit="dps"
          session={session}
          currentTimeMs={currentTimeMs}
          onSeek={onSeek}
          series={[{ key: settings.accel.angular.xKey, label: settings.accel.angular.xKey, color: SERIES_COLORS[1] }]}
        />
        <AnalysisPanel
          title="Pitch rate"
          unit="dps"
          session={session}
          currentTimeMs={currentTimeMs}
          onSeek={onSeek}
          series={[{ key: settings.accel.angular.yKey, label: settings.accel.angular.yKey, color: SERIES_COLORS[2] }]}
        />
        <AnalysisPanel
          title="Yaw rate"
          unit="dps"
          session={session}
          currentTimeMs={currentTimeMs}
          onSeek={onSeek}
          series={[{ key: settings.accel.angular.zKey, label: settings.accel.angular.zKey, color: SERIES_COLORS[0] }]}
        />
        <AnalysisPanel
          title="기어 / 배터리"
          unit={`현재 ${gearText} · ${batteryText} · ${speedText}`}
          session={session}
          currentTimeMs={currentTimeMs}
          onSeek={onSeek}
          series={[
            ...(gearKey ? [{ key: gearKey, label: "Gear", color: "#111827" }] : []),
            ...(batteryKey ? [{ key: batteryKey, label: "Batt", color: SERIES_COLORS[0] }] : []),
          ]}
        />
      </div>
    </section>
  );
}
