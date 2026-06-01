from benchmarks.generate_synthetic_log import generate_synthetic_log


def test_generate_synthetic_log_writes_expected_rows_and_header(tmp_path):
    output = tmp_path / "synthetic.csv"

    generate_synthetic_log(output, rows=5, extra_channels=3)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 6
    assert lines[0].startswith("Timestamp,RPM,TPS_percent,OilTemp_C")
