import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test } from "vitest";
import { createDefaultLogReplaySettings } from "../../domain/logSettingsDefaults";
import { clearStoredLogReplayState, saveStoredLogReplayState } from "../../storage/logReplayStore";
import { LogReplayTab } from "./LogReplayTab";

const csvText = [
  "Timestamp,RPM,VSS_kmh,GPS_Speed_KPH,Gear,Batt_V,Latitude,Longitude,ax_g,ay_g,adu_x,adu_y,adu_z",
  "0,1000,12,11,1,12.4,35.2920,126.5740,0.1,0.2,0.01,-0.02,0.03",
  "0.1,3000,42,40,2,12.1,35.2922,126.5743,0.4,-0.1,0.04,-0.03,0.02",
].join("\n");

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

  test("restores CSV into the all-in-one analysis view and keeps upload controls at the bottom", async () => {
    await saveStoredLogReplayState({
      csv: { fileName: "saved.csv", text: csvText },
      settings: createDefaultLogReplaySettings(),
      ui: { activeTab: "overview", overlayKeys: ["RPM"], cardKeys: ["RPM"] },
    });

    render(<LogReplayTab />);

    expect(await screen.findByText("파일: saved.csv")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "전체 분석" })).toHaveClass("active");
    expect(screen.getByRole("heading", { name: "GPS 궤적" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "RPM / VSS" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Roll rate" })).toBeInTheDocument();

    const overview = screen.getByTestId("analysis-overview");
    const uploader = screen.getByTestId("log-uploader");
    const position = overview.compareDocumentPosition(uploader);
    expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
