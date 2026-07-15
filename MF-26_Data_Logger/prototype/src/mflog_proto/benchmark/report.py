"""Benchmark report model and exporters."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json
import math
from pathlib import Path
from typing import Any

from mflog_proto.benchmark.metrics import EnvironmentInfo


@dataclass(frozen=True)
class BenchmarkMetric:
    name: str
    value: float
    unit: str
    gate_max: float | None = None
    gate_min: float | None = None
    category: str = "General"
    details: str = ""

    @property
    def passed(self) -> bool:
        if not math.isfinite(self.value):
            return False
        if self.gate_min is not None and self.value < self.gate_min:
            return False
        if self.gate_max is not None and self.value > self.gate_max:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        value: float | None = self.value if math.isfinite(self.value) else None
        return {
            "name": self.name,
            "category": self.category,
            "value": value,
            "unit": self.unit,
            "gate_min": self.gate_min,
            "gate_max": self.gate_max,
            "passed": self.passed,
            "details": self.details,
        }


@dataclass(frozen=True)
class BenchmarkReport:
    environment: EnvironmentInfo
    input_summary: dict[str, Any]
    metrics: tuple[BenchmarkMetric, ...]
    hotspots: tuple[str, ...] = ()
    recommendation: str = "Candidate stack remains under evaluation."

    @property
    def passed(self) -> bool:
        return all(metric.passed for metric in self.metrics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment.to_dict(),
            "input_summary": dict(self.input_summary),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "hotspots": list(self.hotspots),
            "recommendation": self.recommendation,
            "passed": self.passed,
        }


def export_benchmark_json(path: Path, report: BenchmarkReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


def export_benchmark_html(path: Path, report: BenchmarkReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(_metric_row(metric) for metric in report.metrics)
    hotspots = "\n".join(f"<li>{escape(item)}</li>" for item in report.hotspots)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MF-LOG-ANALYZER v2 Benchmark Report</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #1f2428; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
    th, td {{ border: 1px solid #ccd3d8; padding: 8px; text-align: left; }}
    th {{ background: #eef2f5; }}
    .pass {{ color: #1f7a3f; font-weight: 700; }}
    .fail {{ color: #a12828; font-weight: 700; }}
    .pending {{ color: #8a5a00; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>MF-LOG-ANALYZER v2 Benchmark Report</h1>
  <p>Python {escape(report.environment.python_version)} | {escape(report.environment.platform)}
     | {escape(report.environment.machine)}</p>
  <h2>Input</h2>
  <pre>{escape(json.dumps(report.input_summary, ensure_ascii=False, indent=2))}</pre>
  <h2>Metrics</h2>
  <table>
    <thead>
      <tr>
        <th>Category</th><th>Name</th><th>Value</th><th>Gate</th><th>Status</th><th>Details</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
  <h2>Hotspots</h2>
  <ul>{hotspots}</ul>
  <h2>Recommendation</h2>
  <p>{escape(report.recommendation)}</p>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _metric_row(metric: BenchmarkMetric) -> str:
    status, status_class = _metric_status(metric)
    return (
        "<tr>"
        f"<td>{escape(metric.category)}</td>"
        f"<td>{escape(metric.name)}</td>"
        f"<td>{_metric_value_text(metric)}</td>"
        f"<td>{escape(_metric_gate_text(metric))}</td>"
        f"<td class=\"{status_class}\">{status}</td>"
        f"<td>{escape(metric.details) if metric.details else '-'}</td>"
        "</tr>"
    )


def _metric_gate_text(metric: BenchmarkMetric) -> str:
    gate_parts: list[str] = []
    if metric.gate_min is not None:
        gate_parts.append(f">= {metric.gate_min:g}")
    if metric.gate_max is not None:
        gate_parts.append(f"<= {metric.gate_max:g}")
    gate = " and ".join(gate_parts)
    unit = "" if metric.unit == "n/a" else f" {metric.unit}"

    if not math.isfinite(metric.value):
        return f"pending ({gate}{unit})" if gate else "pending"
    return f"{gate}{unit}" if gate else "-"


def _metric_status(metric: BenchmarkMetric) -> tuple[str, str]:
    if not math.isfinite(metric.value):
        return "PENDING", "pending"
    if metric.passed:
        return "PASS", "pass"
    return "FAIL", "fail"


def _metric_value_text(metric: BenchmarkMetric) -> str:
    if not math.isfinite(metric.value):
        return "n/a"
    return f"{metric.value:g} {escape(metric.unit)}"
