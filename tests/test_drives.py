from dataclasses import replace
from types import SimpleNamespace
import uuid

import pytest

from recoverx import drives
from recoverx.cli import main
from recoverx.drives import DriveSelection, DriveSource, protect_drive_output, protect_source_history
from recoverx.models import RecoveryError
from recoverx.store import Store


@pytest.fixture
def selected():
    return DriveSelection("C", 99, 8192, 512, 1024, 4096, "Disposable mock", "TEST", "NTFS")


@pytest.fixture
def raw_mock(monkeypatch, selected):
    class FakeRaw:
        def __init__(self, number, size, sector_size):
            assert (number, size, sector_size) == (99, 8192, 512)
            self.content = bytearray(bytes(range(256)) * 32)
            self.closed = False
            self.calls = []

        def read(self, offset, length):
            assert offset % 512 == 0 and length % 512 == 0
            assert 1024 <= offset <= offset + length <= 5120
            self.calls.append((offset, length))
            return bytes(self.content[offset:offset + length])

        def close(self):
            self.closed = True

    monkeypatch.setattr(drives, "select_drive", lambda _: selected)
    monkeypatch.setattr(drives, "WindowsRawSource", FakeRaw)


def test_selected_drive_bounds_alignment_and_identity(selected, raw_mock):
    with DriveSource(selected) as source:
        assert source.read(3, 1001) == bytes(source.raw.content[1027:2028])
        assert source.read(4095, 1) == bytes(source.raw.content[5119:5120])
        assert source.read(4096, 0) == b""
        for offset, length in [(-1, 1), (4090, 7), (0, -1), (0, 64 * 1024 * 1024 + 1)]:
            with pytest.raises(RecoveryError):
                source.read(offset, length)
        source.raw.content[1024] ^= 1
        with pytest.raises(RecoveryError, match="identity changed"):
            source.assert_unchanged()
    assert source.raw.closed


def test_changed_drive_rejected_before_open(selected, monkeypatch):
    monkeypatch.setattr(drives, "select_drive", lambda _: replace(selected, serial="DIFFERENT"))
    monkeypatch.setattr(drives, "WindowsRawSource", lambda *_: pytest.fail("Must not open changed drive"))
    with pytest.raises(RecoveryError, match="changed"):
        DriveSource(selected)


def test_same_physical_disk_rejected_even_with_another_partition(selected, monkeypatch, tmp_path):
    monkeypatch.setattr(drives, "volume_disks", lambda _: {99})
    with pytest.raises(RecoveryError, match="another physical disk"):
        protect_drive_output(selected, tmp_path)
    with pytest.raises(RecoveryError):
        protect_source_history(selected, tmp_path / "history.sqlite")
    protect_source_history(selected, ":memory:")
    monkeypatch.setattr(drives, "volume_disks", lambda _: {88})
    protect_drive_output(selected, tmp_path)


def test_shared_memory_history_survives_worker_connections_without_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    uri = f"file:recoverx-{uuid.uuid4().hex}?mode=memory&cache=shared"
    anchor = Store(uri)
    try:
        with_source = SimpleNamespace(identity={"test": True}, size=1024)
        writer = Store(uri)
        scan_id = writer.new_scan(with_source, "quick")
        writer.close()
        reader = Store(uri)
        assert reader.get(scan_id)["total"] == 1024
        reader.close()
        assert list(tmp_path.iterdir()) == []
    finally:
        anchor.close()


def test_cli_drive_requires_consent_before_discovery(monkeypatch, tmp_path):
    monkeypatch.setattr("recoverx.cli.select_drive", lambda _: pytest.fail("No consent"))
    db = tmp_path / "history.sqlite"
    assert main(["scan", "C:", "--drive", "--db", str(db)]) == 1
    assert not db.exists()


def test_cli_blocks_source_disk_database_before_device_open(selected, monkeypatch, tmp_path):
    monkeypatch.setattr("recoverx.cli.select_drive", lambda _: selected)
    monkeypatch.setattr("recoverx.cli.open_source", lambda _: pytest.fail("Unsafe history must fail first"))
    monkeypatch.setattr(drives, "volume_disks", lambda _: {99})
    db = tmp_path / "history.sqlite"
    assert main(["scan", "C:", "--drive", "--consent", "--db", str(db)]) == 1
    assert not db.exists()


def test_drive_discovery_only_lists_real_mounted_partitions(monkeypatch):
    monkeypatch.setattr(drives, "enumerate_devices", lambda: [{
        "number": 99, "name": "test", "serial": "S", "size": 8192, "sector_size": 512,
        "partitions": [
            {"mount": "C", "offset": 1024, "size": 4096, "filesystem": "NTFS"},
            {"mount": None, "offset": 0, "size": 512},
        ],
    }])
    assert [d.letter for d in drives.list_drives()] == ["C"]
    with pytest.raises(RecoveryError):
        drives.select_drive(r"C:\Windows")
