from pathlib import Path

import pytest

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
            WindowState(title="Time-Series Graph", x=10, y=20, width=400, height=250),
            WindowState(title="G-G Diagram", x=30, y=40, width=420, height=260),
        ),
        selected_channels=("RPM", "TPS_percent"),
        playback_seconds=4.2,
        preset_tab_order=("차량 거동", "GPS / LapTime"),
        active_tab_index=1,
    )

    project_path = tmp_path / "session.mflogproto.json"
    save_project_state(project_path, state)

    assert load_project_state(project_path) == state


def test_project_state_rejects_unknown_schema_version(tmp_path):
    project_path = tmp_path / "future.json"
    project_path.write_text('{"schema_version": 999}', encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported project schema"):
        load_project_state(project_path)


def test_project_state_defaults_optional_sections():
    state = ProjectState.from_dict({"schema_version": 1})

    assert state.csv_path is None
    assert state.open_windows == ()
    assert state.active_profile == "prototype"
