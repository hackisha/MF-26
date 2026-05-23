import { EMU_SENSOR_DEFINITIONS } from "./logReplayColumns";
import type { LogSample, LogSession, SensorDefinition, SensorType, SensorValue } from "./logReplayTypes";

function splitCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];

    if (char === '"' && quoted && next === '"') {
      current += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      cells.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }

  cells.push(current.trim());
  return cells;
}

function inferNumericTimestampFactor(values: string[]): number {
  const numericValues = values.map(Number).filter(Number.isFinite);
  if (numericValues.length === 0) return 1_000;

  const first = numericValues[0];
  if (first >= 1_000_000_000_000) return 1;
  if (first >= 1_000_000_000) return 1_000;

  const deltas = numericValues
    .slice(1)
    .map((value, index) => Math.abs(value - numericValues[index]))
    .filter((delta) => delta > 0)
    .sort((a, b) => a - b);
  const medianDelta = deltas[Math.floor(deltas.length / 2)];
  return medianDelta !== undefined && medianDelta >= 5 ? 1 : 1_000;
}

function parseTimeMs(value: string | undefined, rowIndex: number, numericFactor: number, previousTimeMs?: number): number {
  const fallbackTimeMs = previousTimeMs !== undefined ? previousTimeMs + 50 : rowIndex * 50;
  if (!value) return fallbackTimeMs;

  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    return Math.round(numeric * numericFactor);
  }

  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : fallbackTimeMs;
}

function inferUnknownType(values: string[]): SensorType {
  const actualValues = values.filter((value) => value !== "");
  if (actualValues.length > 0 && actualValues.every((value) => Number.isFinite(Number(value)))) {
    return "number";
  }

  return "text";
}

function shouldParseNumeric(type: SensorType): boolean {
  return type === "number";
}

function sensorForColumn(column: string, type: SensorType): SensorDefinition {
  const known = EMU_SENSOR_DEFINITIONS[column as keyof typeof EMU_SENSOR_DEFINITIONS];
  if (known) return { key: column, ...known };

  return {
    key: column,
    label: column,
    type,
  };
}

export function parseEmuLogCsv(text: string, fileName: string): LogSession {
  const lines = text
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length < 2) {
    throw new Error("CSV에는 헤더와 최소 1개 이상의 데이터 행이 필요합니다.");
  }

  const columns = splitCsvLine(lines[0]);
  if (columns.length === 0 || columns.some((column) => !column)) {
    throw new Error("CSV 헤더를 읽을 수 없습니다.");
  }

  const duplicateColumn = columns.find((column, index) => columns.indexOf(column) !== index);
  if (duplicateColumn) {
    throw new Error(`CSV 헤더에 중복 컬럼이 있습니다: ${duplicateColumn}`);
  }

  const rows = lines.slice(1).map(splitCsvLine);
  const timestampIndex = columns.indexOf("Timestamp");
  const numericTimestampFactor =
    timestampIndex >= 0 ? inferNumericTimestampFactor(rows.map((row) => row[timestampIndex]?.trim() ?? "")) : 1_000;
  const columnTypes = Object.fromEntries(
    columns.map((column, columnIndex) => {
      const known = EMU_SENSOR_DEFINITIONS[column as keyof typeof EMU_SENSOR_DEFINITIONS];
      return [column, known?.type ?? inferUnknownType(rows.map((row) => row[columnIndex]?.trim() ?? ""))];
    }),
  ) as Record<string, SensorType>;

  const invalidCounts: Record<string, number> = {};
  let previousTimeMs: number | undefined;
  const samples: LogSample[] = rows.map((cells, rowIndex) => {
    const values: Record<string, SensorValue> = {};

    columns.forEach((column, columnIndex) => {
      const raw = cells[columnIndex]?.trim() ?? "";
      const type = columnTypes[column];

      if (shouldParseNumeric(type)) {
        const parsed = Number(raw);
        if (raw !== "" && Number.isFinite(parsed)) {
          values[column] = parsed;
        } else {
          values[column] = null;
          invalidCounts[column] = (invalidCounts[column] ?? 0) + 1;
        }
      } else if (type === "state") {
        const parsed = Number(raw);
        if (raw === "") {
          values[column] = null;
          invalidCounts[column] = (invalidCounts[column] ?? 0) + 1;
        } else {
          values[column] = Number.isFinite(parsed) ? parsed : raw;
        }
      } else {
        values[column] = raw;
      }
    });

    const rawTimestamp = timestampIndex >= 0 ? cells[timestampIndex]?.trim() ?? "" : "";
    const timeMs = parseTimeMs(rawTimestamp, rowIndex, numericTimestampFactor, previousTimeMs);
    previousTimeMs = timeMs;

    return {
      rowIndex,
      timeMs,
      rawTimestamp,
      values,
    };
  });

  const baseTime = samples[0]?.timeMs ?? 0;
  const normalizedSamples = samples.map((sample) => ({
    ...sample,
    timeMs: Math.max(0, sample.timeMs - baseTime),
  }));

  const sensors = columns.map((column) => sensorForColumn(column, columnTypes[column]));
  const durationMs = normalizedSamples.at(-1)?.timeMs ?? 0;
  const averageDeltaMs = normalizedSamples.length > 1 ? durationMs / (normalizedSamples.length - 1) : 0;

  return {
    id: `${fileName}-${Date.now()}`,
    fileName,
    columns,
    sensors,
    samples: normalizedSamples,
    summary: {
      rowCount: normalizedSamples.length,
      durationMs,
      startLabel: normalizedSamples[0]?.rawTimestamp ?? "0",
      endLabel: normalizedSamples.at(-1)?.rawTimestamp ?? "0",
      estimatedSampleRateHz: averageDeltaMs > 0 ? 1000 / averageDeltaMs : undefined,
      invalidCounts,
    },
  };
}
