import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parseCsv } from "../../src/domain/csvImport";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import { runDiagnostics } from "../../src/domain/diagnostics";
import { applyProfile } from "../../src/domain/profileApply";
import type { AppliedLog } from "../../src/domain/types";

const profile2025 = defaultProfiles[0];

function loadAppliedLog(): AppliedLog {
  const csv = fs.readFileSync(path.join(process.cwd(), "tests/fixtures/2025-sample.csv"), "utf8");
  return applyProfile("2025-sample.csv", parseCsv(csv), profile2025);
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
