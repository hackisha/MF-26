"""Application entry point for the prototype UI."""

from __future__ import annotations

import sys

from PySide6 import QtWidgets

from mflog_proto.ui.main_window import MainWindow


def main() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
