# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


SPEC_PATH = Path(SPECPATH).resolve()
PROTOTYPE_ROOT = SPEC_PATH.parent
PROJECT_ROOT = PROTOTYPE_ROOT.parent
ENTRYPOINT = "src/mflog_proto/app.py"
APP_ICON_PNG_PATH = PROTOTYPE_ROOT / "src" / "mflog_proto" / "assets" / "app_icon.png"
APP_ICON_ICO_PATH = PROTOTYPE_ROOT / "src" / "mflog_proto" / "assets" / "app_icon.ico"

datas = []
for asset_name in ("car.glb", "데이터분석기 콘티.pdf"):
    asset_path = PROJECT_ROOT / asset_name
    if asset_path.exists():
        datas.append((str(asset_path), "."))
for app_asset_path in (APP_ICON_PNG_PATH, APP_ICON_ICO_PATH):
    if app_asset_path.exists():
        datas.append((str(app_asset_path), "mflog_proto/assets"))

hiddenimports = collect_submodules(
    "pyqtgraph",
    filter=lambda name: not name.startswith("pyqtgraph.opengl"),
)

a = Analysis(
    [str(PROTOTYPE_ROOT / ENTRYPOINT)],
    pathex=[str(PROTOTYPE_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MF-LOG-ANALYZER-v2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(APP_ICON_ICO_PATH),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MF-LOG-ANALYZER-v2",
)
