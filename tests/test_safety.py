import struct

import pytest

from recoverx.engine import run_scan
from recoverx.models import RecoveryError
from recoverx.partitions import detect
from recoverx.source import ImageSource
from recoverx.store import Store
from tests.fixtures import exfat_image, fat_image


def test_corrupt_exfat_boot_fails_closed(tmp_path):
    path = tmp_path / "corrupt.img"
    exfat_image(path)
    with path.open("r+b") as f:
        f.seek(120)
        f.write(b"X")
    with ImageSource(path) as source, pytest.raises(RecoveryError, match="checksum"):
        run_scan(source, Store(":memory:"), "quick")


def test_corrupt_exfat_entry_set_not_exported(tmp_path):
    path = tmp_path / "corrupt.img"
    exfat_image(path)
    with path.open("r+b") as f:
        f.seek(32 * 512 + 32 + 32 + 20)
        f.write(struct.pack("<I", 8))
    store = Store(":memory:")
    with ImageSource(path) as source:
        scan_id = run_scan(source, store, "quick")
    assert store.count(scan_id) == 0


def test_cyclic_fat_directory_rejected(tmp_path):
    path = tmp_path / "cycle.img"
    fat_image(path, loop=True)
    with ImageSource(path) as source, pytest.raises(RecoveryError, match="Cyclic"):
        run_scan(source, Store(":memory:"), "quick")


def test_mbr_partition_outside_image_rejected(tmp_path):
    path = tmp_path / "mbr.img"
    data = bytearray(1024)
    data[510:512] = b"\x55\xaa"
    data[450] = 0x0C
    struct.pack_into("<II", data, 454, 1, 999999)
    path.write_bytes(data)
    with ImageSource(path) as source, pytest.raises(RecoveryError, match="outside"):
        detect(source)


def test_reader_enforces_bounds(tmp_path):
    path = tmp_path / "disk.img"
    path.write_bytes(bytes(1024))
    with ImageSource(path) as source:
        for offset, length in ((-1, 1), (0, -1), (1024, 1), (0, 65 * 1024 * 1024)):
            with pytest.raises(RecoveryError, match="outside"):
                source.read(offset, length)
