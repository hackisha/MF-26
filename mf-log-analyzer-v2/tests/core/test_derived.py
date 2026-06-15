import numpy as np
import polars as pl
import pytest

from mf_log_analyzer_v2.core.derived import add_formula_channel
from mf_log_analyzer_v2.core.models import LogTable


def test_add_formula_channel_subtracts_series():
    log = LogTable(
        file_name="sample.csv",
        frame=pl.DataFrame(
            {
                "Timestamp": [0.0, 0.1, 0.2],
                "DBW_TARGET_PERCENT": [20.0, 22.0, 21.0],
                "DBW_ACTUAL_PERCENT": [18.0, 20.0, 24.0],
            }
        ),
        time_channel="Timestamp",
    )

    derived = add_formula_channel(log, "DBW_ERROR", "DBW_TARGET_PERCENT - DBW_ACTUAL_PERCENT")

    assert derived.file_name == "sample.csv"
    assert derived.time_channel == "Timestamp"
    assert "DBW_ERROR" not in log.frame.columns
    np.testing.assert_allclose(derived.values("DBW_ERROR"), np.array([2.0, 2.0, -3.0]))


def test_add_formula_channel_supports_allowed_operators_and_constants():
    log = LogTable(
        file_name="sample.csv",
        frame=pl.DataFrame({"Timestamp": [0.0, 0.1], "RPM": [1000.0, 1100.0]}),
        time_channel="Timestamp",
    )

    derived = add_formula_channel(log, "RPM_SCALED", "(RPM + 100) * 2 / 4")

    np.testing.assert_allclose(derived.values("RPM_SCALED"), np.array([550.0, 600.0]))


def test_add_formula_channel_broadcasts_numeric_constant():
    log = LogTable(
        file_name="sample.csv",
        frame=pl.DataFrame({"Timestamp": [0.0, 0.1, 0.2]}),
        time_channel="Timestamp",
    )

    derived = add_formula_channel(log, "BASELINE", "2.5")

    np.testing.assert_allclose(derived.values("BASELINE"), np.array([2.5, 2.5, 2.5]))


def test_add_formula_channel_rejects_unknown_channel():
    log = LogTable(
        file_name="sample.csv",
        frame=pl.DataFrame({"Timestamp": [0.0], "RPM": [1000.0]}),
        time_channel="Timestamp",
    )

    with pytest.raises(ValueError, match="Unknown formula token: MISSING"):
        add_formula_channel(log, "RPM_OFFSET", "MISSING + 1")


@pytest.mark.parametrize(
    "formula",
    [
        "ABS(RPM)",
        "RPM.real",
        "RPM[0]",
        "[RPM]",
        "RPM > 1000",
    ],
)
def test_add_formula_channel_rejects_unsupported_expressions(formula: str):
    log = LogTable(
        file_name="sample.csv",
        frame=pl.DataFrame({"Timestamp": [0.0], "RPM": [1000.0]}),
        time_channel="Timestamp",
    )

    with pytest.raises(ValueError, match="Unsupported formula expression"):
        add_formula_channel(log, "DERIVED", formula)
