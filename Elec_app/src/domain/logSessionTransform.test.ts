import { describe, expect, test } from "vitest";
import { createDefaultLogReplaySettings } from "./logSettingsDefaults";
import { applyLogReplaySettings } from "./logSessionTransform";
import type { LogSession } from "./logReplayTypes";

function session(): LogSession {
  return {
    id: "s1",
    fileName: "run.csv",
    columns: ["Timestamp", "RPM", "OilPressure_bar", "ax_g"],
    sensors: [
      { key: "Timestamp", label: "Timestamp", type: "text" },
      { key: "RPM", label: "RPM", type: "number", unit: "rpm" },
      { key: "OilPressure_bar", label: "Oil Pressure", type: "number", unit: "bar" },
      { key: "ax_g", label: "Accel X", type: "number", unit: "g" },
    ],
    samples: [
      { rowIndex: 0, timeMs: 0, values: { Timestamp: "0", RPM: 1000, OilPressure_bar: 2, ax_g: 1 } },
      { rowIndex: 1, timeMs: 100, values: { Timestamp: "0.1", RPM: 2000, OilPressure_bar: 1, ax_g: 2 } },
    ],
    summary: {
      rowCount: 2,
      durationMs: 100,
      startLabel: "0",
      endLabel: "0.1",
      invalidCounts: {},
      estimatedSampleRateHz: 10,
    },
  };
}

describe("applyLogReplaySettings", () => {
  test("applies scale and offset and adds derived sensor values", () => {
    const settings = createDefaultLogReplaySettings(session().sensors);
    const rpm = settings.sensors.find((sensor) => sensor.sourceKey === "RPM");
    if (!rpm) throw new Error("missing rpm config");
    rpm.scale = 0.001;
    rpm.unit = "krpm";
    settings.derivedSensors.push({
      id: "rpm-oil-score",
      label: "RPM Oil Score",
      expression: "RPM * OilPressure_bar",
      unit: "",
      group: "custom",
      precision: 2,
      color: "#ffc300",
      fallback: "empty",
      enabled: true,
    });

    const transformed = applyLogReplaySettings(session(), settings);

    expect(transformed.samples[1].values.RPM).toBe(2);
    expect(transformed.sensors.find((sensor) => sensor.key === "RPM")?.unit).toBe("krpm");
    expect(transformed.samples[1].values["rpm-oil-score"]).toBe(2);
    expect(transformed.columns).toContain("rpm-oil-score");
  });
});
