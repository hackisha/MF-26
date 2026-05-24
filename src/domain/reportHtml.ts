import type { RunSummary } from "./summary";
import type { AppliedLog, DetectedEvent, DiagnosticFinding, Segment, VehicleProfile } from "./types";

export type ReportHtmlInput = {
  log: AppliedLog;
  profile: VehicleProfile;
  events: DetectedEvent[];
  diagnostics: DiagnosticFinding[];
  summary: RunSummary;
  segments?: Segment[];
};

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatValue(value: number | null, unit = ""): string {
  if (value === null) return "N/A";
  return `${Number.isInteger(value) ? value.toString() : value.toFixed(2)}${unit}`;
}

function formatTimeRange(startSec: number | undefined, endSec: number | undefined): string {
  if (startSec === undefined && endSec === undefined) return "";
  if (startSec === undefined) return `- ${formatValue(endSec ?? null, " s")}`;
  if (endSec === undefined) return `${formatValue(startSec, " s")} -`;
  return `${formatValue(startSec, " s")} - ${formatValue(endSec, " s")}`;
}

function summaryRows(summary: RunSummary): string {
  const rows: Array<[string, string]> = [
    ["Duration", formatValue(summary.durationSec, " s")],
    ["Max speed", formatValue(summary.maxSpeedKph, " km/h")],
    ["Max RPM", formatValue(summary.maxRpm, " rpm")],
    ["Max corrected G", formatValue(summary.maxCorrectedG, " g")],
    ["Max EOT in", formatValue(summary.maxEotInC, " degC")],
    ["Min oil pressure", formatValue(summary.minOilPressureBar, " bar")],
    ["Warning events", summary.warningEventCount.toString()],
    ["Critical events", summary.criticalEventCount.toString()]
  ];

  return rows.map(([label, value]) => `<tr><th>${escapeHtml(label)}</th><td>${escapeHtml(value)}</td></tr>`).join("");
}

function diagnosticsRows(diagnostics: DiagnosticFinding[]): string {
  if (diagnostics.length === 0) {
    return '<tr><td colspan="6">No diagnostics.</td></tr>';
  }

  return diagnostics
    .map((finding) => {
      const affectedChannels = finding.affectedChannelIds.map((channelId) => escapeHtml(channelId)).join(", ");
      const timeRange = formatTimeRange(finding.startSec, finding.endSec);

      return `<tr><td>${escapeHtml(finding.severity)}</td><td>${escapeHtml(finding.id)}</td><td>${escapeHtml(
        finding.title
      )}</td><td>${escapeHtml(finding.detail)}</td><td>${affectedChannels}</td><td>${escapeHtml(timeRange)}</td></tr>`;
    })
    .join("");
}

function eventRows(events: DetectedEvent[]): string {
  if (events.length === 0) {
    return '<tr><td colspan="7">No events.</td></tr>';
  }

  return events
    .map(
      (event) =>
        `<tr><td>${escapeHtml(event.severity)}</td><td>${escapeHtml(event.id)}</td><td>${escapeHtml(
          event.ruleId
        )}</td><td>${escapeHtml(event.name)}</td><td>${escapeHtml(formatValue(event.startSec, " s"))}</td><td>${escapeHtml(
          formatValue(event.endSec, " s")
        )}</td><td>${escapeHtml(event.description)}</td></tr>`
    )
    .join("");
}

function overlayRows(profile: VehicleProfile): string {
  if (profile.overlays.length === 0) {
    return '<tr><td colspan="4">No overlay presets.</td></tr>';
  }

  return profile.overlays
    .map(
      (overlay) =>
        `<tr><td>${escapeHtml(overlay.name)}</td><td>${escapeHtml(overlay.id)}</td><td>${escapeHtml(
          overlay.channelIds.join(", ")
        )}</td><td>${escapeHtml(overlay.mode)}</td></tr>`
    )
    .join("");
}

function segmentRows(segments: Segment[]): string {
  if (segments.length === 0) {
    return '<tr><td colspan="5">No segments.</td></tr>';
  }

  return segments
    .map(
      (segment) =>
        `<tr><td>${escapeHtml(segment.name)}</td><td>${escapeHtml(segment.source)}</td><td>${escapeHtml(
          formatValue(segment.startSec, " s")
        )}</td><td>${escapeHtml(formatValue(segment.endSec, " s"))}</td><td>${escapeHtml(
          formatValue(Math.max(0, segment.endSec - segment.startSec), " s")
        )}</td></tr>`
    )
    .join("");
}

function finiteCoordinateCount(log: AppliedLog): number {
  let count = 0;

  for (const row of log.rows) {
    const lat = row.values.Latitude;
    const lon = row.values.Longitude;
    if (typeof lat === "number" && Number.isFinite(lat) && typeof lon === "number" && Number.isFinite(lon)) {
      count += 1;
    }
  }

  return count;
}

function sectionEnabled(enabledSections: Set<string>, sectionId: string): boolean {
  return enabledSections.has(sectionId);
}

export function buildReportHtml({ log, profile, events, diagnostics, summary, segments = [] }: ReportHtmlInput): string {
  const enabledSections = new Set(profile.reportSections);
  const sections: string[] = [];

  if (sectionEnabled(enabledSections, "summary")) {
    sections.push(`
    <section>
      <h2>Summary</h2>
      <table>
        <tbody>
          ${summaryRows(summary)}
        </tbody>
      </table>
    </section>`);
  }

  if (sectionEnabled(enabledSections, "diagnostics")) {
    sections.push(`
    <section>
      <h2>Diagnostics</h2>
      <table>
        <thead>
          <tr><th>Severity</th><th>ID</th><th>Title</th><th>Detail</th><th>Channels</th><th>Time</th></tr>
        </thead>
        <tbody>
          ${diagnosticsRows(diagnostics)}
        </tbody>
      </table>
    </section>`);
  }

  if (sectionEnabled(enabledSections, "events")) {
    sections.push(`
    <section>
      <h2>Events</h2>
      <table>
        <thead>
          <tr><th>Severity</th><th>ID</th><th>Rule</th><th>Name</th><th>Start</th><th>End</th><th>Description</th></tr>
        </thead>
        <tbody>
          ${eventRows(events)}
        </tbody>
      </table>
    </section>`);
  }

  if (sectionEnabled(enabledSections, "overlays")) {
    sections.push(`
    <section>
      <h2>Overlay Presets</h2>
      <table>
        <thead>
          <tr><th>Name</th><th>ID</th><th>Channels</th><th>Mode</th></tr>
        </thead>
        <tbody>
          ${overlayRows(profile)}
        </tbody>
      </table>
    </section>`);
  }

  if (sectionEnabled(enabledSections, "behavior")) {
    sections.push(`
    <section>
      <h2>Vehicle Behavior</h2>
      <p>Max corrected G: ${escapeHtml(formatValue(summary.maxCorrectedG, " g"))}</p>
      <p>Roll, pitch, and yaw are behavior tendencies, not drift-corrected precision attitude estimates.</p>
    </section>`);
  }

  if (sectionEnabled(enabledSections, "map")) {
    sections.push(`
    <section>
      <h2>Map / Lap</h2>
      <p>Finite GPS coordinate samples: ${finiteCoordinateCount(log)}</p>
      <p>Offline coordinate-path analysis remains available when map tiles are unavailable.</p>
    </section>`);
  }

  if (sectionEnabled(enabledSections, "segments")) {
    sections.push(`
    <section>
      <h2>Segments</h2>
      <table>
        <thead>
          <tr><th>Name</th><th>Source</th><th>Start</th><th>End</th><th>Duration</th></tr>
        </thead>
        <tbody>
          ${segmentRows(segments)}
        </tbody>
      </table>
    </section>`);
  }

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MF Log Analyzer Report</title>
</head>
<body>
  <main>
    <h1>MF Log Analyzer Report</h1>
    <section>
      <h2>Log</h2>
      <p>File: ${escapeHtml(log.fileName)}</p>
      <p>Profile: ${escapeHtml(profile.name)} (${escapeHtml(profile.revision)})</p>
      <p>Profile ID: ${escapeHtml(log.profileId)} (${escapeHtml(log.profileRevision)})</p>
      <p>Rows: ${log.rows.length}</p>
      <p>ADXL345 correction applied: ax_corrected_g = ax_g / 8, ay_corrected_g = ay_g / 8, az_corrected_g = az_g / 8.</p>
    </section>
    ${sections.join("")}
  </main>
</body>
</html>`;
}
