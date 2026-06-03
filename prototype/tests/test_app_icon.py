from PySide6 import QtGui, QtWidgets


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


def test_application_icon_uses_white_background_and_blue_logo():
    from mflog_proto.app_icon import APP_ICON_PATH

    image = QtGui.QImage(str(APP_ICON_PATH))
    assert not image.isNull()

    white_pixels = 0
    blue_pixels = 0
    sample_count = 0
    step = max(1, image.width() // 64)
    for y in range(0, image.height(), step):
        for x in range(0, image.width(), step):
            color = image.pixelColor(x, y)
            red = color.red()
            green = color.green()
            blue = color.blue()
            sample_count += 1
            if red >= 245 and green >= 245 and blue >= 245:
                white_pixels += 1
            if blue >= 120 and blue > red * 1.5 and blue > green * 1.2:
                blue_pixels += 1

    assert white_pixels > sample_count * 0.65
    assert blue_pixels > sample_count * 0.03
