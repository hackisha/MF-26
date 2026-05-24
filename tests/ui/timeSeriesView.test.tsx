import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import type { AnalysisSession, VehicleProfile } from "../../src/domain/types";
import { useSessionStore } from "../../src/state/sessionStore";
import { TimeSeriesView } from "../../src/ui/TimeSeriesView";

const plotCalls: Array<ComponentProps<"div"> & { data?: unknown; layout?: unknown; config?: unknown }> = [];

vi.mock("plotly.js-dist-min", () => ({ default: {} }));

vi.mock("react-plotly.js/factory", () => ({
  default: () => (props: ComponentProps<"div"> & { data?: unknown; layout?: unknown; config?: unknown }) => {
    plotCalls.push(props);
    return <div data-testid="plotly-graph" />;
  }
}));

function createSession(): AnalysisSession {
  return {
    filePath: "C:\\logs\\sample.csv",
    profileId: defaultProfiles[0].id,
    log: {
      fileName: "sample.csv",
      profileId: defaultProfiles[0].id,
      profileRevision: defaultProfiles[0].revision,
      rawHeaders: ["Timestamp", "EOT_IN", "EOT_OUT", "CLT_C", "TPS_percent", "ay_g"],
      rows: [
        { index: 0, timestampSec: 0, values: { EOT_IN: 80, EOT_OUT: 75, CLT_C: 70, TPS_percent: 0, ay_corrected_g: -1 } },
        { index: 1, timestampSec: 1, values: { EOT_IN: 90, EOT_OUT: 85, CLT_C: Number.NaN, TPS_percent: 50, ay_corrected_g: 0 } },
        {
          index: 2,
          timestampSec: 2,
          values: { EOT_IN: 100, EOT_OUT: Number.POSITIVE_INFINITY, CLT_C: 90, TPS_percent: 100, ay_corrected_g: 1 }
        }
      ]
    },
    diagnostics: [],
    events: [],
    segments: []
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

describe("TimeSeriesView", () => {
  beforeEach(() => {
    plotCalls.length = 0;
    resetStore(createSession());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders selected overlay channels as Plotly traces and filters non-finite values", () => {
    render(<TimeSeriesView />);

    expect((screen.getByLabelText("Overlay preset") as HTMLSelectElement).value).toBe("cooling");
    expect(screen.getByTestId("plotly-graph")).not.toBeNull();

    const traces = plotCalls.at(-1)?.data as Array<{ name: string; x: number[]; y: Array<number | null>; yaxis?: string }>;
    expect(traces.map((trace) => trace.name)).toEqual(["Engine Oil Temp In", "Engine Oil Temp Out", "Coolant Temperature"]);
    expect(traces[0].x).toEqual([0, 1, 2]);
    expect(traces[1].y).toEqual([75, 85, null]);
    expect(traces[2].y).toEqual([70, null, 90]);
  });

  it("assigns separate y axes and layout definitions for separateAxes overlays", () => {
    render(<TimeSeriesView />);

    const traces = plotCalls.at(-1)?.data as Array<{ yaxis: string }>;
    const layout = plotCalls.at(-1)?.layout as Record<string, { title?: { text: string }; side?: string; overlaying?: string; position?: number }> & {
      xaxis: { domain?: [number, number] };
    };

    expect(traces.map((trace) => trace.yaxis)).toEqual(["y", "y2", "y3"]);
    expect(layout.yaxis.title?.text).toBe("Engine Oil Temp In (degC)");
    expect(layout.yaxis2.title?.text).toBe("Engine Oil Temp Out (degC)");
    expect(layout.yaxis3.title?.text).toBe("Coolant Temperature (degC)");
    expect(layout.yaxis2.overlaying).toBe("y");
    expect(layout.yaxis3.overlaying).toBe("y");
    expect(layout.xaxis.domain).toBeDefined();
    expect(layout.yaxis2.position).toBe(layout.xaxis.domain?.[1]);
    expect(layout.yaxis3.position).toBeLessThan(layout.xaxis.domain?.[0] ?? 0);
  });

  it("normalizes normalized overlays to a 0-100 scale", () => {
    render(<TimeSeriesView />);

    fireEvent.change(screen.getByLabelText("Overlay preset"), { target: { value: "gg-inputs" } });

    const traces = plotCalls.at(-1)?.data as Array<{ name: string; y: Array<number | null> }>;
    expect(traces.map((trace) => trace.name)).toEqual(["Throttle Position", "Corrected Accel Y"]);
    expect(traces[0].y).toEqual([0, 50, 100]);
    expect(traces[1].y).toEqual([0, 50, 100]);
  });

  it("maps constant normalized channels to the middle of the normalized scale", () => {
    const session = createSession();
    session.log.rows = session.log.rows.map((row) => ({ ...row, values: { ...row.values, TPS_percent: 25 } }));
    resetStore(session);

    render(<TimeSeriesView />);

    fireEvent.change(screen.getByLabelText("Overlay preset"), { target: { value: "gg-inputs" } });

    const traces = plotCalls.at(-1)?.data as Array<{ name: string; y: Array<number | null> }>;
    expect(traces.find((trace) => trace.name === "Throttle Position")?.y).toEqual([50, 50, 50]);
  });

  it("shows a dedicated empty state when the active profile has no overlays", () => {
    const profile = { ...defaultProfiles[0], overlays: [] };
    const session = { ...createSession(), profileId: profile.id, log: { ...createSession().log, profileId: profile.id } };
    resetStore(session, [profile]);

    render(<TimeSeriesView />);

    expect(screen.getAllByText("No overlays configured")).toHaveLength(2);
    expect(screen.getByText("This profile does not define time-series overlay presets yet.")).not.toBeNull();
  });

  it("shows no plottable channels when selected overlay channels have no finite values", () => {
    const profile: VehicleProfile = {
      ...defaultProfiles[0],
      overlays: [{ id: "empty-values", name: "Empty Values", channelIds: ["EOT_IN"], mode: "separateAxes" }]
    };
    const session = createSession();
    session.profileId = profile.id;
    session.log.profileId = profile.id;
    session.log.rows = session.log.rows.map((row) => ({ ...row, values: { ...row.values, EOT_IN: null } }));
    resetStore(session, [profile]);

    render(<TimeSeriesView />);

    expect(screen.getByText("No plottable channels")).not.toBeNull();
    expect(screen.getByText("The selected overlay has configured channels, but none contain finite values in this log.")).not.toBeNull();
  });

  it("can move from an empty mounted view to a loaded graph without changing hook order", () => {
    resetStore(null);
    render(<TimeSeriesView />);

    expect(screen.getByText("Open a CSV log to plot configured sensor overlays.")).not.toBeNull();

    act(() => {
      resetStore(createSession());
    });

    expect(screen.getByTestId("plotly-graph")).not.toBeNull();
  });
});
