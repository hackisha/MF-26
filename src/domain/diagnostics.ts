import type { AppliedLog, DiagnosticFinding, SensorChannel, VehicleProfile } from "./types";

function valuesFor(log: AppliedLog, channelId: string): number[] {
  return log.rows
    .map((row) => row.values[channelId])
    .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
}

function hasAnyValue(log: AppliedLog, channelId: string): boolean {
  return valuesFor(log, channelId).length > 0;
}

function minValue(log: AppliedLog, channelId: string): number | null {
  const values = valuesFor(log, channelId);
  return values.length > 0 ? Math.min(...values) : null;
}

function maxAbs(log: AppliedLog, channelId: string): number | null {
  const values = valuesFor(log, channelId);
  return values.length > 0 ? Math.max(...values.map((value) => Math.abs(value))) : null;
}

function hasSourceColumn(rawHeaders: Set<string>, channel: SensorChannel): boolean {
  return channel.sourceColumns.some((sourceColumn) => rawHeaders.has(sourceColumn));
}

function profileChannelFindings(log: AppliedLog, profile: VehicleProfile): DiagnosticFinding[] {
  const findings: DiagnosticFinding[] = [];
  const rawHeaders = new Set(log.rawHeaders);

  for (const [channelId, channel] of Object.entries(profile.channels)) {
    if (!hasSourceColumn(rawHeaders, channel)) {
      findings.push({
        id: `missing-${channelId}`,
        severity: channel.defaultVisible ? "warning" : "info",
        title: `Missing ${channel.displayName}`,
        detail: `None of the source columns for ${channel.displayName} were found in the log.`,
        affectedChannelIds: [channelId]
      });
      continue;
    }

    if (!hasAnyValue(log, channelId)) {
      findings.push({
        id: `empty-${channelId}`,
        severity: "warning",
        title: `No numeric ${channel.displayName} values`,
        detail: `${channel.displayName} is present in the log headers but has no numeric values.`,
        affectedChannelIds: [channelId]
      });
    }
  }

  return findings;
}

function timestampFinding(log: AppliedLog): DiagnosticFinding | null {
  for (let index = 1; index < log.rows.length; index += 1) {
    const previous = log.rows[index - 1];
    const current = log.rows[index];

    if (current.timestampSec <= previous.timestampSec) {
      return {
        id: "timestamp-not-increasing",
        severity: "critical",
        title: "Timestamp is not increasing",
        detail: `Timestamp at row ${current.index} is not greater than the previous row.`,
        affectedChannelIds: ["Timestamp"],
        startSec: current.timestampSec,
        endSec: current.timestampSec
      };
    }
  }

  return null;
}

function lowBatteryFinding(log: AppliedLog): DiagnosticFinding | null {
  const minBatteryVoltage = minValue(log, "Batt_V");

  if (minBatteryVoltage === null || minBatteryVoltage >= 11.8) return null;

  return {
    id: "low-battery-voltage",
    severity: "warning",
    title: "Low battery voltage",
    detail: `Battery voltage dropped to ${minBatteryVoltage.toFixed(1)} V.`,
    affectedChannelIds: ["Batt_V"]
  };
}

function suspiciousAdxlScaleFinding(log: AppliedLog): DiagnosticFinding | null {
  const rawLateralG = maxAbs(log, "ay_g");
  const correctedLateralG = maxAbs(log, "ay_corrected_g");

  if (rawLateralG === null || correctedLateralG === null) return null;
  if (rawLateralG <= 6 || correctedLateralG > 2) return null;

  return {
    id: "suspicious-raw-adxl-scale",
    severity: "info",
    title: "Suspicious raw ADXL scale",
    detail: "Raw lateral acceleration is high while the corrected ADXL345 channel remains in the expected range.",
    affectedChannelIds: ["ay_g", "ay_corrected_g"]
  };
}

export function runDiagnostics(log: AppliedLog, profile: VehicleProfile): DiagnosticFinding[] {
  const findings = profileChannelFindings(log, profile);
  const timestamp = timestampFinding(log);
  const lowBattery = lowBatteryFinding(log);
  const suspiciousAdxlScale = suspiciousAdxlScaleFinding(log);

  if (timestamp) findings.push(timestamp);
  if (lowBattery) findings.push(lowBattery);
  if (suspiciousAdxlScale) findings.push(suspiciousAdxlScale);

  return findings;
}
