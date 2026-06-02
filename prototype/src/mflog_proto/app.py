"""Application entry point for the prototype UI."""

from __future__ import annotations

import sys

from PySide6 import QtWidgets

from mflog_proto.app_icon import apply_application_icon
from mflog_proto.diagnostics.app_logging import log_exception
from mflog_proto.ui.main_window import MainWindow


def main() -> int:
    sys.excepthook = _log_unhandled_exception
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    apply_application_icon(app, window)
    window.show()
    return app.exec()


def _log_unhandled_exception(exc_type, exc, traceback) -> None:
    log_exception(exc, context="unhandled application exception")
    sys.__excepthook__(exc_type, exc, traceback)


if __name__ == "__main__":
    raise SystemExit(main())
