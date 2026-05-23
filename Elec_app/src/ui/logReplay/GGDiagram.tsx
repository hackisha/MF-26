import { useMemo } from "react";
import type { LogSample, LogSession } from "../../domain/logReplayTypes";

interface GGDiagramProps {
  session: LogSession;
  currentSample: LogSample;
}

function getAccel(sample: LogSample, primary: string, fallback: string): number {
  const value = sample.values[primary] ?? sample.values[fallback];
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toPoint(ax: number, ay: number) {
  const range = 2;
  return {
    x: 150 + Math.max(-range, Math.min(range, ay)) * 65,
    y: 150 - Math.max(-range, Math.min(range, ax)) * 65,
  };
}

function chooseAccelPair(columns: string[]): [string, string] | null {
  if (columns.includes("ax_g") && columns.includes("ay_g")) return ["ax_g", "ay_g"];
  if (columns.includes("ADU_ax_g") && columns.includes("ADU_ay_g")) return ["ADU_ax_g", "ADU_ay_g"];
  return null;
}

function downsample<T>(items: T[], max: number): T[] {
  if (items.length <= max) return items;
  const step = (items.length - 1) / (max - 1);
  return Array.from({ length: max }, (_, index) => items[Math.round(index * step)]);
}

export function GGDiagram({ session, currentSample }: GGDiagramProps) {
  const accelPair = chooseAccelPair(session.columns);
  const [axKey, ayKey] = accelPair ?? ["ax_g", "ay_g"];
  const samples = useMemo(() => downsample(session.samples, 900), [session.samples]);
  const points = useMemo(
    () => samples.map((sample) => toPoint(getAccel(sample, axKey, axKey), getAccel(sample, ayKey, ayKey))),
    [axKey, ayKey, samples],
  );
  const axValues = useMemo(() => session.samples.map((sample) => getAccel(sample, axKey, axKey)), [axKey, session.samples]);
  const ayValues = useMemo(() => session.samples.map((sample) => getAccel(sample, ayKey, ayKey)), [ayKey, session.samples]);
  const current = toPoint(getAccel(currentSample, axKey, axKey), getAccel(currentSample, ayKey, ayKey));

  if (!accelPair) {
    return <section className="panel empty-panel">가속도 축 쌍이 없어 G-G 다이어그램을 표시할 수 없습니다.</section>;
  }

  return (
    <section className="panel gg-panel">
      <div className="section-heading">
        <h3>G-G 다이어그램</h3>
        <span>
          제동 {Math.min(...axValues).toFixed(2)}g · 가속 {Math.max(...axValues).toFixed(2)}g · 좌우{" "}
          {Math.min(...ayValues).toFixed(2)}/{Math.max(...ayValues).toFixed(2)}g
        </span>
      </div>
      <svg viewBox="0 0 300 300" aria-label="G-G 다이어그램">
        <circle cx="150" cy="150" r="65" className="gg-ring" />
        <circle cx="150" cy="150" r="130" className="gg-ring" />
        <line x1="0" x2="300" y1="150" y2="150" className="chart-grid" />
        <line x1="150" x2="150" y1="0" y2="300" className="chart-grid" />
        {points.map((point, index) => (
          <circle key={`${point.x}-${point.y}-${index}`} cx={point.x} cy={point.y} r="2" fill="rgba(56,189,248,.35)" />
        ))}
        <circle cx={current.x} cy={current.y} r="8" fill="#facc15" />
      </svg>
    </section>
  );
}
