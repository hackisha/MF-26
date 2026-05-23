import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { createDefaultLogReplaySettings } from "../../domain/logSettingsDefaults";
import type { LogSession } from "../../domain/logReplayTypes";
import { LogAnalysisOverview } from "./LogAnalysisOverview";

const session: LogSession = {
  id: "session",
  fileName: "run.csv",
  columns: ["Timestamp", "RPM", "VSS_kmh", "Gear", "Batt_V", "Latitude", "Longitude", "ax_g", "ay_g", "adu_x", "adu_y", "adu_z"],
  sensors: [
    { key: "Timestamp", label: "Timestamp", type: "text" },
    { key: "RPM", label: "RPM", type: "number", unit: "rpm" },
    { key: "VSS_kmh", label: "VSS", type: "number", unit: "km/h" },
    { key: "Gear", label: "Gear", type: "state" },
    { key: "Batt_V", label: "Battery", type: "number", unit: "V" },
    { key: "Latitude", label: "Latitude", type: "number" },
    { key: "Longitude", label: "Longitude", type: "number" },
    { key: "ax_g", label: "Accel X", type: "number", unit: "g" },
    { key: "ay_g", label: "Accel Y", type: "number", unit: "g" },
    { key: "adu_x", label: "Roll rate", type: "number", unit: "dps" },
    { key: "adu_y", label: "Pitch rate", type: "number", unit: "dps" },
    { key: "adu_z", label: "Yaw rate", type: "number", unit: "dps" },
  ],
  samples: [
    {
      rowIndex: 0,
      timeMs: 0,
      values: { Timestamp: "0", RPM: 1000, VSS_kmh: 10, Gear: 1, Batt_V: 12.4, Latitude: 35.292, Longitude: 126.574, ax_g: 0.1, ay_g: 0.2, adu_x: 0.01, adu_y: -0.02, adu_z: 0.03 },
    },
    {
      rowIndex: 1,
      timeMs: 1000,
      values: { Timestamp: "1", RPM: 3000, VSS_kmh: 35, Gear: 2, Batt_V: 12.1, Latitude: 35.2922, Longitude: 126.5743, ax_g: 0.4, ay_g: -0.1, adu_x: 0.04, adu_y: -0.03, adu_z: 0.02 },
    },
  ],
  summary: { rowCount: 2, durationMs: 1000, startLabel: "0", endLabel: "1", invalidCounts: {} },
};

function createLongSession(rowCount: number): LogSession {
  const samples = Array.from({ length: rowCount }, (_, index) => ({
    rowIndex: index,
    timeMs: index * 100,
    values: {
      Timestamp: String(index / 10),
      RPM: 3000 + Math.sin(index / 10) * 800,
      VSS_kmh: 35 + Math.cos(index / 8) * 12,
      Gear: Math.min(5, Math.floor(index / 400) + 1),
      Batt_V: 12.4 + Math.sin(index / 40) * 0.1,
      Latitude: 35.292 + index * 0.000001,
      Longitude: 126.574 + Math.sin(index / 60) * 0.0002,
      ax_g: Math.sin(index / 12) * 0.4,
      ay_g: Math.cos(index / 10) * 0.5,
      adu_x: Math.sin(index / 9) * 0.04,
      adu_y: Math.cos(index / 11) * 0.03,
      adu_z: Math.sin(index / 7) * 0.05,
    },
  }));

  return {
    ...session,
    samples,
    summary: { ...session.summary, rowCount, durationMs: samples.at(-1)?.timeMs ?? 0 },
  };
}

const sparseSession: LogSession = {
  id: "sparse",
  fileName: "sparse.csv",
  columns: ["Timestamp", "Latitude", "Longitude"],
  sensors: [
    { key: "Timestamp", label: "Timestamp", type: "text" },
    { key: "Latitude", label: "Latitude", type: "number" },
    { key: "Longitude", label: "Longitude", type: "number" },
  ],
  samples: [
    { rowIndex: 0, timeMs: 0, values: { Timestamp: "0", Latitude: 35.292, Longitude: 126.574 } },
    { rowIndex: 1, timeMs: 1000, values: { Timestamp: "1", Latitude: 35.293, Longitude: 126.575 } },
  ],
  summary: { rowCount: 2, durationMs: 1000, startLabel: "0", endLabel: "1", invalidCounts: {} },
};

describe("LogAnalysisOverview", () => {
  test("renders the dense all-in-one analysis panels with a shared playhead", () => {
    const onSeek = vi.fn();
    render(
      <LogAnalysisOverview
        session={session}
        currentSample={session.samples[1]}
        settings={createDefaultLogReplaySettings(session.sensors)}
        currentTimeMs={600}
        onSeek={onSeek}
      />,
    );

    expect(screen.getByTestId("analysis-overview")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "GPS 궤적" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "G-G 다이어그램" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "가속도" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "RPM / VSS" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Roll rate" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pitch rate" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Yaw rate" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "기어 / 배터리" })).toBeInTheDocument();
    expect(screen.getAllByLabelText("현재 재생 위치")).not.toHaveLength(0);

    fireEvent.keyDown(screen.getByRole("slider", { name: "RPM / VSS 재생 위치" }), { key: "ArrowRight" });
    expect(onSeek).toHaveBeenCalledWith(1000);
  });

  test("limits rendered SVG points for long logs", () => {
    const longSession = createLongSession(3000);
    const { container } = render(
      <LogAnalysisOverview
        session={longSession}
        currentSample={longSession.samples[1500]}
        settings={createDefaultLogReplaySettings(longSession.sensors)}
        currentTimeMs={150000}
        onSeek={vi.fn()}
      />,
    );

    expect(container.querySelectorAll(".analysis-gps-line").length).toBeLessThanOrEqual(799);
    expect(container.querySelectorAll(".analysis-gg-dot").length).toBeLessThanOrEqual(900);
  });

  test("shows empty states instead of fake flat charts when expected sensors are missing", () => {
    render(
      <LogAnalysisOverview
        session={sparseSession}
        currentSample={sparseSession.samples[0]}
        settings={createDefaultLogReplaySettings(sparseSession.sensors)}
        currentTimeMs={0}
        onSeek={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "RPM / VSS" })).toBeInTheDocument();
    expect(screen.getAllByText("표시할 숫자 센서가 없습니다.").length).toBeGreaterThan(0);
    expect(screen.getByText("G-G에 필요한 선형 가속도 데이터가 없습니다.")).toBeInTheDocument();
  });
});
