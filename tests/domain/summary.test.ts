import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parseCsv } from "../../src/domain/csvImport";
import { defaultProfiles } from "../../src/domain/defaultProfiles";
import { runDiagnostics } from "../../src/domain/diagnostics";
import { detectEvents } from "../../src/domain/events";
import { applyProfile } from "../../src/domain/profileApply";
import { buildReportHtml } from "../../src/domain/reportHtml";
import { summarizeLog } from "../../src/domain/summary";
import type { AppliedLog, DetectedEvent, DiagnosticFinding, VehicleProfile } from "../../src/domain/types";

const profile2025 = defaultProfiles[0];

function loadAppliedLog(): AppliedLog {
  const csv = fs.readFileSync(path.join(process.cwd(), "tests/fixtures/2025-sample.csv"), "utf8");
  return applyProfile("2025-sample.csv", parseCsv(csv), profile2025);
}

function testLog(rows: AppliedLog["rows"], fileName = "test.csv"): AppliedLog {
  return {
    fileName,
    profileId: "test-profile",
    profileRevision: "test",
    rawHeaders: [],
    rows
  };
}

function row(index: number, timestampSec: number, values: Record<string, number | null>): AppliedLog["rows"][number] {
  return {
    index,
    timestampSec,
    values
  };
}

function testProfile(overrides: Partial<VehicleProfile> = {}): VehicleProfile {
  return {
    id: "test-profile",
    name: "Test Profile",
    revision: "test",
    channels: {},
    rules: [],
    overlays: [],
    reportSections: [],
    ...overrides
  };
}

describe("summarizeLog", () => {
  it("summarizes the 2025 sample fixture", () => {
    const log = loadAppliedLog();
    const events = detectEvents(log, profile2025);
    const summary = summarizeLog(log, events);

    expect(summary.maxSpeedKph).toBe(40);
    expect(summary.maxRpm).toBe(7000);
    expect(summary.criticalEventCount).toBeGreaterThan(0);
    expect(summary.durationSec).toBe(1.5);
    expect(summary.minOilPressureBar).toBe(2);
    expect(summary.maxCorrectedG).toBeCloseTo(1.3);
  });

  it("uses the largest absolute corrected G magnitude even when it is negative", () => {
    const summary = summarizeLog(
      testLog([
        row(0, 0, { ax_corrected_g: 0.8, ay_corrected_g: 0.4 }),
        row(1, 1, { ax_corrected_g: -1.6, ay_corrected_g: 1.2 })
      ]),
      []
    );

    expect(summary.maxCorrectedG).toBe(1.6);
  });

  it("scans large logs without spreading channel values into function arguments", () => {
    const rows = Array.from({ length: 150_000 }, (_, index) =>
      row(index, index * 0.1, {
        GPS_Speed_KPH: index === 149_999 ? 88 : 40,
        VSS_kmh: 99,
        RPM: index === 149_999 ? 8100 : 3000,
        OilPressure_bar: index === 149_999 ? 1.9 : 4.2,
        EOT_IN: index === 149_999 ? 112 : 80,
        EOT_OUT: 100,
        ax_corrected_g: index === 149_999 ? -2.4 : 0.1,
        ay_corrected_g: 0.2
      })
    );

    const summary = summarizeLog(testLog(rows, "large.csv"), [
      {
        id: "large-critical",
        ruleId: "large-critical",
        name: "Large Critical",
        severity: "critical",
        startSec: 0,
        endSec: 1,
        description: "large log event"
      }
    ]);

    expect(summary.maxSpeedKph).toBe(88);
    expect(summary.maxRpm).toBe(8100);
    expect(summary.minOilPressureBar).toBe(1.9);
    expect(summary.maxEotInC).toBe(112);
    expect(summary.maxCorrectedG).toBe(2.4);
    expect(summary.criticalEventCount).toBe(1);
  });
});

describe("buildReportHtml", () => {
  it("builds a report with summary, correction note, diagnostics, and events", () => {
    const log = loadAppliedLog();
    const events = detectEvents(log, profile2025);
    const diagnostics = runDiagnostics(log, profile2025);
    const summary = summarizeLog(log, events);

    const html = buildReportHtml({
      log,
      profile: profile2025,
      events,
      diagnostics,
      summary
    });

    expect(html).toContain("MF Log Analyzer Report");
    expect(html).toContain(
      "ADXL345 correction applied: ax_corrected_g = ax_g / 8, ay_corrected_g = ay_g / 8, az_corrected_g = az_g / 8."
    );
    expect(html).toContain("2025-sample.csv");
    expect(html).toContain("2025 Vehicle");
    expect(html).toContain("High RPM Oil Pressure Drop");
    expect(html).toContain("Low battery voltage");
  });

  it("escapes file, profile, event, and diagnostic text", () => {
    const log = testLog([], `bad <file> "one" & 'two'.csv`);
    const profile = testProfile({
      name: `Profile <fast> "quoted" & 'single'`,
      revision: `rev <1> & "x"`
    });
    const events: DetectedEvent[] = [
      {
        id: `event-<id>&"`,
        ruleId: `rule-<id>&"`,
        name: `Event <name> & "quoted" 'single'`,
        severity: "warning",
        startSec: 1,
        endSec: 2,
        description: `Description <script> & "quoted" 'single'`
      }
    ];
    const diagnostics: DiagnosticFinding[] = [
      {
        id: `diag-<id>&"`,
        severity: "critical",
        title: `Diagnostic <title> & "quoted" 'single'`,
        detail: `Detail <b>bad</b> & "quoted" 'single'`,
        affectedChannelIds: [`RPM<&"`, `OilPressure_bar'`],
        startSec: 3,
        endSec: 4
      }
    ];

    const html = buildReportHtml({
      log,
      profile,
      events,
      diagnostics,
      summary: summarizeLog(log, events)
    });

    expect(html).toContain("bad &lt;file&gt; &quot;one&quot; &amp; &#39;two&#39;.csv");
    expect(html).toContain("Profile &lt;fast&gt; &quot;quoted&quot; &amp; &#39;single&#39;");
    expect(html).toContain("Event &lt;name&gt; &amp; &quot;quoted&quot; &#39;single&#39;");
    expect(html).toContain("Description &lt;script&gt; &amp; &quot;quoted&quot; &#39;single&#39;");
    expect(html).toContain("Diagnostic &lt;title&gt; &amp; &quot;quoted&quot; &#39;single&#39;");
    expect(html).toContain("Detail &lt;b&gt;bad&lt;/b&gt; &amp; &quot;quoted&quot; &#39;single&#39;");
    expect(html).toContain("RPM&lt;&amp;&quot;, OilPressure_bar&#39;");
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<b>bad</b>");
  });
});
