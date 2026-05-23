import { describe, expect, it } from "vitest";
import { defaultProfiles } from "../../src/domain/defaultProfiles";

describe("defaultProfiles", () => {
  it("ships 2025 and 2026 vehicle profiles", () => {
    expect(defaultProfiles.map((profile) => profile.id)).toEqual(["2025-vehicle", "2026-vehicle"]);
  });

  it("maps OilTemp_C as the 2025 source for EOT_IN", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    expect(profile2025?.channels.EOT_IN.sourceColumns).toContain("OilTemp_C");
  });

  it("defines GPS position and VSS_kmh channels for 2025 logs", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    expect(profile2025?.channels.Latitude).toMatchObject({
      id: "Latitude",
      sourceColumns: ["Latitude"],
      unit: "deg",
      group: "GPS",
      calibration: { type: "identity" }
    });
    expect(profile2025?.channels.Longitude).toMatchObject({
      id: "Longitude",
      sourceColumns: ["Longitude"],
      unit: "deg",
      group: "GPS",
      calibration: { type: "identity" }
    });
    expect(profile2025?.channels.VSS_kmh).toMatchObject({
      id: "VSS_kmh",
      sourceColumns: ["VSS_kmh"]
    });
    expect(profile2025?.channels.VSS_KPH).toBeUndefined();
  });

  it("locks rule, overlay, and report section contract values", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    const profile2026 = defaultProfiles.find((profile) => profile.id === "2026-vehicle");

    expect(profile2025?.rules.find((rule) => rule.id === "high-rpm-low-oil-pressure")?.name).toBe(
      "High RPM Oil Pressure Drop"
    );
    expect(profile2025?.overlays.find((overlay) => overlay.name === "Driver Input vs Response")?.id).toBe("gg-inputs");
    expect(profile2025?.reportSections).toEqual(["summary", "diagnostics", "events", "overlays", "behavior", "segments"]);
    expect(profile2026?.reportSections).toEqual([
      "summary",
      "diagnostics",
      "events",
      "overlays",
      "behavior",
      "map",
      "segments"
    ]);
  });

  it("defines corrected ADXL345 acceleration channels", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    expect(profile2025?.channels.ax_g.sourceColumns).toContain("ax_g");
    expect(profile2025?.channels.ay_g.sourceColumns).toContain("ay_g");
    expect(profile2025?.channels.az_g.sourceColumns).toContain("az_g");
    expect(profile2025?.channels.ax_corrected_g.sourceColumns).toContain("ax_g");
    expect(profile2025?.channels.ay_corrected_g.sourceColumns).toContain("ay_g");
    expect(profile2025?.channels.az_corrected_g.sourceColumns).toContain("az_g");
    expect(profile2025?.channels.ax_corrected_g.sourceColumns).not.toContain("ax_corrected_g");
    expect(profile2025?.channels.ay_corrected_g.sourceColumns).not.toContain("ay_corrected_g");
    expect(profile2025?.channels.az_corrected_g.sourceColumns).not.toContain("az_corrected_g");
    expect(profile2025?.channels.ax_corrected_g.calibration).toEqual({ type: "scaleOffset", scale: 0.125, offset: 0 });
    expect(profile2025?.channels.ay_corrected_g.calibration).toEqual({ type: "scaleOffset", scale: 0.125, offset: 0 });
    expect(profile2025?.channels.az_corrected_g.calibration).toEqual({ type: "scaleOffset", scale: 0.125, offset: 0 });
  });
});
