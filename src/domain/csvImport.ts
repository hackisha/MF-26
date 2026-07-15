import Papa from "papaparse";
import type { RawLogRow } from "./types";

export type CsvImportWarning = {
  code: string;
  message: string;
  row: number | null;
};

export type ParsedCsv = {
  headers: string[];
  rows: RawLogRow[];
  warnings: CsvImportWarning[];
};

function isRecoverableFieldMismatch(error: Papa.ParseError): boolean {
  return error.type === "FieldMismatch" && typeof error.row === "number";
}

export function parseCsv(text: string): ParsedCsv {
  const parsed = Papa.parse<RawLogRow>(text, {
    delimiter: ",",
    header: true,
    skipEmptyLines: "greedy",
    dynamicTyping: false
  });

  const unrecoverableError = parsed.errors.find((error) => !isRecoverableFieldMismatch(error));
  if (unrecoverableError) {
    const first = unrecoverableError;
    throw new Error(`CSV parse error at row ${first.row ?? "unknown"}: ${first.message}`);
  }

  const warnings = parsed.errors.map((error) => ({
    code: error.code,
    message: error.message,
    row: typeof error.row === "number" ? error.row : null
  }));
  const malformedRows = new Set(warnings.flatMap((warning) => (warning.row === null ? [] : [warning.row])));

  return {
    headers: parsed.meta.fields ?? [],
    rows: parsed.data.filter((_row, index) => !malformedRows.has(index)),
    warnings
  };
}
