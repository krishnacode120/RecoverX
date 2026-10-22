"""Bounded read-only access. Image identity detects ordinary replacement, not adversarial tampering."""

import hashlib
import os
from pathlib import Path

from .models import RecoveryError

MAX_READ = 64 * 1024 * 1024


class ImageSource:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve(strict=True)
        if not self.path.is_file():
            raise RecoveryError("Select a regular raw disk image")
        self._file = self.path.open("rb", buffering=0)
        self._stat = os.fstat(self._file.fileno())
        self.size = self._stat.st_size
        self.errors: list[dict] = []
        self.identity = self.fingerprint()

    def assert_unchanged(self):
        current = os.fstat(self._file.fileno())
        path_stat = self.path.stat()
        fields = ("st_size", "st_mtime_ns", "st_ino", "st_dev")
        if any(
            getattr(current, f) != getattr(self._stat, f) or getattr(path_stat, f) != getattr(self._stat, f)
            for f in fields
        ):
            raise RecoveryError("Source changed since opening; restart analysis")

    def read(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0 or length > MAX_READ or offset + length > self.size:
            raise RecoveryError("Read outside image or configured memory bound")
        self.assert_unchanged()
        try:
            self._file.seek(offset)
            data = self._file.read(length)
            if len(data) != length:
                raise OSError("Short read")
            return data
        except OSError as exc:
            self.errors.append({"offset": offset, "length": length, "error": type(exc).__name__})
            raise RecoveryError(f"Unreadable range at byte {offset}, length {length}") from exc

    def fingerprint(self):
        n = min(self.size, 65536)
        digest = hashlib.sha256(self.read(0, n) + self.read(self.size - n, n)).hexdigest()
        return {
            "size": self.size,
            "mtime_ns": self._stat.st_mtime_ns,
            "sample_sha256": digest,
            "device": self._stat.st_dev,
            "inode": self._stat.st_ino,
        }

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
