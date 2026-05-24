import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";
import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "./plotlyCore";
import { useSessionStore } from "../state/sessionStore";
import type { AnalysisSession, DetectedEvent, NumericLogRow, Segment } from "../domain/types";
import type { CircleMarker, Map as LeafletMap } from "leaflet";
import { SeverityBadge } from "./SeverityBadge";

const Plot = createPlotlyComponent(Plotly);
const MAX_MAP_PLOT_POINTS = 7000;

type CoordinatePoint = {
  longitude: number;
  latitude: number;
  timestampSec: number;
  speedKph: number | null;
};

type MapTraceType = "scatter" | "scattergl";

type MapTrace = {
  x: number[];
  y: number[];
  text: string[];
  type: MapTraceType;
  mode: "lines+markers" | "markers";
  name: string;
  line?: { color: string; width: number };
  marker: {
    color: number[] | string;
    colorscale?: string;
    size: number;
    opacity: number;
    colorbar?: { title: { text: string } };
    line: { color: string; width: number };
    symbol?: string;
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

type MapMode = "offline" | "online";

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

function downsampleCoordinatePoints(points: CoordinatePoint[], maxPoints = MAX_MAP_PLOT_POINTS): CoordinatePoint[] {
  if (points.length <= maxPoints || maxPoints < 3) return points;

  const sampledPoints = [points[0]];
  const stride = Math.ceil((points.length - 2) / (maxPoints - 2));

  for (let index = 1; index < points.length - 1; index += stride) {
    sampledPoints.push(points[index]);
  }

  sampledPoints.push(points[points.length - 1]);
  return sampledPoints;
}

function nearestCoordinatePoint(points: CoordinatePoint[], timeSec: number | null): CoordinatePoint | null {
  const targetTimeSec = finiteNumber(timeSec);
  if (targetTimeSec === null || points.length === 0) return null;
  if (targetTimeSec <= points[0].timestampSec) return points[0];
  if (targetTimeSec >= points[points.length - 1].timestampSec) return points[points.length - 1];

  let low = 0;
  let high = points.length - 1;
  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (points[mid].timestampSec < targetTimeSec) low = mid + 1;
    else high = mid;
  }

  const after = points[low];
  const before = points[low - 1];
  return Math.abs(after.timestampSec - targetTimeSec) < Math.abs(targetTimeSec - before.timestampSec) ? after : before;
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

function mapPathTrace(points: CoordinatePoint[], pathTraceType: MapTraceType): MapTrace {
  return {
    x: points.map((point) => point.longitude),
    y: points.map((point) => point.latitude),
    text: points.map((point) => `t=${formatSeconds(point.timestampSec)}, speed=${formatSpeed(point.speedKph)}`),
    type: pathTraceType,
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
  };
}

function currentCoordinateTrace(currentPoint: CoordinatePoint): MapTrace {
  return {
    x: [currentPoint.longitude],
    y: [currentPoint.latitude],
    text: [`t=${formatSeconds(currentPoint.timestampSec)}, speed=${formatSpeed(currentPoint.speedKph)}`],
    type: "scatter",
    mode: "markers",
    name: "Current playback position",
    marker: {
      color: "#be123c",
      size: 15,
      opacity: 0.96,
      symbol: "diamond",
      line: { color: "#ffffff", width: 2 }
    },
    hovertemplate: "Current<br>Lon %{x:.6f}<br>Lat %{y:.6f}<br>%{text}<extra></extra>"
  };
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

function OnlineLeafletMap({ points, currentPoint }: { points: CoordinatePoint[]; currentPoint: CoordinatePoint | null }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const currentMarkerRef = useRef<CircleMarker | null>(null);
  const currentPointRef = useRef<CoordinatePoint | null>(currentPoint);
  const leafletRef = useRef<Awaited<typeof import("leaflet")> | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);

  function drawCurrentMarker(point: CoordinatePoint | null) {
    const L = leafletRef.current;
    const map = mapRef.current;

    currentMarkerRef.current?.remove();
    currentMarkerRef.current = null;
    if (!L || !map || !point) return;

    currentMarkerRef.current = L.circleMarker([point.latitude, point.longitude], {
      radius: 8,
      color: "#be123c",
      fillColor: "#be123c",
      fillOpacity: 0.9,
      weight: 2
    }).addTo(map);
  }

  useEffect(() => {
    let disposed = false;
    let map: LeafletMap | null = null;

    async function mountMap() {
      if (!containerRef.current || points.length === 0) return;

      try {
        const L = await import("leaflet");
        if (disposed || !containerRef.current) return;

        leafletRef.current = L;
        map = L.map(containerRef.current, {
          zoomControl: true,
          scrollWheelZoom: true
        });
        mapRef.current = map;

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        const latLngs = points.map((point) => [point.latitude, point.longitude] as [number, number]);
        L.polyline(latLngs, { color: "#0f766e", weight: 4, opacity: 0.82 }).addTo(map);
        L.circleMarker(latLngs[0], { radius: 6, color: "#0f766e", fillColor: "#ffffff", fillOpacity: 1, weight: 3 }).addTo(map);
        L.circleMarker(latLngs.at(-1) ?? latLngs[0], {
          radius: 6,
          color: "#b45309",
          fillColor: "#ffffff",
          fillOpacity: 1,
          weight: 3
        }).addTo(map);
        drawCurrentMarker(currentPointRef.current);

        const bounds = L.latLngBounds(latLngs);
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [28, 28], maxZoom: 18 });
        } else {
          map.setView(latLngs[0], 15);
        }
      } catch {
        if (!disposed) setMapError("Online map could not be initialized.");
      }
    }

    void mountMap();

    return () => {
      disposed = true;
      currentMarkerRef.current?.remove();
      currentMarkerRef.current = null;
      mapRef.current = null;
      leafletRef.current = null;
      map?.remove();
    };
  }, [points]);

  useEffect(() => {
    currentPointRef.current = currentPoint;
    drawCurrentMarker(currentPoint);
  }, [currentPoint]);

  return (
    <div className="online-map-shell">
      <div ref={containerRef} className="leaflet-map" role="img" aria-label="Online GPS map with OpenStreetMap tiles" />
      {mapError ? (
        <p className="form-error" role="alert">
          {mapError}
        </p>
      ) : (
        <p className="map-attribution-note">OpenStreetMap tiles load only while internet access is available.</p>
      )}
    </div>
  );
}

function LoadedMapLapView({ session }: { session: AnalysisSession }) {
  const addManualSegment = useSessionStore((state) => state.addManualSegment);
  const currentTimeSec = useSessionStore((state) => state.currentTimeSec);
  const [mapMode, setMapMode] = useState<MapMode>("offline");
  const [name, setName] = useState("");
  const [startSec, setStartSec] = useState("");
  const [endSec, setEndSec] = useState("");
  const [error, setError] = useState<string | null>(null);

  const points = useMemo(() => coordinatePoints(session.log.rows), [session.log.rows]);
  const plottedPoints = useMemo(() => downsampleCoordinatePoints(points), [points]);
  const currentPoint = useMemo(() => nearestCoordinatePoint(points, currentTimeSec), [currentTimeSec, points]);
  const pathTraceType: MapTraceType = plottedPoints.length < points.length ? "scattergl" : "scatter";
  const pathTrace = useMemo(() => mapPathTrace(plottedPoints, pathTraceType), [pathTraceType, plottedPoints]);
  const traces = useMemo(() => (currentPoint ? [pathTrace, currentCoordinateTrace(currentPoint)] : [pathTrace]), [currentPoint, pathTrace]);
  const layout = useMemo(() => mapLayout(), []);
  const plottedMaxSpeed = useMemo(() => maxSpeed(plottedPoints), [plottedPoints]);
  const onlineMapEnabled = mapMode === "online";

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
        <div>
          <strong>{onlineMapEnabled ? "Online map tiles" : "Offline coordinate fallback"}</strong>
          <span>
            {onlineMapEnabled
              ? "OpenStreetMap tiles are enabled. The GPS path still comes from the loaded CSV."
              : "No online map tiles are loaded. This view plots raw Longitude and Latitude pairs from the log."}
          </span>
        </div>
        <button
          type="button"
          className="map-mode-toggle"
          aria-pressed={onlineMapEnabled}
          onClick={() => setMapMode((currentMode) => (currentMode === "online" ? "offline" : "online"))}
        >
          {onlineMapEnabled ? "Use offline plot" : "Use online map"}
        </button>
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
        <section className="map-lap-panel" aria-label={onlineMapEnabled ? "Online GPS path" : "Offline GPS path"}>
          <div className="map-lap-panel-heading">
            <h2>GPS path</h2>
            <p>{onlineMapEnabled ? "Online map tiles with CSV coordinates." : "Finite coordinate pairs only."}</p>
          </div>
          {points.length === 0 ? (
            <div className="inline-empty">
              <h3>No finite coordinate pairs</h3>
              <p>This offline fallback needs finite Longitude and Latitude samples.</p>
            </div>
          ) : onlineMapEnabled ? (
            <OnlineLeafletMap points={plottedPoints} currentPoint={currentPoint} />
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

        <section className="map-lap-panel map-lap-segments-panel" aria-label="Segments">
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

          <div className="segment-list-scroll" aria-label="Scrollable segment list">
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
          </div>
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
