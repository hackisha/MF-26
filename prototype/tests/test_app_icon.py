from PySide6 import QtWidgets


def test_application_icon_asset_loads_and_applies_to_qt(qtbot):
    from mflog_proto.app_icon import (
        APP_ICON_ICO_PATH,
        APP_ICON_PATH,
        apply_application_icon,
        load_app_icon,
    )

    assert APP_ICON_PATH.exists()
    assert APP_ICON_ICO_PATH.exists()

    icon = load_app_icon()
    assert not icon.isNull()

    app = QtWidgets.QApplication.instance()
    window = QtWidgets.QWidget()
    qtbot.addWidget(window)

    applied_icon = apply_application_icon(app, window)

    assert not applied_icon.isNull()
    assert not app.windowIcon().isNull()
    assert not window.windowIcon().isNull()
