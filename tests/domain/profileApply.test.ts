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

  it("locks high-rpm-low-oil-pressure rule contract values", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    const rule = profile2025?.rules.find((rule) => rule.id === "high-rpm-low-oil-pressure");

    expect(rule).toMatchObject({
      name: "High RPM Oil Pressure Drop",
      severity: "critical",
      minDurationSec: 0.5,
      all: [
        { channelId: "RPM", op: ">", value: 6000 },
        { channelId: "OilPressure_bar", op: "<", value: 2.5 }
      ],
      views: ["summary", "graph", "report"]
    });
  });

  it("locks overlay and report section contract values", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    const profile2026 = defaultProfiles.find((profile) => profile.id === "2026-vehicle");
    const ggInputs = profile2025?.overlays.find((overlay) => overlay.id === "gg-inputs");
    const suspensionBalance = profile2026?.overlays.find((overlay) => overlay.id === "suspension-balance");

    expect(ggInputs).toEqual({
      id: "gg-inputs",
      name: "Driver Input vs Response",
      channelIds: ["TPS_percent", "ay_corrected_g"],
      mode: "normalized"
    });
    expect(suspensionBalance).toEqual({
      id: "suspension-balance",
      name: "Suspension Balance",
      channelIds: ["Susp_FL_mm", "Susp_FR_mm", "Susp_RL_mm", "Susp_RR_mm"],
      mode: "separateAxes"
    });
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

  it("defines 2026-only suspension, aero, and steering channels", () => {
    const profile2026 = defaultProfiles.find((profile) => profile.id === "2026-vehicle");

    expect(Object.keys(profile2026?.channels ?? {})).toEqual(
      expect.arrayContaining([
        "Susp_FL_mm",
        "Susp_FR_mm",
        "Susp_RL_mm",
        "Susp_RR_mm",
        "Pitot_dP_Pa",
        "Pitot_AirSpeed_KPH",
        "SteeringAngle_deg"
      ])
    );
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
