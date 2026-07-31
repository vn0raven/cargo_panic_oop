# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-file Windows build for the standard mouse-first game."""

hidden_imports = [
    "cargo_panic.game",
    "cargo_panic.models",
    "cargo_panic.rendering",
    "cargo_panic.webcam",
]

analysis = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["cv2", "mediapipe"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="CargoPanic",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version="packaging/windows_version_info.txt",
)
