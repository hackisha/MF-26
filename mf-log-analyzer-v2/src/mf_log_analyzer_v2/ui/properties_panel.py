from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PropertiesPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Properties"))
        layout.addStretch(1)
