from __future__ import annotations

from PySide6.QtCore import Qt

from mf_log_analyzer_v2.ui.left_sidebar import LeftSidebar


def test_left_sidebar_plus_menu_emits_add_window(qtbot):
    sidebar = LeftSidebar()
    qtbot.addWidget(sidebar)
    sidebar.show()

    emitted: list[str] = []
    sidebar.add_window_requested.connect(emitted.append)

    qtbot.mouseClick(sidebar.plus_button_for("DBW / ETC"), Qt.MouseButton.LeftButton)

    action = sidebar.current_menu.actions()[0]
    assert action.text() == "Target vs Actual"

    action.trigger()

    assert emitted == ["dbw.target_vs_actual"]


def test_left_sidebar_search_filters_groups(qtbot):
    sidebar = LeftSidebar()
    qtbot.addWidget(sidebar)
    sidebar.show()

    sidebar.search.setText("dbw")

    assert sidebar.group_widget("DBW / ETC").isVisibleTo(sidebar)
    assert not sidebar.group_widget("Cooling Efficiency").isVisibleTo(sidebar)
