import type { RunSummary } from "./summary";
import type { AppliedLog, DetectedEvent, DiagnosticFinding, VehicleProfile } from "./types";

export type ReportHtmlInput = {
  log: AppliedLog;
  profile: VehicleProfile;
  events: DetectedEvent[];
  diagnostics: DiagnosticFinding[];
  summary: RunSummary;
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

export function buildReportHtml({ log, profile, events, diagnostics, summary }: ReportHtmlInput): string {
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
    <section>
      <h2>Summary</h2>
      <table>
        <tbody>
          ${summaryRows(summary)}
        </tbody>
      </table>
    </section>
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
    </section>
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
    </section>
  </main>
</body>
</html>`;
}
