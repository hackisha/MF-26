import json
import math

from mflog_proto.benchmark.metrics import DependencyInfo, EnvironmentInfo
from mflog_proto.benchmark.report import (
    BenchmarkMetric,
    BenchmarkReport,
    export_benchmark_html,
    export_benchmark_json,
)


def _environment() -> EnvironmentInfo:
    return EnvironmentInfo(
        python_version="3.12.6",
        platform="Windows-test",
        machine="AMD64",
        processor="CPU",
        dependencies={"polars": DependencyInfo("polars", True, "1.41.0")},
    )


def test_benchmark_metric_evaluates_gate_status():
    metric = BenchmarkMetric(
        name="csv_load_time",
        value=12.5,
        unit="s",
        gate_max=15.0,
        category="CSV loading",
    )

    assert metric.passed is True
    assert metric.to_dict()["passed"] is True


def test_benchmark_metric_rejects_non_finite_values_and_exports_strict_json(tmp_path):
    report = BenchmarkReport(
        environment=_environment(),
        input_summary={"rows": 300000, "channels": 200},
        metrics=(
            BenchmarkMetric(
                "hover_latency_p95",
                math.nan,
                "ms",
                gate_max=80.0,
                details="Run target-scale benchmark to populate this metric.",
            ),
        ),
    )
    json_path = tmp_path / "benchmark.json"
    html_path = tmp_path / "benchmark.html"

    export_benchmark_json(json_path, report)
    export_benchmark_html(html_path, report)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["metrics"][0]["value"] is None
    assert data["metrics"][0]["passed"] is False
    assert data["passed"] is False

    html = html_path.read_text(encoding="utf-8")
    assert "pending" in html.lower()
    assert "Run target-scale benchmark to populate this metric." in html
    assert "&gt;= 1 n/a" not in html


def test_benchmark_report_exports_json_and_html(tmp_path):
    report = BenchmarkReport(
        environment=_environment(),
        input_summary={"rows": 300000, "channels": 200},
        metrics=(
            BenchmarkMetric("csv_load_time", 12.5, "s", gate_max=15.0, category="CSV loading"),
            BenchmarkMetric("memory_rss", 3.0, "GB", gate_max=2.5, category="Memory"),
        ),
        hotspots=("csv_loader: polars.read_csv",),
        recommendation="Optimize memory before production.",
    )

    json_path = tmp_path / "benchmark.json"
    html_path = tmp_path / "benchmark.html"
    export_benchmark_json(json_path, report)
    export_benchmark_html(html_path, report)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["input_summary"] == {"rows": 300000, "channels": 200}
    assert data["metrics"][0]["passed"] is True
    assert data["metrics"][1]["passed"] is False

    html = html_path.read_text(encoding="utf-8")
    assert "MF-LOG-ANALYZER v2 Benchmark Report" in html
    assert "csv_load_time" in html
    assert "FAIL" in html
    assert "Optimize memory before production." in html
