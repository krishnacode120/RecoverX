import hashlib

import pytest

from recoverx.engine import run_scan
from recoverx.models import Control, RecoveryError, Status
from recoverx.ntfs import Attribute, NTFS, decode_runs, fix_record
from recoverx.partitions import Partition, detect
from recoverx.restore import recover
from recoverx.source import ImageSource
from recoverx.store import Store
from tests.ntfs_fixture import make_ntfs, nonresident


def test_ntfs_recovers_resident_fixups_and_fragmented_runs(tmp_path):
    path = tmp_path / "ntfs.img"
    originals, _ = make_ntfs(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    output = tmp_path / "output"
    output.mkdir()
    store = Store(tmp_path / "history.sqlite")
    try:
        with ImageSource(path) as source:
            assert detect(source) == [Partition(0, source.size, "superfloppy", "Volume")]
            scan_id = run_scan(source, store, "quick")
            candidates = {c.name: c for c in store.results(scan_id)}
            for name, content in originals.items():
                candidate = candidates[name]
                assert candidate.status == Status.LIKELY
                assert candidate.sha256 == hashlib.sha256(content).hexdigest()
                recover(source, candidate, output, allow_image_disk=True)
                assert (output / name).read_bytes() == content
            assert "active.txt" not in candidates
            for name in ("reused.bin", "cleared.bin", "sparse.bin", "continuation.txt", "ntfs-record-19.bin"):
                assert candidates[name].status == Status.UNCERTAIN
                assert not candidates[name].sha256
                assert not candidates[name].extents
                with pytest.raises(RecoveryError):
                    recover(source, candidates[name], output, allow_image_disk=True)
            assert store.get(scan_id)["status"] == "complete"
    finally:
        store.close()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("field,value", [(11, b"\x00\x00"), (13, b"\x03"), (64, b"\x80")])
def test_bad_ntfs_geometry_rejected(tmp_path, field, value):
    path = tmp_path / "ntfs.img"
    make_ntfs(path)
    with path.open("r+b") as image:
        image.seek(field)
        image.write(value)
    with ImageSource(path) as source, pytest.raises(RecoveryError):
        NTFS(source, Partition(0, source.size, "raw", "test"))


@pytest.mark.parametrize(
    "mutation", ["truncated", "missing_end", "out_of_bounds", "sparse", "overlap", "uninitialized"]
)
def test_bad_mapping_pairs_rejected(mutation):
    raw = bytearray(nonresident(0x80, [(100, 1), (120, 1)], 1500))
    if mutation == "truncated":
        raw = raw[:66]
    elif mutation == "missing_end":
        raw = raw[:74]
    elif mutation == "out_of_bounds":
        raw[67:69] = (2000).to_bytes(2, "little", signed=True)
    elif mutation == "sparse":
        raw[64] = 2
    elif mutation == "overlap":
        raw[72:74] = (0).to_bytes(2, "little", signed=True)
    else:
        raw[56:64] = (10).to_bytes(8, "little")
    with pytest.raises(RecoveryError):
        decode_runs(Attribute(0x80, 0, bytes(raw)), 1024, 1024, 0)


def test_mft_bitmap_disagreement_blocks_resident_export(tmp_path):
    path = tmp_path / "ntfs.img"
    _, offsets = make_ntfs(path)
    from recoverx.ntfs import attributes

    raw = path.read_bytes()
    attrs = list(attributes(fix_record(raw[offsets[0] : offsets[0] + 1024])))
    bitmap = next(a for a in attrs if a.kind == 0xB0)
    byte = offsets[0] + bitmap.offset + 24 + 16 // 8
    with path.open("r+b") as image:
        image.seek(byte)
        image.write(b"\x21")
    with ImageSource(path) as source:
        candidates = list(
            NTFS(source, Partition(0, source.size, "raw", "test")).deleted(Control(), lambda *_: None)
        )
    candidate = next(c for c in candidates if c.name == "deleted-note.txt")
    assert candidate.status == Status.UNCERTAIN
    assert any("bitmap" in reason for reason in candidate.reasons)


def test_ntfs_cancellation_is_recorded(tmp_path):
    path = tmp_path / "ntfs.img"
    make_ntfs(path)
    store = Store(tmp_path / "history.sqlite")
    control = Control()
    control.cancelled.set()
    try:
        with ImageSource(path) as source:
            scan_id = run_scan(source, store, "quick", control)
        assert store.get(scan_id)["status"] == "cancelled"
    finally:
        store.close()


def test_ntfs_partition_offset_applies_to_every_extent(tmp_path):
    path = tmp_path / "volume.img"
    originals, _ = make_ntfs(path)
    offset = 4096
    disk = tmp_path / "disk.img"
    disk.write_bytes(bytes(offset) + path.read_bytes())
    with ImageSource(disk) as source:
        adapter = NTFS(source, Partition(offset, path.stat().st_size, "MBR", "test"))
        candidates = list(adapter.deleted(Control(), lambda *_: None))
        for candidate in candidates:
            if candidate.name in originals:
                data = b"".join(source.read(e.offset, e.length) for e in candidate.extents)
                assert data == originals[candidate.name]
                assert all(e.offset >= offset for e in candidate.extents)
