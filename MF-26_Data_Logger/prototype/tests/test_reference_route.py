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
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert "source_path" not in payload


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


def test_reference_route_point_rejects_invalid_latitude() -> None:
    with pytest.raises(ValueError, match="latitude"):
        ReferenceRoutePoint(latitude=91.0, longitude=126.0)


def test_reference_route_point_rejects_nan_latitude() -> None:
    with pytest.raises(ValueError, match="latitude"):
        ReferenceRoutePoint(latitude=float("nan"), longitude=126.0)


def test_reference_route_rejects_invalid_point_objects() -> None:
    with pytest.raises(ValueError, match="points|ReferenceRoutePoint"):
        ReferenceRoute(name="bad", points=("not-a-point",))


def test_reference_route_rejects_null_points(tmp_path: Path) -> None:
    path = tmp_path / "null-points.mflogroute"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "bad",
                "created_at": "2026-06-03T00:00:00+09:00",
                "points": None,
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="points"):
        load_reference_route(path)


def test_reference_route_rejects_non_array_points(tmp_path: Path) -> None:
    path = tmp_path / "number-points.mflogroute"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "bad",
                "created_at": "2026-06-03T00:00:00+09:00",
                "points": 123,
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="points"):
        load_reference_route(path)


def test_reference_route_rejects_point_missing_latitude(tmp_path: Path) -> None:
    path = tmp_path / "missing-latitude.mflogroute"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "bad",
                "created_at": "2026-06-03T00:00:00+09:00",
                "points": [{"longitude": 126.0}],
                "metadata": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="latitude"):
        load_reference_route(path)


def test_reference_route_rejects_non_object_metadata(tmp_path: Path) -> None:
    path = tmp_path / "bad-metadata.mflogroute"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "bad",
                "created_at": "2026-06-03T00:00:00+09:00",
                "points": [],
                "metadata": None,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="metadata"):
        load_reference_route(path)


def test_reference_route_copies_metadata_on_construction() -> None:
    metadata = {"source": "manual"}
    route = ReferenceRoute(name="route", points=(), metadata=metadata)

    metadata["source"] = "mutated"

    assert route.to_dict()["metadata"] == {"source": "manual"}


def test_reference_route_metadata_is_immutable() -> None:
    route = ReferenceRoute(
        name="route",
        points=(),
        metadata={"source": "manual"},
    )

    with pytest.raises(TypeError):
        route.metadata["source"] = "mutated"

    assert route.to_dict()["metadata"] == {"source": "manual"}


def test_reference_route_rejects_unsupported_schema(tmp_path: Path) -> None:
    path = tmp_path / "future.mflogroute"
    path.write_text(
        json.dumps({"schema_version": 99, "name": "future", "points": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="schema"):
        load_reference_route(path)


def test_reference_route_rejects_null_schema(tmp_path: Path) -> None:
    path = tmp_path / "null-schema.mflogroute"
    path.write_text(
        json.dumps({"schema_version": None, "name": "bad", "points": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="schema"):
        load_reference_route(path)


def test_reference_route_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "malformed.mflogroute"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError):
        load_reference_route(path)
