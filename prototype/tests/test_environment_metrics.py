from mflog_proto.benchmark.metrics import collect_environment


def test_collect_environment_reports_dependency_presence():
    env = collect_environment()

    assert env.python_version
    assert env.platform
    assert env.dependencies["pytest"].available is True
    assert "polars" in env.dependencies
    assert "PySide6" in env.dependencies
    assert "pyqtgraph" in env.dependencies


def test_environment_serializes_to_plain_dict():
    env = collect_environment()

    data = env.to_dict()

    assert data["python_version"] == env.python_version
    assert isinstance(data["dependencies"]["numpy"]["available"], bool)

