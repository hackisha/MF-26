import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import type { AnalysisSession, VehicleProfile } from "../../src/domain/types";
import { useSessionStore } from "../../src/state/sessionStore";
import { ReportView } from "../../src/ui/ReportView";
import { SettingsView } from "../../src/ui/SettingsView";

const csv = [
  "Timestamp,RPM,EngineSpeed_RPM,Batt_V,OilPressure_bar,EOT_IN,ax_g,ay_g",
  "0,1000,900,12.4,3.2,80,1,2",
  "1,6200,6100,11.6,2.1,95,2,4"
].join("\n");

function cloneProfile(profile: VehicleProfile): VehicleProfile {
  return structuredClone(profile) as VehicleProfile;
}

function createSession(profile = defaultProfiles[0]): AnalysisSession {
  return {
    filePath: "C:\\logs\\sample.csv",
    profileId: profile.id,
    log: {
      fileName: "sample.csv",
      profileId: profile.id,
      profileRevision: profile.revision,
      rawHeaders: ["Timestamp", "RPM", "Batt_V", "OilPressure_bar", "EOT_IN", "ax_g", "ay_g"],
      rows: [
        {
          index: 0,
          timestampSec: 0,
          values: { RPM: 1000, Batt_V: 12.4, OilPressure_bar: 3.2, EOT_IN: 80, ax_corrected_g: 0.125, ay_corrected_g: 0.25 }
        },
        {
          index: 1,
          timestampSec: 1,
          values: { RPM: 6200, Batt_V: 11.6, OilPressure_bar: 2.1, EOT_IN: 95, ax_corrected_g: 0.25, ay_corrected_g: 0.5 }
        }
      ]
    },
    diagnostics: [],
    events: [
      {
        id: "event-1",
        ruleId: "low-battery-voltage",
        name: "Low Battery Voltage",
        severity: "warning",
        startSec: 1,
        endSec: 1,
        description: "Battery voltage is below the expected operating range."
      }
    ],
    segments: []
  };
}

function installDesktopApi(overrides: Partial<NonNullable<Window["mfLogAnalyzer"]>> = {}) {
  window.mfLogAnalyzer = {
    openCsv: vi.fn(async () => null),
    saveHtmlReport: vi.fn(async () => "C:\\reports\\sample.html"),
    popout: vi.fn(async () => true),
    ...overrides
  };
}

function resetStore(session: AnalysisSession | null = createSession(), profiles: VehicleProfile[] = defaultProfiles) {
  useSessionStore.setState({
    profiles,
    selectedProfileId: profiles[0].id,
    sourceCsv: session ? { filePath: "C:\\logs\\sample.csv", text: csv } : null,
    session,
    currentTimeSec: session?.log.rows[0]?.timestampSec ?? null,
    selectedEventId: null,
    selectedOverlay: profiles[0].overlays[0] ?? null
  });
}

describe("ReportView", () => {
  beforeEach(() => {
    installDesktopApi();
    resetStore();
  });

  afterEach(() => {
    delete window.mfLogAnalyzer;
    vi.restoreAllMocks();
  });

  it("shows a no-session empty state", () => {
    resetStore(null);

    render(<ReportView />);

    expect(screen.getByText("No log loaded")).not.toBeNull();
    expect(screen.getByText("Open a CSV log to preview and save an HTML report.")).not.toBeNull();
  });

  it("renders report HTML in a preview iframe and saves it through the desktop API", async () => {
    render(<ReportView />);

    const preview = screen.getByTitle("HTML report preview") as HTMLIFrameElement;
    expect(preview.srcdoc).toContain("MF Log Analyzer Report");
    expect(preview.srcdoc).toContain("sample.csv");

    fireEvent.click(screen.getByRole("button", { name: "Save HTML" }));

    const saveHtmlReport = vi.mocked(window.mfLogAnalyzer!.saveHtmlReport);
    await waitFor(() => {
      expect(saveHtmlReport).toHaveBeenCalledTimes(1);
    });
    const savedHtml = saveHtmlReport.mock.calls[0][0];
    expect(savedHtml).toContain("MF Log Analyzer Report");
    expect(screen.getByText("Saved report to C:\\reports\\sample.html.")).not.toBeNull();
  });
});

describe("SettingsView", () => {
  beforeEach(() => {
    installDesktopApi();
    resetStore();
  });

  afterEach(() => {
    delete window.mfLogAnalyzer;
    vi.restoreAllMocks();
  });

  it("shows profile metadata and channel mapping rows", () => {
    render(<SettingsView />);

    expect(screen.getByText("2025 Vehicle")).not.toBeNull();
    expect(screen.getByText("2025-vehicle")).not.toBeNull();
    expect(screen.getByText("Engine RPM")).not.toBeNull();
    expect(screen.getByText("RPM")).not.toBeNull();
    expect(screen.getByText("RPM, EngineSpeed_RPM")).not.toBeNull();
    expect(screen.getAllByText("identity").length).toBeGreaterThan(0);
    expect(screen.getAllByText("scale 0.125, offset 0").length).toBeGreaterThan(0);
  });

  it("rejects invalid JSON with a visible message", () => {
    render(<SettingsView />);

    fireEvent.change(screen.getByLabelText("Active profile JSON"), { target: { value: "{ invalid" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply JSON" }));

    expect(screen.getByText(/Invalid JSON:/)).not.toBeNull();
  });

  it("requires edited JSON to keep the active profile id", () => {
    const editedProfile = cloneProfile(defaultProfiles[0]);
    editedProfile.id = "other-profile";
    render(<SettingsView />);

    fireEvent.change(screen.getByLabelText("Active profile JSON"), { target: { value: JSON.stringify(editedProfile, null, 2) } });
    fireEvent.click(screen.getByRole("button", { name: "Apply JSON" }));

    expect(screen.getByText("Profile id must remain 2025-vehicle.")).not.toBeNull();
  });

  it("applies valid JSON with a new revision and reports that the loaded session was rebuilt", () => {
    const editedProfile = cloneProfile(defaultProfiles[0]);
    editedProfile.channels.RPM = {
      ...editedProfile.channels.RPM,
      sourceColumns: ["EngineSpeed_RPM"],
      calibration: { type: "scaleOffset", scale: 2, offset: 1 }
    };
    render(<SettingsView />);

    fireEvent.change(screen.getByLabelText("Active profile JSON"), { target: { value: JSON.stringify(editedProfile, null, 2) } });
    fireEvent.click(screen.getByRole("button", { name: "Apply JSON" }));

    const state = useSessionStore.getState();
    expect(state.profiles[0].revision).not.toBe(defaultProfiles[0].revision);
    expect(state.session?.log.profileRevision).toBe(state.profiles[0].revision);
    expect(state.session?.log.rows[0].values.RPM).toBe(1801);
    expect(screen.getByText("Profile applied and loaded session rebuilt from source CSV.")).not.toBeNull();
  });
});
