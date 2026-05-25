"""Measured target-scale benchmark scenario for the prototype."""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import statistics
import time
from typing import Any

import polars as pl
import psutil

from mflog_proto.benchmark.metrics import collect_environment
from mflog_proto.benchmark.report import BenchmarkMetric, BenchmarkReport
from mflog_proto.data.channel_mapping import MappingState, map_columns
from mflog_proto.data.downsample import DownsampledSeries, min_max_bucket_arrays
from mflog_proto.data.synthetic_log import SyntheticCsvSummary, write_synthetic_csv
from mflog_proto.persistence.project_state import ProjectState, WindowState
from mflog_proto.playback import PlaybackState


@dataclass(frozen=True)
class TargetBenchmarkOptions:
    input_path: Path
    rows: int = 300_000
    channels: int = 200
    generate: bool = False
    defects: bool = False
    include_ui: bool = True
    graph_channel_count: int = 20
    graph_pixel_width: int = 1_200
    playback_updates: int = 900
    hover_queries: int = 1_000


@dataclass(frozen=True)
class TimedValue:
    value: Any
    elapsed_seconds: float


def run_target_benchmark(options: TargetBenchmarkOptions) -> BenchmarkReport:
    process = psutil.Process()
    start_rss_gb = _rss_gb(process)
    generated_summary = _generate_input_if_requested(options)

    loaded = _timed(lambda: _read_csv(options.input_path))
    frame: pl.DataFrame = loaded.value
    mapping = _timed(lambda: map_columns(frame.columns))
    derived = _timed(lambda: _compute_derived_frame(frame))
    health = _timed(lambda: _health_summary(frame))
    graph = _timed(lambda: _build_graph_cache(frame, options))
    playback = _timed(lambda: _measure_playback(graph.value.x_values, options.playback_updates))
    hover = _measure_hover_latency(graph.value.x_values, options.hover_queries)

    metrics = [
        BenchmarkMetric(
            name="elapsed",
            value=loaded.elapsed_seconds,
            unit="s",
            gate_max=15.0,
            category="CSV loading",
            details=f"polars.read_csv shape={frame.height}x{frame.width}",
        ),
        BenchmarkMetric(
            name="elapsed",
            value=mapping.elapsed_seconds,
            unit="s",
            gate_max=5.0,
            category="Mapping",
            details=_mapping_details(mapping.value),
        ),
        BenchmarkMetric(
            name="elapsed",
            value=derived.elapsed_seconds,
            unit="s",
            gate_max=5.0,
            category="Derived channels",
            details=f"{derived.value.width} derived columns",
        ),
        BenchmarkMetric(
            name="elapsed",
            value=health.elapsed_seconds,
            unit="s",
            gate_max=5.0,
            category="Health checks",
            details=_health_details(health.value),
        ),
        BenchmarkMetric(
            name="elapsed",
            value=graph.elapsed_seconds,
            unit="s",
            gate_max=5.0,
            category="Graph cache",
            details=(
                f"{len(graph.value.series)} channels, "
                f"{options.graph_pixel_width} px target"
            ),
        ),
        BenchmarkMetric(
            name="update_rate",
            value=playback.value,
            unit="Hz",
            gate_min=30.0,
            category="Playback cursor",
            details=f"{options.playback_updates} cursor updates",
        ),
        BenchmarkMetric(
            name="p95",
            value=hover,
            unit="ms",
            gate_max=80.0,
            category="Hover latency",
            details=f"{options.hover_queries} nearest-sample lookups",
        ),
    ]

    if options.include_ui:
        metrics.extend(_measure_ui_metrics(graph.value))

    peak_rss_gb = max(start_rss_gb, _rss_gb(process))
    metrics.append(
        BenchmarkMetric(
            name="rss",
            value=peak_rss_gb,
            unit="GB",
            gate_max=2.5,
            category="Memory",
            details="Resident set size after benchmark run.",
        )
    )

    report = BenchmarkReport(
        environment=collect_environment(),
        input_summary=_input_summary(options, frame, generated_summary),
        metrics=tuple(metrics),
        hotspots=_hotspots(metrics),
        recommendation=_recommendation(metrics),
    )
    return report


@dataclass(frozen=True)
class GraphBenchmarkData:
    x_values: list[float]
    series: dict[str, DownsampledSeries]


def _generate_input_if_requested(
    options: TargetBenchmarkOptions,
) -> SyntheticCsvSummary | None:
    if not options.generate:
        if not options.input_path.exists():
            raise FileNotFoundError(options.input_path)
        return None
    return write_synthetic_csv(
        path=options.input_path,
        rows=options.rows,
        channels=options.channels,
        defects=options.defects,
    )


def _read_csv(path: Path) -> pl.DataFrame:
    return pl.read_csv(
        path,
        ignore_errors=True,
        infer_schema_length=1_000,
        null_values=[""],
        try_parse_dates=False,
    )


def _compute_derived_frame(frame: pl.DataFrame) -> pl.DataFrame:
    expressions: list[pl.Expr] = []
    if "ax_g" in frame.columns:
        expressions.append((_numeric_col("ax_g") / 8.0).alias("AX_CORRECTED_G"))
    if "ay_g" in frame.columns:
        expressions.append((_numeric_col("ay_g") / 8.0).alias("AY_CORRECTED_G"))
    if "az_g" in frame.columns:
        expressions.append((_numeric_col("az_g") / 8.0).alias("AZ_CORRECTED_G"))
    if "EOT_OUT" in frame.columns and "OilTemp_C" in frame.columns:
        expressions.append((_numeric_col("EOT_OUT") - _numeric_col("OilTemp_C")).alias("EOT_DELTA"))
    if "DBW_Target_percent" in frame.columns and "DBW_Pos_percent" in frame.columns:
        expressions.append(
            (_numeric_col("DBW_Target_percent") - _numeric_col("DBW_Pos_percent")).alias(
                "DBW_ERROR"
            )
        )
    return frame.select(expressions) if expressions else pl.DataFrame()


def _health_summary(frame: pl.DataFrame) -> dict[str, int | float]:
    timestamp_issues = _timestamp_issue_counts(frame)
    numeric_nulls = frame.select(pl.all().cast(pl.Float64, strict=False).null_count())
    null_count = int(sum(numeric_nulls.row(0))) if numeric_nulls.width else 0
    low_voltage_count = _count_where(frame, "Batt_V", lambda col: col < 10.0)
    dbw_error_count = 0
    if "DBW_Target_percent" in frame.columns and "DBW_Pos_percent" in frame.columns:
        dbw_error_count = int(
            frame.select(
                (
                    (_numeric_col("DBW_Target_percent") - _numeric_col("DBW_Pos_percent")).abs()
                    > 10.0
                )
                .sum()
                .alias("count")
            ).item()
            or 0
        )
    return {
        **timestamp_issues,
        "numeric_nulls": null_count,
        "low_voltage": low_voltage_count,
        "dbw_error": dbw_error_count,
    }


def _build_graph_cache(frame: pl.DataFrame, options: TargetBenchmarkOptions) -> GraphBenchmarkData:
    x_array = _x_array(frame)
    series: dict[str, DownsampledSeries] = {}
    for channel in _graph_channels(frame.columns, options.graph_channel_count):
        y_array = _numeric_array(frame.get_column(channel))
        series[channel] = min_max_bucket_arrays(
            x_array,
            y_array,
            max_points=options.graph_pixel_width,
        )
    return GraphBenchmarkData(x_values=x_array.tolist(), series=series)


def _measure_playback(x_values: list[float], updates: int) -> float:
    if not x_values or updates <= 0:
        return 0.0
    playback = PlaybackState(_sorted_unique_or_index_time(x_values))
    elapsed = _timed(
        lambda: [
            playback.set_sample(index * max(1, len(x_values) // updates))
            for index in range(updates)
        ]
    ).elapsed_seconds
    return updates / elapsed if elapsed > 0 else math.inf


def _measure_hover_latency(x_values: list[float], queries: int) -> float:
    if not x_values or queries <= 0:
        return 0.0
    timestamps = _sorted_unique_or_index_time(x_values)
    playback = PlaybackState(timestamps)
    max_seconds = timestamps[-1]
    latencies: list[float] = []
    for query_index in range(queries):
        seconds = max_seconds * query_index / max(1, queries - 1)
        started = time.perf_counter()
        playback.sample_at_seconds(seconds)
        latencies.append((time.perf_counter() - started) * 1_000.0)
    return _percentile(latencies, 95)


def _measure_ui_metrics(graph_data: GraphBenchmarkData) -> list[BenchmarkMetric]:
    os.environ["QT_QPA_PLATFORM"] = "minimal"
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

    from PySide6 import QtWidgets

    from mflog_proto.ui.main_window import MainWindow
    from mflog_proto.ui.time_series_window import TimeSeriesWindow

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    playback = PlaybackState(_sorted_unique_or_index_time(graph_data.x_values))
    plot_series = {
        channel: (downsampled.x, downsampled.y)
        for channel, downsampled in list(graph_data.series.items())[:10]
    }

    first_plot = _timed(
        lambda: _show_time_series_once(app, TimeSeriesWindow(playback), plot_series)
    )
    workspace_restore = _timed(lambda: _restore_workspace_once(app))
    open_window_update = _timed(lambda: _update_multi_window_workspace_once(app))

    return [
        BenchmarkMetric(
            name="elapsed",
            value=first_plot.elapsed_seconds,
            unit="s",
            gate_max=1.5,
            category="First plot",
            details=f"{len(plot_series)} downsampled channels",
        ),
        BenchmarkMetric(
            name="elapsed",
            value=workspace_restore.elapsed_seconds,
            unit="s",
            gate_max=2.0,
            category="Workspace restore",
            details="Restore saved MDI layout after data is available.",
        ),
        BenchmarkMetric(
            name="elapsed",
            value=open_window_update.elapsed_seconds,
            unit="s",
            gate_max=2.0,
            category="Open-window impact",
            details="8 time-series windows plus G-G and current-values update smoke.",
        ),
    ]


def _show_time_series_once(
    app: Any,
    window: Any,
    plot_series: dict[str, tuple[list[float], list[float | None]]],
) -> None:
    window.set_series(plot_series)
    window.resize(960, 540)
    window.show()
    app.processEvents()
    window.close()
    app.processEvents()


def _restore_workspace_once(app: Any) -> None:
    from mflog_proto.ui.main_window import MainWindow

    window = MainWindow()
    state = ProjectState(
        open_windows=(
            WindowState("Time-Series Graph", x=0, y=0, width=460, height=260),
            WindowState("G-G Diagram", x=40, y=40, width=460, height=260),
            WindowState("Benchmark Summary", x=80, y=80, width=460, height=260),
        ),
        playback_seconds=2.0,
    )
    window.restore_project_state(state)
    app.processEvents()
    window.close()
    app.processEvents()


def _update_multi_window_workspace_once(app: Any) -> None:
    from mflog_proto.ui.main_window import MainWindow

    window = MainWindow()
    for _ in range(7):
        window.add_analysis_window("Time-Series Graph")
    window.add_analysis_window("G-G Diagram")
    window.add_analysis_window("Current Values Table")
    for sample in range(30):
        window.set_playback_position(sample)
        app.processEvents()
    window.close()
    app.processEvents()


def _input_summary(
    options: TargetBenchmarkOptions,
    frame: pl.DataFrame,
    generated_summary: SyntheticCsvSummary | None,
) -> dict[str, Any]:
    return {
        "mode": "target-benchmark",
        "path": str(options.input_path),
        "rows": frame.height,
        "channels": frame.width,
        "target_rows": options.rows,
        "target_channels": options.channels,
        "generated": generated_summary is not None,
        "defects_enabled": options.defects,
        "file_size_bytes": options.input_path.stat().st_size,
        "ui_metrics_included": options.include_ui,
    }


def _mapping_details(mapping: dict[str, Any]) -> str:
    counts: dict[MappingState, int] = {state: 0 for state in MappingState}
    for mapped in mapping.values():
        counts[mapped.state] += 1
    return ", ".join(f"{state.value}={counts[state]}" for state in MappingState)


def _health_details(summary: dict[str, int | float]) -> str:
    return ", ".join(f"{key}={value}" for key, value in summary.items())


def _hotspots(metrics: list[BenchmarkMetric]) -> tuple[str, ...]:
    elapsed = [
        metric for metric in metrics if metric.name == "elapsed" and math.isfinite(metric.value)
    ]
    slowest = sorted(elapsed, key=lambda metric: metric.value, reverse=True)[:3]
    return tuple(f"{metric.category}: {metric.value:.3f} {metric.unit}" for metric in slowest)


def _recommendation(metrics: list[BenchmarkMetric]) -> str:
    failed = [metric.category for metric in metrics if not metric.passed]
    if not failed:
        return "Candidate stack passes this measured prototype benchmark."
    categories = ", ".join(dict.fromkeys(failed))
    return f"Prototype needs optimization or deeper profiling for: {categories}."


def _timestamp_issue_counts(frame: pl.DataFrame) -> dict[str, int]:
    values = _optional_numeric_values(frame, ("Timestamp", "TIME"))
    if values is None:
        return {"timestamp_duplicate": 0, "timestamp_backward": 0, "timestamp_gap": 0}

    duplicates = 0
    backward = 0
    deltas: list[float] = []
    previous: float | None = None
    for value in values:
        if value is None:
            previous = None
            continue
        if previous is not None:
            delta = value - previous
            if delta == 0:
                duplicates += 1
            elif delta < 0:
                backward += 1
            else:
                deltas.append(delta)
        previous = value

    gap = 0
    if deltas:
        baseline = min(deltas)
        if baseline > 0:
            gap = sum(1 for delta in deltas if delta > baseline * 5)
    return {
        "timestamp_duplicate": duplicates,
        "timestamp_backward": backward,
        "timestamp_gap": gap,
    }


def _count_where(frame: pl.DataFrame, channel: str, predicate: Any) -> int:
    if channel not in frame.columns:
        return 0
    value = frame.select(predicate(_numeric_col(channel)).sum().alias("count")).item()
    return int(value or 0)


def _x_array(frame: pl.DataFrame) -> Any:
    values = _optional_numeric_values(frame, ("Timestamp", "TIME"))
    if values is None:
        return _index_time_array(frame.height)
    x_values = [
        float(index) if value is None or not math.isfinite(value) else float(value)
        for index, value in enumerate(values)
    ]
    if any(left > right for left, right in zip(x_values, x_values[1:])):
        return _index_time_array(frame.height)
    return pl.Series(x_values).to_numpy()


def _optional_numeric_values(
    frame: pl.DataFrame,
    candidates: tuple[str, ...],
) -> list[float | None] | None:
    for candidate in candidates:
        if candidate in frame.columns:
            return _numeric_values(frame.get_column(candidate))
    return None


def _numeric_values(series: pl.Series) -> list[float | None]:
    return [
        None if value is None or not math.isfinite(float(value)) else float(value)
        for value in series.cast(pl.Float64, strict=False).to_list()
    ]


def _numeric_array(series: pl.Series) -> Any:
    return series.cast(pl.Float64, strict=False).to_numpy()


def _index_time_array(row_count: int) -> Any:
    return pl.Series(range(row_count)).cast(pl.Float64).to_numpy() * 0.1


def _numeric_col(column: str) -> pl.Expr:
    return pl.col(column).cast(pl.Float64, strict=False)


def _graph_channels(columns: list[str], limit: int) -> list[str]:
    preferred = [
        "RPM",
        "TPS_percent",
        "MAP_kPa",
        "OilTemp_C",
        "EOT_OUT",
        "CLT_C",
        "Batt_V",
        "DBW_Pos_percent",
        "DBW_Target_percent",
        "ax_g",
        "ay_g",
        "az_g",
        "Susp_FL_mm",
        "Susp_FR_mm",
        "Susp_RL_mm",
        "Susp_RR_mm",
        "Pitot_dP_Pa",
        "Pitot_AirSpeed_KPH",
        "SteeringAngle_deg",
    ]
    ordered = [column for column in preferred if column in columns]
    ordered.extend(column for column in columns if column not in ordered and column != "Timestamp")
    return ordered[: max(0, limit)]


def _sorted_unique_or_index_time(values: list[float]) -> list[float]:
    if not values:
        return [0.0]
    previous = -math.inf
    for value in values:
        if value <= previous:
            return [index * 0.1 for index in range(len(values))]
        previous = value
    return values


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((len(sorted_values) - 1) * percentile / 100.0)
    return sorted_values[index]


def _rss_gb(process: psutil.Process) -> float:
    return process.memory_info().rss / (1024**3)


def _timed(function: Any) -> TimedValue:
    started = time.perf_counter()
    value = function()
    return TimedValue(value=value, elapsed_seconds=time.perf_counter() - started)
