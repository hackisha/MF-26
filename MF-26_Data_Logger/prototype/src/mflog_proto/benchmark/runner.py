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
from mflog_proto.benchmark.target import TargetBenchmarkOptions, run_target_benchmark


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
    missing_dependencies = [
        name for name, dependency in environment.dependencies.items() if not dependency.available
    ]
    recommendation = (
        "Install missing dependencies before full 300k x 200 validation: "
        + ", ".join(missing_dependencies)
        if missing_dependencies
        else "Run --target-benchmark to populate measured 300k x 200 performance gates."
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
        recommendation=recommendation,
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
    parser.add_argument(
        "--target-benchmark",
        action="store_true",
        help="Run measured synthetic/CSV target benchmark instead of readiness metadata.",
    )
    parser.add_argument("--input", type=Path, default=Path(".generated/synthetic_300k_200.csv"))
    parser.add_argument("--rows", type=int, default=300_000)
    parser.add_argument("--channels", type=int, default=200)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--defects", action="store_true")
    parser.add_argument("--no-ui", action="store_true")
    parser.add_argument("--graph-channel-count", type=int, default=20)
    parser.add_argument("--graph-pixel-width", type=int, default=1_200)
    parser.add_argument("--playback-updates", type=int, default=900)
    parser.add_argument("--hover-queries", type=int, default=1_000)
    args = parser.parse_args(argv)

    report = _build_report_from_args(args)
    if args.json_output is not None:
        export_benchmark_json(args.json_output, report)
    if args.html_output is not None:
        export_benchmark_html(args.html_output, report)

    stdout_data = report.to_dict() if args.json_output or args.html_output else report.environment.to_dict()
    print(json.dumps(stdout_data, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


def _build_report_from_args(args: argparse.Namespace) -> BenchmarkReport:
    if not args.target_benchmark:
        return build_environment_report()
    return run_target_benchmark(
        TargetBenchmarkOptions(
            input_path=args.input,
            rows=args.rows,
            channels=args.channels,
            generate=args.generate,
            defects=args.defects,
            include_ui=not args.no_ui,
            graph_channel_count=args.graph_channel_count,
            graph_pixel_width=args.graph_pixel_width,
            playback_updates=args.playback_updates,
            hover_queries=args.hover_queries,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
