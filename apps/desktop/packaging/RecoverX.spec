# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).resolve().parents[2]
a = Analysis(
    [str(root / "apps/desktop/main.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(root / "THIRD_PARTY_NOTICES.md"), "."), (str(root / "docs"), "docs")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
# Qt's Windows build imports the OS's unversioned ICU API. On developer hosts,
# PyInstaller can accidentally resolve the same filename to MSYS2's versioned ICU.
# Windows 10/11 supply the correct system DLL; never redistribute the toolchain copy.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() != "icuuc.dll"
              and not Path(entry[0]).name.lower().startswith("icudt")]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="RecoverX",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="RecoverX")
