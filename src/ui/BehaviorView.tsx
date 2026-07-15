import { useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "./plotlyCore";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { useSessionStore } from "../state/sessionStore";
import type { AnalysisSession, NumericLogRow } from "../domain/types";

const Plot = createPlotlyComponent(Plotly);
const vehicleModelUrl = `${import.meta.env.BASE_URL}models/car.glb`;
const MAX_GG_PLOT_POINTS = 6000;

type CloneableObject3D = object & {
  clone: (recursive?: boolean) => CloneableObject3D;
};

type GgPoint = {
  ax: number;
  ay: number;
};

type MotionCueSnapshot = {
  x: number;
  y: number;
  z: number;
  source: "gyro" | "adu";
};

type BehaviorStats = {
  peakLateralG: number | null;
  peakLongitudinalG: number | null;
  latestYawRate: number | null;
  samplesUsed: number;
};

type GgTraceType = "scatter" | "scattergl";

type GgTrace = {
  x: number[];
  y: number[];
  type: GgTraceType;
  mode: "markers" | "lines";
  name: string;
  marker?: {
    color: string;
    size: number;
    opacity: number;
    line: { color: string; width: number };
    symbol?: "diamond";
  };
  line?: {
    color: string;
    width: number;
    dash: "dash";
  };
  hoverinfo?: "skip";
};

type GgLayout = {
  autosize: true;
  margin: { t: number; r: number; b: number; l: number };
  paper_bgcolor: string;
  plot_bgcolor: string;
  hovermode: "closest";
  showlegend: true;
  legend: {
    orientation: "h";
    x: number;
    y: number;
    xanchor: "left";
    yanchor: "bottom";
  };
  xaxis: {
    title: { text: string };
    zeroline: true;
    zerolinecolor: string;
    gridcolor: string;
    range: [number, number];
    automargin: true;
  };
  yaxis: {
    title: { text: string };
    zeroline: true;
    zerolinecolor: string;
    gridcolor: string;
    range: [number, number];
    scaleanchor: "x";
    scaleratio: 1;
    automargin: true;
  };
};

const ggLimitRadiusG = 2;
const circleSampleCount = 96;

function finiteNumber(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function correctedGgPoints(rows: NumericLogRow[]): GgPoint[] {
  return rows
    .map((row) => ggPointForRow(row))
    .filter((point): point is GgPoint => point !== null);
}

function ggPointForRow(row: NumericLogRow): GgPoint | null {
  const ax = finiteNumber(row.values.ax_corrected_g);
  const ay = finiteNumber(row.values.ay_corrected_g);
  return ax !== null && ay !== null ? { ax, ay } : null;
}

function downsampleGgPoints(points: GgPoint[], maxPoints = MAX_GG_PLOT_POINTS): GgPoint[] {
  if (points.length <= maxPoints || maxPoints < 3) return points;

  const sampledPoints = [points[0]];
  const stride = Math.ceil((points.length - 2) / (maxPoints - 2));

  for (let index = 1; index < points.length - 1; index += stride) {
    sampledPoints.push(points[index]);
  }

  sampledPoints.push(points[points.length - 1]);
  return sampledPoints;
}

function nearestRowIndex(rows: NumericLogRow[], timeSec: number): number {
  if (rows.length === 0) return -1;
  if (timeSec <= rows[0].timestampSec) return 0;
  if (timeSec >= rows[rows.length - 1].timestampSec) return rows.length - 1;

  let low = 0;
  let high = rows.length - 1;
  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (rows[mid].timestampSec < timeSec) low = mid + 1;
    else high = mid;
  }

  const after = rows[low];
  const before = rows[low - 1];
  return Math.abs(after.timestampSec - timeSec) < Math.abs(timeSec - before.timestampSec) ? low : low - 1;
}

function rowAtTime(rows: NumericLogRow[], currentTimeSec: number | null): NumericLogRow | null {
  if (rows.length === 0) return null;
  const timeSec = currentTimeSec ?? rows[0].timestampSec;
  const index = nearestRowIndex(rows, timeSec);
  return index >= 0 ? rows[index] : null;
}

function motionCueForRow(row: NumericLogRow): MotionCueSnapshot | null {
  const gx = finiteNumber(row.values.gx_dps);
  const gy = finiteNumber(row.values.gy_dps);
  const gz = finiteNumber(row.values.gz_dps);
  if (gx !== null && gy !== null && gz !== null) return { x: gx, y: gy, z: gz, source: "gyro" };

  const aduX = finiteNumber(row.values.ADU_ax_g);
  const aduY = finiteNumber(row.values.ADU_ay_g);
  const aduZ = finiteNumber(row.values.ADU_az_g);
  if (aduX !== null && aduY !== null && aduZ !== null) return { x: aduX, y: aduY, z: aduZ, source: "adu" };

  return null;
}

function motionCueAtTime(rows: NumericLogRow[], currentTimeSec: number | null): MotionCueSnapshot | null {
  if (rows.length === 0) return null;

  const nearestIndex = nearestRowIndex(rows, currentTimeSec ?? rows[0].timestampSec);
  for (let distance = 0; distance < rows.length; distance += 1) {
    const candidateIndexes = distance === 0 ? [nearestIndex] : [nearestIndex - distance, nearestIndex + distance];
    for (const candidateIndex of candidateIndexes) {
      const row = rows[candidateIndex];
      if (!row) continue;
      const cue = motionCueForRow(row);
      if (cue) return cue;
    }
  }

  return null;
}

function maxAbs(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((max, value) => Math.max(max, Math.abs(value)), 0);
}

function behaviorStats(points: GgPoint[]): Omit<BehaviorStats, "latestYawRate"> {
  return {
    peakLateralG: maxAbs(points.map((point) => point.ay)),
    peakLongitudinalG: maxAbs(points.map((point) => point.ax)),
    samplesUsed: points.length
  };
}

function limitCircleTrace(radiusG: number): GgTrace {
  const angles = Array.from({ length: circleSampleCount + 1 }, (_value, index) => (Math.PI * 2 * index) / circleSampleCount);

  return {
    x: angles.map((angle) => radiusG * Math.cos(angle)),
    y: angles.map((angle) => radiusG * Math.sin(angle)),
    type: "scatter",
    mode: "lines",
    name: `${radiusG.toFixed(1)} g limit circle`,
    line: {
      color: "#b45309",
      width: 2,
      dash: "dash"
    },
    hoverinfo: "skip"
  };
}

function currentGgTrace(point: GgPoint): GgTrace {
  return {
    x: [point.ax],
    y: [point.ay],
    type: "scatter",
    mode: "markers",
    name: "Current playback sample",
    marker: {
      color: "#be123c",
      size: 13,
      opacity: 0.95,
      line: { color: "#ffffff", width: 1.5 },
      symbol: "diamond"
    }
  };
}

function ggSamplesTrace(points: GgPoint[], traceType: GgTraceType): GgTrace {
  return {
    x: points.map((point) => point.ax),
    y: points.map((point) => point.ay),
    type: traceType,
    mode: "markers",
    name: "All corrected G-G samples",
    marker: {
      color: "#0f766e",
      size: 5,
      opacity: 0.24,
      line: { color: "#ffffff", width: 0 }
    }
  };
}

function ggAxisLimit(points: GgPoint[]): number {
  const peak = Math.max(
    ggLimitRadiusG,
    ...points.flatMap((point) => [Math.abs(point.ax), Math.abs(point.ay)])
  );

  return Math.ceil((peak + 0.2) * 2) / 2;
}

function ggLayout(axisLimit: number): GgLayout {
  return {
    autosize: true,
    margin: { t: 18, r: 24, b: 52, l: 62 },
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    hovermode: "closest",
    showlegend: true,
    legend: {
      orientation: "h",
      x: 0,
      y: 1.06,
      xanchor: "left",
      yanchor: "bottom"
    },
    xaxis: {
      title: { text: "Longitudinal acceleration (g)" },
      zeroline: true,
      zerolinecolor: "#6b7b86",
      gridcolor: "#e7edf1",
      range: [-axisLimit, axisLimit],
      automargin: true
    },
    yaxis: {
      title: { text: "Lateral acceleration (g)" },
      zeroline: true,
      zerolinecolor: "#6b7b86",
      gridcolor: "#e7edf1",
      range: [-axisLimit, axisLimit],
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

function scaledCue(value: number, maxValue: number, maxRadians: number): number {
  return clamp(value / maxValue, -1, 1) * maxRadians;
}

function cueScale(snapshot: MotionCueSnapshot): { x: number; y: number; z: number } {
  return snapshot.source === "gyro" ? { x: 160, y: 160, z: 180 } : { x: 2.5, y: 2.5, z: 2.5 };
}

function FallbackVehicleBody() {
  return (
    <>
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
    </>
  );
}

function GlbVehicleBody({ modelUrl = vehicleModelUrl }: { modelUrl?: string }) {
  const [loadedScene, setLoadedScene] = useState<CloneableObject3D | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoadedScene(null);
    setFailed(false);

    const loader = new GLTFLoader();
    loader.load(
      modelUrl,
      (gltf) => {
        if (!cancelled) setLoadedScene(gltf.scene);
      },
      undefined,
      () => {
        if (!cancelled) setFailed(true);
      }
    );

    return () => {
      cancelled = true;
    };
  }, [modelUrl]);

  const scene = useMemo(() => loadedScene?.clone(true) ?? null, [loadedScene]);

  if (failed || !scene) return <FallbackVehicleBody />;

  return <primitive object={scene} position={[0.06, -0.09, 0]} scale={0.55} />;
}

function VehicleTendencyModel({ snapshot }: { snapshot: MotionCueSnapshot }) {
  const scale = cueScale(snapshot);
  const pitch = scaledCue(snapshot.y, scale.y, 0.34);
  const yaw = scaledCue(snapshot.z, scale.z, 0.52);
  const roll = scaledCue(snapshot.x, scale.x, 0.42);
  const yawCue = clamp(Math.abs(snapshot.z) / (snapshot.source === "gyro" ? 120 : 1.4), 0.18, 1);

  return (
    <Canvas camera={{ position: [4, 3, 5], fov: 42 }} className="behavior-canvas" gl={{ preserveDrawingBuffer: true }}>
      <ambientLight intensity={0.6} />
      <directionalLight position={[4, 6, 5]} intensity={1.2} />
      <group rotation={[pitch, yaw, -roll]}>
        <GlbVehicleBody />
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
  const currentTimeSec = useSessionStore((state) => state.currentTimeSec);
  const points = useMemo(() => correctedGgPoints(session.log.rows), [session.log.rows]);
  const plottedPoints = useMemo(() => downsampleGgPoints(points), [points]);
  const currentRow = useMemo(() => rowAtTime(session.log.rows, currentTimeSec), [currentTimeSec, session.log.rows]);
  const currentGgPoint = useMemo(() => (currentRow ? ggPointForRow(currentRow) : null), [currentRow]);
  const motionCue = useMemo(() => motionCueAtTime(session.log.rows, currentTimeSec), [currentTimeSec, session.log.rows]);
  const currentYawRate = useMemo(() => finiteNumber(currentRow?.values.gz_dps), [currentRow]);
  const staticStats = useMemo(() => behaviorStats(points), [points]);
  const stats: BehaviorStats = useMemo(() => ({ ...staticStats, latestYawRate: currentYawRate }), [currentYawRate, staticStats]);
  const sampleTraceType: GgTraceType = plottedPoints.length < points.length ? "scattergl" : "scatter";
  const sampleTrace = useMemo(() => ggSamplesTrace(plottedPoints, sampleTraceType), [plottedPoints, sampleTraceType]);
  const limitTrace = useMemo(() => limitCircleTrace(ggLimitRadiusG), []);
  const traces = useMemo(
    () => (currentGgPoint ? [sampleTrace, limitTrace, currentGgTrace(currentGgPoint)] : [sampleTrace, limitTrace]),
    [currentGgPoint, limitTrace, sampleTrace]
  );
  const layout = useMemo(() => ggLayout(ggAxisLimit(points)), [points]);

  return (
    <section className="behavior-view" aria-label="Vehicle behavior analysis">
      <div className="behavior-note">
        The 3D cue follows the shared playback time cursor. Gyro and ADU axes show qualitative tendency only, not a precision attitude estimate.
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
          <span>current yaw rate</span>
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
            <p>Corrected ADXL acceleration with a 2.0 g reference limit circle.</p>
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

        <section className="behavior-panel" aria-label="Motion cue model">
          <div className="behavior-panel-heading">
            <h2>{motionCue?.source === "adu" ? "ADU axis cue" : "Gyro roll/pitch/yaw cue"}</h2>
            <p>
              {motionCue?.source === "adu"
                ? "Using ADU_ax_g, ADU_ay_g, ADU_az_g at the shared playback time."
                : "Uses gx_dps, gy_dps, gz_dps at the shared playback time."}
            </p>
          </div>
          {motionCue ? (
            <div className="behavior-model-shell">
              <VehicleTendencyModel snapshot={motionCue} />
              <dl className="rate-readout">
                <div>
                  <dt>{motionCue.source === "adu" ? "ADU X" : "roll rate"}</dt>
                  <dd>{motionCue.source === "adu" ? formatG(motionCue.x) : formatDps(motionCue.x)}</dd>
                </div>
                <div>
                  <dt>{motionCue.source === "adu" ? "ADU Y" : "pitch rate"}</dt>
                  <dd>{motionCue.source === "adu" ? formatG(motionCue.y) : formatDps(motionCue.y)}</dd>
                </div>
                <div>
                  <dt>{motionCue.source === "adu" ? "ADU Z" : "yaw rate"}</dt>
                  <dd>{motionCue.source === "adu" ? formatG(motionCue.z) : formatDps(motionCue.z)}</dd>
                </div>
              </dl>
            </div>
          ) : (
            <div className="inline-empty">
              <h3>Motion cue unavailable</h3>
              <p>This CSV has no usable gyro rate or ADU axis values, so the 3D cue is hidden.</p>
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
