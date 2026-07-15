from mflog_proto.data.column_store import ColumnStore
from mflog_proto.data.health import HealthSeverity, run_health_checks


def test_health_check_reports_missing_required_channels():
    store = ColumnStore(row_count=2, raw_columns={"Timestamp": ["0.0", "0.1"]})

    report = run_health_checks(store, required_channels=["RPM", "EOT_IN"])

    assert report.status is HealthSeverity.CRITICAL
    assert report.count_by_severity(HealthSeverity.CRITICAL) == 2
    assert sum(1 for issue in report.issues if issue.code == "missing_channel") == 2


def test_health_check_detects_timestamp_duplicate_backward_and_gap():
    store = ColumnStore(
        row_count=5,
        raw_columns={"Timestamp": ["0.0", "0.1", "0.1", "0.05", "1.0"]},
        standard_sources={"TIME": "Timestamp"},
    )

    report = run_health_checks(store)

    assert report.has_issue("timestamp_duplicate")
    assert report.has_issue("timestamp_backward")
    assert report.has_issue("timestamp_gap")
    backward = next(issue for issue in report.issues if issue.code == "timestamp_backward")
    assert backward.severity is HealthSeverity.CRITICAL
    assert backward.channel_id == "TIME"
    assert backward.sample_index == 3


def test_health_check_detects_invalid_numeric_stuck_out_of_range_and_dropout():
    store = ColumnStore(
        row_count=6,
        raw_columns={
            "RPM": ["1000", "1000", "1000", "1000", "", "bad"],
            "Batt_V": ["13.2", "13.1", "9.5", "13.0", "13.2", "13.1"],
        },
    )

    report = run_health_checks(
        store,
        valid_ranges={"RPM": (0.0, 9000.0), "Batt_V": (10.0, 15.0)},
        stuck_window=4,
    )

    assert report.has_issue("invalid_numeric")
    assert report.has_issue("dropout")
    assert report.has_issue("stuck_sensor")
    assert report.has_issue("out_of_range")
    assert report.has_issue("low_voltage")


def test_health_check_reports_adxl_correction_status_and_dbw_error():
    store = ColumnStore(
        row_count=3,
        raw_columns={
            "ax_g": ["8", "16", "24"],
            "DBW_Target_percent": ["10", "50", "60"],
            "DBW_Pos_percent": ["10", "20", "30"],
        },
        standard_sources={
            "AX_RAW_G": "ax_g",
            "DBW_TARGET_PERCENT": "DBW_Target_percent",
            "DBW_ACTUAL_PERCENT": "DBW_Pos_percent",
        },
    )

    report = run_health_checks(store, dbw_error_threshold=20.0)

    assert report.has_issue("adxl_correction_available")
    assert report.has_issue("dbw_tracking_error")


def test_health_check_distinguishes_adxl_applied_available_and_missing():
    applied_store = ColumnStore(
        row_count=1,
        raw_columns={"AX_CORRECTED_G": ["1.0"]},
        standard_sources={"AX_CORRECTED_G": "AX_CORRECTED_G"},
    )
    raw_store = ColumnStore(
        row_count=1,
        raw_columns={"ax_g": ["8.0"]},
        standard_sources={"AX_RAW_G": "ax_g"},
    )
    missing_store = ColumnStore(row_count=1, raw_columns={"RPM": ["1000"]})

    assert run_health_checks(applied_store).has_issue("adxl_correction_applied")
    assert run_health_checks(raw_store).has_issue("adxl_correction_available")
    assert run_health_checks(missing_store).has_issue("adxl_correction_missing")
