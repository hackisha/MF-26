import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parseCsv } from "../../src/domain/csvImport";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import { detectEvents } from "../../src/domain/events";
import { applyProfile } from "../../src/domain/profileApply";
import { createManualSegment, segmentsFromEvents } from "../../src/domain/segments";
import type { AppliedLog, ThresholdRule, VehicleProfile } from "../../src/domain/types";

const profile2025 = defaultProfiles[0];

function loadAppliedLog(): AppliedLog {
  const csv = fs.readFileSync(path.join(process.cwd(), "tests/fixtures/2025-sample.csv"), "utf8");
  return applyProfile("2025-sample.csv", parseCsv(csv), profile2025);
}

function testLog(rows: AppliedLog["rows"]): AppliedLog {
  return {
    fileName: "test.csv",
    profileId: "test-profile",
    profileRevision: "test",
    rawHeaders: [],
    rows
  };
}

function row(timestampSec: number, values: Record<string, number | null>): AppliedLog["rows"][number] {
  return {
    index: timestampSec,
    timestampSec,
    values
  };
}

function testProfile(rules: ThresholdRule[]): VehicleProfile {
  return {
    id: "test-profile",
    name: "Test Profile",
    revision: "test",
    channels: {},
    rules,
    overlays: [],
    reportSections: []
  };
}

function rule(overrides: Partial<ThresholdRule>): ThresholdRule {
  return {
    id: "test-rule",
    name: "Test Rule",
    severity: "warning",
    all: [],
    any: [],
    minDurationSec: 0,
    description: "Test rule description.",
    views: [],
    ...overrides
  };
}

describe("detectEvents", () => {
  it("detects configured events in the 2025 sample fixture", () => {
    const events = detectEvents(loadAppliedLog(), profile2025);
    const highRpmLowOilPressure = events.find((event) => event.ruleId === "high-rpm-low-oil-pressure");
    const lowBatteryVoltage = events.find((event) => event.ruleId === "low-battery-voltage");

    expect(highRpmLowOilPressure).toMatchObject({
      severity: "critical",
      startSec: 0.2,
      endSec: 1.5
    });
    expect(lowBatteryVoltage).toMatchObject({
      severity: "warning",
      startSec: 0.3,
      endSec: 1.5
    });
  });

  it("creates event-backed segments from detected events", () => {
    const events = detectEvents(loadAppliedLog(), profile2025);
    const segments = segmentsFromEvents(events);

    expect(segments).toEqual(
      events.map((event) => ({
        id: `segment-${event.id}`,
        name: event.name,
        startSec: event.startSec,
        endSec: event.endSec,
        source: "event"
      }))
    );
  });

  it("requires every all condition to match", () => {
    const events = detectEvents(
      testLog([
        row(0, { RPM: 6500, OilPressure_bar: 3.0 }),
        row(1, { RPM: 6500, OilPressure_bar: 2.0 })
      ]),
      testProfile([
        rule({
          all: [
            { channelId: "RPM", op: ">", value: 6000 },
            { channelId: "OilPressure_bar", op: "<", value: 2.5 }
          ]
        })
      ])
    );

    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ startSec: 1, endSec: 1 });
  });

  it("matches any rules when at least one any condition matches", () => {
    const events = detectEvents(
      testLog([
        row(0, { Batt_V: 12.4, RPM: 3000 }),
        row(1, { Batt_V: 12.4, RPM: 7200 })
      ]),
      testProfile([
        rule({
          any: [
            { channelId: "Batt_V", op: "<", value: 11.8 },
            { channelId: "RPM", op: ">", value: 7000 }
          ]
        })
      ])
    );

    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ startSec: 1, endSec: 1 });
  });

  it("ignores events shorter than minDurationSec", () => {
    const events = detectEvents(
      testLog([row(0, { Batt_V: 11.6 }), row(0.4, { Batt_V: 11.6 }), row(1, { Batt_V: 12.4 })]),
      testProfile([
        rule({
          all: [{ channelId: "Batt_V", op: "<", value: 11.8 }],
          minDurationSec: 0.5
        })
      ])
    );

    expect(events).toEqual([]);
  });

  it("uses only the first and last confirmed matching samples for duration", () => {
    const events = detectEvents(
      testLog([row(10, { Batt_V: 11.6 }), row(11.5, { Batt_V: 12.4 })]),
      testProfile([
        rule({
          all: [{ channelId: "Batt_V", op: "<", value: 11.8 }],
          minDurationSec: 1
        })
      ])
    );

    expect(events).toEqual([]);
  });

  it("emits final open events when confirmed matching sample span meets minDurationSec", () => {
    const events = detectEvents(
      testLog([row(10, { Batt_V: 11.6 }), row(11.5, { Batt_V: 11.6 })]),
      testProfile([
        rule({
          all: [{ channelId: "Batt_V", op: "<", value: 11.8 }],
          minDurationSec: 1
        })
      ])
    );

    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ startSec: 10, endSec: 11.5 });
  });

  it("uses stable unique IDs for same-rule windows that start in the same centisecond", () => {
    const events = detectEvents(
      testLog([
        row(1.0041, { RPM: 7000 }),
        row(1.0042, { RPM: 3000 }),
        row(1.0043, { RPM: 7000 })
      ]),
      testProfile([rule({ all: [{ channelId: "RPM", op: ">", value: 6000 }] })])
    );

    expect(events).toHaveLength(2);
    expect(new Set(events.map((event) => event.id)).size).toBe(events.length);
  });

  it("does not match rules without all or any conditions", () => {
    const events = detectEvents(
      testLog([row(0, { RPM: 7000 })]),
      testProfile([rule({ all: undefined, any: undefined })])
    );

    expect(events).toEqual([]);
  });

  it("sorts events by startSec", () => {
    const events = detectEvents(
      testLog([row(0, { Slow: 1, Fast: 0 }), row(1, { Slow: 0, Fast: 1 })]),
      testProfile([
        rule({ id: "later", name: "Later", all: [{ channelId: "Fast", op: "==", value: 1 }] }),
        rule({ id: "earlier", name: "Earlier", all: [{ channelId: "Slow", op: "==", value: 1 }] })
      ])
    );

    expect(events.map((event) => event.ruleId)).toEqual(["earlier", "later"]);
  });

  it("does not match null or missing channel values", () => {
    const events = detectEvents(
      testLog([row(0, { PresentNull: null }), row(1, {})]),
      testProfile([
        rule({
          any: [
            { channelId: "PresentNull", op: "!=", value: 100 },
            { channelId: "Missing", op: "!=", value: 100 }
          ]
        })
      ])
    );

    expect(events).toEqual([]);
  });
});

describe("createManualSegment", () => {
  it("normalizes reversed start and end times", () => {
    expect(createManualSegment("Out lap", 12, 3)).toMatchObject({
      name: "Out lap",
      startSec: 3,
      endSec: 12,
      source: "manual"
    });
  });
});
