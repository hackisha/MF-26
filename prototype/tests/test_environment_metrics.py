from mflog_proto.benchmark.metrics import collect_environment
from mflog_proto.benchmark.runner import build_environment_report, main
import json
import math


def test_collect_environment_reports_dependency_presence():
    env = collect_environment()

    assert env.python_version
    assert env.platform
    assert env.dependencies["pytest"].available is True
    assert "polars" in env.dependencies
    assert "PySide6" in env.dependencies
    assert "pyqtgraph" in env.dependencies


def test_environment_serializes_to_plain_dict():
    env = collect_environment()

    data = env.to_dict()

    assert data["python_version"] == env.python_version
    assert isinstance(data["dependencies"]["numpy"]["available"], bool)


def test_benchmark_runner_builds_environment_report():
    report = build_environment_report()

    assert report.environment.python_version
    assert report.input_summary["mode"] == "prototype-readiness"
    assert report.input_summary["target_rows"] == 300000
    assert report.input_summary["target_channels"] == 200
    assert any(metric.name == "dependency_available" for metric in report.metrics)
    categories = {metric.category for metric in report.metrics}
    assert "CSV loading" in categories
    assert "Graph cache" in categories
    assert "Playback cursor" in categories
    csv_metric = next(metric for metric in report.metrics if metric.category == "CSV loading")
    assert math.isnan(csv_metric.value)
    assert csv_metric.passed is False
    assert report.hotspots


def test_benchmark_runner_preserves_legacy_environment_stdout(capsys):
    assert main([]) == 0

    data = json.loads(capsys.readouterr().out)

    assert "python_version" in data
    assert "dependencies" in data
    assert "environment" not in data
