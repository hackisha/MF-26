from pathlib import Path

import numpy as np

from mf_log_analyzer_v2.core.csv_loader import load_csv
from mf_log_analyzer_v2.core.default_profiles import mf_default_profile


def test_load_csv_maps_aliases_and_calibration(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "Timestamp,OilTemp_C,ax_g,ay_g,DBW_Target_percent,DBW_Pos_percent\n"
        "0.0,91.5,8.0,-16.0,20.0,18.0\n"
        "0.1,92.0,16.0,-8.0,22.0,21.0\n",
        encoding="utf-8",
    )

    log = load_csv(csv_path, mf_default_profile())

    assert log.row_count == 2
    assert log.time_channel == "Timestamp"
    np.testing.assert_allclose(log.values("EOT_IN"), np.array([91.5, 92.0]))
    np.testing.assert_allclose(log.values("AX_CORRECTED_G"), np.array([1.0, 2.0]))
    np.testing.assert_allclose(log.values("AY_CORRECTED_G"), np.array([-2.0, -1.0]))
    np.testing.assert_allclose(log.values("DBW_TARGET_PERCENT"), np.array([20.0, 22.0]))


def test_load_csv_emits_progress(tmp_path: Path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("Timestamp,RPM\n0.0,1000\n", encoding="utf-8")
    stages: list[str] = []

    load_csv(csv_path, mf_default_profile(), on_progress=lambda progress: stages.append(progress.stage))

    assert stages == ["reading", "mapping", "calibrating", "complete"]
