import { FormEvent, useMemo, useState } from "react";
import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js-dist-min";
import { useSessionStore } from "../state/sessionStore";
import type { AnalysisSession, DetectedEvent, NumericLogRow, Segment } from "../domain/types";
import { SeverityBadge } from "./SeverityBadge";

const Plot = createPlotlyComponent(Plotly);

type CoordinatePoint = {
  longitude: number;
  latitude: number;
  timestampSec: number;
  speedKph: number | null;
};

type MapTrace = {
  x: number[];
  y: number[];
  text: string[];
  type: "scatter";
  mode: "lines+markers";
  name: string;
  line: { color: string; width: number };
  marker: {
    color: number[];
    colorscale: string;
    size: number;
    opacity: number;
    colorbar: { title: { text: string } };
    line: { color: string; width: number };
  };
  hovertemplate: string;
};

type MapLayout = {
  autosize: true;
  margin: { t: number; r: number; b: number; l: number };
  paper_bgcolor: string;
  plot_bgcolor: string;
  hovermode: "closest";
  showlegend: false;
  xaxis: {
    title: { text: string };
    zeroline: false;
    gridcolor: string;
    automargin: true;
  };
  yaxis: {
    title: { text: string };
    zeroline: false;
    gridcolor: string;
    scaleanchor: "x";
    scaleratio: 1;
    automargin: true;
  };
};

function finiteNumber(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function speedForRow(row: NumericLogRow): number | null {
  return finiteNumber(row.values.GPS_Speed_KPH) ?? finiteNumber(row.values.VSS_kmh);
}

function coordinatePoints(rows: NumericLogRow[]): CoordinatePoint[] {
  return rows
    .map((row) => {
      const longitude = finiteNumber(row.values.Longitude);
      const latitude = finiteNumber(row.values.Latitude);
      if (longitude === null || latitude === null) return null;

      return {
        longitude,
        latitude,
        timestampSec: row.timestampSec,
        speedKph: speedForRow(row)
      };
    })
    .filter((point): point is CoordinatePoint => point !== null);
}

function maxSpeed(points: CoordinatePoint[]): number | null {
  const speeds = points.map((point) => point.speedKph).filter((speed): speed is number => speed !== null);
  if (speeds.length === 0) return null;
  return Math.max(...speeds);
}

function formatSeconds(value: number): string {
  return `${value.toFixed(2)}s`;
}

function formatSpeed(value: number | null): string {
  return value === null ? "n/a" : `${value.toFixed(1)} km/h`;
}

function mapTrace(points: CoordinatePoint[]): MapTrace[] {
  return [
    {
      x: points.map((point) => point.longitude),
      y: points.map((point) => point.latitude),
      text: points.map((point) => `t=${formatSeconds(point.timestampSec)}, speed=${formatSpeed(point.speedKph)}`),
      type: "scatter",
      mode: "lines+markers",
      name: "GPS path",
      line: { color: "#64748b", width: 1.5 },
      marker: {
        color: points.map((point) => point.speedKph ?? 0),
        colorscale: "Viridis",
        size: 7,
        opacity: 0.82,
        colorbar: { title: { text: "Speed (km/h)" } },
        line: { color: "#ffffff", width: 0.6 }
      },
      hovertemplate: "Lon %{x:.6f}<br>Lat %{y:.6f}<br>%{text}<extra></extra>"
    }
  ];
}

function mapLayout(): MapLayout {
  return {
    autosize: true,
    margin: { t: 18, r: 26, b: 54, l: 64 },
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    hovermode: "closest",
    showlegend: false,
    xaxis: {
      title: { text: "Longitude" },
      zeroline: false,
      gridcolor: "#e7edf1",
      automargin: true
    },
    yaxis: {
      title: { text: "Latitude" },
      zeroline: false,
      gridcolor: "#e7edf1",
      scaleanchor: "x",
      scaleratio: 1,
      automargin: true
    }
  };
}

function eventForSegment(segment: Segment, events: DetectedEvent[]): DetectedEvent | null {
  if (segment.source !== "event") return null;
  const eventId = segment.id.startsWith("segment-") ? segment.id.slice("segment-".length) : null;
  return events.find((event) => event.id === eventId) ?? events.find((event) => event.name === segment.name) ?? null;
}

function segmentRange(segment: Segment): string {
  return `${formatSeconds(segment.startSec)} - ${formatSeconds(segment.endSec)}`;
}

function LoadedMapLapView({ session }: { session: AnalysisSession }) {
  const addManualSegment = useSessionStore((state) => state.addManualSegment);
  const [name, setName] = useState("");
  const [startSec, setStartSec] = useState("");
  const [endSec, setEndSec] = useState("");
  const [error, setError] = useState<string | null>(null);

  const points = useMemo(() => coordinatePoints(session.log.rows), [session.log.rows]);
  const traces = useMemo(() => mapTrace(points), [points]);
  const layout = useMemo(() => mapLayout(), []);
  const plottedMaxSpeed = useMemo(() => maxSpeed(points), [points]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedName = name.trim();
    const trimmedStartSec = startSec.trim();
    const trimmedEndSec = endSec.trim();
    const parsedStartSec = Number(trimmedStartSec);
    const parsedEndSec = Number(trimmedEndSec);

    if (!trimmedName || !trimmedStartSec || !trimmedEndSec || !Number.isFinite(parsedStartSec) || !Number.isFinite(parsedEndSec)) {
      setError("Enter a segment name and finite start/end seconds.");
      return;
    }

    addManualSegment(trimmedName, parsedStartSec, parsedEndSec);
    setName("");
    setStartSec("");
    setEndSec("");
    setError(null);
  };

  return (
    <section className="map-lap-view" aria-label="Map and lap coordinate fallback">
      <div className="map-lap-note">
        <strong>Offline coordinate fallback</strong>
        <span>No online map tiles are loaded. This view plots raw Longitude and Latitude pairs from the log.</span>
      </div>

      <div className="map-lap-stat-strip" aria-label="Map lap statistics">
        <div className="map-lap-stat">
          <span>coordinate samples</span>
          <strong>{points.length}</strong>
        </div>
        <div className="map-lap-stat">
          <span>max plotted speed</span>
          <strong>{formatSpeed(plottedMaxSpeed)}</strong>
        </div>
        <div className="map-lap-stat">
          <span>segments</span>
          <strong>{session.segments.length}</strong>
        </div>
      </div>

      <div className="map-lap-grid">
        <section className="map-lap-panel" aria-label="Offline GPS path">
          <div className="map-lap-panel-heading">
            <h2>GPS path</h2>
            <p>Finite coordinate pairs only.</p>
          </div>
          {points.length === 0 ? (
            <div className="inline-empty">
              <h3>No finite coordinate pairs</h3>
              <p>This offline fallback needs finite Longitude and Latitude samples.</p>
            </div>
          ) : (
            <Plot
              data={traces}
              layout={layout}
              config={{ displaylogo: false, responsive: true }}
              useResizeHandler
              className="map-lap-plot"
            />
          )}
        </section>

        <section className="map-lap-panel" aria-label="Segments">
          <div className="map-lap-panel-heading">
            <h2>Segments</h2>
            <p>Event-derived and manual windows.</p>
          </div>

          <form className="manual-segment-form" onSubmit={handleSubmit}>
            <label>
              <span>Segment name</span>
              <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Lap 1" />
            </label>
            <div className="manual-segment-time-grid">
              <label>
                <span>Start seconds</span>
                <input
                  type="number"
                  step="0.01"
                  value={startSec}
                  onChange={(event) => setStartSec(event.target.value)}
                  placeholder="0.00"
                />
              </label>
              <label>
                <span>End seconds</span>
                <input
                  type="number"
                  step="0.01"
                  value={endSec}
                  onChange={(event) => setEndSec(event.target.value)}
                  placeholder="12.50"
                />
              </label>
            </div>
            {error && <p className="form-error">{error}</p>}
            <button type="submit">Add segment</button>
          </form>

          {session.segments.length === 0 ? (
            <div className="segment-empty">No segments yet.</div>
          ) : (
            <ul className="segment-list">
              {session.segments.map((segment) => {
                const event = eventForSegment(segment, session.events);
                return (
                  <li key={segment.id}>
                    <div>
                      <strong>{segment.name}</strong>
                      <span>{segmentRange(segment)}</span>
                    </div>
                    {event ? <SeverityBadge severity={event.severity} /> : <span className="manual-badge">manual</span>}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>
    </section>
  );
}

export function MapLapView() {
  const session = useSessionStore((state) => state.session);

  if (!session) {
    return (
      <section className="empty-state">
        <h2>No log loaded</h2>
        <p>Open a CSV log to inspect offline GPS coordinates.</p>
      </section>
    );
  }

  return <LoadedMapLapView session={session} />;
}
