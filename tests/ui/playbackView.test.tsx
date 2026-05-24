import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import type { AnalysisSession } from "../../src/domain/types";
import { useSessionStore } from "../../src/state/sessionStore";
import { PlaybackView } from "../../src/ui/PlaybackView";

function createSession(): AnalysisSession {
  return {
    filePath: "C:\\logs\\playback.csv",
    profileId: defaultProfiles[0].id,
    log: {
      fileName: "playback.csv",
      profileId: defaultProfiles[0].id,
      profileRevision: defaultProfiles[0].revision,
      rawHeaders: ["Timestamp", "RPM", "GPS_Speed_KPH", "EOT_IN", "EOT_OUT"],
      rows: [
        { index: 0, timestampSec: 0, values: { RPM: 1000, GPS_Speed_KPH: 0, EOT_IN: 70, EOT_OUT: 65 } },
        { index: 1, timestampSec: 1, values: { RPM: 3200, GPS_Speed_KPH: 24, EOT_IN: 76, EOT_OUT: 70 } },
        { index: 2, timestampSec: 2, values: { RPM: 6400, GPS_Speed_KPH: 51, EOT_IN: 88, EOT_OUT: 81 } }
      ]
    },
    diagnostics: [],
    events: [],
    segments: []
  };
}

function resetStore(session: AnalysisSession | null = createSession()) {
  useSessionStore.setState({
    profiles: defaultProfiles,
    selectedProfileId: defaultProfiles[0].id,
    sourceCsv: null,
    session,
    currentTimeSec: session?.log.rows[0]?.timestampSec ?? null,
    selectedEventId: null,
    selectedOverlay: defaultProfiles[0].overlays[0] ?? null
  });
}

describe("PlaybackView", () => {
  beforeEach(() => {
    resetStore();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("shows a CSV playback empty state before a log is loaded", () => {
    resetStore(null);

    render(<PlaybackView />);

    expect(screen.getByText("Open a CSV log to replay the run.")).not.toBeNull();
  });

  it("renders the active sample and visible channel values", () => {
    useSessionStore.getState().setCurrentTimeSec(1);

    render(<PlaybackView />);

    expect(screen.getByRole("heading", { name: "CSV Playback" })).not.toBeNull();
    expect(screen.getByText("1.00 s")).not.toBeNull();
    expect(screen.getByText("2 / 3")).not.toBeNull();

    const table = screen.getByRole("table", { name: "Current sample values" });
    expect(within(table).getByText("Engine RPM")).not.toBeNull();
    expect(within(table).getByText("3200")).not.toBeNull();
    expect(within(table).getByText("Engine Oil Temp In")).not.toBeNull();
    expect(within(table).getByText("76.00")).not.toBeNull();
  });

  it("seeks and steps through CSV samples by updating the shared time cursor", () => {
    render(<PlaybackView />);

    fireEvent.change(screen.getByLabelText("Playback timeline"), { target: { value: "1.6" } });
    expect(useSessionStore.getState().currentTimeSec).toBe(1.6);
    expect(screen.getByText("3 / 3")).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Previous sample" }));
    expect(useSessionStore.getState().currentTimeSec).toBe(1);

    fireEvent.click(screen.getByRole("button", { name: "Next sample" }));
    expect(useSessionStore.getState().currentTimeSec).toBe(2);
  });

  it("plays the log at the selected speed and stops at the end", () => {
    vi.useFakeTimers();
    render(<PlaybackView />);

    fireEvent.change(screen.getByLabelText("Playback speed"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Play CSV log" }));

    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(useSessionStore.getState().currentTimeSec).toBeCloseTo(1, 2);

    act(() => {
      vi.advanceTimersByTime(600);
    });
    expect(useSessionStore.getState().currentTimeSec).toBe(2);
    expect(screen.getByRole("button", { name: "Play CSV log" })).not.toBeNull();
  });
});
