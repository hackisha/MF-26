"""Benchmark command-line entry point."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Sequence

from mflog_proto.benchmark.metrics import collect_environment
from mflog_proto.benchmark.report import (
    BenchmarkMetric,
    BenchmarkReport,
    export_benchmark_html,
    export_benchmark_json,
)


def build_environment_report() -> BenchmarkReport:
    environment = collect_environment()
    dependency_metrics = tuple(
        BenchmarkMetric(
            name="dependency_available",
            value=1.0 if dependency.available else 0.0,
            unit="bool",
            gate_min=1.0,
            category="Dependencies",
            details=f"{name} {dependency.version or 'missing'}",
        )
        for name, dependency in environment.dependencies.items()
    )
    readiness_metrics = (
        _unmeasured_metric("CSV loading"),
        _unmeasured_metric("Mapping"),
        _unmeasured_metric("Derived channels"),
        _unmeasured_metric("Health checks"),
        _unmeasured_metric("Graph cache"),
        _unmeasured_metric("First plot"),
        _unmeasured_metric("Playback cursor"),
        _unmeasured_metric("Hover latency"),
        _unmeasured_metric("Memory"),
        _unmeasured_metric("Workspace restore"),
    )
    return BenchmarkReport(
        environment=environment,
        input_summary={
            "mode": "prototype-readiness",
            "target_rows": 300000,
            "target_channels": 200,
            "scenario": "environment and benchmark category readiness",
        },
        metrics=dependency_metrics + readiness_metrics,
        hotspots=("Profiling not yet run for target workload.",),
        recommendation="Install missing dependencies before full 300k x 200 validation.",
    )


def _unmeasured_metric(category: str) -> BenchmarkMetric:
    return BenchmarkMetric(
        name="measurement_pending",
        value=math.nan,
        unit="n/a",
        gate_min=1.0,
        category=category,
        details="Run target-scale benchmark to populate this metric.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export MF-LOG-ANALYZER prototype benchmarks.")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--html-output", type=Path)
    args = parser.parse_args(argv)

    report = build_environment_report()
    if args.json_output is not None:
        export_benchmark_json(args.json_output, report)
    if args.html_output is not None:
        export_benchmark_html(args.html_output, report)

    stdout_data = report.to_dict() if args.json_output or args.html_output else report.environment.to_dict()
    print(json.dumps(stdout_data, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
