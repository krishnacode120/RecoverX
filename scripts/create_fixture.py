"""Generate disposable evidence images. Never takes a physical device path."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.fixtures import exfat_image, fat_image, picture, pdf

parser = argparse.ArgumentParser()
parser.add_argument("directory")
args = parser.parse_args()
root = Path(args.directory)
root.mkdir(parents=True, exist_ok=False)
jpeg = fat_image(root / "deleted-fat32.img")
document = exfat_image(root / "deleted-exfat.img")
(root / "carving.img").write_bytes(bytes(4093) + picture() + bytes(4096) + pdf())
(root / "expected.json").write_text(
    json.dumps(
        {"_HOTO.JPG": hashlib.sha256(jpeg).hexdigest(), "note.pdf": hashlib.sha256(document).hexdigest()},
        indent=2,
    )
)
print(root.resolve())
