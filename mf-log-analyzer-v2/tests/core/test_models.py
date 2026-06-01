import numpy as np
import polars as pl

from mf_log_analyzer_v2.core.models import Calibration, ChannelDefinition, LogTable, VehicleProfile


def test_calibration_scale_offset_and_invert():
    calibration = Calibration(scale=0.125, offset=1.0, invert=True)
    values = np.array([8.0, -8.0])
    np.testing.assert_allclose(calibration.apply(values), np.array([-2.0, 0.0]))


def test_vehicle_profile_resolves_source_alias():
    profile = VehicleProfile(
        profile_id="2025",
        name="2025 Vehicle",
        channels={
            "EOT_IN": ChannelDefinition(
                channel_id="EOT_IN",
                display_name={"en": "Engine Oil Temp In", "ko": "엔진오일 온도 IN"},
                source_columns=("EOT_IN", "OilTemp_C"),
                unit="degC",
                group="CoolingOil",
            )
        },
    )

    assert profile.source_for("EOT_IN", ["Timestamp", "OilTemp_C"]) == "OilTemp_C"


def test_log_table_exposes_column_values():
    frame = pl.DataFrame({"Timestamp": [0.0, 0.1], "RPM": [1000.0, 1200.0]})
    log = LogTable(file_name="sample.csv", frame=frame, time_channel="Timestamp")

    assert log.row_count == 2
    assert log.time_range == (0.0, 0.1)
    np.testing.assert_allclose(log.values("RPM"), np.array([1000.0, 1200.0]))
