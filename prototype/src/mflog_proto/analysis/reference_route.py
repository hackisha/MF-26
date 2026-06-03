"""Reference GPS route serialization for GPS Map overlays."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ReferenceRoutePoint:
    latitude: float
    longitude: float


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
        points = tuple(_point_from_dict(item) for item in data.get("points", ()))
        name = str(data.get("name", "")).strip() or _default_route_name(source_path)
        metadata = {
            str(key): str(value) for key, value in dict(data.get("metadata", {})).items()
        }
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
    latitude = float(data["latitude"])
    longitude = float(data["longitude"])
    if latitude < -90.0 or latitude > 90.0:
        raise ValueError(f"Invalid latitude: {latitude}")
    if longitude < -180.0 or longitude > 180.0:
        raise ValueError(f"Invalid longitude: {longitude}")
    return ReferenceRoutePoint(latitude=latitude, longitude=longitude)


def _default_route_name(source_path: Path | None) -> str:
    return "Reference route" if source_path is None else source_path.stem
