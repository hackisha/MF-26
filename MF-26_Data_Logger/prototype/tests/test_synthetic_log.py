import csv
from pathlib import Path

import pytest

from mflog_proto.data.synthetic_log import (
    CORE_CHANNELS,
    SyntheticCsvSummary,
    build_channel_names,
    iter_synthetic_rows,
    write_synthetic_csv,
)


def test_build_channel_names_keeps_core_channels_first_and_pads_sensors():
    names = build_channel_names(len(CORE_CHANNELS) + 2)

    assert names[: len(CORE_CHANNELS)] == list(CORE_CHANNELS)
    assert names[-2:] == ["Sensor_001", "Sensor_002"]


def test_build_channel_names_rejects_totals_smaller_than_core_channels():
    with pytest.raises(ValueError, match="total_channels"):
        build_channel_names(len(CORE_CHANNELS) - 1)


def test_iter_synthetic_rows_is_deterministic_without_defects():
    channels = ["Timestamp", "RPM", "TPS_percent", "Sensor_001"]

    first = list(iter_synthetic_rows(3, channels))
    second = list(iter_synthetic_rows(3, channels))

    assert first == second
    assert first == [
        ["0.000", "2200.000", "20.000", "0.000"],
        ["0.100", "2237.000", "23.000", "1.000"],
        ["0.200", "2274.000", "26.000", "2.000"],
    ]


def test_iter_synthetic_rows_can_inject_deterministic_defects():
    channels = ["Timestamp", "RPM", "TPS_percent", "MAP_kPa", "Sensor_001"]

    rows = list(iter_synthetic_rows(16, channels, defects=True))

    assert rows[4][0] == rows[3][0]
    assert float(rows[9][0]) < float(rows[8][0])
    assert rows[5][1] == "INVALID"
    assert rows[8][2] == rows[7][2] == rows[6][2]
    assert rows[12][3] == ""


def test_write_synthetic_csv_writes_header_rows_and_summary(tmp_path: Path):
    output = tmp_path / "synthetic.csv"

    summary = write_synthetic_csv(output, rows=3, channels=len(CORE_CHANNELS) + 1)

    with output.open(newline="", encoding="utf-8") as handle:
        content = list(csv.reader(handle))

    assert summary == SyntheticCsvSummary(
        path=output,
        rows=3,
        channels=len(CORE_CHANNELS) + 1,
        defects_enabled=False,
        file_size_bytes=output.stat().st_size,
    )
    assert content[0] == list(CORE_CHANNELS) + ["Sensor_001"]
    assert content[1][0] == "0.000"
    assert len(content) == 4
