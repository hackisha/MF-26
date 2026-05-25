import json
import os

from mflog_proto.benchmark.report import export_benchmark_json
from mflog_proto.benchmark.target import TargetBenchmarkOptions, run_target_benchmark


def test_target_benchmark_generates_synthetic_input_and_reports_measured_metrics(tmp_path):
    csv_path = tmp_path / "synthetic.csv"

    report = run_target_benchmark(
        TargetBenchmarkOptions(
            input_path=csv_path,
            rows=64,
            channels=30,
            generate=True,
            include_ui=False,
            graph_channel_count=4,
            playback_updates=12,
            hover_queries=12,
        )
    )

    assert csv_path.exists()
    assert report.input_summary["mode"] == "target-benchmark"
    assert report.input_summary["rows"] == 64
    assert report.input_summary["channels"] == 30
    assert _metric(report, "CSV loading", "elapsed").value >= 0.0
    assert _metric(report, "Mapping", "elapsed").value >= 0.0
    assert _metric(report, "Derived channels", "elapsed").value >= 0.0
    assert _metric(report, "Health checks", "elapsed").value >= 0.0
    assert _metric(report, "Graph cache", "elapsed").value >= 0.0
    assert _metric(report, "Playback cursor", "update_rate").value > 0.0
    assert _metric(report, "Hover latency", "p95").value >= 0.0
    assert _metric(report, "Memory", "rss").value > 0.0


def test_target_benchmark_exports_strict_json_without_pending_measurements(tmp_path):
    report = run_target_benchmark(
        TargetBenchmarkOptions(
            input_path=tmp_path / "synthetic.csv",
            rows=16,
            channels=25,
            generate=True,
            include_ui=False,
            graph_channel_count=2,
            playback_updates=4,
            hover_queries=4,
        )
    )
    json_path = tmp_path / "target-report.json"

    export_benchmark_json(json_path, report)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    categories = {metric["category"] for metric in data["metrics"]}
    assert "CSV loading" in categories
    assert "Workspace restore" not in categories
    assert all(metric["value"] is not None for metric in data["metrics"])


def test_target_benchmark_can_include_minimal_ui_metrics(tmp_path):
    report = run_target_benchmark(
        TargetBenchmarkOptions(
            input_path=tmp_path / "synthetic.csv",
            rows=12,
            channels=25,
            generate=True,
            include_ui=True,
            graph_channel_count=2,
            playback_updates=4,
            hover_queries=4,
        )
    )

    categories = {metric.category for metric in report.metrics}
    assert "First plot" in categories
    assert "Workspace restore" in categories
    assert "Open-window impact" in categories


def test_target_benchmark_forces_minimal_qt_platform_for_ui_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    run_target_benchmark(
        TargetBenchmarkOptions(
            input_path=tmp_path / "synthetic.csv",
            rows=12,
            channels=25,
            generate=True,
            include_ui=True,
            graph_channel_count=2,
            playback_updates=4,
            hover_queries=4,
        )
    )

    assert os.environ["QT_QPA_PLATFORM"] == "minimal"


def test_target_benchmark_with_defects_still_exports_ui_report(tmp_path):
    report = run_target_benchmark(
        TargetBenchmarkOptions(
            input_path=tmp_path / "synthetic-defects.csv",
            rows=16,
            channels=25,
            generate=True,
            defects=True,
            include_ui=True,
            graph_channel_count=2,
            playback_updates=4,
            hover_queries=4,
        )
    )

    health_metric = _metric(report, "Health checks", "elapsed")
    assert "timestamp_duplicate=1" in health_metric.details
    assert "timestamp_backward=1" in health_metric.details
    assert "First plot" in {metric.category for metric in report.metrics}


def _metric(report, category: str, name: str):
    return next(
        metric
        for metric in report.metrics
        if metric.category == category and metric.name == name
    )
