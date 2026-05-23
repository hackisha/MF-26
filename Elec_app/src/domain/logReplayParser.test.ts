import { describe, expect, it } from "vitest";
import { parseEmuLogCsv } from "./logReplayParser";

describe("parseEmuLogCsv", () => {
  it("parses EMU-LOGGER CSV rows and maps sensor metadata", () => {
    const csv = [
      "Timestamp,RPM,VSS_kmh,TPS_percent,CLT_C,Batt_V,CEL_Error",
      "0.00,1000,0,2.5,82,12.4,0",
      "0.05,1200,1.5,4.0,82.1,12.3,0",
    ].join("\n");

    const session = parseEmuLogCsv(csv, "sample.csv");

    expect(session.fileName).toBe("sample.csv");
    expect(session.samples).toHaveLength(2);
    expect(session.samples[1].timeMs).toBe(50);
    expect(session.samples[1].values.RPM).toBe(1200);
    expect(session.sensors.find((sensor) => sensor.key === "CLT_C")?.unit).toBe("C");
    expect(session.summary.estimatedSampleRateHz).toBeCloseTo(20);
  });

  it("tracks invalid numeric values without crashing", () => {
    const csv = [
      "Timestamp,RPM,Batt_V",
      "0.00,1000,12.4",
      "0.05,not-number,",
    ].join("\n");

    const session = parseEmuLogCsv(csv, "bad.csv");

    expect(session.samples[1].values.RPM).toBeNull();
    expect(session.samples[1].values.Batt_V).toBeNull();
    expect(session.summary.invalidCounts.RPM).toBe(1);
    expect(session.summary.invalidCounts.Batt_V).toBe(1);
  });

  it("rejects duplicate headers with a clear Korean error", () => {
    const csv = ["Timestamp,RPM,RPM", "0.00,1000,1200"].join("\n");

    expect(() => parseEmuLogCsv(csv, "duplicate.csv")).toThrow("CSV 헤더에 중복 컬럼이 있습니다: RPM");
  });

  it("keeps fallback timestamps monotonic when date timestamps include a blank row", () => {
    const csv = [
      "Timestamp,RPM",
      "2026-01-01T00:00:00.000Z,1000",
      ",1200",
      "2026-01-01T00:00:00.100Z,1300",
    ].join("\n");

    const session = parseEmuLogCsv(csv, "dates.csv");

    expect(session.samples.map((sample) => sample.timeMs)).toEqual([0, 50, 100]);
  });

  it("handles quoted text cells with escaped quotes and commas", () => {
    const csv = ["Timestamp,Note", '0.00,"Driver said ""ready, set"""'].join("\n");

    const session = parseEmuLogCsv(csv, "quoted.csv");

    expect(session.samples[0].values.Note).toBe('Driver said "ready, set"');
    expect(session.sensors.find((sensor) => sensor.key === "Note")?.type).toBe("text");
  });

  it("treats numeric timestamps below 10000 as seconds", () => {
    const csv = ["Timestamp,RPM", "0.00,1000", "0.05,1200"].join("\n");

    const session = parseEmuLogCsv(csv, "seconds.csv");

    expect(session.samples[1].timeMs).toBe(50);
  });

  it("handles epoch seconds and epoch milliseconds without changing scale", () => {
    const epochSeconds = parseEmuLogCsv(["Timestamp,RPM", "1710000000,1000", "1710000000.05,1200"].join("\n"), "epoch-s.csv");
    const epochMilliseconds = parseEmuLogCsv(["Timestamp,RPM", "1710000000000,1000", "1710000000050,1200"].join("\n"), "epoch-ms.csv");

    expect(epochSeconds.samples[1].timeMs).toBe(50);
    expect(epochMilliseconds.samples[1].timeMs).toBe(50);
  });

  it("uses one timestamp scale for an entire relative-seconds session", () => {
    const csv = ["Timestamp,RPM", "9999.95,1000", "10000.00,1200", "10000.05,1300"].join("\n");

    const session = parseEmuLogCsv(csv, "long-seconds.csv");

    expect(session.samples.map((sample) => sample.timeMs)).toEqual([0, 50, 100]);
  });

  it("preserves textual state values", () => {
    const session = parseEmuLogCsv(["Timestamp,Gear", "0.00,N", "0.05,1"].join("\n"), "gear.csv");

    expect(session.samples[0].values.Gear).toBe("N");
    expect(session.samples[1].values.Gear).toBe(1);
  });
});
