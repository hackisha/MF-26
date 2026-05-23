import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import type { LogSession } from "../../domain/logReplayTypes";
import { SensorOverlayChart } from "./SensorOverlayChart";

const session: LogSession = {
  id: "s1",
  fileName: "run.csv",
  columns: ["Timestamp", "RPM"],
  sensors: [
    { key: "Timestamp", label: "Timestamp", type: "text" },
    { key: "RPM", label: "RPM", type: "number", unit: "rpm" },
  ],
  samples: [
    { rowIndex: 0, timeMs: 0, values: { Timestamp: "0", RPM: 1000 } },
    { rowIndex: 1, timeMs: 1000, values: { Timestamp: "1", RPM: 2000 } },
  ],
  summary: { rowCount: 2, durationMs: 1000, startLabel: "0", endLabel: "1", invalidCounts: {} },
};

describe("SensorOverlayChart", () => {
  test("shows sensor name, value, and unit while hovering the chart", () => {
    render(
      <SensorOverlayChart
        session={session}
        selectedKeys={["RPM"]}
        currentTimeMs={500}
        onSelectedKeysChange={vi.fn()}
        onSeek={vi.fn()}
      />,
    );

    const chart = screen.getByTestId("sensor-overlay-chart");
    Object.defineProperty(chart, "getBoundingClientRect", {
      value: () => ({ left: 0, top: 0, width: 200, height: 100, right: 200, bottom: 100 }),
    });

    fireEvent.mouseMove(chart, { clientX: 120, clientY: 40 });

    const tooltip = document.querySelector(".overlay-tooltip");
    expect(tooltip).toBeInTheDocument();
    expect(within(tooltip as HTMLElement).getByText(/RPM: 2000 rpm/)).toBeInTheDocument();
  });
});
