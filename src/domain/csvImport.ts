import Papa from "papaparse";
import type { RawLogRow } from "./types";

export type ParsedCsv = {
  headers: string[];
  rows: RawLogRow[];
};

export function parseCsv(text: string): ParsedCsv {
  const parsed = Papa.parse<RawLogRow>(text, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: false
  });

  if (parsed.errors.length > 0) {
    const first = parsed.errors[0];
    throw new Error(`CSV parse error at row ${first.row ?? "unknown"}: ${first.message}`);
  }

  return {
    headers: parsed.meta.fields ?? [],
    rows: parsed.data
  };
}
