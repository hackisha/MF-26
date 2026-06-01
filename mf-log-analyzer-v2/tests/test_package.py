from mf_log_analyzer_v2 import __version__


def test_package_exports_version():
    assert __version__ == "0.1.0"


def test_main_window_imports():
    from mf_log_analyzer_v2.ui.main_window import MainWindow

    assert MainWindow.__name__ == "MainWindow"
