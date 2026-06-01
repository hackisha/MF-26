from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTOTYPE_ROOT = PROJECT_ROOT / "prototype"


def test_pyinstaller_spec_declares_entrypoint_and_root_assets():
    spec_path = PROTOTYPE_ROOT / "packaging" / "mflog_analyzer.spec"

    spec_text = spec_path.read_text(encoding="utf-8")

    assert "src/mflog_proto/app.py" in spec_text.replace("\\", "/")
    assert "MF-LOG-ANALYZER-v2" in spec_text
    assert "car.glb" in spec_text
    assert "데이터분석기 콘티.pdf" in spec_text
    assert "app_icon.ico" in spec_text
    assert "icon=str(APP_ICON_ICO_PATH)" in spec_text
