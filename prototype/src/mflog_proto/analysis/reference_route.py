"""Reference GPS route serialization for GPS Map overlays."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ReferenceRoutePoint:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        latitude = _coordinate_value(self.latitude, "latitude")
        longitude = _coordinate_value(self.longitude, "longitude")
        object.__setattr__(self, "latitude", latitude)
        object.__setattr__(self, "longitude", longitude)


@dataclass(frozen=True)
class ReferenceRoute:
    name: str
    points: tuple[ReferenceRoutePoint, ...]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone().isoformat(
            timespec="seconds"
        )
    )
    metadata: dict[str, str] = field(default_factory=dict)
    source_path: Path | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", _points_from_iterable(self.points))
        object.__setattr__(self, "metadata", _metadata_from_dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "created_at": self.created_at,
            "points": [
                {"latitude": point.latitude, "longitude": point.longitude}
                for point in self.points
            ],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        source_path: Path | None = None,
    ) -> "ReferenceRoute":
        schema_version = int(data.get("schema_version", SCHEMA_VERSION))
        if schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported reference route schema: {schema_version}")
        points_data = data.get("points", ())
        if not isinstance(points_data, list | tuple):
            raise ValueError("Reference route points must be a JSON array")
        points = _points_from_iterable(_point_from_dict(item) for item in points_data)
        name = str(data.get("name", "")).strip() or _default_route_name(source_path)
        metadata = _metadata_from_dict(data.get("metadata", {}))
        created_at = str(data.get("created_at", "")).strip()
        return cls(
            name=name,
            points=points,
            created_at=created_at,
            metadata=metadata,
            source_path=source_path,
        )


def save_reference_route(path: Path, route: ReferenceRoute) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(route.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_reference_route(path: Path) -> ReferenceRoute:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Reference route file must contain a JSON object")
    return ReferenceRoute.from_dict(data, source_path=path)


def _point_from_dict(data: Any) -> ReferenceRoutePoint:
    if not isinstance(data, dict):
        raise ValueError("Reference route point must be a JSON object")
    if "latitude" not in data:
        raise ValueError("Reference route point missing latitude")
    if "longitude" not in data:
        raise ValueError("Reference route point missing longitude")
    return ReferenceRoutePoint(latitude=data["latitude"], longitude=data["longitude"])


def _coordinate_value(value: Any, name: str) -> float:
    try:
        coordinate = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}: {value!r}") from exc
    if not math.isfinite(coordinate):
        raise ValueError(f"Invalid {name}: {coordinate}")
    if name == "latitude":
        lower = -90.0
        upper = 90.0
    else:
        lower = -180.0
        upper = 180.0
    if coordinate < lower or coordinate > upper:
        raise ValueError(f"Invalid {name}: {coordinate}")
    return coordinate


def _points_from_iterable(points: Any) -> tuple[ReferenceRoutePoint, ...]:
    try:
        normalized = tuple(points)
    except TypeError as exc:
        raise ValueError("Reference route points must be an iterable") from exc
    for point in normalized:
        if not isinstance(point, ReferenceRoutePoint):
            raise ValueError("Reference route points must contain ReferenceRoutePoint")
    return normalized


def _metadata_from_dict(data: Any) -> dict[str, str]:
    if not isinstance(data, dict):
        raise ValueError("Reference route metadata must be a JSON object")
    return {str(key): str(value) for key, value in data.items()}


def _default_route_name(source_path: Path | None) -> str:
    return "Reference route" if source_path is None else source_path.stem
