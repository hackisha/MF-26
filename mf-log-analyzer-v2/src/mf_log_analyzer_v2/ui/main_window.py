from __future__ import annotations

from PySide6.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MF-LOG-ANALYZER v2")
        self.resize(1280, 800)
