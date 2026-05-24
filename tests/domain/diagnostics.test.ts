import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parseCsv } from "../../src/domain/csvImport";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import { runDiagnostics } from "../../src/domain/diagnostics";
import { applyProfile } from "../../src/domain/profileApply";
import type { AppliedLog, SensorChannel, VehicleProfile } from "../../src/domain/types";

const profile2025 = defaultProfiles[0];

function loadAppliedLog(): AppliedLog {
  const csv = fs.readFileSync(path.join(process.cwd(), "tests/fixtures/2025-sample.csv"), "utf8");
  return applyProfile("2025-sample.csv", parseCsv(csv), profile2025);
}

function testChannel(id: string, defaultVisible: boolean): SensorChannel {
  return {
    id,
    displayName: id,
    sourceColumns: [id],
    unit: "unit",
    group: "Diagnostics",
    calibration: { type: "identity" },
    defaultVisible,
    color: "#000000"
  };
}

function testProfile(channels: Record<string, SensorChannel>): VehicleProfile {
  return {
    id: "test-profile",
    name: "Test Profile",
    revision: "test",
    channels,
    rules: [],
    overlays: [],
    reportSections: []
  };
}

describe("runDiagnostics", () => {
  it("flags low battery voltage and suspicious raw ADXL scale in the 2025 sample", () => {
    const findings = runDiagnostics(loadAppliedLog(), profile2025);

    expect(findings.map((finding) => finding.id)).toEqual(
      expect.arrayContaining(["low-battery-voltage", "suspicious-raw-adxl-scale"])
    );
  });

  it("reports suspicious raw ADXL scale against every raw and corrected accel channel", () => {
    const findings = runDiagnostics(loadAppliedLog(), profile2025);
    const suspiciousAdxl = findings.find((finding) => finding.id === "suspicious-raw-adxl-scale");

    expect(suspiciousAdxl?.affectedChannelIds).toEqual([
      "ax_g",
      "ay_g",
      "az_g",
      "ax_corrected_g",
      "ay_corrected_g",
      "az_corrected_g"
    ]);
  });

  it("reports low battery voltage against Batt_V as a warning", () => {
    const findings = runDiagnostics(loadAppliedLog(), profile2025);
    const lowBattery = findings.find((finding) => finding.id === "low-battery-voltage");

    expect(lowBattery).toMatchObject({
      severity: "warning",
      affectedChannelIds: ["Batt_V"]
    });
  });

  it("reports missing default-visible channels as warnings and hidden channels as info", () => {
    const profile = testProfile({
      VisibleMissing: testChannel("VisibleMissing", true),
      HiddenMissing: testChannel("HiddenMissing", false)
    });
    const log: AppliedLog = {
      fileName: "missing.csv",
      profileId: profile.id,
      profileRevision: profile.revision,
      rawHeaders: [],
      rows: []
    };

    const findings = runDiagnostics(log, profile);

    expect(findings.find((finding) => finding.id === "missing-VisibleMissing")).toMatchObject({
      severity: "warning",
      affectedChannelIds: ["VisibleMissing"]
    });
    expect(findings.find((finding) => finding.id === "missing-HiddenMissing")).toMatchObject({
      severity: "info",
      affectedChannelIds: ["HiddenMissing"]
    });
  });

  it("reports present channels with no numeric values as warning empties", () => {
    const profile = testProfile({
      PresentEmpty: testChannel("PresentEmpty", true)
    });
    const log: AppliedLog = {
      fileName: "empty.csv",
      profileId: profile.id,
      profileRevision: profile.revision,
      rawHeaders: ["PresentEmpty"],
      rows: [
        { index: 0, timestampSec: 0, values: { PresentEmpty: null } },
        { index: 1, timestampSec: 1, values: { PresentEmpty: null } }
      ]
    };

    const findings = runDiagnostics(log, profile);

    expect(findings.find((finding) => finding.id === "empty-PresentEmpty")).toMatchObject({
      severity: "warning",
      affectedChannelIds: ["PresentEmpty"]
    });
  });

  it("does not flag low battery at the exact 11.8 V threshold", () => {
    const log: AppliedLog = {
      fileName: "battery-boundary.csv",
      profileId: profile2025.id,
      profileRevision: profile2025.revision,
      rawHeaders: ["Batt_V"],
      rows: [{ index: 0, timestampSec: 0, values: { Batt_V: 11.8 } }]
    };

    expect(runDiagnostics(log, profile2025).some((finding) => finding.id === "low-battery-voltage")).toBe(false);
  });

  it("does not flag suspicious raw ADXL scale at the raw 6 g boundary", () => {
    const log: AppliedLog = {
      fileName: "adxl-raw-boundary.csv",
      profileId: profile2025.id,
      profileRevision: profile2025.revision,
      rawHeaders: ["ay_g"],
      rows: [{ index: 0, timestampSec: 0, values: { ay_g: 6, ay_corrected_g: 0.75 } }]
    };

    expect(runDiagnostics(log, profile2025).some((finding) => finding.id === "suspicious-raw-adxl-scale")).toBe(
      false
    );
  });

  it("still flags suspicious raw ADXL scale at the corrected 2 g boundary when raw is high", () => {
    const log: AppliedLog = {
      fileName: "adxl-corrected-boundary.csv",
      profileId: profile2025.id,
      profileRevision: profile2025.revision,
      rawHeaders: ["ay_g"],
      rows: [{ index: 0, timestampSec: 0, values: { ay_g: 6.1, ay_corrected_g: 2 } }]
    };

    expect(runDiagnostics(log, profile2025).some((finding) => finding.id === "suspicious-raw-adxl-scale")).toBe(true);
  });

  it("scans large logs without spreading channel values into function arguments", () => {
    const rows = Array.from({ length: 150_000 }, (_, index) => ({
      index,
      timestampSec: index,
      values: {
        Batt_V: index === 149_999 ? 11.7 : 12,
        ay_g: index === 149_999 ? -6.1 : 0,
        ay_corrected_g: index === 149_999 ? -2 : 0
      }
    }));
    const log: AppliedLog = {
      fileName: "large.csv",
      profileId: profile2025.id,
      profileRevision: profile2025.revision,
      rawHeaders: ["Batt_V", "ay_g"],
      rows
    };
    const findingIds = runDiagnostics(log, profile2025).map((finding) => finding.id);

    expect(findingIds).toEqual(expect.arrayContaining(["low-battery-voltage", "suspicious-raw-adxl-scale"]));
  });

  it("reports the first non-increasing timestamp as one critical finding", () => {
    const log: AppliedLog = {
      fileName: "timestamp-regression.csv",
      profileId: profile2025.id,
      profileRevision: profile2025.revision,
      rawHeaders: ["Timestamp"],
      rows: [
        { index: 0, timestampSec: 1, values: { Timestamp: 1 } },
        { index: 1, timestampSec: 1, values: { Timestamp: 1 } },
        { index: 2, timestampSec: 0.5, values: { Timestamp: 0.5 } }
      ]
    };

    const timestampFindings = runDiagnostics(log, profile2025).filter(
      (finding) => finding.id === "timestamp-not-increasing"
    );

    expect(timestampFindings).toHaveLength(1);
    expect(timestampFindings[0]).toMatchObject({
      severity: "critical",
      affectedChannelIds: ["Timestamp"],
      startSec: 1,
      endSec: 1
    });
  });
});
