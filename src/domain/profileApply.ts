import type { AppliedLog, Calibration, NumericLogRow, VehicleProfile } from "./types";
import type { ParsedCsv } from "./csvImport";

function parseNumber(value: string | undefined): number | null {
  if (value === undefined || value.trim() === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function applyCalibration(value: number | null, calibration: Calibration): number | null {
  if (value === null) return null;
  if (calibration.type === "identity") return value;
  if (calibration.type === "invert") return -value;
  return value * calibration.scale + calibration.offset;
}

function readSourceValue(row: Record<string, string>, sourceColumns: string[]): number | null {
  for (const column of sourceColumns) {
    const value = parseNumber(row[column]);
    if (value !== null) return value;
  }
  return null;
}

function readTimestamp(row: Record<string, string>, index: number, profile: VehicleProfile): number {
  const timestampChannel = profile.channels.Timestamp;
  if (!timestampChannel) return index;

  const sourceValue = readSourceValue(row, timestampChannel.sourceColumns);
  const timestamp = applyCalibration(sourceValue, timestampChannel.calibration);
  return timestamp ?? index;
}

export function applyProfile(fileName: string, parsed: ParsedCsv, profile: VehicleProfile): AppliedLog {
  const rows: NumericLogRow[] = parsed.rows.map((row, index) => {
    const values: Record<string, number | null> = {};

    for (const [channelId, channel] of Object.entries(profile.channels)) {
      const sourceValue = readSourceValue(row, channel.sourceColumns);
      values[channelId] = applyCalibration(sourceValue, channel.calibration);
    }

    return {
      index,
      timestampSec: readTimestamp(row, index, profile),
      values
    };
  });

  return {
    fileName,
    profileId: profile.id,
    profileRevision: profile.revision,
    rawHeaders: parsed.headers,
    rows
  };
}
