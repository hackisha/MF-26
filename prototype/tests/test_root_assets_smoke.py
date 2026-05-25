from pathlib import Path

import pytest

from mflog_proto.data.csv_loader import CsvLoadOptions, load_csv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_recommended_small_root_csv_loads_core_columns():
    csv_path = PROJECT_ROOT / "datalog_20250926_173643.csv"
    if not csv_path.exists():
        pytest.skip("local root CSV fixture is not present")

    result = load_csv(
        csv_path,
        CsvLoadOptions(
            selected_columns=[
                "Timestamp",
                "GPS_Speed_KPH",
                "RPM",
                "OilTemp_C",
                "EOT_OUT",
                "Batt_V",
                "DBW_Pos_percent",
                "DBW_Target_percent",
                "ax_g",
                "ay_g",
                "az_g",
            ],
            numeric_probe=False,
        ),
    )

    assert result.store.row_count > 8_000
    assert result.store.source_for("EOT_IN") == "OilTemp_C"
    assert result.store.values("RPM")[1]


def test_root_reference_assets_exist():
    assets = [
        PROJECT_ROOT / "car.glb",
        PROJECT_ROOT / "데이터분석기 콘티.pdf",
        PROJECT_ROOT / "대회로그.zip",
    ]
    missing = [asset.name for asset in assets if not asset.exists()]
    if missing:
        pytest.skip(f"local root assets are not present: {missing}")

    for asset in assets:
        assert asset.stat().st_size > 0
