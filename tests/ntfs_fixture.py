"""Small, explicitly constructed NTFS metadata corpus; never opens a real device."""

import struct


def resident(kind, content, flags=0):
    length = (24 + len(content) + 7) & ~7
    data = bytearray(length)
    struct.pack_into("<IIBBHHH", data, 0, kind, length, 0, 0, 0, flags, 0)
    struct.pack_into("<IH", data, 16, len(content), 24)
    data[24 : 24 + len(content)] = content
    return bytes(data)


def nonresident(kind, runs, size, flags=0):
    pairs, previous, count = bytearray(), 0, 0
    for start, length in runs:
        delta = start - previous
        pairs.extend(b"\x22" + length.to_bytes(2, "little") + delta.to_bytes(2, "little", signed=True))
        previous = start
        count += length
    pairs.append(0)
    result = bytearray((64 + len(pairs) + 7) & ~7)
    struct.pack_into("<IIBBHHH", result, 0, kind, len(result), 1, 0, 0, flags, 0)
    struct.pack_into("<QQH", result, 16, 0, count - 1, 64)
    struct.pack_into("<QQQ", result, 40, count * 1024, size, size)
    result[64 : 64 + len(pairs)] = pairs
    return bytes(result)


def filename(name):
    value = bytearray(66)
    struct.pack_into("<Q", value, 0, (1 << 48) | 5)
    value[64], value[65] = len(name), 1
    return resident(0x30, bytes(value) + name.encode("utf-16-le"))


def record(attrs, number, active=False, directory=False):
    data = bytearray(1024)
    data[:4] = b"FILE"
    struct.pack_into("<HH", data, 4, 48, 3)
    struct.pack_into("<HHHH", data, 16, 1, 1, 56, int(active) | (2 if directory else 0))
    pos = 56
    for attr in attrs:
        data[pos : pos + len(attr)] = attr
        pos += len(attr)
    struct.pack_into("<I", data, pos, 0xFFFFFFFF)
    struct.pack_into("<II", data, 24, pos + 8, 1024)
    struct.pack_into("<I", data, 44, number)
    data[48:50] = b"\xaa\xbb"
    for i in (1, 2):
        end = i * 512 - 2
        data[48 + i * 2 : 50 + i * 2] = data[end : end + 2]
        data[end : end + 2] = data[48:50]
    return bytes(data)


def make_ntfs(path):
    size, cluster = 1024 * 1024, 1024
    image = bytearray(size)
    image[:3], image[3:11] = b"\xeb\x52\x90", b"NTFS    "
    struct.pack_into("<H", image, 11, 512)
    image[13] = 2
    struct.pack_into("<QQQ", image, 40, size // 512, 4, 2)
    image[64] = 246  # -10: 1024-byte records
    image[510:512] = b"\x55\xaa"
    mft_runs = [(4, 16), (32, 16)]
    record_bits = bytearray(b"\xff\xff\x00\x00")
    record_bits[21 // 8] |= 1 << (21 % 8)
    bitmap = bytearray(128)
    for start, length in mft_runs + [(0, 4), (80, 1), (140, 1)]:
        for n in range(start, start + length):
            bitmap[n // 8] |= 1 << (n % 8)
    image[80 * cluster : 80 * cluster + len(bitmap)] = bitmap
    records = {
        0: record([nonresident(0x80, mft_runs, 32 * 1024), resident(0xB0, record_bits)], 0, True),
        3: record([resident(0x70, bytes(8) + b"\x03\x01\x00\x00")], 3, True),
        6: record([nonresident(0x80, [(80, 1)], len(bitmap))], 6, True),
    }
    small = (b"Resident content crossing a fixup boundary.\r\n" * 15)[:600]
    large = bytes((n * 13 + 7) % 256 for n in range(2300))
    records[16] = record([filename("deleted-note.txt"), resident(0x80, small)], 16)
    records[17] = record(
        [filename("fragmented.bin"), nonresident(0x80, [(120, 1), (100, 2)], len(large))], 17
    )
    image[120 * cluster : 121 * cluster] = large[:cluster]
    image[100 * cluster : 100 * cluster + len(large) - cluster] = large[cluster:]
    records[18] = record([filename("reused.bin"), nonresident(0x80, [(140, 1)], 100)], 18)
    torn = bytearray(record([filename("torn.txt"), resident(0x80, b"Do not export")], 19))
    torn[510:512] = b"XX"
    records[19] = bytes(torn)
    records[20] = record([filename("cleared.bin"), nonresident(0x80, [(150, 1)], 512)], 20)
    records[21] = record([filename("active.txt"), resident(0x80, b"Still allocated")], 21, True)
    records[22] = record([filename("sparse.bin"), nonresident(0x80, [(160, 1)], 512, 0x8000)], 22)
    records[23] = record([filename("empty.txt"), resident(0x80, b"")], 23)
    records[24] = record(
        [filename("continuation.txt"), resident(0x20, b"extension"), resident(0x80, b"partial")], 24
    )
    offsets = {}
    for number, content in records.items():
        offset = (4 + number if number < 16 else 32 + number - 16) * cluster
        image[offset : offset + 1024] = content
        offsets[number] = offset
    path.write_bytes(image)
    return {"deleted-note.txt": small, "fragmented.bin": large, "empty.txt": b""}, offsets
