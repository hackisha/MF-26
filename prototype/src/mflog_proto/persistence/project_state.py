"""JSON project/workspace state for the prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class WindowState:
    title: str
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WindowState:
        return cls(
            title=str(data["title"]),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            width=int(data.get("width", 460)),
            height=int(data.get("height", 260)),
        )


@dataclass(frozen=True)
class ProjectState:
    schema_version: int = SCHEMA_VERSION
    csv_path: Path | None = None
    active_profile: str = "prototype"
    channel_mappings: dict[str, str] = field(default_factory=dict)
    derived_channel_settings: dict[str, dict[str, Any]] = field(default_factory=dict)
    open_windows: tuple[WindowState, ...] = ()
    selected_channels: tuple[str, ...] = ()
    playback_seconds: float = 0.0
    preset_tab_order: tuple[str, ...] = ()
    active_tab_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "csv_path": None if self.csv_path is None else str(self.csv_path),
            "active_profile": self.active_profile,
            "channel_mappings": dict(self.channel_mappings),
            "derived_channel_settings": dict(self.derived_channel_settings),
            "open_windows": [window.to_dict() for window in self.open_windows],
            "selected_channels": list(self.selected_channels),
            "playback_seconds": self.playback_seconds,
            "preset_tab_order": list(self.preset_tab_order),
            "active_tab_index": self.active_tab_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectState:
        schema_version = int(data.get("schema_version", SCHEMA_VERSION))
        if schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported project schema version: {schema_version}")

        csv_path = data.get("csv_path")
        return cls(
            schema_version=schema_version,
            csv_path=None if csv_path in (None, "") else Path(str(csv_path)),
            active_profile=str(data.get("active_profile", "prototype")),
            channel_mappings=dict(data.get("channel_mappings", {})),
            derived_channel_settings=dict(data.get("derived_channel_settings", {})),
            open_windows=tuple(
                WindowState.from_dict(item) for item in data.get("open_windows", [])
            ),
            selected_channels=tuple(str(item) for item in data.get("selected_channels", [])),
            playback_seconds=float(data.get("playback_seconds", 0.0)),
            preset_tab_order=tuple(str(item) for item in data.get("preset_tab_order", [])),
            active_tab_index=int(data.get("active_tab_index", 0)),
        )


def save_project_state(path: Path, state: ProjectState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_project_state(path: Path) -> ProjectState:
    return ProjectState.from_dict(json.loads(path.read_text(encoding="utf-8")))
