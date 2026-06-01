from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from mf_log_analyzer_v2.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
