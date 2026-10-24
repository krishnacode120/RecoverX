import hashlib
from io import BytesIO
from types import SimpleNamespace
import zipfile

import pytest
from PIL import Image

from recoverx.models import Candidate, Control, Extent, RecoveryError, Status, Cancelled
from recoverx.preview import archive_listing, preview_content
from recoverx.source import ImageSource
from recoverx.store import Store


def populate(store, count=1):
    scan = store.new_scan(SimpleNamespace(identity={"test": True}, size=1000), "quick")
    for n in range(count):
        item = Candidate(f"file-{n:04}.txt", "txt", n, [], "fixture", Status.LIKELY)
        item.sha256 = hashlib.sha256(str(n).encode()).hexdigest() if n % 2 else None
        store.save(scan, item)
    store.checkpoint(scan, 1000, "complete")
    return scan


def test_search_sort_and_filter_cover_every_page():
    store = Store(":memory:")
    try:
        scan = populate(store, 405)
        assert [c.size for c in store.results(scan, 200, 200, sort="size", descending=True)] == list(
            range(204, 4, -1)
        )
        assert store.count(scan, extractable=True) == 202
        assert len(store.results(scan, 200, 200, extractable=True)) == 2
        assert store.results(scan, query="FILE-0404")[0].size == 404
        assert store.count(scan, query="%") == 0
        unicode = Candidate("Straße.txt", "txt", 4, [], "fixture")
        store.save(scan, unicode)
        assert store.results(scan, query="STRASSE")[0].name == unicode.name
        with pytest.raises(RecoveryError):
            store.results(scan, sort="name; DROP TABLE scans")
        assert store.count(scan) == 406
    finally:
        store.close()


def test_history_merge_preserves_existing_and_is_idempotent(tmp_path):
    source, target = Store(":memory:"), Store(tmp_path / "history.sqlite")
    try:
        first, second = populate(source, 3), populate(target, 2)
        candidate = source.results(first)[0]
        source.db.execute(
            "INSERT INTO recoveries(scan_id,candidate_id,filename,sha256,status,created_at) VALUES(?,?,?,?,?,?)",
            (first, candidate.id, "saved.txt", None, "failed", "2026-10-24"),
        )
        source.merge_into(target)
        source.merge_into(target)
        assert target.count(first) == 3 and target.count(second) == 2
        assert target.db.execute("SELECT COUNT(*) FROM recoveries").fetchone()[0] == 1
        source.db.execute("UPDATE scans SET error='conflict' WHERE id=?", (first,))
        other = populate(source, 1)
        with pytest.raises(RecoveryError, match="conflict"):
            source.merge_into(target)
        assert target.get(first)["error"] is None
        with pytest.raises(RecoveryError):
            target.get(other)
        assert source.count(first) == 3
    finally:
        source.close()
        target.close()


def zipped(count=1):
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for n in range(count):
            archive.writestr(f"../unsafe-{n}.txt", b"A" * 100000)
    return output.getvalue()


def test_archive_preview_never_decompresses_or_extracts(monkeypatch):
    data = zipped()

    def forbidden(*args, **kwargs):
        raise AssertionError("Member contents must not be opened")

    monkeypatch.setattr(zipfile.ZipFile, "open", forbidden)
    listing = archive_listing(data)
    assert "../unsafe-0.txt" in listing and "100,000" in listing
    assert "not extracted" in listing


def test_archive_limits_precede_zip_parsing():
    data = zipped(1001)
    with pytest.raises(RecoveryError, match="limits"):
        archive_listing(data)
    with pytest.raises(RecoveryError):
        archive_listing(b"PK\x03\x04garbage")


def test_preview_hash_bounds_and_cancellation(tmp_path):
    stream = BytesIO()
    Image.new("RGB", (32, 32), "blue").save(stream, "PNG")
    data = stream.getvalue()
    path = tmp_path / "preview.img"
    path.write_bytes(data)
    item = Candidate("image.png", "png", len(data), [Extent(0, len(data))], "fixture")
    item.sha256 = hashlib.sha256(data).hexdigest()
    with ImageSource(path) as source:
        assert preview_content(source, item)["png"].startswith(b"\x89PNG")
        control = Control()
        control.cancelled.set()
        with pytest.raises(Cancelled):
            preview_content(source, item, control)
        item.sha256 = "0" * 64
        with pytest.raises(RecoveryError, match="changed"):
            preview_content(source, item)
        item.size = 5 * 1024 * 1024
        with pytest.raises(RecoveryError, match="4 MiB"):
            preview_content(source, item)
