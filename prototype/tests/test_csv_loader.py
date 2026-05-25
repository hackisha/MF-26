from pathlib import Path

import pytest

from mflog_proto.data.csv_loader import (
    CsvLoadCancelled,
    CsvLoadOptions,
    CsvLoadRequest,
    load_csv,
    load_csv_request,
)


def test_load_csv_handles_duplicate_columns_and_numeric_errors(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "Timestamp,RPM,RPM,OilTemp_C\n"
        "0.0,1000,1001,80\n"
        "0.1,bad,1002,81\n",
        encoding="utf-8",
    )

    result = load_csv(csv_path, CsvLoadOptions(numeric_probe=True))

    assert result.store.row_count == 2
    assert result.store.raw_column_names == ["Timestamp", "RPM", "RPM__2", "OilTemp_C"]
    assert result.duplicate_columns == {"RPM": ["RPM", "RPM__2"]}
    assert result.numeric_errors[0].column == "RPM"
    assert result.numeric_errors[0].row_number == 3


def test_load_csv_can_select_columns(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("Timestamp,RPM,TPS_percent\n0.0,1000,12\n", encoding="utf-8")

    result = load_csv(csv_path, CsvLoadOptions(selected_columns=["Timestamp", "RPM"]))

    assert result.store.raw_column_names == ["Timestamp", "RPM"]
    assert result.store.values("RPM") == ["1000"]


def test_load_csv_maps_oil_temp_alias_to_standard_channel(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("Timestamp,OilTemp_C\n0.0,80\n", encoding="utf-8")

    result = load_csv(csv_path)

    assert result.store.source_for("EOT_IN") == "OilTemp_C"
    assert result.store.values("EOT_IN") == ["80"]


def test_load_csv_rejects_unknown_selected_columns(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("Timestamp,RPM\n0.0,1000\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing selected columns"):
        load_csv(csv_path, CsvLoadOptions(selected_columns=["MissingSensor"]))


def test_load_csv_maps_dbw_actual_alias_to_standard_channel(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("Timestamp,DBW_Actual_percent\n0.0,23\n", encoding="utf-8")

    result = load_csv(csv_path)

    assert result.store.source_for("DBW_ACTUAL_PERCENT") == "DBW_Actual_percent"
    assert result.store.values("DBW_ACTUAL_PERCENT") == ["23"]


def test_load_csv_reports_malformed_rows_without_dropping_session(tmp_path: Path):
    csv_path = tmp_path / "malformed.csv"
    csv_path.write_text(
        "Timestamp,RPM,TPS_percent\n"
        "0.0,1000,12\n"
        "0.1,1100\n"
        "0.2,1200,14,extra\n",
        encoding="utf-8",
    )

    result = load_csv(csv_path)

    assert result.store.row_count == 3
    assert result.store.values("TPS_percent") == ["12", "", "14"]
    assert [(row.row_number, row.expected_columns, row.actual_columns) for row in result.malformed_rows] == [
        (3, 3, 2),
        (4, 3, 4),
    ]


def test_load_csv_request_emits_progress_callbacks(tmp_path: Path):
    csv_path = tmp_path / "progress.csv"
    csv_path.write_text(
        "Timestamp,RPM\n"
        "0.0,1000\n"
        "0.1,1100\n"
        "0.2,1200\n",
        encoding="utf-8",
    )
    events = []

    result = load_csv_request(
        CsvLoadRequest(
            path=csv_path,
            progress_interval_rows=2,
            on_progress=events.append,
        )
    )

    assert result.store.row_count == 3
    assert [event.rows_loaded for event in events] == [2, 3]
    assert events[-1].columns_loaded == 2
    assert events[-1].physical_line_number == 4


def test_load_csv_request_can_be_cancelled_by_progress_callback(tmp_path: Path):
    csv_path = tmp_path / "cancel.csv"
    csv_path.write_text(
        "Timestamp,RPM\n"
        "0.0,1000\n"
        "0.1,1100\n"
        "0.2,1200\n",
        encoding="utf-8",
    )
    cancel_after_progress = False

    def on_progress(progress):
        nonlocal cancel_after_progress
        if progress.rows_loaded >= 2:
            cancel_after_progress = True

    def is_cancelled() -> bool:
        return cancel_after_progress

    with pytest.raises(CsvLoadCancelled) as error:
        load_csv_request(
            CsvLoadRequest(
                path=csv_path,
                progress_interval_rows=2,
                on_progress=on_progress,
                is_cancelled=is_cancelled,
            )
        )

    assert error.value.rows_loaded == 2
