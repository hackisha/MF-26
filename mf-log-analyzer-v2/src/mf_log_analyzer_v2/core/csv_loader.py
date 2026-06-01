from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

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
    raw = pl.read_csv(path, infer_schema_length=10_000, ignore_errors=True)
    headers = raw.columns

    _emit(on_progress, "mapping", total_rows=raw.height)
    mapped_columns: dict[str, pl.Series] = {}

    _emit(on_progress, "calibrating", total_rows=raw.height)
    for channel_id, channel in profile.channels.items():
        source = profile.source_for(channel_id, headers)
        if source is None:
            continue
        values = raw[source].cast(pl.Float64, strict=False).to_numpy()
        mapped_columns[channel_id] = pl.Series(channel_id, channel.calibration.apply(values))

    if "Timestamp" not in mapped_columns:
        mapped_columns["Timestamp"] = pl.Series("Timestamp", list(range(raw.height)), dtype=pl.Float64)

    frame = pl.DataFrame(mapped_columns)
    _emit(on_progress, "complete", processed_rows=frame.height, total_rows=frame.height)
    return LogTable(file_name=path.name, frame=frame, time_channel="Timestamp")
