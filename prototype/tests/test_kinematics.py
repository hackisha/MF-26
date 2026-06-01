import pytest

from mflog_proto.analysis.kinematics import compute_ideal_path


def test_compute_ideal_path_integrates_bicycle_model_from_gps_start() -> None:
    result = compute_ideal_path(
        timestamps=[0.0, 1.0, 2.0],
        speed_kph=[36.0, 36.0, 36.0],
        steering_angle_deg=[10.0, 10.0, 10.0],
        latitude=[37.0, 37.0, 37.0],
        longitude=[127.0, 127.0001, 127.0002],
        wheelbase_m=2.0,
        steering_ratio=1.0,
    )

    assert result.status == "ready"
    assert result.valid_count == 3
    assert result.latitude[0] == pytest.approx(37.0)
    assert result.longitude[0] == pytest.approx(127.0)
    assert result.longitude[-1] > result.longitude[0]
    assert result.latitude[-1] > result.latitude[0]


def test_compute_ideal_path_reports_missing_inputs() -> None:
    result = compute_ideal_path(
        timestamps=[0.0, 1.0],
        speed_kph=[36.0, 36.0],
        steering_angle_deg=[],
        latitude=[37.0, 37.0],
        longitude=[127.0, 127.0001],
        wheelbase_m=1.6,
        steering_ratio=1.0,
    )

    assert result.status == "waiting for steering"
    assert result.valid_count == 0
