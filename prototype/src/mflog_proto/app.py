"""Application entry point for the prototype UI."""

from __future__ import annotations

import sys

from PySide6 import QtWidgets

from mflog_proto.app_icon import apply_application_icon
from mflog_proto.ui.main_window import MainWindow


def main() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    apply_application_icon(app, window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
