import hashlib
import json
import os

import pytest

from recoverx.engine import deep_scan, run_scan
from recoverx.formats import validate
from recoverx.models import Cancelled, Control, RecoveryError, Status
from recoverx.partitions import detect
from recoverx.restore import recover, safe_name
from recoverx.source import ImageSource
from recoverx.store import Store, protect_history
from tests.fixtures import exfat_image, fat_image, gpt_image, office_zip, pdf, picture


def scan_image(path, mode="deep"):
    store = Store(":memory:")
    with ImageSource(path) as source:
        scan_id = run_scan(source, store, mode)
    return store, scan_id


@pytest.mark.parametrize("kind", ["PNG", "JPEG", "GIF", "BMP", "WEBP"])
def test_real_image_decoder_and_boundary(tmp_path, kind):
    data = picture(kind)
    path = tmp_path / "disk.img"
    path.write_bytes(b"\0" * 4093 + data + b"\0" * 4000)
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    with ImageSource(path) as source:
        items = list(deep_scan(source, chunk_size=4096))
        item = next(c for c in items if c.sha256 == hashlib.sha256(data).hexdigest())
        output = tmp_path / "out"
        output.mkdir()
        result = recover(source, item, output, allow_image_disk=True)
        assert result["sha256"] == hashlib.sha256(data).hexdigest()
        assert (output / item.name).read_bytes() == data
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original


def test_fat_deleted_jpeg_hash_and_source_unchanged(tmp_path):
    path = tmp_path / "fat.img"
    original = fat_image(path)
    before = hashlib.sha256(path.read_bytes()).digest()
    store, scan_id = scan_image(path, "quick")
    candidate = store.results(scan_id)[0]
    assert candidate.name == "_HOTO.JPG"
    assert candidate.sha256 == hashlib.sha256(original).hexdigest()
    output = tmp_path / "output"
    output.mkdir()
    with ImageSource(path) as source:
        result = recover(source, candidate, output, allow_image_disk=True)
    assert result["status"] == "export verified"
    assert (output / candidate.name).read_bytes() == original
    assert hashlib.sha256(path.read_bytes()).digest() == before


@pytest.mark.parametrize("allocated,size", [(True, None), (False, 2048)])
def test_fat_never_guesses_deleted_chain(tmp_path, allocated, size):
    path = tmp_path / "fat.img"
    fat_image(path, allocated=allocated, size_override=size)
    store, scan_id = scan_image(path, "quick")
    candidate = store.results(scan_id)[0]
    assert candidate.status == Status.UNCERTAIN
    assert not candidate.extents and not candidate.sha256


@pytest.mark.parametrize("fragmented", [False, True])
def test_exfat_deleted_pdf_and_fragmented_extents(tmp_path, fragmented):
    path = tmp_path / "exfat.img"
    original = pdf() + b" " * 700
    exfat_image(path, original, fragmented=fragmented)
    store, scan_id = scan_image(path, "quick")
    candidate = store.results(scan_id)[0]
    assert candidate.name == "note.pdf"
    assert candidate.sha256 == hashlib.sha256(original).hexdigest()
    with ImageSource(path) as source:
        recover(source, candidate, tmp_path, allow_image_disk=True)
    assert (tmp_path / "note.pdf").read_bytes() == original
    if fragmented:
        assert candidate.extents[1].offset != candidate.extents[0].offset + 512


def test_exfat_reallocated_cluster_is_not_exportable(tmp_path):
    path = tmp_path / "exfat.img"
    exfat_image(path, allocated=True)
    store, scan_id = scan_image(path, "quick")
    assert not store.results(scan_id)[0].extents


@pytest.mark.parametrize("bad", [False, True])
def test_gpt_checksums(tmp_path, bad):
    path = tmp_path / "gpt.img"
    gpt_image(path, bad)
    with ImageSource(path) as source:
        if bad:
            with pytest.raises(RecoveryError, match="checksum"):
                detect(source)
        else:
            assert detect(source)[0].offset == 34 * 512


def test_containers_are_parsed():
    original = office_zip()
    length, kind, status, _ = validate("zip", original + b"other data")
    assert (length, kind, status) == (len(original), "docx", Status.VERIFIED)
    assert validate("pdf", pdf())[0] == len(pdf())
    assert validate("pdf", b"%PDF-1.7\nfake %%EOF")[0] == 0


def test_bad_crc_and_random_headers_rejected():
    data = bytearray(picture())
    data[40] ^= 1
    assert validate("png", bytes(data))[0] == 0
    assert validate("zip", b"PK\x03\x04" + os.urandom(128))[0] == 0
    assert validate("bmp", b"BM" + b"\xff" * 100)[0] == 0


def test_cancel_resume_and_dedup(tmp_path):
    path = tmp_path / "disk.img"
    path.write_bytes(picture() + bytes(3 * 1024 * 1024))
    store = Store(tmp_path / "history.sqlite")
    control = Control()

    def progress(done, total, phase):
        control.cancelled.set()

    with ImageSource(path) as source:
        scan_id = run_scan(source, store, control=control, progress=progress)
        assert store.get(scan_id)["status"] == "cancelled"
        assert store.get(scan_id)["checkpoint"] == 1024 * 1024
        run_scan(source, store, resume=scan_id)
    assert store.get(scan_id)["status"] == "complete"
    assert store.count(scan_id) == 1


def test_resume_rejects_changed_source(tmp_path):
    path = tmp_path / "disk.img"
    path.write_bytes(bytes(4096))
    store, scan_id = scan_image(path)
    path.write_bytes(bytes(4097))
    with ImageSource(path) as source, pytest.raises(RecoveryError, match="mismatch"):
        run_scan(source, store, resume=scan_id)


def test_export_conflict_cancel_and_hash_mismatch(tmp_path):
    path = tmp_path / "disk.img"
    path.write_bytes(picture())
    store, scan_id = scan_image(path)
    candidate = store.results(scan_id)[0]
    with ImageSource(path) as source:
        control = Control()
        control.cancelled.set()
        with pytest.raises(Cancelled):
            recover(source, candidate, tmp_path, control, allow_image_disk=True)
        assert not list(tmp_path.glob("*.partial"))
        candidate.sha256 = "0" * 64
        with pytest.raises(RecoveryError, match="hash"):
            recover(source, candidate, tmp_path, allow_image_disk=True)
        candidate.sha256 = hashlib.sha256(picture()).hexdigest()
        recover(source, candidate, tmp_path, allow_image_disk=True)
        with pytest.raises(RecoveryError, match="exists"):
            recover(source, candidate, tmp_path, allow_image_disk=True)


def test_destination_on_source_disk_blocked(tmp_path, monkeypatch):
    path = tmp_path / "disk.img"
    path.write_bytes(picture())
    store, scan_id = scan_image(path)
    monkeypatch.setattr("recoverx.restore.volume_disks", lambda _: {1})
    with ImageSource(path) as source, pytest.raises(RecoveryError, match="separate physical"):
        recover(source, store.results(scan_id)[0], tmp_path)


def test_empty_and_unsupported(tmp_path):
    path = tmp_path / "disk.img"
    path.write_bytes(b"")
    store, scan_id = scan_image(path)
    assert store.count(scan_id) == 0
    path.write_bytes(b"\xeb\x52\x90NTFS    " + bytes(4096))
    with pytest.raises(RecoveryError, match="No supported"):
        scan_image(path, "quick")


def test_unreadable_range_fails_scan_and_records_state(tmp_path):
    path = tmp_path / "disk.img"
    path.write_bytes(bytes(2 * 1024 * 1024))
    store = Store(":memory:")
    with ImageSource(path) as source:
        original = source.read

        def failing(offset, length):
            if offset >= 1024 * 1024 - 32:
                raise RecoveryError("Simulated unreadable sectors")
            return original(offset, length)

        source.read = failing
        with pytest.raises(RecoveryError, match="unreadable"):
            run_scan(source, store)
    assert store.db.execute("SELECT status FROM scans").fetchone()[0] == "failed"


def test_bounded_streaming_sparse_image(tmp_path):
    path = tmp_path / "sparse.img"
    with path.open("wb") as stream:
        stream.truncate(64 * 1024 * 1024)
    with ImageSource(path) as source:
        original, maximum = source.read, [0]

        def measured(offset, length):
            maximum[0] = max(maximum[0], length)
            return original(offset, length)

        source.read = measured
        assert list(deep_scan(source)) == []
        assert maximum[0] <= 1024 * 1024 + 32


def test_safe_names_and_portable_report(tmp_path):
    assert "/" not in safe_name("../../evil.exe")
    assert safe_name("CON.txt").startswith("recovered_")
    path = tmp_path / "disk.img"
    path.write_bytes(picture())
    store, scan_id = scan_image(path)
    report = json.dumps(store.report(scan_id))
    assert str(tmp_path) not in report
    assert "original_path" not in report


def test_source_replacement_detected(tmp_path):
    path = tmp_path / "disk.img"
    path.write_bytes(bytes(512))
    with ImageSource(path) as source:
        path.write_bytes(bytes(1024))
        with pytest.raises(RecoveryError, match="changed"):
            source.read(0, 1)


def test_history_cannot_write_to_hard_linked_source(tmp_path):
    source = tmp_path / "source.img"
    source.write_bytes(bytes(4096))
    alias = tmp_path / "history.sqlite"
    os.link(source, alias)
    with pytest.raises(RecoveryError, match="hard link"):
        protect_history(source, alias)
    assert source.read_bytes() == bytes(4096)
