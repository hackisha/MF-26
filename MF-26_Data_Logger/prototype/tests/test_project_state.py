from pathlib import Path

import pytest

from mflog_proto.analysis.event_reviews import EventReview, EventReviewState
from mflog_proto.analysis.segments import AnalysisSegment
from mflog_proto.persistence.project_state import (
    ProjectState,
    WindowState,
    load_project_state,
    save_project_state,
)


def test_project_state_round_trips_json(tmp_path):
    state = ProjectState(
        csv_path=Path("sample.csv"),
        active_profile="mf_2026",
        channel_mappings={"RPM": "RPM"},
        derived_channel_settings={"AX_CORRECTED_G": {"formula": "ax_g / 8"}},
        open_windows=(
            WindowState(
                title="Time-Series Graph",
                x=10,
                y=20,
                width=400,
                height=250,
                opacity=0.72,
            ),
            WindowState(title="G-G Diagram", x=30, y=40, width=420, height=260),
        ),
        selected_channels=("RPM", "TPS_percent"),
        playback_seconds=4.2,
        preset_tab_order=("차량 거동", "GPS / LapTime"),
        active_tab_index=1,
        vehicle_model_path=Path("models/custom-car.glb"),
        reference_route_path=Path("routes/endurance.mflogroute"),
        reference_route_name="Endurance reference",
        video_path=Path("videos/endurance_gopro.mp4"),
        video_offset_ms=-1250,
        video_muted=False,
        visualization_settings={
            "gps_map_background_enabled": True,
            "graph_line_color": "#ec7063",
            "graph_line_width": 0.75,
            "gg_limit_radius": 2.25,
        },
        ideal_path_settings={
            "enabled": True,
            "wheelbase_m": 1.65,
            "steering_ratio": 12.5,
            "steering_channel": "SteeringAngle_deg",
        },
        sidebar_settings={
            "search_visible": False,
            "add_button_visible": True,
            "sort_mode": "A-Z",
            "density": "Compact",
            "width_px": 320,
        },
    )

    project_path = tmp_path / "session.mflogproto.json"
    save_project_state(project_path, state)

    restored = load_project_state(project_path)

    assert restored == state
    assert restored.reference_route_path == Path("routes/endurance.mflogroute")
    assert restored.reference_route_name == "Endurance reference"
    assert restored.video_path == Path("videos/endurance_gopro.mp4")
    assert restored.video_offset_ms == -1250
    assert restored.video_muted is False
    assert restored.open_windows[0].opacity == pytest.approx(0.72)
    assert restored.open_windows[1].opacity == 1.0
    assert restored.visualization_settings["gg_limit_radius"] == 2.25
    assert restored.ideal_path_settings["steering_ratio"] == 12.5
    assert restored.sidebar_settings["density"] == "Compact"


def test_project_state_rejects_unknown_schema_version(tmp_path):
    project_path = tmp_path / "future.json"
    project_path.write_text('{"schema_version": 999}', encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported project schema"):
        load_project_state(project_path)


@pytest.mark.parametrize("video_muted", ["false", 0, 1, None])
def test_project_state_rejects_non_bool_video_muted(video_muted):
    data = ProjectState().to_dict()
    data["video_muted"] = video_muted

    with pytest.raises(ValueError, match="video_muted"):
        ProjectState.from_dict(data)


def test_project_state_defaults_optional_sections():
    state = ProjectState.from_dict({"schema_version": 1})

    assert state.csv_path is None
    assert state.open_windows == ()
    assert state.active_profile == "prototype"
    assert state.vehicle_model_path is None
    assert state.reference_route_path is None
    assert state.reference_route_name == ""
    assert state.video_path is None
    assert state.video_offset_ms == 0
    assert state.video_muted is True


def test_project_state_v2_round_trips_event_reviews_and_segments(tmp_path):
    state = ProjectState(
        event_reviews=(
            EventReview(
                name="Battery low",
                time_ms=18320,
                severity="warning",
                sensor="Battery voltage",
                value=13.878,
                condition="value < 14.0",
                state=EventReviewState.CONFIRMED,
                note="Check alternator",
            ),
        ),
        analysis_segments=(AnalysisSegment("Corner 1", 1000, 3500),),
        selected_sidebar_group="분석",
        report_output_path=tmp_path / "report.html",
    )

    project_path = tmp_path / "session.mflogproj"
    save_project_state(project_path, state)
    restored = load_project_state(project_path)

    assert restored.schema_version == 2
    assert restored.event_reviews == state.event_reviews
    assert restored.analysis_segments == state.analysis_segments
    assert restored.selected_sidebar_group == "분석"
    assert restored.report_output_path == tmp_path / "report.html"


def test_project_state_loads_v1_files_with_empty_integrated_ux_fields(tmp_path):
    project_path = tmp_path / "v1.mflogproj"
    project_path.write_text(
        '{"schema_version": 1, "active_profile": "prototype", "open_windows": []}',
        encoding="utf-8",
    )

    restored = load_project_state(project_path)

    assert restored.schema_version == 2
    assert restored.event_reviews == ()
    assert restored.analysis_segments == ()
    assert restored.selected_sidebar_group == "시각화"
    assert restored.report_output_path is None
    assert restored.video_path is None
    assert restored.video_offset_ms == 0
    assert restored.video_muted is True
    assert restored.visualization_settings == {}
    assert restored.ideal_path_settings == {}
    assert restored.sidebar_settings == {}
