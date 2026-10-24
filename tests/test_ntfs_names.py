import hashlib
import struct

import pytest

from recoverx.engine import run_scan
from recoverx.models import RecoveryError
from recoverx.ntfs import attributes, fix_record
from recoverx.recycle import parse_metadata
from recoverx.restore import recover
from recoverx.source import ImageSource
from recoverx.store import Store
from tests.ntfs_fixture import filename, make_ntfs, record, resident


def named(name, parent=5, sequence=1):
    attr = bytearray(filename(name))
    struct.pack_into("<Q", attr, 24, (sequence << 48) | parent)
    return bytes(attr)


def metadata(path, size, version=2):
    encoded = (path + "\0").encode("utf-16-le")
    header = struct.pack("<QQQ", version, size, 133000000000000000)
    return header + (
        encoded.ljust(520, b"\0") if version == 1 else struct.pack("<I", len(encoded) // 2) + encoded
    )


def corpus(path, mutation=""):
    originals, offsets = make_ntfs(path)
    image = bytearray(path.read_bytes())
    content = b"Original holiday notes.\r\n"
    original_path = r"C:\Users\Alice\Documents\holiday.txt"
    records = {
        5: record([], 5, True, True),
        25: record([named("Documents")], 25, True, True),
        26: record([named("$Recycle.Bin")], 26, True, True),
        27: record([named("S-1-5-21-1000", 26)], 27, True, True),
        16: record([named("deleted-note.txt", 25), resident(0x80, originals["deleted-note.txt"])], 16),
        28: record([named("$IABC123.txt", 27), resident(0x80, metadata(original_path, len(content)))], 28),
        29: record([named("$RABC123.txt", 27), resident(0x80, content)], 29),
    }
    if mutation == "stale":
        records[25] = record([named("Documents")], 25, True, True)
        raw = bytearray(records[25])
        struct.pack_into("<H", raw, 16, 2)
        records[25] = bytes(raw)
    elif mutation == "cycle":
        records[25] = record([named("Documents", 25)], 25, True, True)
    elif mutation == "outside":
        records[16] = record(
            [named("deleted-note.txt", 9999), resident(0x80, originals["deleted-note.txt"])], 16
        )
    elif mutation == "duplicate":
        records[30] = records[28]
    elif mutation == "size":
        records[28] = record([named("$IABC123.txt", 27), resident(0x80, metadata(original_path, 999))], 28)
    for number, raw in records.items():
        offset = (4 + number if number < 16 else 32 + number - 16) * 1024
        image[offset : offset + 1024] = raw
    attrs = list(attributes(fix_record(image[offsets[0] : offsets[0] + 1024])))
    bitmap = next(a for a in attrs if a.kind == 0xB0)
    for number in (25, 26, 27):
        image[offsets[0] + bitmap.offset + 24 + number // 8] |= 1 << (number % 8)
    path.write_bytes(image)
    return content, original_path


def test_paths_and_recycle_names_recover_exact_bytes(tmp_path):
    path = tmp_path / "ntfs.img"
    content, original = corpus(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    store = Store(":memory:")
    output = tmp_path / "output"
    output.mkdir()
    try:
        with ImageSource(path) as source:
            scan = run_scan(source, store, "quick")
            files = {c.name: c for c in store.results(scan)}
            assert files["deleted-note.txt"].original_path == r"\Documents\deleted-note.txt"
            item = files["holiday.txt"]
            assert item.original_path == original
            assert item.sha256 == hashlib.sha256(content).hexdigest()
            recover(source, item, output, allow_image_disk=True)
            assert (output / "holiday.txt").read_bytes() == content
            assert all("original_path" not in c for c in store.report(scan)["candidates"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    finally:
        store.close()


@pytest.mark.parametrize("mutation", ["stale", "cycle", "outside"])
def test_unprovable_parent_path_does_not_block_content(tmp_path, mutation):
    path = tmp_path / "ntfs.img"
    corpus(path, mutation)
    store = Store(":memory:")
    try:
        with ImageSource(path) as source:
            scan = run_scan(source, store, "quick")
            item = store.results(scan, query="deleted-note.txt")[0]
            assert item.original_path is None and item.sha256
    finally:
        store.close()


@pytest.mark.parametrize("mutation", ["duplicate", "size"])
def test_ambiguous_recycle_metadata_does_not_rename(tmp_path, mutation):
    path = tmp_path / "ntfs.img"
    corpus(path, mutation)
    store = Store(":memory:")
    try:
        with ImageSource(path) as source:
            scan = run_scan(source, store, "quick")
            assert store.results(scan, query="$RABC123.txt")
            assert not store.results(scan, query="holiday.txt")
    finally:
        store.close()


@pytest.mark.parametrize("version", [1, 2])
def test_recycle_metadata_versions(version):
    path = r"C:\folder\original.txt"
    assert parse_metadata(metadata(path, 123, version)) == (123, path, "original.txt")


@pytest.mark.parametrize(
    "path", [r"C:\folder\..\escape.txt", r"relative\file.txt", r"C:\file:stream", "C:\\bad\0name"]
)
def test_recycle_metadata_rejects_unsafe_paths(path):
    with pytest.raises(RecoveryError):
        parse_metadata(metadata(path, 123))
