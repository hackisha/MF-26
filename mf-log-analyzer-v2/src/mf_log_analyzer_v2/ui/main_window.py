from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow

from mf_log_analyzer_v2.ui.left_sidebar import LeftSidebar
from mf_log_analyzer_v2.ui.properties_panel import PropertiesPanel
from mf_log_analyzer_v2.ui.workspace import Workspace


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MF-LOG-ANALYZER v2")
        self.resize(1440, 920)

        self.workspace = Workspace()
        self.setCentralWidget(self.workspace)

        self.left_sidebar = LeftSidebar()
        tools_dock = QDockWidget("Tools", self)
        tools_dock.setWidget(self.left_sidebar)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, tools_dock)

        self.properties_panel = PropertiesPanel()
        properties_dock = QDockWidget("Properties", self)
        properties_dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, properties_dock)

        self.left_sidebar.add_window_requested.connect(self.workspace.add_placeholder_window)
