import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import type { AnalysisSession, VehicleProfile } from "../../src/domain/types";
import { useSessionStore } from "../../src/state/sessionStore";
import { BehaviorView } from "../../src/ui/BehaviorView";

const plotCalls: Array<ComponentProps<"div"> & { data?: unknown; layout?: unknown; config?: unknown }> = [];

vi.mock("plotly.js-dist-min", () => ({ default: {} }));

vi.mock("react-plotly.js/factory", () => ({
  default: () => (props: ComponentProps<"div"> & { data?: unknown; layout?: unknown; config?: unknown }) => {
    plotCalls.push(props);
    return <div data-testid="behavior-plot" />;
  }
}));

vi.mock("@react-three/fiber", () => ({
  Canvas: () => <div data-testid="behavior-canvas" />
}));

function createSession(): AnalysisSession {
  return {
    filePath: "C:\\logs\\behavior.csv",
    profileId: defaultProfiles[0].id,
    log: {
      fileName: "behavior.csv",
      profileId: defaultProfiles[0].id,
      profileRevision: defaultProfiles[0].revision,
      rawHeaders: ["Timestamp", "ax_g", "ay_g", "gx_dps", "gy_dps", "gz_dps"],
      rows: [
        {
          index: 0,
          timestampSec: 0,
          values: { ax_corrected_g: 0.1, ay_corrected_g: -0.8, ax_g: 8, ay_g: 9, gx_dps: 5, gy_dps: -3, gz_dps: 12 }
        },
        {
          index: 1,
          timestampSec: 1,
          values: { ax_corrected_g: Number.NaN, ay_corrected_g: 0.2, ax_g: 16, ay_g: 18, gx_dps: null, gy_dps: null, gz_dps: null }
        },
        {
          index: 2,
          timestampSec: 2,
          values: { ax_corrected_g: -0.4, ay_corrected_g: Number.POSITIVE_INFINITY, ax_g: 24, ay_g: 27, gx_dps: 8, gy_dps: -6, gz_dps: -20 }
        },
        {
          index: 3,
          timestampSec: 3,
          values: { ax_corrected_g: 0.7, ay_corrected_g: 1.1, ax_g: 32, ay_g: 36, gx_dps: 10, gy_dps: -9, gz_dps: 30 }
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

describe("BehaviorView", () => {
  beforeEach(() => {
    plotCalls.length = 0;
    resetStore(createSession());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a no-session empty state", () => {
    resetStore(null);

    render(<BehaviorView />);

    expect(screen.getByText("No log loaded")).not.toBeNull();
    expect(screen.getByText("Open a CSV log to analyze vehicle behavior.")).not.toBeNull();
  });

  it("uses corrected acceleration channels, filters non-finite G-G points, and draws a limit circle", () => {
    render(<BehaviorView />);

    const traces = plotCalls.at(-1)?.data as Array<{ x: number[]; y: number[]; mode: string; type: string; name: string }>;
    const layout = plotCalls.at(-1)?.layout as {
      showlegend: boolean;
      xaxis: { title: { text: string }; zeroline: boolean; range: [number, number] };
      yaxis: { title: { text: string }; scaleanchor: string; zeroline: boolean; range: [number, number] };
    };
    const sampleTrace = traces.find((trace) => trace.name === "Corrected G-G samples");
    const limitTrace = traces.find((trace) => trace.name === "2.0 g limit circle");

    expect(screen.getByTestId("behavior-plot")).not.toBeNull();
    expect(sampleTrace?.x).toEqual([0.1, 0.7]);
    expect(sampleTrace?.y).toEqual([-0.8, 1.1]);
    expect(sampleTrace?.mode).toBe("markers");
    expect(sampleTrace?.type).toBe("scatter");
    expect(limitTrace?.mode).toBe("lines");
    expect(Math.max(...(limitTrace?.x ?? []))).toBeCloseTo(2);
    expect(Math.min(...(limitTrace?.x ?? []))).toBeCloseTo(-2);
    expect(Math.max(...(limitTrace?.y ?? []))).toBeCloseTo(2);
    expect(Math.min(...(limitTrace?.y ?? []))).toBeCloseTo(-2);
    expect(layout.showlegend).toBe(true);
    expect(layout.xaxis.title.text).toBe("Longitudinal acceleration (g)");
    expect(layout.yaxis.title.text).toBe("Lateral acceleration (g)");
    expect(layout.yaxis.scaleanchor).toBe("x");
    expect(layout.xaxis.zeroline).toBe(true);
    expect(layout.yaxis.zeroline).toBe(true);
    expect(layout.xaxis.range[0]).toBeLessThanOrEqual(-2);
    expect(layout.yaxis.range[1]).toBeGreaterThanOrEqual(2);
    const stats = screen.getByLabelText("Behavior statistics");
    expect(stats.textContent).toContain("samples used");
    expect(stats.textContent).toContain("2");
    expect(screen.getByText("1.10 g")).not.toBeNull();
    expect(screen.getByText("0.70 g")).not.toBeNull();
  });

  it("shows a no-usable-G empty state when corrected acceleration is unavailable", () => {
    const session = createSession();
    session.log.rows = session.log.rows.map((row) => ({
      ...row,
      values: { gx_dps: row.values.gx_dps, gy_dps: row.values.gy_dps, gz_dps: row.values.gz_dps }
    }));
    resetStore(session);

    render(<BehaviorView />);

    expect(screen.getByText("No usable corrected acceleration")).not.toBeNull();
    expect(screen.getByText("This view needs finite ax_corrected_g and ay_corrected_g samples for the G-G diagram.")).not.toBeNull();
    expect(screen.queryByTestId("behavior-plot")).toBeNull();
    expect(screen.getByTestId("behavior-canvas")).not.toBeNull();
  });

  it("explains when gyro values are unavailable", () => {
    const session = createSession();
    session.log.rows = session.log.rows.map((row) => ({
      ...row,
      values: { ...row.values, gx_dps: null, gy_dps: Number.NaN, gz_dps: Number.POSITIVE_INFINITY }
    }));
    resetStore(session);

    render(<BehaviorView />);

    expect(screen.getByText("Gyro data unavailable")).not.toBeNull();
    expect(
      screen.getByText("This CSV has no usable gx_dps, gy_dps, and gz_dps values, so the roll/pitch/yaw cue is hidden.")
    ).not.toBeNull();
    expect(screen.getByText("latest yaw rate")).not.toBeNull();
    expect(screen.getByText("n/a")).not.toBeNull();
  });

  it("uses the latest finite yaw rate even when roll and pitch are unavailable", () => {
    const session = createSession();
    session.log.rows = session.log.rows.map((row, index) => ({
      ...row,
      values: {
        ...row.values,
        gx_dps: null,
        gy_dps: Number.NaN,
        gz_dps: index === session.log.rows.length - 1 ? 44 : row.values.gz_dps
      }
    }));
    resetStore(session);

    render(<BehaviorView />);

    expect(screen.getByText("44.0 deg/s")).not.toBeNull();
    expect(screen.getByText("Gyro data unavailable")).not.toBeNull();
  });
});
