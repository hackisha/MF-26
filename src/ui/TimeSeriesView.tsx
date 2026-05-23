// @ts-expect-error react-plotly.js does not ship bundled TypeScript declarations in this project.
import Plot from "react-plotly.js";
import { useSessionStore } from "../state/sessionStore";
import type { NumericLogRow, OverlayPreset, SensorChannel, VehicleProfile } from "../domain/types";
import { ChannelPicker } from "./ChannelPicker";

type PlotPoint = number | null;

type Trace = {
  x: PlotPoint[];
  y: PlotPoint[];
  type: "scatter";
  mode: "lines";
  name: string;
  line: {
    color: string;
    width: number;
  };
  connectgaps: false;
};

type PlottableChannel = {
  channel: SensorChannel;
  values: PlotPoint[];
};

function finiteOrNull(value: number): PlotPoint {
  return Number.isFinite(value) ? value : null;
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

function tracesForOverlay(
  profile: VehicleProfile,
  overlay: OverlayPreset,
  rows: NumericLogRow[]
): Trace[] {
  const xValues = rows.map((row) => finiteOrNull(row.timestampSec));
  return plottableChannels(profile, overlay, rows).map(({ channel, values }) => ({
    x: xValues,
    y: overlay.mode === "normalized" ? normalizeValues(values) : values,
    type: "scatter",
    mode: "lines",
    name: traceName(channel),
    line: {
      color: channel.color,
      width: 2
    },
    connectgaps: false
  }));
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
  const traces = overlay ? tracesForOverlay(profile, overlay, session.log.rows) : [];

  return (
    <section className="time-series-view" aria-label="Time-series graph">
      <div className="view-toolbar">
        <ChannelPicker profile={profile} selectedOverlay={overlay} onOverlayChange={setSelectedOverlay} />
        {overlay && (
          <p className="toolbar-note">
            {overlay.mode === "normalized" ? "Normalized 0-100 scale" : "Single-axis native-unit overlay"}
          </p>
        )}
      </div>

      {traces.length === 0 ? (
        <section className="empty-state">
          <h2>No plottable channels</h2>
          <p>The selected overlay has no configured channels with finite values in this log.</p>
        </section>
      ) : (
        <div className="graph-panel">
          <Plot
            data={traces}
            layout={{
              autosize: true,
              margin: { t: 16, r: 24, b: 48, l: 56 },
              paper_bgcolor: "#ffffff",
              plot_bgcolor: "#ffffff",
              hovermode: "x unified",
              showlegend: true,
              legend: { orientation: "h", x: 0, y: 1.12 },
              xaxis: { title: { text: "Time (s)" }, zeroline: false },
              yaxis: {
                title: { text: overlay?.mode === "normalized" ? "Normalized value" : "Value" },
                zeroline: false
              }
            }}
            config={{ displaylogo: false, responsive: true }}
            useResizeHandler
            className="time-series-plot"
          />
        </div>
      )}
    </section>
  );
}
