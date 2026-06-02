"""HTML report rendering for MF-LOG-ANALYZER sessions."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Mapping, Sequence

from mflog_proto.analysis.event_reviews import EventReview
from mflog_proto.analysis.segments import SegmentSummary


def render_html_report(
    *,
    session: Mapping[str, object],
    selected_channels: Sequence[str],
    event_reviews: Sequence[EventReview],
    segment_summaries: Sequence[SegmentSummary],
    generated_at: str,
) -> str:
    return "\n".join(
        (
            "<!doctype html>",
            '<html lang="ko">',
            "<head>",
            '<meta charset="utf-8">',
            "<title>MF-LOG-ANALYZER v2 Report</title>",
            _style_block(),
            "</head>",
            "<body>",
            "<h1>MF-LOG-ANALYZER v2 Report</h1>",
            f"<p>Generated at {escape(generated_at)}</p>",
            "<h2>Session</h2>",
            _session_table(session),
            "<h2>Selected Channels</h2>",
            _list_block(selected_channels),
            "<h2>Event Review</h2>",
            _event_table(event_reviews),
            "<h2>Segments</h2>",
            _segment_table(segment_summaries),
            "</body>",
            "</html>",
        )
    )


def write_html_report(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def _style_block() -> str:
    return """
<style>
body { font-family: "Malgun Gothic", "Segoe UI", sans-serif; margin: 32px; color: #1b2329; }
h1 { margin-bottom: 0.2rem; }
h2 { margin-top: 2rem; border-bottom: 1px solid #ccd5dd; padding-bottom: 0.3rem; }
table { border-collapse: collapse; width: 100%; margin-top: 0.6rem; }
th, td { border: 1px solid #ccd5dd; padding: 0.45rem 0.55rem; text-align: left; }
th { background: #eef3f6; }
.empty { color: #66727b; }
</style>
"""


def _session_table(session: Mapping[str, object]) -> str:
    rows = [
        ("File", session.get("file_name", "-")),
        ("Rows", session.get("row_count", "-")),
        ("Duration", f"{float(session.get('duration_seconds', 0.0)):.3f} s"),
        ("Sample", f"{int(session.get('sample_ms', 0))} ms"),
        ("Events", session.get("event_count", "-")),
    ]
    body = "".join(
        f"<tr><th>{escape(label)}</th><td>{escape(str(value))}</td></tr>"
        for label, value in rows
    )
    return f"<table>{body}</table>"


def _list_block(values: Sequence[str]) -> str:
    if not values:
        return '<p class="empty">-</p>'
    items = "".join(f"<li>{escape(value)}</li>" for value in values)
    return f"<ul>{items}</ul>"


def _event_table(event_reviews: Sequence[EventReview]) -> str:
    if not event_reviews:
        return '<p class="empty">No events.</p>'
    rows = "".join(
        "<tr>"
        f"<td>{review.time_ms / 1000.0:.3f} s</td>"
        f"<td>{escape(review.severity)}</td>"
        f"<td>{escape(review.name)}</td>"
        f"<td>{escape(review.sensor)}</td>"
        f"<td>{review.value:g}</td>"
        f"<td>{escape(review.condition)}</td>"
        f"<td>{escape(review.state.value)}</td>"
        f"<td>{escape(review.note)}</td>"
        "</tr>"
        for review in event_reviews
    )
    return (
        "<table><thead><tr>"
        "<th>Time</th><th>Severity</th><th>Name</th><th>Sensor</th>"
        "<th>Value</th><th>Condition</th><th>State</th><th>Note</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def _segment_table(segment_summaries: Sequence[SegmentSummary]) -> str:
    if not segment_summaries:
        return '<p class="empty">No segments.</p>'
    rows = "".join(
        "<tr>"
        f"<td>{escape(summary.name)}</td>"
        f"<td>{summary.start_ms / 1000.0:.3f} s</td>"
        f"<td>{summary.end_ms / 1000.0:.3f} s</td>"
        f"<td>{summary.row_count}</td>"
        f"<td>{_fmt(summary.average_speed)}</td>"
        f"<td>{_fmt(summary.max_speed)}</td>"
        f"<td>{_fmt(summary.min_rpm)}</td>"
        f"<td>{_fmt(summary.max_rpm)}</td>"
        f"<td>{_fmt(summary.average_tps)}</td>"
        f"<td>{_fmt(summary.max_abs_ax)}</td>"
        f"<td>{_fmt(summary.max_abs_ay)}</td>"
        f"<td>{_fmt(summary.min_battery_voltage)}</td>"
        "</tr>"
        for summary in segment_summaries
    )
    return (
        "<table><thead><tr>"
        "<th>Name</th><th>Start</th><th>End</th><th>Rows</th>"
        "<th>Avg Speed</th><th>Max Speed</th><th>Min RPM</th><th>Max RPM</th>"
        "<th>Avg TPS</th><th>Max |ax|</th><th>Max |ay|</th><th>Min Batt</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"
