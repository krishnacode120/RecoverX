"""Bounded NTFS 3.x deleted-record recovery from read-only sources.

Disk structure references: Microsoft NTFS developer notes, linked in docs/NTFS.md.
No filesystem repair, guessed contiguous runs, sparse expansion, or decompression.
"""

from dataclasses import dataclass
from functools import lru_cache
import struct
import re

from .models import Candidate, Extent, RecoveryError, Status

MAX_RUNS = 65536
MAX_RECORDS = 16_000_000
STRIDE = 512


def u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def u64(data, offset):
    return struct.unpack_from("<Q", data, offset)[0]


def fix_record(raw):
    """Validate every transfer marker before restoring the saved sector tails."""
    if len(raw) < 512 or len(raw) % STRIDE or raw[:4] != b"FILE":
        raise RecoveryError("Invalid NTFS FILE record")
    usa, count = u16(raw, 4), u16(raw, 6)
    if count != len(raw) // STRIDE + 1 or usa < 42 or usa + count * 2 > STRIDE - 2:
        raise RecoveryError("Invalid NTFS update sequence array")
    marker = raw[usa:usa + 2]
    fixed = bytearray(raw)
    for i in range(1, count):
        tail = i * STRIDE - 2
        if raw[tail:tail + 2] != marker:
            raise RecoveryError("NTFS record has a torn-write fixup mismatch")
        fixed[tail:tail + 2] = raw[usa + i * 2:usa + i * 2 + 2]
    used, allocated, first = u32(fixed, 24), u32(fixed, 28), u16(fixed, 20)
    if allocated != len(raw) or not 48 <= first <= used <= allocated or first % 8:
        raise RecoveryError("Invalid NTFS record bounds")
    if usa + count * 2 > first:
        raise RecoveryError("NTFS fixup array overlaps attributes")
    return bytes(fixed)


@dataclass(frozen=True)
class Attribute:
    kind: int
    offset: int
    raw: bytes

    @property
    def nonresident(self):
        return self.raw[8] == 1

    @property
    def named(self):
        return self.raw[9] != 0

    @property
    def flags(self):
        return u16(self.raw, 12)

    @property
    def size(self):
        return u64(self.raw, 48) if self.nonresident else u32(self.raw, 16)

    def value(self):
        if self.nonresident:
            raise RecoveryError("Expected resident NTFS attribute")
        start, size = u16(self.raw, 20), u32(self.raw, 16)
        return self.raw[start:start + size]


def attributes(record):
    end, offset = u32(record, 24), u16(record, 20)
    while offset + 4 <= end:
        kind = u32(record, offset)
        if kind == 0xFFFFFFFF:
            return
        if offset + 16 > end:
            break
        length = u32(record, offset + 4)
        if length < 24 or length % 8 or offset + length > end:
            raise RecoveryError("Invalid NTFS attribute length")
        raw = record[offset:offset + length]
        form, names = raw[8], raw[9]
        minimum = 64 if form == 1 else 24
        if form not in (0, 1) or length < minimum:
            raise RecoveryError("Invalid NTFS attribute form")
        name_offset = u16(raw, 10)
        if names and (name_offset < minimum or name_offset + names * 2 > length):
            raise RecoveryError("Invalid NTFS attribute name")
        if form == 0:
            start, size = u16(raw, 20), u32(raw, 16)
            if start < minimum or start + size > length:
                raise RecoveryError("Resident NTFS value outside attribute")
            if names and start < name_offset + names * 2:
                raise RecoveryError("Overlapping NTFS name and value")
        else:
            pairs = u16(raw, 32)
            if pairs < minimum or pairs >= length:
                raise RecoveryError("Invalid NTFS mapping-pairs offset")
            if names and pairs < name_offset + names * 2:
                raise RecoveryError("Overlapping NTFS name and runlist")
        yield Attribute(kind, offset, raw)
        offset += length
    raise RecoveryError("NTFS attribute terminator missing")


def decode_runs(attr, clusters, cluster_size, volume_offset):
    if not attr.nonresident or attr.flags or u16(attr.raw, 34):
        raise RecoveryError("Compressed, encrypted, sparse or flagged NTFS data is unsupported")
    low, high = u64(attr.raw, 16), u64(attr.raw, 24)
    if low != 0 or high >= clusters:
        raise RecoveryError("NTFS data needs unsupported continuation records")
    if u64(attr.raw, 56) != attr.size:
        raise RecoveryError("NTFS data is not fully initialized")
    runs, pos, lcn, vcn = [], u16(attr.raw, 32), 0, 0
    while pos < len(attr.raw):
        header = attr.raw[pos]
        pos += 1
        if not header:
            break
        length_bytes, delta_bytes = header & 15, header >> 4
        if not 1 <= length_bytes <= 8 or not 1 <= delta_bytes <= 8:
            raise RecoveryError("Sparse or invalid NTFS mapping pair")
        if pos + length_bytes + delta_bytes > len(attr.raw):
            raise RecoveryError("Truncated NTFS runlist")
        count = int.from_bytes(attr.raw[pos:pos + length_bytes], "little")
        pos += length_bytes
        lcn += int.from_bytes(attr.raw[pos:pos + delta_bytes], "little", signed=True)
        pos += delta_bytes
        if not count or lcn < 0 or lcn + count > clusters or vcn + count > high + 1:
            raise RecoveryError("NTFS data run outside volume or VCN bounds")
        runs.append(Extent(volume_offset + lcn * cluster_size, count * cluster_size))
        vcn += count
        if len(runs) > MAX_RUNS:
            raise RecoveryError("NTFS run count exceeds defensive limit")
    else:
        raise RecoveryError("NTFS runlist terminator missing")
    if vcn != high + 1 or attr.size > vcn * cluster_size:
        raise RecoveryError("Incomplete NTFS data runlist")
    if u64(attr.raw, 40) != vcn * cluster_size:
        raise RecoveryError("NTFS allocated length disagrees with runlist")
    ordered = sorted(runs, key=lambda e: e.offset)
    if any(a.offset + a.length > b.offset for a, b in zip(ordered, ordered[1:])):
        raise RecoveryError("Overlapping NTFS data runs")
    return runs


class Stream:
    def __init__(self, source, extents, size):
        if size < 0 or sum(e.length for e in extents) < size:
            raise RecoveryError("Incomplete NTFS stream")
        self.source, self.extents, self.size = source, extents, size

    def slices(self, offset, length):
        if offset < 0 or length < 0 or offset + length > self.size:
            raise RecoveryError("NTFS stream read outside bounds")
        result, logical, remaining = [], 0, length
        for extent in self.extents:
            if remaining and offset < logical + extent.length:
                skip = max(0, offset - logical)
                take = min(remaining, extent.length - skip)
                result.append(Extent(extent.offset + skip, take))
                offset += take
                remaining -= take
            logical += extent.length
            if not remaining:
                break
        if remaining:
            raise RecoveryError("Missing NTFS stream extent")
        return result

    def read(self, offset, length):
        if length > 1024 * 1024:
            raise RecoveryError("NTFS stream read exceeds memory limit")
        return b"".join(self.source.read(e.offset, e.length) for e in self.slices(offset, length))


def resident_slices(mft, record_offset, record, attr):
    """Map restored resident bytes to original on-disk locations, including USA tails."""
    start = attr.offset + u16(attr.raw, 20)
    end, pos, result = start + attr.size, start, []
    usa = u16(record, 4)
    while pos < end:
        sector = pos // STRIDE + 1
        tail = sector * STRIDE - 2
        if pos < tail:
            take = min(end, tail) - pos
            result.extend(mft.slices(record_offset + pos, take))
        else:
            take = min(end, tail + 2) - pos
            result.extend(mft.slices(record_offset + usa + sector * 2 + pos - tail, take))
        pos += take
    return result


class NTFS:
    def __init__(self, source, partition):
        self.source, self.partition = source, partition
        boot = source.read(partition.offset, 512)
        if boot[3:11] != b"NTFS    " or boot[510:512] != b"\x55\xaa":
            raise RecoveryError("Invalid NTFS boot sector")
        sector, spc, sectors = u16(boot, 11), boot[13], u64(boot, 40)
        if sector not in (512, 4096) or not spc or spc & (spc - 1) or spc > 128:
            raise RecoveryError("Invalid NTFS sector/cluster geometry")
        self.cluster_size = sector * spc
        self.clusters = sectors // spc
        if not self.clusters or sectors * sector > partition.size:
            raise RecoveryError("NTFS volume exceeds source partition")
        encoding = int.from_bytes(boot[64:65], "little", signed=True)
        self.record_size = 1 << -encoding if -16 <= encoding < 0 else encoding * self.cluster_size
        if not 512 <= self.record_size <= 65536 or self.record_size % STRIDE:
            raise RecoveryError("Invalid NTFS record size")
        mft_lcn = u64(boot, 48)
        if mft_lcn >= self.clusters:
            raise RecoveryError("NTFS MFT is outside volume")
        offset = partition.offset + mft_lcn * self.cluster_size
        if offset + self.record_size > partition.offset + sectors * sector:
            raise RecoveryError("NTFS bootstrap record exceeds volume")
        record = fix_record(source.read(offset, self.record_size))
        attrs = self._base_attributes(record, required_in_use=True)
        data = self._one(attrs, 0x80)
        runs = decode_runs(data, self.clusters, self.cluster_size, partition.offset)
        if runs[0].offset != offset or runs[0].length < self.record_size:
            raise RecoveryError("NTFS MFT bootstrap location disagrees with data runs")
        if data.size % self.record_size or not 16 <= data.size // self.record_size <= MAX_RECORDS:
            raise RecoveryError("NTFS MFT size exceeds supported bounds")
        self.mft = Stream(source, runs, data.size)
        self.record_bitmap = self._stream(self._one(attrs, 0xB0), record, 0)
        if self.record_bitmap.size * 8 < self.mft.size // self.record_size:
            raise RecoveryError("NTFS MFT bitmap is truncated")
        volume = self._record(3)
        info = self._one(self._base_attributes(volume, True), 0x70).value()
        if len(info) < 12 or info[8] != 3 or info[9] not in (0, 1):
            raise RecoveryError("Only NTFS 3.0/3.1 metadata is supported")
        bitmap_record = self._record(6)
        self.bitmap = self._stream(
            self._one(self._base_attributes(bitmap_record, True), 0x80),
            bitmap_record,
            6 * self.record_size,
        )
        if self.bitmap.size * 8 < self.clusters:
            raise RecoveryError("NTFS volume allocation bitmap is truncated")
        self._bitmap_page = lru_cache(maxsize=16)(self._read_bitmap_page)

    @staticmethod
    def _one(attrs, kind):
        found = [a for a in attrs if a.kind == kind and not a.named]
        if len(found) != 1:
            raise RecoveryError("Missing or split NTFS metadata attribute")
        return found[0]

    @staticmethod
    def _base_attributes(record, required_in_use=False):
        if u64(record, 32):
            raise RecoveryError("NTFS extension record is unsupported")
        if required_in_use and not u16(record, 22) & 1:
            raise RecoveryError("Required NTFS metadata record is not in use")
        attrs = list(attributes(record))
        if any(a.kind == 0x20 for a in attrs):
            raise RecoveryError("NTFS attribute-list continuation is unsupported")
        return attrs

    def _record(self, number):
        return fix_record(self.mft.read(number * self.record_size, self.record_size))

    def _stream(self, attr, record, record_offset):
        if attr.flags:
            raise RecoveryError("Flagged NTFS stream is unsupported")
        if attr.nonresident:
            runs = decode_runs(attr, self.clusters, self.cluster_size, self.partition.offset)
        else:
            runs = resident_slices(self.mft, record_offset, record, attr)
        return Stream(self.source, runs, attr.size)

    def _read_bitmap_page(self, which, page):
        stream = self.bitmap if which == "volume" else self.record_bitmap
        start = page * 65536
        return stream.read(start, min(65536, stream.size - start))

    def _allocated(self, which, index):
        byte = index // 8
        page = self._bitmap_page(which, byte // 65536)
        return bool(page[byte % 65536] & (1 << (index % 8)))

    def _filename(self, attrs, number):
        names = []
        for attr in attrs:
            if attr.kind != 0x30 or attr.nonresident:
                continue
            value = attr.value()
            if len(value) < 66 or not value[64] or 66 + value[64] * 2 > len(value):
                raise RecoveryError("Invalid NTFS filename attribute")
            namespace = value[65]
            if namespace > 3:
                raise RecoveryError("Invalid NTFS filename namespace")
            name = value[66:66 + value[64] * 2].decode("utf-16-le", errors="strict")
            names.append((namespace == 2, name))
        return sorted(names)[0][1] if names else f"ntfs-record-{number}.bin"

    def deleted(self, control, progress):
        total = self.mft.size // self.record_size
        for number in range(16, total):
            control.check()
            if number % 256 == 0:
                progress(number * self.record_size, self.mft.size, "Reading NTFS deleted records")
            raw = self.mft.read(number * self.record_size, self.record_size)
            if raw[:4] != b"FILE" or u16(raw, 22) & 3:
                continue
            candidate = Candidate(
                f"ntfs-record-{number}.bin", "bin", 0, [], "NTFS deleted record",
                Status.UNCERTAIN, [f"NTFS MFT record {number}"],
            )
            try:
                record = fix_record(raw)
                attrs = list(attributes(record))
                candidate.name = self._filename(attrs, number)
                extension = candidate.name.rsplit(".", 1)[-1].lower() if "." in candidate.name else "bin"
                candidate.kind = extension if re.fullmatch("[a-z0-9]{1,32}", extension) else "bin"
                self._base_attributes(record)
                if self._allocated("records", number):
                    raise RecoveryError("NTFS record bitmap says this record is allocated")
                data = self._one(attrs, 0x80)
                if data.size > self.partition.size:
                    raise RecoveryError("Declared NTFS file size exceeds volume")
                candidate.size = data.size
                stream = self._stream(data, record, number * self.record_size)
                if data.nonresident:
                    for extent in stream.extents:
                        start = (extent.offset - self.partition.offset) // self.cluster_size
                        count = extent.length // self.cluster_size
                        for cluster in range(start, start + count):
                            control.check()
                            if self._allocated("volume", cluster):
                                raise RecoveryError("Deleted file clusters have been reallocated")
                candidate.extents = stream.slices(0, stream.size)
                candidate.status = Status.LIKELY
                candidate.reasons.extend([
                    "Surviving unnamed data stream and allocation checks passed",
                    "Original filename when preserved; directory hierarchy is not reconstructed",
                    "Current bytes may differ from the original; SSD TRIM cannot be reversed",
                ])
            except (RecoveryError, UnicodeError) as exc:
                candidate.extents = []
                candidate.status = Status.UNCERTAIN
                candidate.reasons.append(str(exc))
            yield candidate
        progress(self.mft.size, self.mft.size, "NTFS metadata complete")
