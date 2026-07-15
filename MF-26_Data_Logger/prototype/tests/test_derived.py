from mflog_proto.data.column_store import ColumnStore
from mflog_proto.data.derived import compute_basic_derived_channels


def test_compute_basic_derived_channels_preserves_adxl_correction_and_temperature_delta():
    store = ColumnStore(
        row_count=2,
        raw_columns={
            "ax_g": ["8", "16"],
            "ay_g": ["-8", "0"],
            "az_g": ["4", "bad"],
            "OilTemp_C": ["90", "91"],
            "EOT_OUT": ["100", "99"],
        },
        standard_sources={
            "AX_RAW_G": "ax_g",
            "AY_RAW_G": "ay_g",
            "AZ_RAW_G": "az_g",
            "EOT_IN": "OilTemp_C",
            "EOT_OUT": "EOT_OUT",
        },
    )

    derived = compute_basic_derived_channels(store)

    assert derived["AX_CORRECTED_G"] == [1.0, 2.0]
    assert derived["AY_CORRECTED_G"] == [-1.0, 0.0]
    assert derived["AZ_CORRECTED_G"][0] == 0.5
    assert derived["AZ_CORRECTED_G"][1] is None
    assert derived["EOT_DELTA"] == [10.0, 8.0]


def test_compute_basic_derived_channels_adds_dbw_error_when_inputs_exist():
    store = ColumnStore(
        row_count=2,
        raw_columns={
            "DBW_Target_percent": ["25", "50"],
            "DBW_Actual_percent": ["20", "45.5"],
        },
        standard_sources={
            "DBW_TARGET_PERCENT": "DBW_Target_percent",
            "DBW_ACTUAL_PERCENT": "DBW_Actual_percent",
        },
    )

    derived = compute_basic_derived_channels(store)

    assert derived["DBW_ERROR"] == [5.0, 4.5]
