import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import type { AnalysisSession } from "../../src/domain/types";
import { useSessionStore } from "../../src/state/sessionStore";
import { TimeSeriesView } from "../../src/ui/TimeSeriesView";

const plotCalls: Array<ComponentProps<"div"> & { data?: unknown; layout?: unknown; config?: unknown }> = [];

vi.mock("react-plotly.js", () => ({
  default: (props: ComponentProps<"div"> & { data?: unknown; layout?: unknown; config?: unknown }) => {
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

function resetStore(session: AnalysisSession | null = null) {
  useSessionStore.setState({
    profiles: defaultProfiles,
    selectedProfileId: defaultProfiles[0].id,
    sourceCsv: null,
    session,
    currentTimeSec: null,
    selectedEventId: null,
    selectedOverlay: defaultProfiles[0].overlays[0] ?? null
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

  it("normalizes normalized overlays to a 0-100 scale", () => {
    render(<TimeSeriesView />);

    fireEvent.change(screen.getByLabelText("Overlay preset"), { target: { value: "gg-inputs" } });

    const traces = plotCalls.at(-1)?.data as Array<{ name: string; y: Array<number | null> }>;
    expect(traces.map((trace) => trace.name)).toEqual(["Throttle Position", "Corrected Accel Y"]);
    expect(traces[0].y).toEqual([0, 50, 100]);
    expect(traces[1].y).toEqual([0, 50, 100]);
  });
});
