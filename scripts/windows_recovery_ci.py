"""CI-only real Windows deletion and read-only recovery exercise; never used on user media."""

import hashlib
import json
import os
from pathlib import Path
import sys

from recoverx.drives import DriveSource, select_drive
from recoverx.engine import run_scan
from recoverx.restore import recover
from recoverx.source import ImageSource
from recoverx.store import Store

FILES = {
    "resident-ci.txt": b"RecoverX Windows deleted resident fixture.\r\n" * 3,
    "nonresident-ci.bin": bytes((n * 17 + 11) % 256 for n in range(12000)),
    "empty-ci.txt": b"",
}


def verify(source, destination=None):
    store = Store(":memory:")
    try:
        scan = run_scan(source, store, "quick")
        found = {item.name: item for item in store.results(scan, limit=1000)}
        for name, content in FILES.items():
            if name not in found:
                raise AssertionError(f"Windows deleted record missing: {name}")
            item = found[name]
            expected = hashlib.sha256(content).hexdigest()
            if item.sha256 != expected:
                raise AssertionError(f"Wrong or unavailable bytes for {name}: {item.to_dict()}")
            if destination:
                recover(source, item, destination, allow_image_disk=True)
                assert (destination / name).read_bytes() == content
        print(json.dumps({"verified": list(FILES), "reader": type(source).__name__, "candidates": store.count(scan)}))
    finally:
        store.close()


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.name != "nt":
        raise RuntimeError("Only runs in GitHub Actions on Windows")
    action, target = sys.argv[1:3]
    if action == "prepare":
        root = Path(target)
        if root.anchor != str(root) or root.drive.casefold() == os.environ["SystemDrive"].casefold():
            raise RuntimeError("Expected isolated fixture drive root")
        folder = root / "RecoverX-CI"
        folder.mkdir()
        for name, content in FILES.items():
            with (folder / name).open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        for name in FILES:
            (folder / name).unlink()
    elif action == "drive":
        selection = select_drive(target)
        if selection.disk_number != int(sys.argv[3]) or selection.name == "":
            raise RuntimeError("Fixture disk mapping changed")
        with DriveSource(selection) as source:
            verify(source)
    elif action == "image":
        path = Path(target)
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        output = Path(sys.argv[3]) / "recovered"
        output.mkdir()
        with ImageSource(path) as source:
            verify(source, output)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    else:
        raise RuntimeError("Unknown fixture action")


if __name__ == "__main__":
    main()
