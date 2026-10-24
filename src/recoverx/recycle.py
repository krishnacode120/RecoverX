"""Pair surviving deleted Recycle Bin records without treating metadata as proof of content."""

import hashlib
import json
from pathlib import PureWindowsPath
import re
import struct

from .models import Candidate, RecoveryError


def parse_metadata(data):
    if len(data) < 24:
        raise RecoveryError("Truncated Recycle Bin metadata")
    version, size, deleted = struct.unpack_from("<QQQ", data)
    if not deleted or size > (1 << 63) - 1:
        raise RecoveryError("Invalid Recycle Bin size or deletion time")
    if version == 1 and len(data) == 544:
        text = data[24:].decode("utf-16-le", errors="strict")
        if "\0" not in text:
            raise RecoveryError("Unterminated Recycle Bin path")
        path, padding = text.split("\0", 1)
        if padding.strip("\0"):
            raise RecoveryError("Unexpected Recycle Bin path padding")
    elif version == 2 and len(data) >= 30:
        units = struct.unpack_from("<I", data, 24)[0]
        if not 2 <= units <= 32768 or len(data) != 28 + units * 2:
            raise RecoveryError("Invalid Recycle Bin path length")
        text = data[28:].decode("utf-16-le", errors="strict")
        if not text.endswith("\0") or "\0" in text[:-1]:
            raise RecoveryError("Unterminated Recycle Bin path")
        path = text[:-1]
    else:
        raise RecoveryError("Unsupported Recycle Bin metadata version or length")
    parsed = PureWindowsPath(path)
    if (
        not re.match(r"^[A-Za-z]:\\", path) or not parsed.name
        or any(part in (".", "..") for part in path.split("\\"))
        or any(ord(ch) < 32 for ch in path)
        or any(ch in path[3:] for ch in '<>:"/|?*')
    ):
        raise RecoveryError("Unsafe or nonabsolute Recycle Bin original path")
    return size, path, parsed.name


def enrich_recycle_bin(source, store, scan_id, start, end, control):
    rows = store.db.execute(
        "SELECT payload FROM candidates WHERE scan_id=? "
        "AND json_extract(payload, '$.method')='NTFS deleted record' "
        "AND (json_extract(payload, '$.name') GLOB '$[Ii]*' "
        "OR json_extract(payload, '$.name') GLOB '$[Rr]*') LIMIT 20001",
        (scan_id,),
    ).fetchall()
    if len(rows) > 20000:
        return
    groups = {}
    for (raw,) in rows:
        control.check()
        item = Candidate.from_dict(json.loads(raw))
        if not item.original_path or not item.sha256 or not item.extents:
            continue
        if any(e.offset < start or e.offset + e.length > end for e in item.extents):
            continue
        path = PureWindowsPath(item.original_path)
        if len(path.parts) != 4 or path.parts[1].casefold() != "$recycle.bin":
            continue
        if not re.fullmatch(r"S-1-(?:\d+-)+\d+", path.parts[2], re.IGNORECASE):
            continue
        key = (str(path.parent).casefold(), item.name[2:].casefold())
        groups.setdefault(key, []).append(item)
    for items in groups.values():
        control.check()
        metadata = [i for i in items if i.name[:2].casefold() == "$i"]
        contents = [i for i in items if i.name[:2].casefold() == "$r"]
        if len(metadata) != 1 or len(contents) != 1:
            continue
        info, item = metadata[0], contents[0]
        if not 24 <= info.size <= 65564:
            continue
        data = b"".join(source.read(e.offset, e.length) for e in info.extents)
        if hashlib.sha256(data).hexdigest() != info.sha256:
            continue
        try:
            size, path, name = parse_metadata(data)
        except (RecoveryError, UnicodeError):
            continue
        if size != item.size:
            continue
        item.reasons.append(f"Recycle Bin metadata paired with {item.name}; original name is metadata evidence")
        item.name, item.original_path = name, path
        extension = name.rsplit(".", 1)[-1].lower() if "." in name else "bin"
        item.kind = extension if re.fullmatch("[a-z0-9]{1,32}", extension) else "bin"
        store.db.execute(
            "UPDATE candidates SET payload=? WHERE id=? AND scan_id=?",
            (json.dumps(item.to_dict()), item.id, scan_id),
        )
