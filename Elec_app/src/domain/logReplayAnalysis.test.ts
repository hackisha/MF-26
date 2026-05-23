import { describe, expect, it } from "vitest";
import { extractLogEvents, findNearestSample, limitOverlaySelection, normalizeSeries } from "./logReplayAnalysis";
import { parseEmuLogCsv } from "./logReplayParser";
import { createDefaultLogReplaySettings } from "./logSettingsDefaults";

const session = parseEmuLogCsv(
  [
    "Timestamp,RPM,VSS_kmh,TPS_percent,CLT_C,Batt_V,CEL_Error,OilPressure_bar,FuelPressure_bar",
    "0.00,1000,0,2,80,12.4,0,2.0,3.2",
    "0.05,5000,50,70,106,10.9,1,0.7,2.0",
    "0.10,4000,45,30,98,12.1,0,1.6,3.0",
  ].join("\n"),
  "events.csv",
);

describe("log replay analysis", () => {
  it("finds the nearest sample for a playhead time", () => {
    expect(findNearestSample(session.samples, 60)?.values.RPM).toBe(5000);
  });

  it("limits overlay selection to four keys", () => {
    expect(limitOverlaySelection(["RPM", "TPS_percent", "VSS_kmh", "CLT_C", "Batt_V"], "OilTemp_C")).toEqual([
      "RPM",
      "TPS_percent",
      "VSS_kmh",
      "CLT_C",
    ]);
  });

  it("normalizes numeric series to 0..1", () => {
    expect(normalizeSeries([10, 20, 30])).toEqual([0, 0.5, 1]);
  });

  it("extracts warning and danger events", () => {
    const events = extractLogEvents(session);
    expect(events.map((event) => event.type)).toContain("cel");
    expect(events.map((event) => event.type)).toContain("low-battery");
    expect(events.map((event) => event.type)).toContain("high-coolant");
    expect(events.map((event) => event.type)).toContain("low-oil-pressure");
    expect(events.map((event) => event.type)).toContain("low-fuel-pressure");
  });

  it("coalesces repeated anomaly samples into one event per episode", () => {
    const repeated = parseEmuLogCsv(
      ["Timestamp,Batt_V", "0.00,10.8", "0.05,10.7", "0.10,12.2", "0.15,10.6"].join("\n"),
      "repeated.csv",
    );

    const lowBattery = extractLogEvents(repeated).filter((event) => event.type === "low-battery");

    expect(lowBattery).toHaveLength(2);
    expect(lowBattery.map((event) => event.timeMs)).toEqual([0, 150]);
  });

  it("extracts oil temperature, gps, and rpm anomaly events", () => {
    const rich = parseEmuLogCsv(
      [
        "Timestamp,RPM,OilTemp_C,Latitude,Longitude",
        "0.00,4000,90,37.1,127.1",
        "0.05,0,130,,",
        "0.10,7000,95,38.0,128.0",
      ].join("\n"),
      "rich.csv",
    );

    const eventTypes = extractLogEvents(rich).map((event) => event.type);

    expect(eventTypes).toContain("high-oil-temp");
    expect(eventTypes).toContain("rpm-zero");
    expect(eventTypes).toContain("gps-gap");
    expect(eventTypes).toContain("gps-jump");
  });

  it("does not trigger default rule events for missing sensors", () => {
    const missingOil = parseEmuLogCsv(["Timestamp,RPM", "0.00,4000", "0.05,4500"].join("\n"), "missing-oil.csv");
    const settings = createDefaultLogReplaySettings(missingOil.sensors);

    expect(extractLogEvents(missingOil, settings).map((event) => event.type)).not.toContain("low-oil-pressure");
  });
});
