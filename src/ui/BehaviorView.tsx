import { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js-dist-min";
import { useSessionStore } from "../state/sessionStore";
import type { AnalysisSession, NumericLogRow } from "../domain/types";

const Plot = createPlotlyComponent(Plotly);

type GgPoint = {
  ax: number;
  ay: number;
};

type GyroSnapshot = {
  gx: number;
  gy: number;
  gz: number;
};

type BehaviorStats = {
  peakLateralG: number | null;
  peakLongitudinalG: number | null;
  latestYawRate: number | null;
  samplesUsed: number;
};

type GgTrace = {
  x: number[];
  y: number[];
  type: "scatter";
  mode: "markers";
  name: string;
  marker: {
    color: string;
    size: number;
    opacity: number;
    line: { color: string; width: number };
  };
};

type GgLayout = {
  autosize: true;
  margin: { t: number; r: number; b: number; l: number };
  paper_bgcolor: string;
  plot_bgcolor: string;
  hovermode: "closest";
  showlegend: false;
  xaxis: {
    title: { text: string };
    zeroline: true;
    zerolinecolor: string;
    gridcolor: string;
    automargin: true;
  };
  yaxis: {
    title: { text: string };
    zeroline: true;
    zerolinecolor: string;
    gridcolor: string;
    scaleanchor: "x";
    scaleratio: 1;
    automargin: true;
  };
};

function finiteNumber(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function correctedGgPoints(rows: NumericLogRow[]): GgPoint[] {
  return rows
    .map((row) => {
      const ax = finiteNumber(row.values.ax_corrected_g);
      const ay = finiteNumber(row.values.ay_corrected_g);
      return ax !== null && ay !== null ? { ax, ay } : null;
    })
    .filter((point): point is GgPoint => point !== null);
}

function latestGyroSnapshot(rows: NumericLogRow[]): GyroSnapshot | null {
  for (let index = rows.length - 1; index >= 0; index -= 1) {
    const row = rows[index];
    const gx = finiteNumber(row.values.gx_dps);
    const gy = finiteNumber(row.values.gy_dps);
    const gz = finiteNumber(row.values.gz_dps);
    if (gx !== null && gy !== null && gz !== null) return { gx, gy, gz };
  }

  return null;
}

function latestFiniteChannel(rows: NumericLogRow[], channelId: string): number | null {
  for (let index = rows.length - 1; index >= 0; index -= 1) {
    const value = finiteNumber(rows[index].values[channelId]);
    if (value !== null) return value;
  }

  return null;
}

function maxAbs(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((max, value) => Math.max(max, Math.abs(value)), 0);
}

function behaviorStats(points: GgPoint[], latestYawRate: number | null): BehaviorStats {
  return {
    peakLateralG: maxAbs(points.map((point) => point.ay)),
    peakLongitudinalG: maxAbs(points.map((point) => point.ax)),
    latestYawRate,
    samplesUsed: points.length
  };
}

function ggTrace(points: GgPoint[]): GgTrace[] {
  return [
    {
      x: points.map((point) => point.ax),
      y: points.map((point) => point.ay),
      type: "scatter",
      mode: "markers",
      name: "Corrected G-G samples",
      marker: {
        color: "#0f766e",
        size: 7,
        opacity: 0.72,
        line: { color: "#ffffff", width: 0.5 }
      }
    }
  ];
}

function ggLayout(): GgLayout {
  return {
    autosize: true,
    margin: { t: 18, r: 24, b: 52, l: 62 },
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    hovermode: "closest",
    showlegend: false,
    xaxis: {
      title: { text: "Longitudinal acceleration (g)" },
      zeroline: true,
      zerolinecolor: "#6b7b86",
      gridcolor: "#e7edf1",
      automargin: true
    },
    yaxis: {
      title: { text: "Lateral acceleration (g)" },
      zeroline: true,
      zerolinecolor: "#6b7b86",
      gridcolor: "#e7edf1",
      scaleanchor: "x",
      scaleratio: 1,
      automargin: true
    }
  };
}

function formatG(value: number | null): string {
  return value === null ? "n/a" : `${value.toFixed(2)} g`;
}

function formatDps(value: number | null): string {
  return value === null ? "n/a" : `${value.toFixed(1)} deg/s`;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function scaledRate(value: number, maxDps: number, maxRadians: number): number {
  return clamp(value / maxDps, -1, 1) * maxRadians;
}

function VehicleTendencyModel({ gyro }: { gyro: GyroSnapshot }) {
  const pitch = scaledRate(gyro.gy, 160, 0.34);
  const yaw = scaledRate(gyro.gz, 180, 0.52);
  const roll = scaledRate(gyro.gx, 160, 0.42);
  const yawCue = clamp(Math.abs(gyro.gz) / 120, 0.18, 1);

  return (
    <Canvas camera={{ position: [4, 3, 5], fov: 42 }} className="behavior-canvas">
      <ambientLight intensity={0.6} />
      <directionalLight position={[4, 6, 5]} intensity={1.2} />
      <group rotation={[pitch, yaw, -roll]}>
        <mesh position={[0, 0.25, 0]}>
          <boxGeometry args={[2.4, 0.32, 1.05]} />
          <meshStandardMaterial color="#0f766e" roughness={0.45} metalness={0.12} />
        </mesh>
        <mesh position={[1.38, 0.25, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.45, 0.82, 4]} />
          <meshStandardMaterial color="#d97706" roughness={0.38} metalness={0.08} />
        </mesh>
        <mesh position={[-1.05, 0.36, 0]}>
          <boxGeometry args={[0.34, 0.45, 1.2]} />
          <meshStandardMaterial color="#155e75" roughness={0.5} />
        </mesh>
        {[
          [-0.78, -0.05, -0.66],
          [-0.78, -0.05, 0.66],
          [0.82, -0.05, -0.66],
          [0.82, -0.05, 0.66]
        ].map(([x, y, z]) => (
          <mesh key={`${x}-${z}`} position={[x, y, z]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.22, 0.22, 0.18, 24]} />
            <meshStandardMaterial color="#172026" roughness={0.7} />
          </mesh>
        ))}
        <mesh position={[1.9, 0.25, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.13, 0.42, 24]} />
          <meshStandardMaterial color="#be123c" emissive="#7f1d1d" emissiveIntensity={0.12} />
        </mesh>
      </group>
      <mesh position={[0, -0.36, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.55, 1.61, 48, 1, 0, Math.PI * yawCue]} />
        <meshStandardMaterial color="#0284c7" transparent opacity={0.46} />
      </mesh>
      <gridHelper args={[4.5, 8, "#a9b4bc", "#d8e0e5"]} position={[0, -0.38, 0]} />
    </Canvas>
  );
}

function LoadedBehaviorView({ session }: { session: AnalysisSession }) {
  const points = useMemo(() => correctedGgPoints(session.log.rows), [session.log.rows]);
  const gyro = useMemo(() => latestGyroSnapshot(session.log.rows), [session.log.rows]);
  const latestYawRate = useMemo(() => latestFiniteChannel(session.log.rows, "gz_dps"), [session.log.rows]);
  const stats = useMemo(() => behaviorStats(points, latestYawRate), [latestYawRate, points]);
  const traces = useMemo(() => ggTrace(points), [points]);
  const layout = useMemo(() => ggLayout(), []);

  return (
    <section className="behavior-view" aria-label="Vehicle behavior analysis">
      <div className="behavior-note">
        Gyro-driven model shows instantaneous roll, pitch, and yaw tendency only. It is not a precision attitude estimate.
      </div>

      <div className="behavior-stat-strip" aria-label="Behavior statistics">
        <div className="behavior-stat">
          <span>peak lateral G</span>
          <strong>{formatG(stats.peakLateralG)}</strong>
        </div>
        <div className="behavior-stat">
          <span>peak longitudinal G</span>
          <strong>{formatG(stats.peakLongitudinalG)}</strong>
        </div>
        <div className="behavior-stat">
          <span>latest yaw rate</span>
          <strong>{formatDps(stats.latestYawRate)}</strong>
        </div>
        <div className="behavior-stat">
          <span>samples used</span>
          <strong>{stats.samplesUsed}</strong>
        </div>
      </div>

      <div className="behavior-grid">
        <section className="behavior-panel" aria-label="G-G diagram">
          <div className="behavior-panel-heading">
            <h2>G-G diagram</h2>
            <p>Corrected ADXL acceleration channels only.</p>
          </div>
          {points.length === 0 ? (
            <div className="inline-empty">
              <h3>No usable corrected acceleration</h3>
              <p>This view needs finite ax_corrected_g and ay_corrected_g samples for the G-G diagram.</p>
            </div>
          ) : (
            <Plot
              data={traces}
              layout={layout}
              config={{ displaylogo: false, responsive: true }}
              useResizeHandler
              className="behavior-plot"
            />
          )}
        </section>

        <section className="behavior-panel" aria-label="Vehicle tendency model">
          <div className="behavior-panel-heading">
            <h2>Rate tendency model</h2>
            <p>Latest finite gx_dps, gy_dps, gz_dps sample.</p>
          </div>
          {gyro ? (
            <div className="behavior-model-shell">
              <VehicleTendencyModel gyro={gyro} />
              <dl className="rate-readout">
                <div>
                  <dt>roll rate</dt>
                  <dd>{formatDps(gyro.gx)}</dd>
                </div>
                <div>
                  <dt>pitch rate</dt>
                  <dd>{formatDps(gyro.gy)}</dd>
                </div>
                <div>
                  <dt>yaw rate</dt>
                  <dd>{formatDps(gyro.gz)}</dd>
                </div>
              </dl>
            </div>
          ) : (
            <div className="inline-empty">
              <h3>No gyro tendency</h3>
              <p>Finite gx_dps, gy_dps, and gz_dps samples are needed for the rate-driven vehicle model.</p>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}

export function BehaviorView() {
  const session = useSessionStore((state) => state.session);

  if (!session) {
    return (
      <section className="empty-state">
        <h2>No log loaded</h2>
        <p>Open a CSV log to analyze vehicle behavior.</p>
      </section>
    );
  }

  return <LoadedBehaviorView session={session} />;
}
