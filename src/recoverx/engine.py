import hashlib
import json

from .filesystems import ExFAT, FAT32
from .formats import MAX_CANDIDATE, REGISTRY, validate
from .models import Candidate, Cancelled, Control, Extent, RecoveryError, Status, no_progress
from .ntfs import NTFS
from .recycle import enrich_recycle_bin
from .partitions import Partition, detect
from .native import find_offsets


def candidate_hash(source, candidate, control):
    digest = hashlib.sha256()
    nonzero = False
    for extent in candidate.extents:
        for offset in range(extent.offset, extent.offset + extent.length, 1024 * 1024):
            control.check()
            data = source.read(offset, min(1024 * 1024, extent.offset + extent.length - offset))
            digest.update(data)
            nonzero = nonzero or any(data)
    if candidate.method == "NTFS deleted record" and candidate.size and not nonzero:
        candidate.status = Status.UNCERTAIN
        candidate.reasons.append("All bytes are zero; possible cleared or discarded data, not proof of TRIM")
        candidate.extents = []
        return None
    return digest.hexdigest()


def deep_scan(
    source,
    control=None,
    progress=no_progress,
    chunk_size=1024 * 1024,
    start=0,
    max_candidate=MAX_CANDIDATE,
    checkpoint=None,
):
    control = control or Control()
    if not 4096 <= chunk_size <= 16 * 1024 * 1024 or not 1024 <= max_candidate <= MAX_CANDIDATE:
        raise RecoveryError("Invalid scanning memory limits")
    overlap = max(len(f.magic) + f.displacement for f in REGISTRY)
    for base in range(start, source.size, chunk_size):
        control.check()
        end = min(base + chunk_size, source.size)
        begin = max(0, base - overlap)
        block = source.read(begin, min(source.size, end + overlap) - begin)
        hits = set()
        for fmt in REGISTRY:
            for p in find_offsets(block, fmt.magic):
                control.check()
                offset = begin + p - fmt.displacement
                if not base <= offset < end or (offset, fmt.kind) in hits:
                    continue
                hits.add((offset, fmt.kind))
                if len(hits) > 4096:
                    raise RecoveryError("Signature density exceeds defensive limit")
                raw = source.read(offset, min(max_candidate, source.size - offset))
                length, kind, status, reason = validate(fmt.kind, raw)
                candidate = Candidate(
                    f"{kind}_{offset:012x}.{kind}",
                    kind,
                    length,
                    [Extent(offset, length)] if length else [],
                    "signature carving",
                    status,
                    [reason, "Carving assumes contiguous bytes; original name and path unknown"],
                )
                # Include the signature offset even when no extent is safe to extract.
                if not length:
                    candidate.reasons.append(f"Signature offset: {offset}")
                else:
                    candidate.sha256 = hashlib.sha256(raw[:length]).hexdigest()
                yield candidate
        if checkpoint:
            checkpoint(end)
        progress(end, source.size, "Scanning raw bytes")


def run_scan(source, store, mode="deep", control=None, progress=no_progress, resume=None, sector_size=512):
    control = control or Control()
    if mode not in ("quick", "deep"):
        raise RecoveryError("Scan mode must be quick or deep")
    if resume and hasattr(source, "disk_number"):
        raise RecoveryError("Mounted drive scans cannot resume across sessions; use an unchanged disk image")
    scan_id = resume or store.new_scan(source, mode)
    scan = store.get(scan_id)
    if json.loads(scan["source_identity"]) != source.identity or scan["mode"] != mode:
        raise RecoveryError("Checkpoint source or mode mismatch")
    if resume and mode != "deep":
        raise RecoveryError("Only deep scans support persisted resume")
    if scan["status"] == "complete":
        return scan_id
    cursor = scan["checkpoint"]

    def checkpoint(offset):
        nonlocal cursor
        cursor = offset
        store.checkpoint(scan_id, offset)

    try:
        if mode == "deep":
            iterator = deep_scan(source, control, progress, start=cursor, checkpoint=checkpoint)
            for candidate in iterator:
                store.save(scan_id, candidate)
        else:
            partitions = detect(source, sector_size) or [Partition(0, source.size, "raw", "Volume")]
            supported = 0
            for partition in partitions:
                control.check()
                if partition.size < 512:
                    continue
                boot = source.read(partition.offset, 512)
                if boot[3:11] == b"NTFS    ":
                    adapter = NTFS(source, partition)
                elif boot[3:11] == b"EXFAT   ":
                    adapter = ExFAT(source, partition)
                elif boot[82:90] == b"FAT32   ":
                    adapter = FAT32(source, partition)
                else:
                    continue
                supported += 1
                for candidate in adapter.deleted(control, progress):
                    if candidate.status in (Status.LIKELY, Status.VERIFIED) and (
                        candidate.extents or candidate.size == 0
                    ):
                        candidate.sha256 = candidate_hash(source, candidate, control)
                    store.save(scan_id, candidate)
                if isinstance(adapter, NTFS):
                    enrich_recycle_bin(
                        source, store, scan_id, partition.offset, partition.offset + partition.size, control
                    )
            if not supported:
                raise RecoveryError(
                    "No supported NTFS/FAT32/exFAT filesystem found; deep scan remains available"
                )
        control.check()
        source.assert_unchanged()
        store.checkpoint(scan_id, source.size, "complete")
        progress(source.size, source.size, "Complete")
    except Cancelled:
        store.checkpoint(scan_id, cursor, "cancelled")
    except Exception as exc:
        store.checkpoint(scan_id, cursor, "failed", type(exc).__name__)
        raise
    return scan_id
