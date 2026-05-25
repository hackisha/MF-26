from pathlib import Path

import pytest

from mflog_proto.data.csv_loader import CsvLoadOptions, load_csv


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
