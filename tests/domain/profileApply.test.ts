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

  it("defines corrected ADXL345 acceleration channels", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    expect(profile2025?.channels.ax_corrected_g.calibration).toEqual({ type: "scaleOffset", scale: 0.125, offset: 0 });
    expect(profile2025?.channels.ay_corrected_g.calibration).toEqual({ type: "scaleOffset", scale: 0.125, offset: 0 });
    expect(profile2025?.channels.az_corrected_g.calibration).toEqual({ type: "scaleOffset", scale: 0.125, offset: 0 });
  });
});
