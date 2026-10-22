"""Conservative FAT32/exFAT deleted-entry recovery. No guesses about freed FAT chains."""

import math
import struct

from .models import Candidate, Control, Extent, RecoveryError, Status, no_progress


def u16(b, p):
    return struct.unpack_from("<H", b, p)[0]


def u32(b, p):
    return struct.unpack_from("<I", b, p)[0]


def u64(b, p):
    return struct.unpack_from("<Q", b, p)[0]


class FAT32:
    def __init__(self, source, partition):
        self.source, self.partition = source, partition
        b = source.read(partition.offset, 512)
        self.sector = u16(b, 11)
        self.spc, self.reserved, self.fats = b[13], u16(b, 14), b[16]
        self.fat_sectors, self.root, total = u32(b, 36), u32(b, 44), u32(b, 32)
        if (
            self.sector not in (512, 1024, 2048, 4096)
            or self.spc not in (1, 2, 4, 8, 16, 32, 64, 128)
            or self.fats not in (1, 2)
            or not self.reserved
            or not self.fat_sectors
            or u16(b, 17)
            or u16(b, 22)
            or b[510:512] != b"\x55\xaa"
        ):
            raise RecoveryError("Invalid or unsupported FAT32 geometry")
        self.cluster_size = self.sector * self.spc
        self.data_sector = self.reserved + self.fats * self.fat_sectors
        self.count = (total - self.data_sector) // self.spc
        if (
            self.count < 1
            or total * self.sector > partition.size
            or (self.count + 2) * 4 > self.fat_sectors * self.sector
        ):
            raise RecoveryError("FAT32 geometry exceeds partition")
        flags = u16(b, 40)
        self.mirrored = not bool(flags & 0x80)
        active = (flags & 15) if flags & 0x80 else 0
        if active >= self.fats:
            raise RecoveryError("Invalid active FAT")
        self.fat_offset = partition.offset + (self.reserved + active * self.fat_sectors) * self.sector

    def cluster_offset(self, cluster):
        if not 2 <= cluster < self.count + 2:
            raise RecoveryError("Cluster outside filesystem")
        return self.partition.offset + self.data_sector * self.sector + (cluster - 2) * self.cluster_size

    def next_cluster(self, cluster):
        self.cluster_offset(cluster)
        value = u32(self.source.read(self.fat_offset + cluster * 4, 4), 0) & 0x0FFFFFFF
        if self.mirrored and self.fats == 2:
            mirror = self.fat_offset + self.fat_sectors * self.sector + cluster * 4
            if u32(self.source.read(mirror, 4), 0) & 0x0FFFFFFF != value:
                raise RecoveryError("FAT copies disagree; allocation cannot be trusted")
        return value

    def chain(self, first, control):
        seen = set()
        while first < 0x0FFFFFF8:
            control.check()
            self.cluster_offset(first)
            if first in seen or len(seen) >= 131072:
                raise RecoveryError("Cyclic or excessive cluster chain")
            seen.add(first)
            yield first
            first = self.next_cluster(first)

    def deleted(self, control=None, progress=no_progress):
        control = control or Control()
        queue, seen = [(self.root, "")], set()
        entries = 0
        while queue:
            first, path = queue.pop()
            if first in seen:
                continue
            seen.add(first)
            if len(seen) > 32768:
                raise RecoveryError("Directory traversal bound exceeded")
            ended = False
            for cluster in self.chain(first, control):
                block = self.source.read(self.cluster_offset(cluster), self.cluster_size)
                for p in range(0, len(block), 32):
                    control.check()
                    entries += 1
                    if entries > 2_000_000:
                        raise RecoveryError("Directory entry limit exceeded")
                    e = block[p : p + 32]
                    if e[0] == 0:
                        ended = True
                        break
                    if e[11] == 15 or e[11] & 8 or e[0] == 46:
                        continue
                    deleted = e[0] == 0xE5
                    name = (b"_" + e[1:8] if deleted else e[:8]).decode("cp437", "replace").strip()
                    ext = e[8:11].decode("cp437", "replace").strip()
                    name += ("." + ext) if ext else ""
                    start = (u16(e, 20) << 16) | u16(e, 26)
                    if e[11] & 16:
                        if not deleted:
                            queue.append((start, path + name + "/"))
                        continue
                    if not deleted:
                        continue
                    size = u32(e, 28)
                    candidate = Candidate(
                        name, ext.lower() or "unknown", size, [], "FAT32 metadata", original_path=path + name
                    )
                    if size == 0:
                        candidate.reasons = ["Deleted empty file; original first filename character lost"]
                        candidate.status = Status.LIKELY
                    elif (
                        2 <= start < self.count + 2
                        and size <= self.cluster_size
                        and self.next_cluster(start) == 0
                    ):
                        candidate.extents = [Extent(self.cluster_offset(start), size)]
                        candidate.status = Status.LIKELY
                        candidate.reasons = [
                            "Single-cluster deleted entry; cluster currently unallocated",
                            "Unallocated does not prove content was not overwritten",
                        ]
                    else:
                        candidate.reasons = [
                            "Cluster chain missing, allocated, invalid, or requires multiple clusters",
                            "Contiguous allocation is not assumed; use deep scan",
                        ]
                    yield candidate
                progress(
                    min(self.partition.size, entries * 32), self.partition.size, "Reading FAT32 directories"
                )
                if ended:
                    break


class ExFAT:
    def __init__(self, source, partition):
        self.source, self.partition = source, partition
        b = source.read(partition.offset, 512)
        if b[3:11] != b"EXFAT   " or not 9 <= b[108] <= 12 or b[109] > 16 - b[108]:
            raise RecoveryError("Invalid exFAT boot geometry")
        self.sector = 1 << b[108]
        boot_region = source.read(partition.offset, 12 * self.sector)
        checksum = 0
        for index, byte in enumerate(boot_region[: 11 * self.sector]):
            if index not in (106, 107, 112):
                checksum = (((checksum & 1) << 31) + (checksum >> 1) + byte) & 0xFFFFFFFF
        if any(u32(boot_region, i) != checksum for i in range(11 * self.sector, 12 * self.sector, 4)):
            raise RecoveryError("exFAT boot checksum mismatch")
        self.cluster_size = self.sector << b[109]
        self.fat_sector, self.fat_length = u32(b, 80), u32(b, 84)
        self.heap, self.count, self.root = u32(b, 88), u32(b, 92), u32(b, 96)
        self.active = u16(b, 106) & 1
        if b[110] not in (1, 2) or self.active >= b[110]:
            raise RecoveryError("Invalid exFAT FAT count")
        self.fat_offset = partition.offset + (self.fat_sector + self.active * self.fat_length) * self.sector
        if (
            u64(b, 72) * self.sector > partition.size
            or self.count < 1
            or (self.count + 2) * 4 > self.fat_length * self.sector
            or self.fat_sector < 24
            or self.heap < self.fat_sector + self.fat_length * b[110]
            or self.heap * self.sector + self.count * self.cluster_size > partition.size
        ):
            raise RecoveryError("exFAT structures outside partition")
        self.bitmap_clusters = []
        self.bitmap_size = 0

    def cluster_offset(self, cluster):
        if not 2 <= cluster < self.count + 2:
            raise RecoveryError("exFAT cluster outside filesystem")
        return self.partition.offset + self.heap * self.sector + (cluster - 2) * self.cluster_size

    def chain(self, first, control):
        seen = set()
        while first < 0xFFFFFFF8:
            control.check()
            self.cluster_offset(first)
            if first in seen or len(seen) >= 131072:
                raise RecoveryError("Cyclic or excessive exFAT chain")
            seen.add(first)
            yield first
            first = u32(self.source.read(self.fat_offset + first * 4, 4), 0)

    def directory(self, first, control):
        for cluster in self.chain(first, control):
            block = self.source.read(self.cluster_offset(cluster), self.cluster_size)
            for p in range(0, len(block), 32):
                control.check()
                e = block[p : p + 32]
                if e[0] == 0:
                    return
                yield e

    def allocated(self, cluster):
        bit = cluster - 2
        byte = bit // 8
        if byte >= self.bitmap_size:
            raise RecoveryError("Truncated exFAT allocation bitmap")
        ci, off = divmod(byte, self.cluster_size)
        pos = self.cluster_offset(self.bitmap_clusters[ci]) + off
        return bool(self.source.read(pos, 1)[0] & (1 << (bit % 8)))

    def deleted(self, control=None, progress=no_progress):
        control = control or Control()
        for e in self.directory(self.root, control):
            if e[0] == 0x81 and e[1] & 1 == self.active:
                self.bitmap_size = u64(e, 24)
                if self.bitmap_size < math.ceil(self.count / 8):
                    raise RecoveryError("Incomplete exFAT bitmap")
                needed = math.ceil(self.bitmap_size / self.cluster_size)
                if needed > 131072:
                    raise RecoveryError("Allocation bitmap exceeds resource limit")
                for c in self.chain(u32(e, 20), control):
                    self.bitmap_clusters.append(c)
                    if len(self.bitmap_clusters) == needed:
                        break
                if len(self.bitmap_clusters) != needed:
                    raise RecoveryError("Incomplete exFAT bitmap chain")
                break
        if not self.bitmap_clusters:
            raise RecoveryError("exFAT allocation bitmap unavailable")
        # Root only in this release; subdirectory allocation modes require additional traversal rules.
        iterator = iter(self.directory(self.root, control))
        for e in iterator:
            if e[0] not in (0x05, 0x85):
                continue
            count = e[1]
            if not 2 <= count <= 18:
                raise RecoveryError("Invalid exFAT entry set length")
            secondaries = []
            for _ in range(count):
                try:
                    secondaries.append(next(iterator))
                except StopIteration as exc:
                    raise RecoveryError("Truncated exFAT entry set") from exc
            if e[0] != 0x05 or u16(e, 4) & 16:
                continue
            restored_set = bytearray(e + b"".join(secondaries))
            for at in range(0, len(restored_set), 32):
                restored_set[at] |= 0x80
            checksum = 0
            for index, byte in enumerate(restored_set):
                if index not in (2, 3):
                    checksum = (((checksum & 1) << 15) + (checksum >> 1) + byte) & 0xFFFF
            if checksum != u16(e, 2):
                # Invalid entry sets provide no trustworthy layout information.
                continue
            stream = secondaries[0]
            if stream[0] != 0x40 or any(s[0] != 0x41 for s in secondaries[1:]):
                continue
            name = b"".join(s[2:32] for s in secondaries[1:]).decode("utf-16-le", "replace")[: stream[3]]
            size, valid, start = u64(stream, 24), u64(stream, 8), u32(stream, 20)
            candidate = Candidate(
                name or "unnamed", name.rsplit(".", 1)[-1].lower(), size, [], "exFAT metadata"
            )
            needed = math.ceil(size / self.cluster_size)
            if valid != size or needed > 131072 or not stream[1] & 1:
                candidate.reasons = ["Uninitialized data or extent limit prevents exact reconstruction"]
                yield candidate
                continue
            try:
                if stream[1] & 2:
                    clusters = list(range(start, start + needed))
                else:
                    clusters = []
                    for c in self.chain(start, control):
                        clusters.append(c)
                        if len(clusters) >= needed:
                            break
                if len(clusters) != needed:
                    raise RecoveryError("Incomplete deleted chain")
                extents, left = [], size
                for c in clusters:
                    offset = self.cluster_offset(c)
                    if self.allocated(c):
                        raise RecoveryError("Deleted extent is currently allocated")
                    take = min(left, self.cluster_size)
                    extents.append(Extent(offset, take))
                    left -= take
                candidate.extents, candidate.status = extents, Status.LIKELY
                candidate.reasons = [
                    "Extent layout resolved from stream flags/FAT; allocation bitmap is free",
                    "Deleted entry checksums cannot authenticate original contents",
                ]
            except RecoveryError as exc:
                candidate.reasons = [str(exc)]
            yield candidate
        progress(self.partition.size, self.partition.size, "exFAT root directory complete")
