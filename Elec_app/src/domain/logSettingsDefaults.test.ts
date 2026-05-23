import { describe, expect, test } from "vitest";
import { createDefaultLogReplaySettings, inferSensorConfigs } from "./logSettingsDefaults";
import type { SensorDefinition } from "./logReplayTypes";

describe("log replay settings defaults", () => {
  test("creates defaults for GPS, ADXL linear acceleration, ADU angular acceleration, presets, and rules", () => {
    const settings = createDefaultLogReplaySettings();

    expect(settings.version).toBe(1);
    expect(settings.gps.latitudeKey).toBe("Latitude");
    expect(settings.gps.longitudeKey).toBe("Longitude");
    expect(settings.accel.linear.unit).toBe("g");
    expect(settings.accel.linear.xKey).toBe("ax_g");
    expect(settings.accel.angular.unit).toBe("degps");
    expect(settings.accel.angular.xKey).toBe("adu_x");
    expect(settings.eventRules.map((rule) => rule.id)).toContain("low-oil-pressure");
    expect(settings.graphPresets.map((preset) => preset.id)).toContain("engine");
  });

  test("infers display groups from parsed sensor definitions", () => {
    const sensors: SensorDefinition[] = [
      { key: "RPM", label: "RPM", type: "number", unit: "rpm" },
      { key: "ADXL_ax_g", label: "ADXL X", type: "number", unit: "g" },
      { key: "adu_z", label: "ADU Z", type: "number", unit: "deg/s" },
    ];

    const configs = inferSensorConfigs(sensors);

    expect(configs.find((sensor) => sensor.sourceKey === "RPM")?.group).toBe("engine");
    expect(configs.find((sensor) => sensor.sourceKey === "ADXL_ax_g")?.group).toBe("linear-accel");
    expect(configs.find((sensor) => sensor.sourceKey === "adu_z")?.group).toBe("angular");
  });
});
