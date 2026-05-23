import type { AppliedLog, DetectedEvent } from "./types";

export type RunSummary = {
  durationSec: number;
  maxSpeedKph: number | null;
  maxRpm: number | null;
  maxCorrectedG: number | null;
  maxEotInC: number | null;
  minOilPressureBar: number | null;
  warningEventCount: number;
  criticalEventCount: number;
};

function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function maxChannelValue(log: AppliedLog, channelId: string): number | null {
  let maximum: number | null = null;

  for (const row of log.rows) {
    const value = row.values[channelId];
    if (!isFiniteNumber(value)) continue;
    maximum = maximum === null ? value : Math.max(maximum, value);
  }

  return maximum;
}

function minChannelValue(log: AppliedLog, channelId: string): number | null {
  let minimum: number | null = null;

  for (const row of log.rows) {
    const value = row.values[channelId];
    if (!isFiniteNumber(value)) continue;
    minimum = minimum === null ? value : Math.min(minimum, value);
  }

  return minimum;
}

function maxCorrectedG(log: AppliedLog): number | null {
  let maximum: number | null = null;
  const channelIds = ["ax_corrected_g", "ay_corrected_g"];

  for (const row of log.rows) {
    for (const channelId of channelIds) {
      const value = row.values[channelId];
      if (!isFiniteNumber(value)) continue;

      const magnitude = Math.abs(value);
      maximum = maximum === null ? magnitude : Math.max(maximum, magnitude);
    }
  }

  return maximum;
}

function durationSec(log: AppliedLog): number {
  if (log.rows.length === 0) return 0;

  const first = log.rows[0].timestampSec;
  const last = log.rows[log.rows.length - 1].timestampSec;

  return Math.max(0, last - first);
}

function countEvents(events: DetectedEvent[], severity: DetectedEvent["severity"]): number {
  let count = 0;

  for (const event of events) {
    if (event.severity === severity) count += 1;
  }

  return count;
}

export function summarizeLog(log: AppliedLog, events: DetectedEvent[]): RunSummary {
  const maxGpsSpeed = maxChannelValue(log, "GPS_Speed_KPH");

  return {
    durationSec: durationSec(log),
    maxSpeedKph: maxGpsSpeed ?? maxChannelValue(log, "VSS_kmh"),
    maxRpm: maxChannelValue(log, "RPM"),
    maxCorrectedG: maxCorrectedG(log),
    maxEotInC: maxChannelValue(log, "EOT_IN"),
    minOilPressureBar: minChannelValue(log, "OilPressure_bar"),
    warningEventCount: countEvents(events, "warning"),
    criticalEventCount: countEvents(events, "critical")
  };
}
