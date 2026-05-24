import { beforeEach, describe, expect, it } from "vitest";
import {
  createWorkspacePanel,
  defaultWorkspacePresets,
  loadWorkspacePresets,
  normalizeWorkspacePreset,
  saveWorkspacePresets,
  workspacePresetIdFromName,
  workspaceStorageKey,
  type WorkspacePreset
} from "../../src/domain/workspacePresets";

describe("workspacePresets", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("provides default multi-panel presets for common log review jobs", () => {
    expect(defaultWorkspacePresets.map((preset) => preset.id)).toEqual([
      "cooling-review",
      "vehicle-behavior",
      "engine-safety"
    ]);
    expect(defaultWorkspacePresets.find((preset) => preset.id === "cooling-review")?.panels.map((panel) => panel.view)).toEqual([
      "time-series",
      "map-lap"
    ]);
    expect(defaultWorkspacePresets.find((preset) => preset.id === "vehicle-behavior")?.panels.map((panel) => panel.view)).toEqual([
      "behavior",
      "map-lap"
    ]);
  });

  it("loads saved presets from localStorage", () => {
    const savedPreset: WorkspacePreset = {
      id: "custom-cooling",
      name: "Custom Cooling",
      panels: [
        {
          id: "custom-graph",
          view: "time-series",
          title: "Graph",
          x: 0,
          y: 0,
          width: 8,
          height: 5
        }
      ]
    };

    window.localStorage.setItem(workspaceStorageKey, JSON.stringify([savedPreset]));

    expect(loadWorkspacePresets()).toEqual([savedPreset]);
  });

  it("falls back to defaults when saved presets are missing or invalid", () => {
    expect(loadWorkspacePresets()).toEqual(defaultWorkspacePresets);

    window.localStorage.setItem(workspaceStorageKey, "{not-json");

    expect(loadWorkspacePresets()).toEqual(defaultWorkspacePresets);
  });

  it("saves presets as JSON", () => {
    const presets = [
      {
        id: "track-review",
        name: "Track Review",
        panels: [createWorkspacePanel("map-lap", [])]
      }
    ];

    saveWorkspacePresets(presets);

    expect(JSON.parse(window.localStorage.getItem(workspaceStorageKey) ?? "null")).toEqual(presets);
  });

  it("normalizes panel geometry to the workspace grid", () => {
    const preset = normalizeWorkspacePreset({
      id: "bad-layout",
      name: "Bad Layout",
      panels: [
        {
          id: "too-large",
          view: "behavior",
          title: "Behavior",
          x: -4,
          y: -2,
          width: 99,
          height: 99
        },
        {
          id: "too-small",
          view: "playback",
          title: "",
          x: 11,
          y: 7,
          width: 1,
          height: 1
        }
      ]
    });

    expect(preset.panels[0]).toMatchObject({ x: 0, y: 0, width: 12, height: 8 });
    expect(preset.panels[1]).toMatchObject({ title: "CSV Playback", x: 8, y: 6, width: 4, height: 2 });
  });

  it("uses safe default geometry when saved panel numbers are missing or invalid", () => {
    const preset = normalizeWorkspacePreset({
      id: "partial-layout",
      name: "Partial Layout",
      panels: [
        {
          id: "partial-panel",
          view: "summary",
          title: "Summary",
          x: Number.NaN,
          y: Number.POSITIVE_INFINITY,
          width: Number.NaN,
          height: Number.NEGATIVE_INFINITY
        }
      ]
    });

    expect(preset.panels[0]).toMatchObject({ x: 0, y: 0, width: 6, height: 4 });
  });

  it("creates a new panel with a unique id and default title", () => {
    const existing = [createWorkspacePanel("behavior", [])];
    const nextPanel = createWorkspacePanel("behavior", existing);

    expect(existing[0].id).toBe("behavior-1");
    expect(nextPanel).toMatchObject({
      id: "behavior-2",
      view: "behavior",
      title: "Vehicle Behavior",
      width: 6,
      height: 4
    });
  });

  it("creates stable unique preset ids from user-facing names", () => {
    expect(workspacePresetIdFromName("Race Review", [])).toBe("race-review");
    expect(workspacePresetIdFromName("  Cooling / Oil  ", [])).toBe("cooling-oil");
    expect(workspacePresetIdFromName("!!!", [])).toBe("workspace");
    expect(workspacePresetIdFromName("Race Review", [{ id: "race-review", name: "Race Review", panels: [] }])).toBe(
      "race-review-2"
    );
  });
});
