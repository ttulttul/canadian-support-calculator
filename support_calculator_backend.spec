# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

project_root = Path(SPECPATH)

datas = collect_data_files("support_calculator")
datas += [
    (
        str(project_root / "frontend" / "dist"),
        "support_calculator/frontend_dist",
    ),
]
weasyprint_datas, weasyprint_binaries, weasyprint_hiddenimports = collect_all("weasyprint")
datas += weasyprint_datas
binaries = weasyprint_binaries
hiddenimports = weasyprint_hiddenimports

a = Analysis(
    ["support_calculator/__main__.py"],
    pathex=[str(project_root)],
    binaries=binaries,
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
    name="support-calculator-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="support-calculator-backend",
)
