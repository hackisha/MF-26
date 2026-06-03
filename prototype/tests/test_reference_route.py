from __future__ import annotations

import json
from pathlib import Path

import pytest

from mflog_proto.analysis.reference_route import (
    ReferenceRoute,
    ReferenceRoutePoint,
    load_reference_route,
    save_reference_route,
)


def test_reference_route_round_trips_mflogroute_json(tmp_path: Path) -> None:
    path = tmp_path / "endurance.mflogroute"
    route = ReferenceRoute(
        name="Endurance reference",
        points=(
            ReferenceRoutePoint(latitude=35.29301, longitude=126.574061),
            ReferenceRoutePoint(latitude=35.29320, longitude=126.574300),
        ),
        created_at="2026-06-03T00:00:00+09:00",
        metadata={"source": "manual"},
    )

    save_reference_route(path, route)
    restored = load_reference_route(path)

    assert restored.name == "Endurance reference"
    assert restored.source_path == path
    assert restored.points == route.points
    assert restored.metadata == {"source": "manual"}
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1


def test_reference_route_rejects_invalid_coordinates(tmp_path: Path) -> None:
    path = tmp_path / "bad.mflogroute"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "bad",
                "created_at": "2026-06-03T00:00:00+09:00",
                "points": [{"latitude": 91.0, "longitude": 126.0}],
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="latitude"):
        load_reference_route(path)


def test_reference_route_rejects_unsupported_schema(tmp_path: Path) -> None:
    path = tmp_path / "future.mflogroute"
    path.write_text(
        json.dumps({"schema_version": 99, "name": "future", "points": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="schema"):
        load_reference_route(path)
