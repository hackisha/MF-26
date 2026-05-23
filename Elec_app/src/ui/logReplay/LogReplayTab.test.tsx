import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test } from "vitest";
import { clearStoredLogReplayState, saveStoredLogReplayState } from "../../storage/logReplayStore";
import { createDefaultLogReplaySettings } from "../../domain/logSettingsDefaults";
import { LogReplayTab } from "./LogReplayTab";

describe("LogReplayTab", () => {
  beforeEach(async () => {
    localStorage.clear();
    await clearStoredLogReplayState();
  });

  test("starts as a real uploader workspace, not a static preview with sample telemetry", async () => {
    render(<LogReplayTab />);

    expect(await screen.findByRole("heading", { name: "EMU 로그 재생" })).toBeInTheDocument();
    expect(screen.getByLabelText("CSV 로그 파일")).toBeInTheDocument();
    expect(screen.queryByText("test_run_0523.csv")).not.toBeInTheDocument();
    expect(screen.queryByText("MF-26 Replay")).not.toBeInTheDocument();
  });

  test("restores the previous CSV without re-uploading", async () => {
    await saveStoredLogReplayState({
      csv: { fileName: "saved.csv", text: "Timestamp,RPM,VSS_kmh\n0,1000,10\n0.1,2000,20" },
      settings: createDefaultLogReplaySettings(),
      ui: { activeTab: "dashboard", overlayKeys: ["RPM"], cardKeys: ["RPM"] },
    });

    render(<LogReplayTab />);

    expect(await screen.findByText("파일: saved.csv")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "대시보드" })).toHaveClass("active");
  });
});
