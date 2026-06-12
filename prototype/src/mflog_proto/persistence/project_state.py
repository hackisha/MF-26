"""JSON project/workspace state for the prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from mflog_proto.analysis.event_reviews import EventReview
from mflog_proto.analysis.segments import AnalysisSegment

SCHEMA_VERSION = 2
SUPPORTED_SCHEMA_VERSIONS = {1, 2}


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
    vehicle_model_path: Path | None = None
    reference_route_path: Path | None = None
    reference_route_name: str = ""
    video_path: Path | None = None
    video_offset_ms: int = 0
    video_muted: bool = True
    visualization_settings: dict[str, Any] = field(default_factory=dict)
    ideal_path_settings: dict[str, Any] = field(default_factory=dict)
    sidebar_settings: dict[str, Any] = field(default_factory=dict)
    event_reviews: tuple[EventReview, ...] = ()
    analysis_segments: tuple[AnalysisSegment, ...] = ()
    selected_sidebar_group: str = "시각화"
    report_output_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "csv_path": None if self.csv_path is None else str(self.csv_path),
            "vehicle_model_path": (
                None if self.vehicle_model_path is None else str(self.vehicle_model_path)
            ),
            "reference_route_path": (
                None if self.reference_route_path is None else str(self.reference_route_path)
            ),
            "reference_route_name": self.reference_route_name,
            "video_path": None if self.video_path is None else str(self.video_path),
            "video_offset_ms": self.video_offset_ms,
            "video_muted": self.video_muted,
            "visualization_settings": dict(self.visualization_settings),
            "ideal_path_settings": dict(self.ideal_path_settings),
            "sidebar_settings": dict(self.sidebar_settings),
            "active_profile": self.active_profile,
            "channel_mappings": dict(self.channel_mappings),
            "derived_channel_settings": dict(self.derived_channel_settings),
            "open_windows": [window.to_dict() for window in self.open_windows],
            "selected_channels": list(self.selected_channels),
            "playback_seconds": self.playback_seconds,
            "preset_tab_order": list(self.preset_tab_order),
            "active_tab_index": self.active_tab_index,
            "event_reviews": [review.to_dict() for review in self.event_reviews],
            "analysis_segments": [segment.to_dict() for segment in self.analysis_segments],
            "selected_sidebar_group": self.selected_sidebar_group,
            "report_output_path": (
                None if self.report_output_path is None else str(self.report_output_path)
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectState:
        schema_version = int(data.get("schema_version", SCHEMA_VERSION))
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(f"Unsupported project schema version: {schema_version}")

        csv_path = data.get("csv_path")
        vehicle_model_path = data.get("vehicle_model_path")
        reference_route_path = data.get("reference_route_path")
        video_path = data.get("video_path")
        report_output_path = data.get("report_output_path")
        return cls(
            schema_version=SCHEMA_VERSION,
            csv_path=None if csv_path in (None, "") else Path(str(csv_path)),
            vehicle_model_path=(
                None if vehicle_model_path in (None, "") else Path(str(vehicle_model_path))
            ),
            reference_route_path=(
                None if reference_route_path in (None, "") else Path(str(reference_route_path))
            ),
            reference_route_name=str(data.get("reference_route_name", "")),
            video_path=None if video_path in (None, "") else Path(str(video_path)),
            video_offset_ms=int(data.get("video_offset_ms", 0)),
            video_muted=_optional_bool(data, "video_muted", default=True),
            visualization_settings=dict(data.get("visualization_settings", {})),
            ideal_path_settings=dict(data.get("ideal_path_settings", {})),
            sidebar_settings=dict(data.get("sidebar_settings", {})),
            report_output_path=(
                None if report_output_path in (None, "") else Path(str(report_output_path))
            ),
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
            event_reviews=tuple(
                EventReview.from_dict(item) for item in data.get("event_reviews", [])
            ),
            analysis_segments=tuple(
                AnalysisSegment.from_dict(item) for item in data.get("analysis_segments", [])
            ),
            selected_sidebar_group=str(data.get("selected_sidebar_group", "시각화")),
        )


def save_project_state(path: Path, state: ProjectState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_project_state(path: Path) -> ProjectState:
    return ProjectState.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _optional_bool(data: dict[str, Any], key: str, *, default: bool) -> bool:
    if key not in data:
        return default
    value = data[key]
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value
