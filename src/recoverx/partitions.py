import struct
import zlib
from dataclasses import dataclass

from .models import RecoveryError


@dataclass(frozen=True)
class Partition:
    offset: int
    size: int
    scheme: str
    name: str


def detect(source, sector_size=512):
    if sector_size not in (512, 4096):
        raise RecoveryError("Supported logical sector sizes are 512 and 4096")
    if source.size < 512:
        return []
    boot = source.read(0, 512)
    # A filesystem boot record is not a partition table.
    if boot[3:11] in (b"EXFAT   ", b"NTFS    ") or boot[82:90] == b"FAT32   ":
        return [Partition(0, source.size, "superfloppy", "Volume")]
    if boot[510:512] != b"\x55\xaa":
        return []
    entries = [struct.unpack_from("<B3sB3sII", boot, 446 + 16 * i) for i in range(4)]
    if any(e[2] == 0xEE for e in entries):
        h = bytearray(source.read(sector_size, sector_size))
        if h[:8] != b"EFI PART":
            raise RecoveryError("Protective MBR has no valid GPT header")
        size, crc = struct.unpack_from("<II", h, 12)
        if not 92 <= size <= sector_size:
            raise RecoveryError("Invalid GPT header size")
        struct.pack_into("<I", h, 16, 0)
        if zlib.crc32(h[:size]) != crc:
            raise RecoveryError("GPT header checksum mismatch")
        first, last = struct.unpack_from("<QQ", h, 40)
        table, count, width, checksum = struct.unpack_from("<QIII", h, 72)
        if count > 16384 or width < 128 or width > 4096 or count * width > 16 * 1024 * 1024:
            raise RecoveryError("GPT table exceeds bounds")
        raw = source.read(table * sector_size, count * width)
        if zlib.crc32(raw) != checksum:
            raise RecoveryError("GPT entry checksum mismatch")
        result = []
        for i in range(count):
            entry = raw[i * width : (i + 1) * width]
            if entry[:16] == bytes(16):
                continue
            start, end = struct.unpack_from("<QQ", entry, 32)
            if start < first or end > last or end < start or (end + 1) * sector_size > source.size:
                raise RecoveryError("GPT partition outside image")
            name = entry[56:128].decode("utf-16-le", errors="replace").rstrip("\0")
            result.append(Partition(start * sector_size, (end - start + 1) * sector_size, "GPT", name))
        return result
    result = []
    for i, entry in enumerate(entries):
        _, _, kind, _, start, count = entry
        if not kind or not count:
            continue
        if kind in (5, 15, 133):
            raise RecoveryError("Extended MBR partitions need the optional Sleuth Kit adapter")
        if start < 1 or (start + count) * sector_size > source.size:
            raise RecoveryError("MBR partition outside image")
        result.append(Partition(start * sector_size, count * sector_size, "MBR", f"Partition {i + 1}"))
    return result
