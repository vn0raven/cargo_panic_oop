# -*- mode: python ; coding: utf-8 -*-
"""Windows onedir build with webcam support."""

from pathlib import Path
from PyInstaller.utils.hooks import collect_all

project_root = Path(SPEC).resolve().parents[2]
model_file = project_root / "cargo_panic" / "assets" / "hand_landmarker.task"
version_file = project_root / "tools" / "packaging" / "windows_version_info.txt"

if not model_file.is_file():
    raise FileNotFoundError(
        "Missing cargo_panic/assets/hand_landmarker.task. Run BUILD_EXE.bat again."
    )

mediapipe_datas, mediapipe_binaries, mediapipe_hidden = collect_all("mediapipe")
cv2_datas, cv2_binaries, cv2_hidden = collect_all("cv2")

datas = mediapipe_datas + cv2_datas + [
    (str(model_file), "cargo_panic/assets"),
]
binaries = mediapipe_binaries + cv2_binaries
hidden_imports = [
    "cargo_panic.game",
    "cargo_panic.models",
    "cargo_panic.rendering",
    "cargo_panic.webcam",
] + mediapipe_hidden + cv2_hidden

analysis = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="CargoPanic",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(version_file),
)

collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="CargoPanic",
)
