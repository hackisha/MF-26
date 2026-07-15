import numpy as np

from mflog_proto.analysis.segments import AnalysisSegment, compute_segment_summary


def test_compute_segment_summary_uses_available_sensor_channels():
    timestamps = np.array([0.0, 1.0, 2.0, 3.0])
    sensors = {
        "VSS / GPS speed": np.array([10.0, 20.0, 30.0, 40.0]),
        "RPM": np.array([1000.0, 2000.0, 3000.0, 4000.0]),
        "TPS": np.array([5.0, 10.0, 20.0, 25.0]),
        "ax": np.array([0.1, -0.3, 0.5, 0.2]),
        "ay": np.array([0.2, 0.4, -0.7, 0.1]),
        "Battery voltage": np.array([13.9, 13.8, 13.7, 13.6]),
    }

    summary = compute_segment_summary(
        AnalysisSegment(name="Corner 1", start_ms=1000, end_ms=3000),
        timestamps,
        sensors,
    )

    assert summary.name == "Corner 1"
    assert summary.duration_ms == 2000
    assert summary.row_count == 3
    assert summary.average_speed == 30.0
    assert summary.max_speed == 40.0
    assert summary.min_rpm == 2000.0
    assert summary.max_rpm == 4000.0
    assert summary.average_tps == 55.0 / 3.0
    assert summary.max_abs_ax == 0.5
    assert summary.max_abs_ay == 0.7
    assert summary.min_battery_voltage == 13.6


def test_compute_segment_summary_keeps_missing_channels_empty():
    summary = compute_segment_summary(
        AnalysisSegment(name="Short", start_ms=0, end_ms=1000),
        np.array([0.0, 1.0]),
        {},
    )

    assert summary.average_speed is None
    assert summary.max_speed is None
    assert summary.row_count == 2
