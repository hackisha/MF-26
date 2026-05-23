import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const storeMock = vi.hoisted(() => ({
  loadStoredLogReplayState: vi.fn(async () => null),
  saveStoredLogReplayState: vi.fn(async () => {
    throw new Error("storage full");
  }),
  clearStoredLogReplayState: vi.fn(async () => undefined),
}));

vi.mock("./storage/logReplayStore", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./storage/logReplayStore")>();
  return {
    ...actual,
    loadStoredLogReplayState: storeMock.loadStoredLogReplayState,
    saveStoredLogReplayState: storeMock.saveStoredLogReplayState,
    clearStoredLogReplayState: storeMock.clearStoredLogReplayState,
  };
});

import App from "./App";

const csvText = [
  "Timestamp,RPM,VSS_kmh,GPS_Speed_KPH,Gear,Batt_V,Latitude,Longitude,ax_g,ay_g,adu_x,adu_y,adu_z",
  "0,1000,12,11,1,12.4,35.2920,126.5740,0.1,0.2,0.01,-0.02,0.03",
  "0.1,3000,42,40,2,12.1,35.2922,126.5743,0.4,-0.1,0.04,-0.03,0.02",
].join("\n");

describe("App log replay persistence", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  test("keeps the uploaded CSV session when switching away from and back to log analysis even if browser storage fails", async () => {
    const user = userEvent.setup();
    render(<App />);
    const file = new File([csvText], "track-day.csv", { type: "text/csv" });
    Object.defineProperty(file, "text", { value: async () => csvText });

    await user.upload(screen.getByLabelText("CSV 로그 파일"), file);
    expect(await screen.findByText("파일: track-day.csv")).toBeInTheDocument();
    expect(storeMock.saveStoredLogReplayState).toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "배선 디버거 핀/커넥터 추적" }));
    expect(await screen.findByRole("heading", { name: "배선 디버거" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "로그 분석 CSV 분석/재생" }));

    expect(await screen.findByText("파일: track-day.csv")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "분석할 CSV가 없습니다" })).not.toBeInTheDocument();
  });
});
