import pytest

from mflog_proto.analysis.dynamics import compute_dynamics_summary


def test_compute_dynamics_summary_reports_g_utilization_and_limit_exceedance():
    summary = compute_dynamics_summary(
        timestamps_seconds=[0.0, 0.1, 0.2],
        sensors={
            "AX_CORRECTED_G": [0.2, -0.8, 0.1],
            "AY_CORRECTED_G": [0.3, 0.9, -1.2],
            "yaw rate": [2.0, 15.0, -20.0],
        },
        g_limit_radius=1.0,
    )

    assert summary.sample_count == 3
    assert summary.peak_lateral_g == 1.2
    assert summary.peak_longitudinal_g == 0.8
    assert summary.peak_combined_g == pytest.approx((0.8**2 + 0.9**2) ** 0.5)
    assert summary.g_limit_exceedance_count == 2
    assert summary.g_utilization_percent == pytest.approx(120.4, abs=0.1)
    assert summary.max_abs_yaw_rate_dps == 20.0


def test_compute_dynamics_summary_classifies_yaw_response_with_steering_data():
    summary = compute_dynamics_summary(
        timestamps_seconds=[0.0, 0.1, 0.2],
        sensors={
            "VSS / GPS speed": [36.0, 36.0, 36.0],
            "steering angle": [10.0, 10.0, 10.0],
            "yaw rate": [90.0, 90.0, 90.0],
            "AX_CORRECTED_G": [0.0, 0.0, 0.0],
            "AY_CORRECTED_G": [0.2, 0.2, 0.2],
        },
        wheelbase_m=1.6,
        steering_ratio=1.0,
        steering_channel="steering angle",
    )

    assert summary.yaw_response_ratio is not None
    assert summary.yaw_response_ratio > 1.25
    assert summary.balance_label == "oversteer tendency"


def test_compute_dynamics_summary_handles_missing_steering_as_optional():
    summary = compute_dynamics_summary(
        timestamps_seconds=[0.0, 0.1],
        sensors={
            "AX_CORRECTED_G": [0.1, 0.2],
            "AY_CORRECTED_G": [0.2, 0.3],
            "yaw rate": [1.0, 2.0],
        },
    )

    assert summary.yaw_response_ratio is None
    assert summary.balance_label == "steering data unavailable"


def test_compute_dynamics_summary_marks_unavailable_acceleration_as_missing():
    summary = compute_dynamics_summary(
        timestamps_seconds=[0.0, 0.1],
        sensors={
            "AX_CORRECTED_G": [0.0, 0.0],
            "AY_CORRECTED_G": [0.0, 0.0],
        },
        available_channels=set(),
    )

    assert summary.peak_lateral_g is None
    assert summary.peak_longitudinal_g is None
    assert summary.peak_combined_g is None
    assert summary.g_utilization_percent is None
    assert summary.g_limit_exceedance_count == 0
