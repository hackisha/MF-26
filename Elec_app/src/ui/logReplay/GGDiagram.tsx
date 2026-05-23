import { useMemo } from "react";
import type { AccelConfig } from "../../domain/logSettingsTypes";
import type { LogSample, LogSession } from "../../domain/logReplayTypes";

interface GGDiagramProps {
  session: LogSession;
  currentSample: LogSample;
  accelConfig: AccelConfig;
}

function numberValue(sample: LogSample, key: string): number {
  const value = sample.values[key];
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toPoint(ax: number, ay: number) {
  const range = 2;
  return {
    x: 150 + Math.max(-range, Math.min(range, ay)) * 65,
    y: 150 - Math.max(-range, Math.min(range, ax)) * 65,
  };
}

function adjustedPair(sample: LogSample, xKey: string, yKey: string, config: AccelConfig): [number, number] {
  let ax = numberValue(sample, xKey);
  let ay = numberValue(sample, yKey);
  if (config.linear.swapXY) [ax, ay] = [ay, ax];
  if (config.linear.invertX) ax *= -1;
  if (config.linear.invertY) ay *= -1;
  return [ax, ay];
}

function downsample<T>(items: T[], max: number): T[] {
  if (items.length <= max) return items;
  const step = (items.length - 1) / (max - 1);
  return Array.from({ length: max }, (_, index) => items[Math.round(index * step)]);
}

export function GGDiagram({ session, currentSample, accelConfig }: GGDiagramProps) {
  const { xKey, yKey } = accelConfig.linear;
  const hasAccel = session.columns.includes(xKey) && session.columns.includes(yKey);
  const samples = useMemo(() => downsample(session.samples, 900), [session.samples]);
  const points = useMemo(() => {
    return samples.map((sample) => {
      const [ax, ay] = adjustedPair(sample, xKey, yKey, accelConfig);
      return toPoint(ax, ay);
    });
  }, [accelConfig.linear.invertX, accelConfig.linear.invertY, accelConfig.linear.swapXY, samples, xKey, yKey]);
  const axValues = useMemo(() => session.samples.map((sample) => numberValue(sample, xKey)), [session.samples, xKey]);
  const ayValues = useMemo(() => session.samples.map((sample) => numberValue(sample, yKey)), [session.samples, yKey]);
  const currentPair = adjustedPair(currentSample, xKey, yKey, accelConfig);
  const current = toPoint(currentPair[0], currentPair[1]);

  if (!hasAccel) {
    return <section className="panel empty-panel">ADXL 선형 가속도 축이 없어 G-G 다이어그램을 표시할 수 없습니다.</section>;
  }

  return (
    <section className="panel gg-panel">
      <div className="section-heading">
        <h3>G-G 다이어그램</h3>
        <span>
          전후 {Math.min(...axValues).toFixed(2)}g / {Math.max(...axValues).toFixed(2)}g · 좌우{" "}
          {Math.min(...ayValues).toFixed(2)}g / {Math.max(...ayValues).toFixed(2)}g
        </span>
      </div>
      <svg viewBox="0 0 300 300" aria-label="G-G 다이어그램">
        <circle cx="150" cy="150" r="65" className="gg-ring" />
        <circle cx="150" cy="150" r="130" className="gg-ring" />
        <line x1="0" x2="300" y1="150" y2="150" className="chart-grid" />
        <line x1="150" x2="150" y1="0" y2="300" className="chart-grid" />
        {points.map((point, index) => (
          <circle key={`${point.x}-${point.y}-${index}`} cx={point.x} cy={point.y} r="2" fill="rgba(37,99,235,.32)" />
        ))}
        <circle cx={current.x} cy={current.y} r="8" fill="#f59e0b" />
      </svg>
    </section>
  );
}
