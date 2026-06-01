"""Application icon helpers."""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6 import QtGui, QtWidgets


APP_ICON_FILENAME = "app_icon.png"
APP_ICON_ICO_FILENAME = "app_icon.ico"
_ASSET_DIR = Path(__file__).resolve().parent / "assets"


def _asset_path(filename: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        bundled_path = Path(bundle_root) / "mflog_proto" / "assets" / filename
        if bundled_path.exists():
            return bundled_path
    return _ASSET_DIR / filename


APP_ICON_PATH = _asset_path(APP_ICON_FILENAME)
APP_ICON_ICO_PATH = _asset_path(APP_ICON_ICO_FILENAME)


def load_app_icon() -> QtGui.QIcon:
    return QtGui.QIcon(str(APP_ICON_PATH))


def apply_application_icon(
    app: QtWidgets.QApplication | None = None,
    window: QtWidgets.QWidget | None = None,
) -> QtGui.QIcon:
    icon = load_app_icon()
    if app is not None:
        app.setWindowIcon(icon)
    if window is not None:
        window.setWindowIcon(icon)
    return icon
