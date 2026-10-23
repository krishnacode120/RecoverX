"""Cross-check against ntfs-3g-created metadata, with simulated deletion flags.

Runs on Linux CI. All writes are to a newly created temporary image. This is not
a Windows deletion/TRIM test and does not qualify hardware recovery.
"""

import hashlib
import os
import shutil
import struct
import subprocess
import sys

import pytest

from recoverx.engine import run_scan
from recoverx.ntfs import NTFS, attributes, u16
from recoverx.partitions import Partition
from recoverx.restore import recover
from recoverx.source import ImageSource
from recoverx.store import Store


@pytest.mark.skipif(sys.platform != "linux", reason="Independent ntfs-3g corpus runs on Linux CI")
@pytest.mark.parametrize("length", [300, 12000])
def test_independently_formatted_ntfs(tmp_path, length):
    mkntfs, ntfscp = shutil.which("mkntfs"), shutil.which("ntfscp")
    if not mkntfs or not ntfscp:
        if os.environ.get("RECOVERX_REQUIRE_NTFS_TOOLS") == "1":
            pytest.fail("Linux CI must install ntfs-3g utilities")
        pytest.skip("Install ntfs-3g to run the independent metadata corpus")
    image = tmp_path / "independent.img"
    with image.open("xb") as stream:
        stream.truncate(64 * 1024 * 1024)
    subprocess.run([mkntfs, "-F", "-Q", str(image)], check=True, capture_output=True, timeout=60)
    original = bytes((i * 23 + 41) % 256 for i in range(length))
    content = tmp_path / "reference.bin"
    content.write_bytes(original)
    subprocess.run([ntfscp, str(image), str(content), "/recover-me.bin"], check=True,
                   capture_output=True, timeout=60)

    # Mark only the known test file's record and storage as free. Do not mount a
    # volume or invoke repair tools, and never accept a device path as input.
    patches = []
    with ImageSource(image) as source:
        fs = NTFS(source, Partition(0, source.size, "test", "independent"))
        found = []
        for index in range(16, fs.mft.size // fs.record_size):
            record = fs._record(index)
            attrs = list(attributes(record))
            if fs._filename(attrs, index) == "recover-me.bin":
                found.append((index, record, attrs))
        assert len(found) == 1
        index, record, attrs = found[0]
        flag_location = fs.mft.slices(index * fs.record_size + 22, 2)
        assert len(flag_location) == 1
        patches.append((flag_location[0].offset, struct.pack("<H", u16(record, 22) & ~1)))
        record_byte = index // 8
        bit_location = fs.record_bitmap.slices(record_byte, 1)[0].offset
        patches.append((bit_location, bytes([source.read(bit_location, 1)[0] & ~(1 << (index % 8))])))
        data = fs._one(attrs, 0x80)
        stream = fs._stream(data, record, index * fs.record_size)
        bitmap_changes = {}
        if data.nonresident:
            for extent in stream.extents:
                first = extent.offset // fs.cluster_size
                for cluster in range(first, first + extent.length // fs.cluster_size):
                    location = fs.bitmap.slices(cluster // 8, 1)[0].offset
                    old = bitmap_changes.get(location, source.read(location, 1)[0])
                    bitmap_changes[location] = old & ~(1 << (cluster % 8))
        patches.extend((offset, bytes([value])) for offset, value in bitmap_changes.items())
    with image.open("r+b") as output:
        for offset, value in patches:
            output.seek(offset)
            output.write(value)

    before = hashlib.sha256(image.read_bytes()).digest()
    output_dir = tmp_path / "recovered"
    output_dir.mkdir()
    store = Store(tmp_path / "scan.sqlite")
    try:
        with ImageSource(image) as source:
            scan_id = run_scan(source, store, "quick")
            candidates = [c for c in store.results(scan_id) if c.name == "recover-me.bin"]
            assert len(candidates) == 1
            assert candidates[0].sha256 == hashlib.sha256(original).hexdigest()
            recover(source, candidates[0], output_dir, allow_image_disk=True)
        assert (output_dir / "recover-me.bin").read_bytes() == original
    finally:
        store.close()
    assert hashlib.sha256(image.read_bytes()).digest() == before
