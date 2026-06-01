from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import polars as pl

from mf_log_analyzer_v2.core.models import LoadProgress, LogTable, VehicleProfile

ProgressCallback = Callable[[LoadProgress], None]


def _emit(
    callback: ProgressCallback | None,
    stage: str,
    processed_rows: int = 0,
    total_rows: int | None = None,
) -> None:
    if callback is not None:
        callback(LoadProgress(stage=stage, processed_rows=processed_rows, total_rows=total_rows))


def load_csv(path: Path, profile: VehicleProfile, on_progress: ProgressCallback | None = None) -> LogTable:
    _emit(on_progress, "reading")
    header = pl.read_csv(path, n_rows=0)
    headers = header.columns

    _emit(on_progress, "mapping")
    mapped_columns: dict[str, pl.Series] = {}
    sources_by_channel: dict[str, str] = {}
    needed_sources: list[str] = []
    missing_required_channels: list[str] = []
    seen_sources: set[str] = set()

    for channel_id, channel in profile.channels.items():
        source = profile.source_for(channel_id, headers)
        if source is None:
            if channel.required:
                missing_required_channels.append(channel_id)
            continue
        sources_by_channel[channel_id] = source
        if source not in seen_sources:
            needed_sources.append(source)
            seen_sources.add(source)

    if missing_required_channels:
        missing = ", ".join(missing_required_channels)
        raise ValueError(f"Missing required channel: {missing}")

    if needed_sources:
        raw = pl.read_csv(path, columns=needed_sources, infer_schema_length=10_000)
        row_count = raw.height
    else:
        row_counter = pl.read_csv(path, columns=[headers[0]], infer_schema_length=10_000)
        raw = pl.DataFrame()
        row_count = row_counter.height

    _emit(on_progress, "calibrating", total_rows=row_count)
    for channel_id, source in sources_by_channel.items():
        channel = profile.channels[channel_id]
        source_values = raw[source]
        if source_values.null_count() > 0:
            raise ValueError(f"Missing numeric value in source column: {source}")

        values = source_values.cast(pl.Float64, strict=True).to_numpy()
        if not np.isfinite(values).all():
            raise ValueError(f"Non-finite numeric value in source column: {source}")

        mapped_columns[channel_id] = pl.Series(channel_id, channel.calibration.apply(values))

    if "Timestamp" not in mapped_columns:
        mapped_columns["Timestamp"] = pl.Series("Timestamp", list(range(row_count)), dtype=pl.Float64)

    frame = pl.DataFrame(mapped_columns)
    _emit(on_progress, "complete", processed_rows=frame.height, total_rows=frame.height)
    return LogTable(file_name=path.name, frame=frame, time_channel="Timestamp")
