from benchmarks.benchmark_foundation import PROJECT_ROOT, SYNTHETIC_LOG_PATH
from benchmarks.generate_synthetic_log import generate_synthetic_log


def test_generate_synthetic_log_writes_expected_rows_and_header(tmp_path):
    output = tmp_path / "synthetic.csv"

    generate_synthetic_log(output, rows=5, extra_channels=3)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 6
    assert lines[0].startswith("Timestamp,RPM,TPS_percent,OilTemp_C")

    header = lines[0].split(",")
    first_data_row = lines[1].split(",")
    assert len(header) == 13
    assert len(first_data_row) == len(header)
    assert header[-3:] == ["Extra_000", "Extra_001", "Extra_002"]


def test_foundation_benchmark_writes_to_artifacts_directory():
    assert SYNTHETIC_LOG_PATH == PROJECT_ROOT / "benchmarks" / "artifacts" / "synthetic_300k.csv"
