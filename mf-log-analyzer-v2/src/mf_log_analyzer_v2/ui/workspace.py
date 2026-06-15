from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMdiArea


class Workspace(QMdiArea):
    def add_placeholder_window(self, window_key: str) -> None:
        label = QLabel(window_key)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub_window = self.addSubWindow(label)
        sub_window.setWindowTitle(window_key)
        sub_window.resize(420, 260)
        sub_window.show()
