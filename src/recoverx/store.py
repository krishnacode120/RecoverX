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
        self.db.execute("PRAGMA temp_store=MEMORY")
        self.db.create_function("casefold", 1, lambda value: str(value or "").casefold(), deterministic=True)
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

    @staticmethod
    def _filter(scan_id, query="", kind="", status="", extractable=False):
        clauses, args = ["scan_id=?"], [scan_id]
        for field, value in (("name", query), ("kind", kind), ("status", status)):
            if value:
                if field == "name":
                    clauses.append("instr(casefold(json_extract(payload, '$.name')), casefold(?)) > 0")
                else:
                    clauses.append(f"json_extract(payload, '$.{field}')=?")
                args.append(value)
        if extractable:
            clauses.append("json_extract(payload, '$.sha256') IS NOT NULL")
        return " AND ".join(clauses), args

    def results(self, scan_id, offset=0, limit=200, *, sort="discovery", descending=False, **filters):
        orders = {
            "discovery": "rowid",
            "name": "casefold(json_extract(payload, '$.name'))",
            "size": "CAST(json_extract(payload, '$.size') AS INTEGER)",
            "kind": "json_extract(payload, '$.kind')",
            "status": "json_extract(payload, '$.status')",
        }
        if sort not in orders or offset < 0 or limit < 1:
            raise RecoveryError("Invalid result ordering or page")
        where, args = self._filter(scan_id, **filters)
        direction = "DESC" if descending else "ASC"
        rows = self.db.execute(
            f"SELECT payload FROM candidates WHERE {where} "
            f"ORDER BY {orders[sort]} {direction}, rowid ASC LIMIT ? OFFSET ?",
            (*args, min(1000, limit), offset),
        )
        return [Candidate.from_dict(json.loads(r[0])) for r in rows]

    def candidate(self, scan_id, candidate_id):
        row = self.db.execute(
            "SELECT payload FROM candidates WHERE id=? AND scan_id=?", (candidate_id, scan_id)
        ).fetchone()
        if row is None:
            raise RecoveryError("Candidate does not belong to this scan")
        return Candidate.from_dict(json.loads(row[0]))

    def count(self, scan_id, **filters):
        where, args = self._filter(scan_id, **filters)
        return self.db.execute(f"SELECT COUNT(*) FROM candidates WHERE {where}", args).fetchone()[0]

    def merge_into(self, destination):
        """Merge atomically, retaining existing scans and rejecting conflicting IDs."""
        self.db.commit()
        with destination.db:
            for table, columns in (
                ("scans", "id,source_identity,mode,status,checkpoint,total,started_at,error"),
                ("candidates", "id,scan_id,dedup,payload"),
            ):
                for row in self.db.execute(f"SELECT {columns} FROM {table}"):
                    row = tuple(row)
                    existing = destination.db.execute(
                        f"SELECT {columns} FROM {table} WHERE id=?", (row[0],)
                    ).fetchone()
                    if existing is not None:
                        if tuple(existing) != row:
                            raise RecoveryError("History conflict: the same ID contains different data")
                    else:
                        placeholders = ",".join("?" for _ in row)
                        destination.db.execute(
                            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", row
                        )
            columns = "scan_id,candidate_id,filename,sha256,status,created_at"
            for row in self.db.execute(f"SELECT {columns} FROM recoveries"):
                row = tuple(row)
                match = " AND ".join(f"{column} IS ?" for column in columns.split(","))
                if destination.db.execute(f"SELECT 1 FROM recoveries WHERE {match}", row).fetchone() is None:
                    destination.db.execute(
                        f"INSERT INTO recoveries ({columns}) VALUES (?,?,?,?,?,?)", row
                    )

    def source_disk_numbers(self):
        return {
            identity["disk_number"]
            for (raw,) in self.db.execute("SELECT source_identity FROM scans")
            if (identity := json.loads(raw)).get("type") == "windows-drive"
        }

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
