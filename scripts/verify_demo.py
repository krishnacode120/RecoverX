"""End-to-end generated fixture recovery with an independently known reference hash."""

import hashlib
import json
from pathlib import Path

from recoverx.models import Control
from recoverx.restore import recover
from recoverx.source import ImageSource
from recoverx.store import Store

root = Path("artifacts/demo")
destination = Path("artifacts/recovered-demo")
destination.mkdir(exist_ok=True)
expected = json.loads((root / "expected.json").read_text())
store = Store("artifacts/demo.sqlite")
outcomes = []
for kind, image in (("fat32", "deleted-fat32.img"), ("exfat", "deleted-exfat.img")):
    report = json.loads(Path(f"artifacts/{kind}-report.json").read_text())
    candidate = store.results(report["scan"]["id"])[0]
    image_path = root / image
    before = hashlib.file_digest(image_path.open("rb"), "sha256").hexdigest()
    with ImageSource(image_path) as source:
        result = recover(source, candidate, destination, Control(), allow_image_disk=True)
    after = hashlib.file_digest(image_path.open("rb"), "sha256").hexdigest()
    assert before == after
    assert result["sha256"] == expected[candidate.name]
    result["source_unchanged"] = True
    result["reference_hash_match"] = True
    outcomes.append(result)
store.close()
Path("artifacts/recovery-verification.json").write_text(json.dumps(outcomes, indent=2))
print(json.dumps(outcomes, indent=2))
