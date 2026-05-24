import { useMemo } from "react";
import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js-dist-min";
import { useSessionStore } from "../state/sessionStore";
import type { NumericLogRow, OverlayPreset, SensorChannel, VehicleProfile } from "../domain/types";
import { ChannelPicker } from "./ChannelPicker";

const Plot = createPlotlyComponent(Plotly);
const AXIS_SPACING = 0.055;
const MAX_AXIS_PADDING = 0.24;
const MAX_TIME_SERIES_PLOT_POINTS = 6000;

type PlotPoint = number | null;
type TraceType = "scatter" | "scattergl";

type Trace = {
  x: PlotPoint[];
  y: PlotPoint[];
  type: TraceType;
  mode: "lines";
  name: string;
  line: {
    color: string;
    width: number;
  };
  connectgaps: false;
  yaxis: string;
};

type PlottableChannel = {
  channel: SensorChannel;
  values: PlotPoint[];
};

type PlotAxis = {
  title: { text: string };
  zeroline: false;
  automargin: true;
  overlaying?: "y";
  side?: "left" | "right";
  anchor?: "free";
  position?: number;
};

type PlotShape = {
  type: "line";
  x0: number;
  x1: number;
  y0: 0;
  y1: 1;
  xref: "x";
  yref: "paper";
  line: { color: string; width: number; dash: "dot" };
};

type DownsampledSeries = {
  x: PlotPoint[];
  y: PlotPoint[];
};

type PlotLayout = {
  autosize: true;
  margin: { t: number; r: number; b: number; l: number };
  paper_bgcolor: string;
  plot_bgcolor: string;
  hovermode: "x unified";
  showlegend: true;
  legend: { orientation: "h"; x: number; y: number };
  xaxis: { title: { text: string }; zeroline: false; domain?: [number, number] };
  yaxis: PlotAxis;
  shapes?: PlotShape[];
  [axisKey: `yaxis${number}`]: PlotAxis;
};

type AxisPadding = {
  left: number;
  right: number;
};

function finiteOrNull(value: number): PlotPoint {
  return Number.isFinite(value) ? value : null;
}

function finiteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function normalizeValues(values: PlotPoint[]): PlotPoint[] {
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;

  for (const value of values) {
    if (value === null) continue;
    if (value < min) min = value;
    if (value > max) max = value;
  }

  if (!Number.isFinite(min) || !Number.isFinite(max)) return values;
  if (min === max) return values.map((value) => (value === null ? null : 50));

  const range = max - min;
  return values.map((value) => (value === null ? null : ((value - min) / range) * 100));
}

function downsampleSeries(
  xValues: PlotPoint[],
  yValues: PlotPoint[],
  maxPoints = MAX_TIME_SERIES_PLOT_POINTS
): DownsampledSeries {
  if (xValues.length <= maxPoints || maxPoints < 3) return { x: xValues, y: yValues };

  const sampledIndexes: number[] = [0];
  const bucketCount = Math.max(1, Math.floor((maxPoints - 2) / 2));
  const bucketSize = Math.ceil((xValues.length - 2) / bucketCount);

  for (let start = 1; start < xValues.length - 1; start += bucketSize) {
    const end = Math.min(xValues.length - 1, start + bucketSize);
    let minIndex = -1;
    let maxIndex = -1;
    let minValue = Number.POSITIVE_INFINITY;
    let maxValue = Number.NEGATIVE_INFINITY;

    for (let index = start; index < end; index += 1) {
      const value = yValues[index];
      if (!finiteNumber(value)) continue;
      if (value < minValue) {
        minValue = value;
        minIndex = index;
      }
      if (value > maxValue) {
        maxValue = value;
        maxIndex = index;
      }
    }

    if (minIndex === -1 || maxIndex === -1) {
      sampledIndexes.push(start);
      continue;
    }

    const orderedIndexes = minIndex <= maxIndex ? [minIndex, maxIndex] : [maxIndex, minIndex];
    for (const index of orderedIndexes) {
      if (sampledIndexes.at(-1) !== index) sampledIndexes.push(index);
    }
  }

  if (sampledIndexes.at(-1) !== xValues.length - 1) sampledIndexes.push(xValues.length - 1);

  return {
    x: sampledIndexes.map((index) => xValues[index]),
    y: sampledIndexes.map((index) => yValues[index])
  };
}

function traceTypeForPointCount(pointCount: number): TraceType {
  return pointCount > MAX_TIME_SERIES_PLOT_POINTS ? "scattergl" : "scatter";
}

function activeProfile(profiles: VehicleProfile[], profileId: string): VehicleProfile | null {
  return profiles.find((profile) => profile.id === profileId) ?? profiles[0] ?? null;
}

function resolveOverlay(profile: VehicleProfile, selectedOverlay: OverlayPreset | null): OverlayPreset | null {
  if (selectedOverlay && profile.overlays.some((overlay) => overlay.id === selectedOverlay.id)) return selectedOverlay;
  return profile.overlays[0] ?? null;
}

function plottableChannels(
  profile: VehicleProfile,
  overlay: OverlayPreset,
  rows: NumericLogRow[]
): PlottableChannel[] {
  return overlay.channelIds
    .map((channelId) => profile.channels[channelId])
    .filter((channel): channel is SensorChannel => Boolean(channel))
    .map((channel) => {
      const values = rows.map((row) => finiteOrNull(row.values[channel.id] ?? Number.NaN));
      const hasFiniteValue = values.some((value) => value !== null);
      return hasFiniteValue ? { channel, values } : null;
    })
    .filter((entry): entry is PlottableChannel => entry !== null);
}

function traceName(channel: SensorChannel): string {
  return channel.displayName;
}

function traceAxisId(index: number, overlay: OverlayPreset): string {
  if (overlay.mode === "normalized") return "y";
  return index === 0 ? "y" : `y${index + 1}`;
}

function layoutAxisKey(index: number): "yaxis" | `yaxis${number}` {
  return index === 0 ? "yaxis" : `yaxis${index + 1}`;
}

function axisTitle(channel: SensorChannel): string {
  return channel.unit ? `${channel.displayName} (${channel.unit})` : channel.displayName;
}

function clampAxisPosition(position: number): number {
  return Math.min(1, Math.max(0, Number(position.toFixed(3))));
}

function axisPadding(traceCount: number): AxisPadding {
  const extraLeftAxes = Math.floor((traceCount - 1) / 2);
  const extraRightAxes = Math.ceil((traceCount - 1) / 2);

  return {
    left: Math.min(MAX_AXIS_PADDING, extraLeftAxes * AXIS_SPACING),
    right: Math.min(MAX_AXIS_PADDING, extraRightAxes * AXIS_SPACING)
  };
}

function axisPosition(index: number, traceCount: number): number | undefined {
  if (index === 0) return undefined;

  const padding = axisPadding(traceCount);
  const domainStart = padding.left;
  const domainEnd = 1 - padding.right;

  if (index % 2 === 1) {
    const rightOrdinal = Math.floor((index - 1) / 2);
    return clampAxisPosition(domainEnd + rightOrdinal * AXIS_SPACING);
  }

  const leftOrdinal = Math.floor(index / 2) - 1;
  return clampAxisPosition(domainStart - (leftOrdinal + 1) * AXIS_SPACING);
}

function axisSide(index: number): "left" | "right" {
  return index % 2 === 1 ? "right" : "left";
}

function xAxisDomain(traceCount: number, overlay: OverlayPreset): [number, number] | undefined {
  if (overlay.mode !== "separateAxes" || traceCount < 3) return undefined;

  const padding = axisPadding(traceCount);
  return [padding.left, 1 - padding.right];
}

function tracesForChannels(overlay: OverlayPreset, rows: NumericLogRow[], channels: PlottableChannel[]): Trace[] {
  const xValues = rows.map((row) => finiteOrNull(row.timestampSec));
  return channels.map(({ channel, values }, index) => {
    const yValues = overlay.mode === "normalized" ? normalizeValues(values) : values;
    const sampledSeries = downsampleSeries(xValues, yValues);

    return {
      x: sampledSeries.x,
      y: sampledSeries.y,
      type: traceTypeForPointCount(xValues.length),
      mode: "lines",
      name: traceName(channel),
      line: {
        color: channel.color,
        width: 2
      },
      connectgaps: false,
      yaxis: traceAxisId(index, overlay)
    };
  });
}

function playbackCursorShape(currentTimeSec: number): PlotShape {
  return {
    type: "line",
    x0: currentTimeSec,
    x1: currentTimeSec,
    y0: 0,
    y1: 1,
    xref: "x",
    yref: "paper",
    line: { color: "#b45309", width: 1.5, dash: "dot" }
  };
}

function layoutForChannels(overlay: OverlayPreset, channels: PlottableChannel[], currentTimeSec: number | null): PlotLayout {
  const domain = xAxisDomain(channels.length, overlay);
  const padding = axisPadding(channels.length);
  const layout: PlotLayout = {
    autosize: true,
    margin: {
      t: 16,
      r: overlay.mode === "separateAxes" ? 64 + padding.right * 520 : 24,
      b: 48,
      l: overlay.mode === "separateAxes" ? 64 + padding.left * 520 : 56
    },
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    hovermode: "x unified",
    showlegend: true,
    legend: { orientation: "h", x: 0, y: 1.12 },
    xaxis: { title: { text: "Time (s)" }, zeroline: false, ...(domain ? { domain } : {}) },
    yaxis: {
      title: { text: overlay.mode === "normalized" ? "Normalized value" : axisTitle(channels[0].channel) },
      zeroline: false,
      automargin: true,
      side: "left"
    },
    ...(finiteNumber(currentTimeSec) ? { shapes: [playbackCursorShape(currentTimeSec)] } : {})
  };

  if (overlay.mode === "separateAxes") {
    channels.slice(1).forEach(({ channel }, offset) => {
      const index = offset + 1;
      layout[layoutAxisKey(index)] = {
        title: { text: axisTitle(channel) },
        zeroline: false,
        automargin: true,
        overlaying: "y",
        side: axisSide(index),
        anchor: "free",
        position: axisPosition(index, channels.length)
      };
    });
  }

  return layout;
}

type LoadedTimeSeriesViewProps = {
  session: NonNullable<ReturnType<typeof useSessionStore.getState>["session"]>;
  profile: VehicleProfile;
  overlay: OverlayPreset | null;
  setSelectedOverlay: (overlay: OverlayPreset | null) => void;
};

function LoadedTimeSeriesView({ session, profile, overlay, setSelectedOverlay }: LoadedTimeSeriesViewProps) {
  const currentTimeSec = useSessionStore((state) => state.currentTimeSec);
  const channels = useMemo(
    () => (overlay ? plottableChannels(profile, overlay, session.log.rows) : []),
    [overlay, profile, session.log.rows]
  );
  const traces = useMemo(() => (overlay ? tracesForChannels(overlay, session.log.rows, channels) : []), [channels, overlay, session.log.rows]);
  const layout = useMemo(
    () => (overlay && channels.length > 0 ? layoutForChannels(overlay, channels, currentTimeSec) : null),
    [channels, currentTimeSec, overlay]
  );

  return (
    <section className="time-series-view" aria-label="Time-series graph">
      <div className="view-toolbar">
        <ChannelPicker profile={profile} selectedOverlay={overlay} onOverlayChange={setSelectedOverlay} />
        {overlay && (
          <p className="toolbar-note">
            {overlay.mode === "normalized" ? "Normalized 0-100 scale" : "Separate native-unit axes"}
          </p>
        )}
      </div>

      {!overlay ? (
        <section className="empty-state">
          <h2>No overlays configured</h2>
          <p>This profile does not define time-series overlay presets yet.</p>
        </section>
      ) : traces.length === 0 ? (
        <section className="empty-state">
          <h2>No plottable channels</h2>
          <p>The selected overlay has configured channels, but none contain finite values in this log.</p>
        </section>
      ) : (
        <div className="graph-panel">
          <Plot
            data={traces}
            layout={layout ?? undefined}
            config={{ displaylogo: false, responsive: true }}
            useResizeHandler
            className="time-series-plot"
          />
        </div>
      )}
    </section>
  );
}

export function TimeSeriesView() {
  const session = useSessionStore((state) => state.session);
  const profiles = useSessionStore((state) => state.profiles);
  const selectedOverlay = useSessionStore((state) => state.selectedOverlay);
  const setSelectedOverlay = useSessionStore((state) => state.setSelectedOverlay);

  if (!session) {
    return (
      <section className="empty-state">
        <h2>No log loaded</h2>
        <p>Open a CSV log to plot configured sensor overlays.</p>
      </section>
    );
  }

  const profile = activeProfile(profiles, session.profileId);
  if (!profile) {
    return (
      <section className="empty-state">
        <h2>No profile available</h2>
        <p>The current session does not have an available vehicle profile.</p>
      </section>
    );
  }

  const overlay = resolveOverlay(profile, selectedOverlay);
  return <LoadedTimeSeriesView session={session} profile={profile} overlay={overlay} setSelectedOverlay={setSelectedOverlay} />;
}
