"""Offscreen UI tests with mocked discovery; no Windows device is opened."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from recoverx.desktop import Window
from recoverx.drives import DriveSelection, memory_history
from recoverx.store import Store


def test_desktop_starts_in_memory_and_selects_drive_without_opening_it(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.chdir(tmp_path)
    window = Window()
    assert memory_history(window.db)
    assert list(tmp_path.iterdir()) == []
    drive = DriveSelection("C", 99, 8192, 512, 1024, 4096, "Mock disk", "TEST", "NTFS")
    monkeypatch.setattr("recoverx.desktop.list_drives", lambda: [drive])
    monkeypatch.setattr(
        "recoverx.desktop.open_source", lambda *_: (_ for _ in ()).throw(AssertionError("Opened"))
    )
    monkeypatch.setattr("recoverx.desktop.QInputDialog.getItem", lambda *args: (drive.label, True))
    monkeypatch.setattr(window, "execute", lambda operation, finished: finished(operation(None, None)))
    window.choose_drive()
    assert window.source_path == drive
    assert window.mode.currentText() == "quick"
    assert not window.consent.isChecked()
    assert not window.same_disk.isEnabled()
    assert list(tmp_path.iterdir()) == []
    window.close()
    app.processEvents()


def test_desktop_history_choice_opens_existing_external_history(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    window = Window()
    monkeypatch.setattr("recoverx.desktop.QFileDialog.getExistingDirectory", lambda *_: str(tmp_path))
    window.choose_history()
    assert window.db == str(tmp_path / "recoverx-history.sqlite")
    assert not memory_history(window.db)
    store = Store(window.db)
    store.close()
    window.close()
    app.processEvents()


def test_history_migration_retains_current_scan_and_filter(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from recoverx.models import Candidate

    app = QApplication.instance() or QApplication([])
    window = Window()
    scan = window._history_anchor.new_scan(SimpleNamespace(identity={"test": True}, size=1000), "quick")
    for n in range(205):
        window._history_anchor.save(scan, Candidate(f"note-{n}.txt", "txt", n, [], "test"))
    window._history_anchor.checkpoint(scan, 1000, "complete")
    window.scan_finished(scan)
    window.search.setText("note-204")
    window.apply_filters()
    assert len(window.items) == 1
    monkeypatch.setattr("recoverx.desktop.QFileDialog.getExistingDirectory", lambda *_: str(tmp_path))
    window.choose_history()
    assert window.scan_id == scan and len(window.items) == 1
    assert window._history_anchor.count(scan) == 205
    window.close()
    app.processEvents()


def test_history_guard_covers_previously_scanned_drives(monkeypatch, tmp_path):
    from types import SimpleNamespace

    app = QApplication.instance() or QApplication([])
    window = Window()
    window._history_anchor.new_scan(
        SimpleNamespace(identity={"type": "windows-drive", "disk_number": 99}, size=4096), "quick"
    )
    original = window.db
    monkeypatch.setattr("recoverx.desktop.QFileDialog.getExistingDirectory", lambda *_: str(tmp_path))
    monkeypatch.setattr("recoverx.desktop.volume_disks", lambda *_: {99})
    warnings = []
    monkeypatch.setattr("recoverx.desktop.QMessageBox.warning", lambda *args: warnings.append(args))
    window.choose_history()
    assert window.db == original and warnings
    assert not (tmp_path / "recoverx-history.sqlite").exists()
    window.close()
    app.processEvents()
