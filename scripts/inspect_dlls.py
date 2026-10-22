"""Diagnose missing exports in the local frozen build without loading untrusted recovered files."""

from pathlib import Path
import pefile

root = Path("dist/RecoverX/_internal")
search = [root, root / "PySide6", root / "shiboken6", Path("C:/Windows/System32")]
cache = {}
for file in [
    root / "PySide6/QtCore.pyd",
    root / "PySide6/Qt6Core.dll",
    root / "PySide6/pyside6.abi3.dll",
    root / "shiboken6/shiboken6.abi3.dll",
    root / "icuuc.dll",
]:
    if not file.exists():
        continue
    p = pefile.PE(str(file))
    for entry in getattr(p, "DIRECTORY_ENTRY_IMPORT", []):
        name = entry.dll.decode()
        if name.lower().startswith("api-ms-"):
            continue
        found = next((directory / name for directory in search if (directory / name).exists()), None)
        if not found:
            print(file.name, "missing dependency", name)
            continue
        if found not in cache:
            dep = pefile.PE(str(found))
            cache[found] = (
                {s.name for s in dep.DIRECTORY_ENTRY_EXPORT.symbols}
                if hasattr(dep, "DIRECTORY_ENTRY_EXPORT")
                else set()
            )
        missing = [
            item.name.decode() for item in entry.imports if item.name and item.name not in cache[found]
        ]
        if missing:
            print(file.name, name, "missing exports", missing[:12])
