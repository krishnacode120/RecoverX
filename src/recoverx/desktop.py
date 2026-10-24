"""Native interface; every disk operation runs outside the GUI thread."""

import json
from pathlib import Path
import sys
import sqlite3
import uuid

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .engine import run_scan
from .models import Control, RecoveryError, Status
from .preview import preview_content
from .restore import image_device, recover, write_json_exclusive
from .drives import (
    DriveSelection,
    list_drives,
    memory_history,
    open_source,
    protect_drive_output,
    protect_source_history,
)
from .store import Store, protect_history
from .windows import WindowsRawSource, enumerate_devices, volume_disks


class Worker(QThread):
    progress = Signal(int, int, str)
    result = Signal(object)
    error = Signal(str)

    def __init__(self, operation, control):
        super().__init__()
        self.operation, self.control = operation, control

    def run(self):
        try:
            # Qt int signals are 32-bit: report progress as bounded per-mille; actual bytes in text.
            def progress(done, total, phase):
                self.progress.emit(
                    int(1000 * done / total) if total else 0, 1000, f"{phase} · {done:,} / {total:,} bytes"
                )

            self.result.emit(self.operation(self.control, progress))
        except Exception as exc:
            self.error.emit(str(exc))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RecoverX · Local recovery workspace")
        self.resize(1160, 790)
        self.db = f"file:recoverx-{uuid.uuid4().hex}?mode=memory&cache=shared"
        self._history_anchor = Store(self.db)
        self.source_path, self.scan_id, self.page = None, None, 0
        self.worker, self.control, self.items = None, Control(), []
        shell = QWidget()
        self.setCentralWidget(shell)
        layout = QVBoxLayout(shell)
        title = QLabel("RECOVERX    /    Your files. Your machine.")
        title.setStyleSheet("font-size: 24px; font-weight: 700; padding: 16px")
        layout.addWidget(title)
        note = QLabel(
            "Read-only analysis · No cloud account · Nothing uploaded · NTFS upgrade (experimental)"
        )
        note.setStyleSheet("color: #8da9cb; padding: 0 16px 12px")
        layout.addWidget(note)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.setup_scan()
        self.setup_devices()
        self.setup_history()
        self.setup_help()
        self.bar, self.phase = (
            QProgressBar(),
            QLabel("Ready. Select a disposable image or an authorized source."),
        )
        self.bar.setRange(0, 1000)
        layout.addWidget(self.bar)
        layout.addWidget(self.phase)
        controls = QHBoxLayout()
        self.pause = QPushButton("Pause")
        self.pause.clicked.connect(self.toggle_pause)
        self.cancel = QPushButton("Cancel")
        self.cancel.clicked.connect(lambda: self.control.cancelled.set())
        controls.addWidget(self.pause)
        controls.addWidget(self.cancel)
        layout.addLayout(controls)
        self.pause.setEnabled(False)
        self.cancel.setEnabled(False)
        self.setStyleSheet("""
            QWidget {background:#0b1220; color:#dce8fa; font-size:13px;}
            QPushButton {background:#173052; border:1px solid #28466b; padding:10px 16px; border-radius:6px;}
            QPushButton:hover {background:#20529b;} QPushButton:disabled {color:#65748a;}
            QTableWidget, QTextEdit, QComboBox {background:#111e31; border:1px solid #253650;}
            QHeaderView::section {background:#17283e; padding:8px; border:0;}
            QTabBar::tab {padding:12px 20px;} QTabBar::tab:selected {color:#5ba8ff;}
            QProgressBar {border:1px solid #253650; height:18px; text-align:center;}
            QProgressBar::chunk {background:#2784ee;}
        """)

    def setup_scan(self):
        page, box = QWidget(), QVBoxLayout()
        page.setLayout(box)
        self.tabs.addTab(page, "Recovery workspace")
        row = QHBoxLayout()
        choose = QPushButton("Open raw image")
        choose.clicked.connect(self.choose_image)
        choose_drive = QPushButton("Select Windows drive…")
        choose_drive.clicked.connect(self.choose_drive)
        self.image_label = QLabel("No source selected")
        self.mode = QComboBox()
        self.mode.addItems(["quick", "deep"])
        self.start = QPushButton("Start scan")
        self.start.clicked.connect(self.start_scan)
        for widget in (choose, choose_drive, self.image_label, self.mode, self.start):
            row.addWidget(widget)
        box.addLayout(row)
        self.consent = QCheckBox(
            "I am authorized to analyze this source. I understand recovery is not guaranteed."
        )
        box.addWidget(self.consent)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search filenames across all pages")
        self.status_filter = QComboBox()
        self.status_filter.addItem("All content statuses", "")
        for status in Status:
            self.status_filter.addItem(status.value, status.value)
        self.sort = QComboBox()
        for label, value in (
            ("Discovery order", "discovery"),
            ("Name", "name"),
            ("Size", "size"),
            ("Type", "kind"),
            ("Content status", "status"),
        ):
            self.sort.addItem(label, value)
        self.descending = QCheckBox("Descending")
        self.extractable = QCheckBox("Extractable only")
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(250)
        self.filter_timer.timeout.connect(self.apply_filters)
        self.search.textChanged.connect(lambda: self.filter_timer.start())
        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        self.sort.currentIndexChanged.connect(self.apply_filters)
        self.descending.toggled.connect(self.apply_filters)
        self.extractable.toggled.connect(self.apply_filters)
        for widget in (self.search, self.status_filter, self.sort, self.descending, self.extractable):
            filters.addWidget(widget)
        box.addLayout(filters)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Select / name", "Type", "Bytes", "Content status", "Evidence"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.preview)
        box.addWidget(self.table)
        pages = QHBoxLayout()
        previous, following, select = (
            QPushButton("Previous 200"),
            QPushButton("Next 200"),
            QPushButton("Select extractable on page"),
        )
        previous.clicked.connect(lambda: self.change_page(-1))
        following.clicked.connect(lambda: self.change_page(1))
        select.clicked.connect(self.select_page)
        self.page_label = QLabel("No scan")
        for w in (previous, following, select, self.page_label):
            pages.addWidget(w)
        box.addLayout(pages)
        self.details, self.thumbnail = QTextEdit(), QLabel()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(140)
        box.addWidget(self.details)
        box.addWidget(self.thumbnail)
        preview_button = QPushButton("Preview selected image or archive")
        preview_button.clicked.connect(self.load_preview)
        box.addWidget(preview_button)
        self.same_disk = QCheckBox(
            "Allow same-disk output for a disposable image file only (never a selected drive)"
        )
        box.addWidget(self.same_disk)
        row = QHBoxLayout()
        restore, report = QPushButton("Recover selected to…"), QPushButton("Export scan report…")
        restore.clicked.connect(self.restore_selected)
        report.clicked.connect(self.export_report)
        row.addWidget(restore)
        row.addWidget(report)
        box.addLayout(row)

    def setup_devices(self):
        page, box = QWidget(), QVBoxLayout()
        page.setLayout(box)
        self.tabs.addTab(page, "Devices & imaging")
        box.addWidget(
            QLabel(
                "Create an image on another physical disk before analysis. No device opens until you explicitly start imaging."
            )
        )
        self.devices = QComboBox()
        box.addWidget(self.devices)
        refresh = QPushButton("Discover Windows storage devices")
        refresh.clicked.connect(self.discover)
        box.addWidget(refresh)
        self.device_info = QTextEdit()
        self.device_info.setReadOnly(True)
        box.addWidget(self.device_info)
        self.device_consent = QCheckBox(
            "I am authorized to read the selected physical disk and save its contents locally."
        )
        box.addWidget(self.device_consent)
        image = QPushButton("Create verified raw image…")
        image.clicked.connect(self.create_image)
        box.addWidget(image)

    def setup_history(self):
        page, box = QWidget(), QVBoxLayout()
        page.setLayout(box)
        self.tabs.addTab(page, "History & resume")
        choose_history = QPushButton("Choose folder for persistent history…")
        choose_history.clicked.connect(self.choose_history)
        box.addWidget(choose_history)
        self.history = QComboBox()
        box.addWidget(self.history)
        refresh, load, resume = (
            QPushButton("Refresh local history"),
            QPushButton("View results"),
            QPushButton("Resume deep scan with selected image"),
        )
        refresh.clicked.connect(self.refresh_history)
        load.clicked.connect(self.load_history)
        resume.clicked.connect(lambda: self.start_scan(resume=True))
        for w in (refresh, load, resume):
            box.addWidget(w)
        box.addWidget(
            QLabel(
                "History starts in memory and is lost on exit unless you choose a persistent history folder.\n"
                "For drive scans, history and output must be on another physical disk.\n"
                "Deep scans resume from a committed block checkpoint. Quick scans restart."
            )
        )
        box.addStretch()
        self.refresh_history()

    def setup_help(self):
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText(
            "RecoverX NTFS upgrade\n\n"
            "1. Work from an image where possible. Never install or save onto media containing deleted files.\n"
            "2. Select a Windows drive or raw image and consent. Quick scan reads NTFS/FAT32/exFAT metadata.\n"
            "   A live drive can change during scanning. Use an offline image for consistent evidence.\n"
            "3. Review evidence. A filename or signature is not proof of recoverable content.\n"
            "4. Select candidates and choose a different destination. Existing files are never replaced.\n"
            "5. Export a JSON report to view in the web dashboard. Reports contain names and offsets; review before sharing.\n\n"
            "Limits: FAT32 single-cluster deleted files; exFAT root files with provable extents; 32 MiB carving limit. "
            "NTFS supports base-record resident/plain nonresident data; continuation, sparse, compressed, "
            "and encrypted streams are unresolved. ext4, EWF, virtual disks and fragmented carving are unsupported. "
            "No recovery of overwritten or TRIM-discarded bytes. Hardware failures need specialist imaging.\n\n"
            "Previews show metadata, bounded image thumbnails and ZIP/Office member listings. Recovered scripts, macros and binaries never run.\n"
            "No local network listener starts with this application. No silent privilege elevation.\n\n"
            "History starts in memory; select an external folder to retain it."
        )
        self.tabs.addTab(help_text, "Guide & settings")

    def busy(self):
        return self.worker is not None and self.worker.isRunning()

    def execute(self, operation, finished):
        if self.busy():
            return
        self.control = Control()
        self.worker = Worker(operation, self.control)
        self.worker.progress.connect(self.on_progress)
        self.worker.error.connect(lambda message: QMessageBox.warning(self, "RecoverX", message))
        self.worker.result.connect(finished)
        self.worker.finished.connect(self.idle)
        self.start.setEnabled(False)
        self.pause.setEnabled(True)
        self.cancel.setEnabled(True)
        self.worker.start()

    def idle(self):
        self.start.setEnabled(True)
        self.pause.setEnabled(False)
        self.cancel.setEnabled(False)
        self.pause.setText("Pause")
        self.refresh_history()

    def on_progress(self, done, total, phase):
        self.bar.setValue(done)
        self.phase.setText(phase)

    def toggle_pause(self):
        if self.control.paused.is_set():
            self.control.paused.clear()
            self.pause.setText("Pause")
        else:
            self.control.paused.set()
            self.pause.setText("Resume")

    def choose_image(self):
        if self.busy():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose raw disk image", "", "Raw images (*.img *.raw *.dd);;All files (*)"
        )
        if path:
            try:
                protect_history(path, self.db)
            except RecoveryError as exc:
                QMessageBox.warning(self, "Source conflict", str(exc))
                return
            self.source_path = path
            self.scan_id, self.items = None, []
            self.table.setRowCount(0)
            self.same_disk.setEnabled(True)
            self.image_label.setText(Path(path).name)
            self.consent.setChecked(False)

    def choose_drive(self):
        if self.busy():
            return

        def finished(drives):
            if not drives:
                QMessageBox.information(self, "No drives", "No supported Windows drive mappings were found.")
                return
            labels = [drive.label for drive in drives]
            label, accepted = QInputDialog.getItem(
                self, "Select source drive", "Drive to read:", labels, 0, False
            )
            if not accepted:
                return
            drive = drives[labels.index(label)]
            try:
                if not memory_history(self.db):
                    protect_drive_output(drive, Path(self.db).parent)
            except RecoveryError as exc:
                QMessageBox.warning(self, "History destination", str(exc))
                return
            self.source_path, self.scan_id, self.items = drive, None, []
            self.table.setRowCount(0)
            self.image_label.setText(drive.label)
            self.mode.setCurrentText("quick")
            self.consent.setChecked(False)
            self.same_disk.setChecked(False)
            self.same_disk.setEnabled(False)
            self.phase.setText(
                "Drive selected. Consent and start to open it read-only; administrator rights may be needed."
            )

        self.execute(lambda *_: list_drives(), finished)

    def choose_history(self):
        if self.busy():
            return
        folder = QFileDialog.getExistingDirectory(
            self, "History folder (another physical disk for drive scans)"
        )
        if not folder:
            return
        target = str(Path(folder) / "recoverx-history.sqlite")
        if not memory_history(self.db) and Path(self.db).resolve() == Path(target).resolve():
            return
        anchor = None
        try:
            disks = self._history_anchor.source_disk_numbers()
            if disks and disks & volume_disks(folder):
                raise RecoveryError("History must be saved off every scanned physical source disk")
            if isinstance(self.source_path, DriveSelection):
                protect_drive_output(self.source_path, folder)
            elif self.source_path:
                protect_history(self.source_path, target)
            anchor = Store(target)
            self._history_anchor.merge_into(anchor)
        except (RecoveryError, OSError, sqlite3.Error) as exc:
            if anchor is not None:
                anchor.close()
            QMessageBox.warning(self, "History folder", str(exc))
            return
        self._history_anchor.close()
        self._history_anchor, self.db = anchor, target
        self.refresh_history()
        if self.scan_id:
            self.load_results()
        self.phase.setText(f"History saved to {target}, including this session's scans and results.")

    def start_scan(self, checked=False, resume=False):
        if self.busy():
            return
        if not self.source_path or not self.consent.isChecked():
            QMessageBox.information(
                self, "Select and authorize", "Choose a drive or image and check the authorization box first."
            )
            return
        path, mode, db = self.source_path, self.mode.currentText(), self.db
        resume_id = self.history.currentData() if resume else None
        if resume:
            mode = "deep"

        def operation(control, progress):
            with open_source(path) as source:
                protect_source_history(source, db)
                store = Store(db)
                try:
                    return run_scan(source, store, mode, control, progress, resume_id)
                finally:
                    store.close()

        self.execute(operation, self.scan_finished)

    def scan_finished(self, scan_id):
        self.scan_id, self.page = scan_id, 0
        self.load_results()
        self.tabs.setCurrentIndex(0)

    def load_results(self):
        if not self.scan_id:
            return
        store = Store(self.db)
        try:
            filters = self.result_filters()
            count, state = store.count(self.scan_id, **filters), store.get(self.scan_id)["status"]
            self.page = min(self.page, max(0, (count - 1) // 200))
            self.items = store.results(
                self.scan_id,
                self.page * 200,
                200,
                sort=self.sort.currentData(),
                descending=self.descending.isChecked(),
                **filters,
            )
        finally:
            store.close()
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.items))
        for row, item in enumerate(self.items):
            for col, text in enumerate(
                [item.name, item.kind, str(item.size), item.status, "; ".join(item.reasons)]
            ):
                cell = QTableWidgetItem(text)
                if col == 0:
                    cell.setCheckState(Qt.CheckState.Unchecked)
                    if not item.sha256:
                        cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                self.table.setItem(row, col, cell)
        self.table.blockSignals(False)
        self.details.clear()
        self.thumbnail.clear()
        self.page_label.setText(f"{count} matching candidates · page {self.page + 1} · {state}")
        self.phase.setText(f"Scan {state}. Review the evidence before extraction.")

    def change_page(self, delta):
        if not self.scan_id or self.busy():
            return
        if delta > 0 and len(self.items) < 200:
            return
        self.page = max(0, self.page + delta)
        self.load_results()

    def select_page(self):
        for row, item in enumerate(self.items):
            if item.sha256:
                self.table.item(row, 0).setCheckState(Qt.CheckState.Checked)

    def result_filters(self):
        return {
            "query": self.search.text(),
            "status": self.status_filter.currentData(),
            "extractable": self.extractable.isChecked(),
        }

    def apply_filters(self, *_):
        if self.busy():
            return
        self.page = 0
        self.load_results()

    def preview(self):
        row = self.table.currentRow()
        self.thumbnail.clear()
        if 0 <= row < len(self.items):
            self.details.setPlainText(json.dumps(self.items[row].to_dict(), indent=2))

    def load_preview(self):
        row = self.table.currentRow()
        if self.busy() or not self.source_path or not self.scan_id or not 0 <= row < len(self.items):
            return
        item, path, scan_id, db = self.items[row], self.source_path, self.scan_id, self.db

        def operation(control, progress):
            store = Store(db)
            try:
                identity = json.loads(store.get(scan_id)["source_identity"])
            finally:
                store.close()
            with open_source(path) as source:
                if source.identity != identity:
                    raise RecoveryError("Selected source does not match this scan")
                return preview_content(source, item, control)

        def finished(result):
            current = self.table.currentRow()
            if not 0 <= current < len(self.items) or self.items[current].id != item.id:
                return
            if "png" in result:
                pixmap = QPixmap()
                pixmap.loadFromData(result["png"], "PNG")
                self.thumbnail.setPixmap(pixmap)
            else:
                self.details.setPlainText(result["text"])

        self.execute(operation, finished)

    def assert_source(self, source):
        store = Store(self.db)
        try:
            if json.loads(store.get(self.scan_id)["source_identity"]) != source.identity:
                raise RecoveryError("The selected image does not match this scan")
        finally:
            store.close()

    def restore_selected(self):
        if self.busy() or not self.scan_id or not self.source_path:
            return
        selected = [
            item
            for row, item in enumerate(self.items)
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked
        ]
        if not selected:
            QMessageBox.information(self, "Selection", "Select at least one extractable candidate.")
            return
        destination = QFileDialog.getExistingDirectory(self, "Choose recovery destination")
        if not destination:
            return
        path, allow, scan_id, db = self.source_path, self.same_disk.isChecked(), self.scan_id, self.db

        def operation(control, progress):
            outcomes = []
            with open_source(path) as source:
                protect_source_history(source, db)
                store = Store(db)
                try:
                    if json.loads(store.get(scan_id)["source_identity"]) != source.identity:
                        raise RecoveryError("Selected source does not match the scan")
                    for item in selected:
                        control.check()
                        try:
                            outcomes.append(recover(source, item, destination, control, progress, allow))
                        except RecoveryError as exc:
                            outcomes.append({"filename": item.name, "status": "failed", "error": str(exc)})
                    return outcomes
                finally:
                    store.close()

        self.execute(operation, lambda outcomes: self.details.setPlainText(json.dumps(outcomes, indent=2)))

    def export_report(self):
        if not self.scan_id or self.busy():
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Export report (contains filenames)", "recoverx-report.json", "JSON (*.json)"
        )
        if target:
            try:
                if isinstance(self.source_path, DriveSelection):
                    protect_drive_output(self.source_path, Path(target).parent)
            except RecoveryError as exc:
                QMessageBox.warning(self, "Report destination", str(exc))
                return
            store = Store(self.db)
            try:
                write_json_exclusive(target, store.report(self.scan_id))
                self.phase.setText("Report exported. No data was uploaded.")
            except Exception as exc:
                QMessageBox.warning(self, "Report", str(exc))
            finally:
                store.close()

    def discover(self):
        def finished(devices):
            self.devices.clear()
            for d in devices:
                self.devices.addItem(
                    f"Disk {d['number']} · {d['name']} · {d['size']:,} bytes · {d['bus']}", d
                )
            self.device_info.setPlainText(json.dumps(devices, indent=2))

        self.execute(lambda *_: enumerate_devices(), finished)

    def create_image(self):
        if self.busy() or not self.devices.currentData() or not self.device_consent.isChecked():
            return
        device = self.devices.currentData()
        target, _ = QFileDialog.getSaveFileName(
            self, "Save on another physical disk", "disk.img", "Raw image (*.img)"
        )
        if not target:
            return

        def operation(control, progress):
            current = next((d for d in enumerate_devices() if d["number"] == device["number"]), None)
            if current != device:
                raise RecoveryError("Device information changed; rediscover and authorize again")
            with WindowsRawSource(device["number"], device["size"], device["sector_size"]) as source:
                return image_device(source, target, control, progress)

        self.execute(operation, lambda result: self.device_info.setPlainText(json.dumps(result, indent=2)))

    def refresh_history(self):
        store = Store(self.db)
        try:
            rows = store.db.execute(
                "SELECT id,mode,status,started_at FROM scans ORDER BY started_at DESC LIMIT 200"
            ).fetchall()
            self.history.clear()
            for row in rows:
                self.history.addItem(f"{row[3]} · {row[1]} · {row[2]} · {row[0][:8]}", row[0])
        finally:
            store.close()

    def load_history(self):
        if self.history.currentData() and not self.busy():
            self.scan_finished(self.history.currentData())

    def closeEvent(self, event):
        if self.busy():
            self.control.cancelled.set()
            self.phase.setText("Cancelling safely. Close again after the worker stops.")
            event.ignore()
        else:
            self._history_anchor.close()
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RecoverX")
    window = Window()
    window.show()
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(500, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
