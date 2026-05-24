import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import type { AnalysisSession, VehicleProfile } from "../../src/domain/types";
import { useSessionStore } from "../../src/state/sessionStore";
import { MapLapView } from "../../src/ui/MapLapView";

const plotCalls: Array<ComponentProps<"div"> & { data?: unknown; layout?: unknown; config?: unknown }> = [];

vi.mock("plotly.js-dist-min", () => ({ default: {} }));

vi.mock("react-plotly.js/factory", () => ({
  default: () => (props: ComponentProps<"div"> & { data?: unknown; layout?: unknown; config?: unknown }) => {
    plotCalls.push(props);
    return <div data-testid="map-lap-plot" />;
  }
}));

vi.mock("leaflet", () => {
  const addTo = vi.fn(() => ({}));
  const remove = vi.fn();
  const fitBounds = vi.fn();
  const setView = vi.fn();

  return {
    map: vi.fn(() => ({ remove, fitBounds, setView })),
    tileLayer: vi.fn(() => ({ addTo })),
    polyline: vi.fn(() => ({ addTo, getBounds: vi.fn(() => ({})) })),
    circleMarker: vi.fn(() => ({ addTo })),
    latLngBounds: vi.fn(() => ({ isValid: vi.fn(() => true) }))
  };
});

function createSession(): AnalysisSession {
  return {
    filePath: "C:\\logs\\gps.csv",
    profileId: defaultProfiles[0].id,
    log: {
      fileName: "gps.csv",
      profileId: defaultProfiles[0].id,
      profileRevision: defaultProfiles[0].revision,
      rawHeaders: ["Timestamp", "Latitude", "Longitude", "GPS_Speed_KPH", "VSS_kmh"],
      rows: [
        { index: 0, timestampSec: 0, values: { Latitude: 37.1, Longitude: 127.1, GPS_Speed_KPH: 40, VSS_kmh: 35 } },
        { index: 1, timestampSec: 1, values: { Latitude: 37.2, Longitude: 127.2, GPS_Speed_KPH: null, VSS_kmh: 55 } },
        { index: 2, timestampSec: 2, values: { Latitude: 0, Longitude: 0, GPS_Speed_KPH: 90, VSS_kmh: 80 } },
        {
          index: 3,
          timestampSec: 3,
          values: { Latitude: Number.NaN, Longitude: 127.3, GPS_Speed_KPH: 70, VSS_kmh: 65 }
        }
      ]
    },
    diagnostics: [],
    events: [
      {
        id: "high-g-1",
        ruleId: "high-lateral-g",
        name: "High Lateral G",
        severity: "warning",
        startSec: 0.5,
        endSec: 1.5,
        description: "Lateral acceleration stayed high."
      }
    ],
    segments: [
      { id: "segment-high-g-1", name: "High Lateral G", startSec: 0.5, endSec: 1.5, source: "event" },
      { id: "manual-4.00-6.00", name: "Cool-down", startSec: 4, endSec: 6, source: "manual" }
    ]
  };
}

function resetStore(session: AnalysisSession | null = null, profiles: VehicleProfile[] = defaultProfiles) {
  useSessionStore.setState({
    profiles,
    selectedProfileId: profiles[0].id,
    sourceCsv: null,
    session,
    currentTimeSec: null,
    selectedEventId: null,
    selectedOverlay: profiles[0].overlays[0] ?? null
  });
}

describe("MapLapView", () => {
  beforeEach(() => {
    plotCalls.length = 0;
    resetStore(createSession());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a no-session empty state", () => {
    resetStore(null);

    render(<MapLapView />);

    expect(screen.getByText("No log loaded")).not.toBeNull();
    expect(screen.getByText("Open a CSV log to inspect offline GPS coordinates.")).not.toBeNull();
  });

  it("filters unusable coordinates and colors points by GPS speed with VSS fallback", () => {
    render(<MapLapView />);

    const traces = plotCalls.at(-1)?.data as Array<{
      x: number[];
      y: number[];
      text: string[];
      marker: { color: number[]; colorbar: { title: { text: string } } };
      mode: string;
      type: string;
    }>;
    const layout = plotCalls.at(-1)?.layout as { yaxis: { scaleanchor: string; scaleratio: number }; xaxis: { title: { text: string } } };

    expect(screen.getByText("Offline coordinate fallback")).not.toBeNull();
    expect(screen.getByTestId("map-lap-plot")).not.toBeNull();
    expect(traces[0].x).toEqual([127.1, 127.2, 0]);
    expect(traces[0].y).toEqual([37.1, 37.2, 0]);
    expect(traces[0].marker.color).toEqual([40, 55, 90]);
    expect(traces[0].text).toEqual([
      "t=0.00s, speed=40.0 km/h",
      "t=1.00s, speed=55.0 km/h",
      "t=2.00s, speed=90.0 km/h"
    ]);
    expect(traces[0].mode).toBe("lines+markers");
    expect(traces[0].type).toBe("scatter");
    expect(layout.yaxis.scaleanchor).toBe("x");
    expect(layout.yaxis.scaleratio).toBe(1);
    expect(layout.xaxis.title.text).toBe("Longitude");
    expect(screen.getByLabelText("Map lap statistics").textContent).toContain("3");
    expect(screen.getByLabelText("Map lap statistics").textContent).toContain("90.0 km/h");
  });

  it("toggles from the offline plot to an online OpenStreetMap layer", () => {
    render(<MapLapView />);

    const toggle = screen.getByRole("button", { name: "Use online map" });
    expect(toggle.getAttribute("aria-pressed")).toBe("false");
    expect(screen.getByText("Offline coordinate fallback")).not.toBeNull();

    fireEvent.click(toggle);

    expect(toggle.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("Online map tiles")).not.toBeNull();
    expect(screen.getByLabelText("Online GPS map with OpenStreetMap tiles")).not.toBeNull();
    expect(screen.queryByTestId("map-lap-plot")).toBeNull();
  });

  it("shows a no-coordinate empty state when no finite coordinate pairs are available", () => {
    const session = createSession();
    session.log.rows = session.log.rows.map((row) => ({
      ...row,
      values: { ...row.values, Latitude: row.index === 0 ? null : Number.NaN, Longitude: row.index === 0 ? Number.NaN : null }
    }));
    resetStore(session);

    render(<MapLapView />);

    expect(screen.getByText("No finite coordinate pairs")).not.toBeNull();
    expect(screen.getByText("This offline fallback needs finite Longitude and Latitude samples.")).not.toBeNull();
    expect(screen.queryByTestId("map-lap-plot")).toBeNull();
  });

  it("shows event severity and manual segment badges", () => {
    render(<MapLapView />);

    expect(screen.getByLabelText("Scrollable segment list").className).toContain("segment-list-scroll");
    expect(screen.getByText("warning")).not.toBeNull();
    expect(screen.getByText("manual")).not.toBeNull();
    expect(screen.getByText("High Lateral G")).not.toBeNull();
    expect(screen.getByText("Cool-down")).not.toBeNull();
  });

  it("validates manual segment input and adds normalized manual segments", () => {
    render(<MapLapView />);

    fireEvent.click(screen.getByRole("button", { name: "Add segment" }));
    expect(screen.getByText("Enter a segment name and finite start/end seconds.")).not.toBeNull();

    fireEvent.change(screen.getByLabelText("Segment name"), { target: { value: "Launch window" } });
    fireEvent.click(screen.getByRole("button", { name: "Add segment" }));
    expect(screen.getByText("Enter a segment name and finite start/end seconds.")).not.toBeNull();
    expect(useSessionStore.getState().session?.segments.some((segment) => segment.name === "Launch window")).toBe(false);

    fireEvent.change(screen.getByLabelText("Segment name"), { target: { value: "Pit entry" } });
    fireEvent.change(screen.getByLabelText("Start seconds"), { target: { value: "8" } });
    fireEvent.change(screen.getByLabelText("End seconds"), { target: { value: "6" } });
    fireEvent.click(screen.getByRole("button", { name: "Add segment" }));

    expect(screen.queryByText("Enter a segment name and finite start/end seconds.")).toBeNull();
    expect(screen.getByText("Pit entry")).not.toBeNull();

    const added = useSessionStore.getState().session?.segments.at(-1);
    expect(added).toMatchObject({ name: "Pit entry", startSec: 6, endSec: 8, source: "manual" });
  });
});
