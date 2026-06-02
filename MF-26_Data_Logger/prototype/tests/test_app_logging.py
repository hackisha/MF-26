from mflog_proto.diagnostics.app_logging import log_exception, log_root


def test_log_exception_writes_exception_details(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    try:
        raise RuntimeError("sample failure")
    except RuntimeError as exc:
        path = log_exception(exc, context="report export")

    assert path.parent == log_root()
    text = path.read_text(encoding="utf-8")
    assert "report export" in text
    assert "RuntimeError" in text
    assert "sample failure" in text
