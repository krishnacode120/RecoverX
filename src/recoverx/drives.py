"""Explicit Windows drive selection and bounded read-only access.

Mounted-volume scans are not snapshots. Export hashes detect changed candidate
bytes, but cannot prove historical authenticity or recover discarded SSD data.
"""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from .models import RecoveryError
from .source import ImageSource, MAX_READ
from .windows import WindowsRawSource, enumerate_devices, volume_disks


@dataclass(frozen=True)
class DriveSelection:
    letter: str
    disk_number: int
    disk_size: int
    sector_size: int
    offset: int
    size: int
    name: str
    serial: str
    filesystem: str

    @property
    def label(self):
        return f"{self.letter}: · {self.filesystem} · {self.name} · {self.size:,} bytes"


def list_drives():
    result = []
    for disk in enumerate_devices():
        for part in disk.get("partitions", []):
            letter = str(part.get("mount") or "").upper()
            if not re.fullmatch("[A-Z]", letter):
                continue
            result.append(DriveSelection(
                letter, int(disk["number"]), int(disk["size"]), int(disk["sector_size"]),
                int(part["offset"]), int(part["size"]), str(disk["name"]),
                str(disk.get("serial") or ""), str(part.get("filesystem") or "Unknown"),
            ))
    return result


def select_drive(letter):
    if not re.fullmatch(r"[A-Za-z]:?", letter):
        raise RecoveryError("Use a Windows drive letter, for example C:")
    match = [drive for drive in list_drives() if drive.letter == letter[0].upper()]
    if len(match) != 1:
        raise RecoveryError("Drive is unavailable or does not map to one supported physical partition")
    return match[0]


def memory_history(path):
    return str(path) == ":memory:" or bool(
        re.fullmatch(r"file:recoverx-[0-9a-f]{32}\?mode=memory&cache=shared", str(path))
    )


def protect_drive_output(drive, directory):
    directory = Path(directory).resolve(strict=True)
    if not directory.is_dir():
        raise RecoveryError("Choose an existing output folder")
    if drive.disk_number in volume_disks(directory):
        raise RecoveryError("Choose a folder on another physical disk; another partition is not enough")


def protect_source_history(source, db):
    if hasattr(source, "disk_number") and not memory_history(db):
        protect_drive_output(source, Path(db).resolve().parent)


class DriveSource:
    def __init__(self, selection):
        if not isinstance(selection, DriveSelection):
            raise RecoveryError("Drive must be explicitly selected")
        current = select_drive(selection.letter)
        if current != selection:
            raise RecoveryError("Drive identity or geometry changed; select it again")
        if (
            selection.sector_size not in (512, 4096)
            or selection.offset < 0
            or selection.size <= 0
            or selection.offset % selection.sector_size
            or selection.size % selection.sector_size
            or selection.offset + selection.size > selection.disk_size
        ):
            raise RecoveryError("Invalid selected partition geometry")
        self.selection = selection
        self.disk_number, self.size = selection.disk_number, selection.size
        self.raw = WindowsRawSource(selection.disk_number, selection.disk_size, selection.sector_size)
        try:
            self.boot_hash = hashlib.sha256(self.read(0, 512)).hexdigest()
            self.identity = {
                "type": "windows-drive",
                "disk_number": self.disk_number,
                "disk_serial": selection.serial,
                "offset": selection.offset,
                "size": selection.size,
                "boot_sha256": self.boot_hash,
            }
        except BaseException:
            self.raw.close()
            raise

    def read(self, offset, length):
        if offset < 0 or length < 0 or length > MAX_READ or offset + length > self.size:
            raise RecoveryError("Drive read outside selected partition or memory bounds")
        sector = self.selection.sector_size
        result = bytearray()
        while length:
            take = min(length, 1024 * 1024)
            physical = self.selection.offset + offset
            start = physical // sector * sector
            finish = ((physical + take + sector - 1) // sector) * sector
            data = self.raw.read(start, finish - start)
            result.extend(data[physical - start:physical - start + take])
            offset += take
            length -= take
        return bytes(result)

    def assert_unchanged(self):
        if hashlib.sha256(self.read(0, 512)).hexdigest() != self.boot_hash:
            raise RecoveryError("Drive boot identity changed; stop and reselect the source")

    def close(self):
        self.raw.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def open_source(selection):
    return DriveSource(selection) if isinstance(selection, DriveSelection) else ImageSource(selection)
