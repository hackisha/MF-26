import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import type { AnalysisSession } from "../../src/domain/types";
import { workspaceStorageKey, type WorkspacePanel, type WorkspacePanelView } from "../../src/domain/workspacePresets";
import { useSessionStore } from "../../src/state/sessionStore";
import { WorkspaceView } from "../../src/ui/WorkspaceView";

function renderWorkspace() {
  return render(
    <WorkspaceView
      renderPanel={(view: WorkspacePanelView) => <div data-testid={`workspace-panel-content-${view}`}>{view}</div>}
    />
  );
}

function panelByTitle(title: string): HTMLElement {
  return screen.getByLabelText(`Workspace panel: ${title}`);
}

function savedPresets(): Array<{ id: string; panels: WorkspacePanel[] }> {
  return JSON.parse(window.localStorage.getItem(workspaceStorageKey) ?? "[]") as Array<{
    id: string;
    panels: WorkspacePanel[];
  }>;
}

function createSession(): AnalysisSession {
  return {
    filePath: "C:\\logs\\workspace.csv",
    profileId: defaultProfiles[0].id,
    log: {
      fileName: "workspace.csv",
      profileId: defaultProfiles[0].id,
      profileRevision: defaultProfiles[0].revision,
      rawHeaders: ["Timestamp", "RPM"],
      rows: [
        { index: 0, timestampSec: 0, values: { RPM: 1000 } },
        { index: 1, timestampSec: 1, values: { RPM: 2400 } },
        { index: 2, timestampSec: 2, values: { RPM: 5200 } }
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

describe("WorkspaceView", () => {
  beforeEach(() => {
    window.localStorage.clear();
    resetStore();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("renders the default cooling workspace with multiple analysis panels", () => {
    renderWorkspace();

    expect(screen.getByRole("heading", { name: "Workspace" })).not.toBeNull();
    expect((screen.getByLabelText("Workspace preset") as HTMLSelectElement).value).toBe("cooling-review");
    expect(panelByTitle("Time-Series Graph")).not.toBeNull();
    expect(panelByTitle("Map / Lap")).not.toBeNull();
    expect(screen.getByRole("heading", { name: "Shared CSV Playback" })).not.toBeNull();
    expect(screen.getByTestId("workspace-panel-content-time-series")).not.toBeNull();
    expect(screen.getByTestId("workspace-panel-content-map-lap")).not.toBeNull();
  });

  it("uses the workspace playback rail to control the shared time cursor", () => {
    renderWorkspace();

    const rail = screen.getByLabelText("Workspace playback controls");
    fireEvent.change(within(rail).getByLabelText("Playback timeline"), { target: { value: "1.6" } });

    expect(useSessionStore.getState().currentTimeSec).toBe(1.6);
    expect(within(rail).getByText("3 / 3")).not.toBeNull();
  });

  it("switches between workspace presets", () => {
    renderWorkspace();

    fireEvent.change(screen.getByLabelText("Workspace preset"), { target: { value: "vehicle-behavior" } });

    expect(panelByTitle("Vehicle Behavior")).not.toBeNull();
    expect(screen.getByTestId("workspace-panel-content-behavior")).not.toBeNull();
    expect(screen.queryByLabelText("Workspace panel: Time-Series Graph")).toBeNull();
  });

  it("adds and removes panels from the active workspace", () => {
    renderWorkspace();

    fireEvent.change(screen.getByLabelText("Panel type"), { target: { value: "diagnostics" } });
    fireEvent.click(screen.getByRole("button", { name: "Add panel" }));

    expect(panelByTitle("Log Diagnostics")).not.toBeNull();
    expect(screen.getByTestId("workspace-panel-content-diagnostics")).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Close Log Diagnostics panel" }));

    expect(screen.queryByLabelText("Workspace panel: Log Diagnostics")).toBeNull();
  });

  it("moves and resizes panels on the workspace grid", () => {
    renderWorkspace();

    const graphPanel = panelByTitle("Time-Series Graph");
    expect(graphPanel.dataset.gridX).toBe("0");
    expect(graphPanel.dataset.gridWidth).toBe("12");

    const titleBar = within(graphPanel).getByLabelText("Time-Series Graph panel controls");
    fireEvent.click(within(titleBar).getByRole("button", { name: "Shrink Time-Series Graph width" }));
    fireEvent.click(within(titleBar).getByRole("button", { name: "Move Time-Series Graph right" }));

    expect(panelByTitle("Time-Series Graph").dataset.gridX).toBe("1");
    expect(panelByTitle("Time-Series Graph").dataset.gridWidth).toBe("11");
  });

  it("saves the adjusted workspace preset to localStorage", () => {
    const { unmount } = renderWorkspace();

    fireEvent.click(screen.getByRole("button", { name: "Shrink Time-Series Graph width" }));
    fireEvent.click(screen.getByRole("button", { name: "Move Time-Series Graph right" }));
    fireEvent.click(screen.getByRole("button", { name: "Save layout" }));

    expect(savedPresets().find((preset) => preset.id === "cooling-review")?.panels[0].x).toBe(1);

    unmount();
    renderWorkspace();

    expect(panelByTitle("Time-Series Graph").dataset.gridX).toBe("1");
  });

  it("saves the current panel set as a new named preset", () => {
    renderWorkspace();

    fireEvent.change(screen.getByLabelText("Panel type"), { target: { value: "diagnostics" } });
    fireEvent.click(screen.getByRole("button", { name: "Add panel" }));
    fireEvent.change(screen.getByLabelText("Preset name"), { target: { value: "Race Review" } });
    fireEvent.click(screen.getByRole("button", { name: "Save as preset" }));

    expect((screen.getByLabelText("Workspace preset") as HTMLSelectElement).value).toBe("race-review");
    expect(screen.getByRole("option", { name: "Race Review" })).not.toBeNull();
    expect(savedPresets().find((preset) => preset.id === "race-review")?.panels.map((panel) => panel.view)).toContain(
      "diagnostics"
    );
  });

  it("resets the active preset to the default layout", () => {
    renderWorkspace();

    fireEvent.click(screen.getByRole("button", { name: "Move Time-Series Graph right" }));
    fireEvent.click(screen.getByRole("button", { name: "Save layout" }));
    fireEvent.click(screen.getByRole("button", { name: "Reset preset" }));

    expect(panelByTitle("Time-Series Graph").dataset.gridX).toBe("0");
  });
});
