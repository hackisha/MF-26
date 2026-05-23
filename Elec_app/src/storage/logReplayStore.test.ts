import { beforeEach, describe, expect, test } from "vitest";
import { createDefaultLogReplaySettings } from "../domain/logSettingsDefaults";
import { clearStoredLogReplayState, loadStoredLogReplayState, saveStoredLogReplayState } from "./logReplayStore";

describe("logReplayStore", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test("persists the last CSV, settings, and UI state across tab remounts", async () => {
    const settings = createDefaultLogReplaySettings();
    await saveStoredLogReplayState({
      csv: { fileName: "run.csv", text: "Timestamp,RPM\n0,1000\n0.1,2000" },
      settings,
      ui: { activeTab: "overlay", overlayKeys: ["RPM"], cardKeys: ["RPM"] },
    });

    const stored = await loadStoredLogReplayState();

    expect(stored?.csv.fileName).toBe("run.csv");
    expect(stored?.settings.gps.latitudeKey).toBe("Latitude");
    expect(stored?.ui.activeTab).toBe("overlay");
  });

  test("clears persisted replay state", async () => {
    await saveStoredLogReplayState({
      csv: { fileName: "run.csv", text: "Timestamp,RPM\n0,1000" },
      settings: createDefaultLogReplaySettings(),
      ui: { activeTab: "dashboard", overlayKeys: [], cardKeys: [] },
    });

    await clearStoredLogReplayState();

    expect(await loadStoredLogReplayState()).toBeNull();
  });

  test("drops malformed persisted state instead of returning unsafe shapes", async () => {
    localStorage.setItem("muzil-tools:log-replay-state:v1", JSON.stringify({ csv: { fileName: "bad.csv" } }));

    expect(await loadStoredLogReplayState()).toBeNull();
  });
});
