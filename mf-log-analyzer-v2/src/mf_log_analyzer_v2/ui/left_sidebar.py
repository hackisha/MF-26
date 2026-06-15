from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class ToolEntry:
    label: str
    key: str


@dataclass(frozen=True)
class ToolGroup:
    label: str
    entries: tuple[ToolEntry, ...]


GROUPS: tuple[ToolGroup, ...] = (
    ToolGroup(
        "Vehicle Behavior",
        (
            ToolEntry("G-G Diagram", "behavior.gg"),
            ToolEntry("3D Vehicle Attitude", "behavior.3d"),
        ),
    ),
    ToolGroup(
        "GPS / LapTime",
        (
            ToolEntry("GPS Map", "gps.map"),
            ToolEntry("Lap Time Table", "gps.lap_table"),
        ),
    ),
    ToolGroup("Cooling Efficiency", (ToolEntry("EOT IN / OUT Overlay", "cooling.eot_overlay"),)),
    ToolGroup("Engine Safety", (ToolEntry("RPM / Oil Pressure", "engine.rpm_oil_pressure"),)),
    ToolGroup(
        "DBW / ETC",
        (
            ToolEntry("Target vs Actual", "dbw.target_vs_actual"),
            ToolEntry("PID Term Viewer", "dbw.pid_terms"),
        ),
    ),
    ToolGroup("Electrical / Voltage", (ToolEntry("Battery Voltage", "electrical.battery_voltage"),)),
    ToolGroup("Suspension", (ToolEntry("4-Corner Stroke Graph", "suspension.stroke"),)),
    ToolGroup(
        "Data Analysis",
        (
            ToolEntry("XY Scatter Plot", "data.xy_scatter"),
            ToolEntry("3D Surface / Map Viewer", "data.surface_map"),
        ),
    ),
    ToolGroup("Documents", (ToolEntry("Add PDF Viewer", "documents.pdf_viewer"),)),
    ToolGroup("User Presets", (ToolEntry("Saved Workspace Preset", "presets.workspace"),)),
)


class LeftSidebar(QWidget):
    add_window_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_menu: QMenu | None = None
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search tools")
        self._group_widgets: dict[str, QWidget] = {}
        self._plus_buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self.search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        content = QWidget()
        self._groups_layout = QVBoxLayout(content)
        self._groups_layout.setContentsMargins(0, 0, 0, 0)
        self._groups_layout.setSpacing(6)
        scroll.setWidget(content)

        for group in GROUPS:
            self._add_group(group)

        self._groups_layout.addStretch(1)
        self.search.textChanged.connect(self._filter_groups)

    def plus_button_for(self, label: str) -> QPushButton:
        return self._plus_buttons[label]

    def group_widget(self, label: str) -> QWidget:
        return self._group_widgets[label]

    def _add_group(self, group: ToolGroup) -> None:
        group_widget = QFrame()
        group_widget.setFrameShape(QFrame.Shape.StyledPanel)
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(8, 6, 8, 6)
        group_layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel(group.label)
        add_button = QPushButton("+")
        add_button.setFixedWidth(28)
        add_button.clicked.connect(lambda _checked=False, tool_group=group: self._open_menu(tool_group, add_button))
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(add_button)
        group_layout.addLayout(header)

        for entry in group.entries:
            group_layout.addWidget(QLabel(entry.label))

        self._group_widgets[group.label] = group_widget
        self._plus_buttons[group.label] = add_button
        self._groups_layout.addWidget(group_widget)

    def _open_menu(self, group: ToolGroup, button: QPushButton) -> None:
        menu = QMenu(self)
        for entry in group.entries:
            action = menu.addAction(entry.label)
            action.setData(entry.key)
            action.triggered.connect(lambda _checked=False, key=entry.key: self.add_window_requested.emit(key))

        self.current_menu = menu
        menu.popup(button.mapToGlobal(button.rect().bottomLeft()))

    def _filter_groups(self, text: str) -> None:
        query = text.strip().casefold()
        for group in GROUPS:
            matches_group = query in group.label.casefold()
            matches_entry = any(query in entry.label.casefold() for entry in group.entries)
            self._group_widgets[group.label].setVisible(not query or matches_group or matches_entry)
