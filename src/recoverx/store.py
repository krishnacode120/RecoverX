import json
import sqlite3
import uuid
import os
from pathlib import Path
from datetime import datetime, timezone

from .models import Candidate, RecoveryError
from .drives import memory_history


def protect_history(source_path, db_path):
    if memory_history(db_path):
        return
    source, db = Path(source_path).resolve(), Path(db_path).resolve()
    if source == db or (source.exists() and db.exists() and os.path.samefile(source, db)):
        raise RecoveryError("History database cannot be the source image or a hard link to it")


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, uri=memory_history(path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS scans (
                id TEXT PRIMARY KEY, source_identity TEXT NOT NULL, mode TEXT NOT NULL,
                status TEXT NOT NULL, checkpoint INTEGER NOT NULL DEFAULT 0,
                total INTEGER NOT NULL, started_at TEXT NOT NULL, error TEXT);
            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY, scan_id TEXT NOT NULL REFERENCES scans(id),
                dedup TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(scan_id, dedup));
            CREATE INDEX IF NOT EXISTS candidates_scan ON candidates(scan_id);
            CREATE TABLE IF NOT EXISTS recoveries (
                id INTEGER PRIMARY KEY, scan_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
                filename TEXT NOT NULL, sha256 TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL);
        """)
        self.db.commit()

    def new_scan(self, source, mode):
        scan_id = uuid.uuid4().hex
        self.db.execute(
            "INSERT INTO scans(id,source_identity,mode,status,total,started_at) VALUES(?,?,?,?,?,?)",
            (
                scan_id,
                json.dumps(source.identity, sort_keys=True),
                mode,
                "running",
                source.size,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.db.commit()
        return scan_id

    def get(self, scan_id):
        self.db.row_factory = sqlite3.Row
        row = self.db.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
        if row is None:
            raise RecoveryError("Unknown scan")
        return dict(row)

    def save(self, scan_id, candidate):
        key = json.dumps(
            [
                candidate.method,
                [(e.offset, e.length) for e in candidate.extents],
                candidate.name if not candidate.extents else candidate.kind,
            ]
        )
        self.db.execute(
            "INSERT OR IGNORE INTO candidates VALUES(?,?,?,?)",
            (candidate.id, scan_id, key, json.dumps(candidate.to_dict())),
        )

    def checkpoint(self, scan_id, offset, status="running", error=None):
        self.db.execute(
            "UPDATE scans SET checkpoint=?,status=?,error=? WHERE id=?", (offset, status, error, scan_id)
        )
        self.db.commit()

    def results(self, scan_id, offset=0, limit=200):
        rows = self.db.execute(
            "SELECT payload FROM candidates WHERE scan_id=? ORDER BY rowid LIMIT ? OFFSET ?",
            (scan_id, min(1000, limit), offset),
        )
        return [Candidate.from_dict(json.loads(r[0])) for r in rows]

    def candidate(self, scan_id, candidate_id):
        row = self.db.execute(
            "SELECT payload FROM candidates WHERE id=? AND scan_id=?", (candidate_id, scan_id)
        ).fetchone()
        if row is None:
            raise RecoveryError("Candidate does not belong to this scan")
        return Candidate.from_dict(json.loads(row[0]))

    def count(self, scan_id):
        return self.db.execute("SELECT COUNT(*) FROM candidates WHERE scan_id=?", (scan_id,)).fetchone()[0]

    def report(self, scan_id):
        scan = self.get(scan_id)
        count = self.count(scan_id)
        if count > 10000:
            raise RecoveryError("Portable report limit is 10,000 candidates; detailed results stay in SQLite")
        files = []
        for offset in range(0, count, 1000):
            for candidate in self.results(scan_id, offset, 1000):
                item = candidate.to_dict()
                # Reports intentionally omit local source paths and original directory paths.
                item.pop("original_path", None)
                files.append(item)
        return {
            "version": 1,
            "scan": {k: scan[k] for k in ("id", "mode", "status", "checkpoint", "total", "started_at")},
            "candidates": files,
            "privacy": "Contains filenames and offsets. Import only into a trusted viewer.",
        }

    def close(self):
        self.db.close()
