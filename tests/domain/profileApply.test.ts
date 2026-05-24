import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parseCsv } from "../../src/domain/csvImport";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import { applyProfile } from "../../src/domain/profileApply";

const csvHeader2025 = [
  "Timestamp",
  "Latitude",
  "Longitude",
  "GPS_Speed_KPH",
  "Satellites",
  "Altitude_m",
  "Heading_deg",
  "RPM",
  "TPS_percent",
  "IAT_C",
  "MAP_kPa",
  "PulseWidth_ms",
  "AnalogIn1_V",
  "AnalogIn2_V",
  "AnalogIn3_V",
  "AnalogIn4_V",
  "VSS_kmh",
  "Baro_kPa",
  "OilTemp_C",
  "OilPressure_bar",
  "FuelPressure_bar",
  "CLT_C",
  "EOT_OUT",
  "fuelPumpTemp",
  "IgnAngle_deg",
  "DwellTime_ms",
  "WBO_Lambda",
  "LambdaCorrection_percent",
  "EGT1_C",
  "EGT2_C",
  "Gear",
  "EmuTemp_C",
  "Batt_V",
  "CEL_Error",
  "Flags1",
  "Ethanol_percent",
  "DBW_Pos_percent",
  "DBW_Target_percent",
  "TC_drpm_raw",
  "TC_drpm",
  "TC_TorqueReduction_percent",
  "PitLimit_TorqueReduction_percent",
  "AnalogIn5_V",
  "AnalogIn6_V",
  "OutFlags1",
  "OutFlags2",
  "OutFlags3",
  "OutFlags4",
  "BoostTarget_kPa",
  "PWM1_DC_percent",
  "DSG_Mode",
  "LambdaTarget",
  "PWM2_DC_percent",
  "FuelUsed_L",
  "ax_g",
  "ay_g",
  "az_g",
  "gx_dps",
  "gy_dps",
  "gz_dps",
  "ADU_ax_g",
  "ADU_ay_g",
  "ADU_az_g"
];

describe("defaultProfiles", () => {
  it("ships 2025 and 2026 vehicle profiles", () => {
    expect(defaultProfiles.map((profile) => profile.id)).toEqual(["2025-vehicle", "2026-vehicle"]);
  });

  it("maps OilTemp_C as the 2025 source for EOT_IN", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    expect(profile2025?.channels.EOT_IN.sourceColumns).toContain("OilTemp_C");
  });

  it("covers every source column from the 2025 CSV header", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    const coveredSourceColumns = new Set(
      Object.values(profile2025?.channels ?? {}).flatMap((channel) => channel.sourceColumns)
    );

    expect(csvHeader2025.filter((sourceColumn) => !coveredSourceColumns.has(sourceColumn))).toEqual([]);
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
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    const profile2026 = defaultProfiles.find((profile) => profile.id === "2026-vehicle");
    const channelIds2026Only = [
      "Susp_FL_mm",
      "Susp_FR_mm",
      "Susp_RL_mm",
      "Susp_RR_mm",
      "Pitot_dP_Pa",
      "Pitot_AirSpeed_KPH",
      "SteeringAngle_deg"
    ];

    expect(Object.keys(profile2026?.channels ?? {})).toEqual(expect.arrayContaining(channelIds2026Only));
    expect(Object.keys(profile2025?.channels ?? {})).not.toEqual(expect.arrayContaining(channelIds2026Only));
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

  it("does not share mutable channel, rule, or overlay objects between 2025 and 2026 profiles", () => {
    const profile2025 = defaultProfiles.find((profile) => profile.id === "2025-vehicle");
    const profile2026 = defaultProfiles.find((profile) => profile.id === "2026-vehicle");
    const rule2025 = profile2025?.rules.find((rule) => rule.id === "high-rpm-low-oil-pressure");
    const rule2026 = profile2026?.rules.find((rule) => rule.id === "high-rpm-low-oil-pressure");
    const overlay2025 = profile2025?.overlays.find((overlay) => overlay.id === "gg-inputs");
    const overlay2026 = profile2026?.overlays.find((overlay) => overlay.id === "gg-inputs");

    profile2026?.channels.RPM.sourceColumns.push("Mutated_RPM");
    if (rule2026?.all?.[0]) {
      rule2026.all[0].value = 7000;
    }
    overlay2026?.channelIds.push("Mutated_Channel");

    expect(profile2025?.channels.RPM.sourceColumns).toEqual(["RPM", "EngineSpeed_RPM"]);
    expect(rule2025?.all?.[0].value).toBe(6000);
    expect(overlay2025?.channelIds).toEqual(["TPS_percent", "ay_corrected_g"]);
  });
});

describe("applyProfile", () => {
  it("preserves CSV headers and raw row strings", () => {
    const parsed = parseCsv("Timestamp,RPM\n0.10,00123\n");

    expect(parsed.headers).toEqual(["Timestamp", "RPM"]);
    expect(parsed.rows).toEqual([{ Timestamp: "0.10", RPM: "00123" }]);
    expect(parsed.warnings).toEqual([]);
  });

  it("skips malformed field-count rows and records import warnings", () => {
    const parsed = parseCsv("Timestamp,RPM\n0,1000\nbad-row\n1,2000\n");

    expect(parsed.rows).toEqual([
      { Timestamp: "0", RPM: "1000" },
      { Timestamp: "1", RPM: "2000" }
    ]);
    expect(parsed.warnings).toEqual([
      {
        code: "TooFewFields",
        message: "Too few fields: expected 2 fields but parsed 1",
        row: 1
      }
    ]);
  });

  it("creates numeric rows and corrected ADXL345 channels", () => {
    const csv = fs.readFileSync(path.join(process.cwd(), "tests/fixtures/2025-sample.csv"), "utf8");
    const parsed = parseCsv(csv);
    const profile2025 = defaultProfiles[0];
    const applied = applyProfile("2025-sample.csv", parsed, profile2025);

    expect(applied.rows).toHaveLength(5);
    expect(applied.rows[1].values.EOT_IN).toBe(73);
    expect(applied.rows[1].values.ax_corrected_g).toBeCloseTo(0.2);
    expect(applied.rows[1].values.ay_corrected_g).toBeCloseTo(0.3);
    expect(applied.rows[1].values.az_corrected_g).toBeCloseTo(1.01);
  });

  it("uses timestamp source aliases for row timestamps", () => {
    const parsed = parseCsv("Time_s,RPM\n12.50,3000\n");
    const applied = applyProfile("time-sample.csv", parsed, defaultProfiles[0]);

    expect(applied.rows[0].timestampSec).toBe(12.5);
    expect(applied.rows[0].values.Timestamp).toBe(12.5);
  });

  it("falls back to later source aliases when earlier aliases are blank or non-numeric", () => {
    const parsed = parseCsv("RPM,EngineSpeed_RPM\nnot-a-number,6400\n,7100\n");
    const applied = applyProfile("rpm-aliases.csv", parsed, defaultProfiles[0]);

    expect(applied.rows[0].values.RPM).toBe(6400);
    expect(applied.rows[1].values.RPM).toBe(7100);
  });

  it("sets a channel value to null when every source alias is blank or non-numeric", () => {
    const parsed = parseCsv("RPM,EngineSpeed_RPM\nnot-a-number,\n");
    const applied = applyProfile("bad-rpm.csv", parsed, defaultProfiles[0]);

    expect(applied.rows[0].values.RPM).toBeNull();
  });
});
