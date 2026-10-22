from io import BytesIO
from pathlib import Path
import struct
import zlib
import zipfile

from PIL import Image


def picture(kind="PNG"):
    stream = BytesIO()
    Image.new("RGB", (32, 24), (28, 115, 239)).save(stream, format=kind)
    return stream.getvalue()


def pdf():
    header = b"%PDF-1.4\n"
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n",
    ]
    data, offsets = header, [0]
    for obj in objects:
        offsets.append(len(data))
        data += obj
    xref = len(data)
    data += b"xref\n0 3\n0000000000 65535 f \n"
    data += b"".join(f"{off:010d} 00000 n \n".encode() for off in offsets[1:])
    return data + f"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()


def office_zip():
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        archive.writestr("word/document.xml", "<document>RecoverX fixture</document>")
    return stream.getvalue()


def fat_image(path, content=None, size_override=None, allocated=False, loop=False):
    content = content or picture("JPEG")
    sector, spc, reserved, fat_sectors, count = 512, 2, 32, 512, 65525
    total = reserved + fat_sectors + count * spc
    boot = bytearray(sector)
    boot[:3] = b"\xeb\x58\x90"
    boot[3:11] = b"RECOVERX"
    struct.pack_into("<H", boot, 11, sector)
    boot[13], boot[16] = spc, 1
    struct.pack_into("<H", boot, 14, reserved)
    struct.pack_into("<I", boot, 32, total)
    struct.pack_into("<I", boot, 36, fat_sectors)
    struct.pack_into("<I", boot, 44, 2)
    boot[82:90], boot[510:512] = b"FAT32   ", b"\x55\xaa"
    data_start = (reserved + fat_sectors) * sector
    with open(path, "wb") as f:
        f.truncate(total * sector)
        f.seek(0)
        f.write(boot)
        f.seek(reserved * sector)
        f.write(
            struct.pack(
                "<IIII", 0x0FFFFFF8, 0x0FFFFFFF, 2 if loop else 0x0FFFFFFF, 0x0FFFFFFF if allocated else 0
            )
        )
        entry = bytearray(32)
        entry[:11] = b"\xe5HOTO   JPG"
        entry[11] = 32
        struct.pack_into("<H", entry, 26, 3)
        struct.pack_into("<I", entry, 28, size_override if size_override is not None else len(content))
        f.seek(data_start)
        f.write(entry)
        if loop:
            f.write(bytes([0xE5, 0, 0, 0]) * ((spc * sector - 32) // 4))
        f.seek(data_start + sector * spc)
        f.write(content)
    return content


def exfat_image(path, content=None, fragmented=False, allocated=False):
    content = content or pdf()
    sector, heap, count, total = 512, 32, 128, 160
    boot = bytearray(512)
    boot[3:11] = b"EXFAT   "
    struct.pack_into("<Q", boot, 72, total)
    for at, value in ((80, 24), (84, 2), (88, heap), (92, count), (96, 2)):
        struct.pack_into("<I", boot, at, value)
    boot[108], boot[109], boot[110] = 9, 0, 1
    boot[510:512] = b"\x55\xaa"
    image = bytearray(total * sector)
    image[:512] = boot
    fat = 24 * sector
    struct.pack_into("<I", image, fat + 2 * 4, 0xFFFFFFFF)
    struct.pack_into("<I", image, fat + 3 * 4, 0xFFFFFFFF)
    root = heap * sector
    image[root] = 0x81
    struct.pack_into("<I", image, root + 20, 3)
    struct.pack_into("<Q", image, root + 24, 16)
    image[(heap + 1) * sector] = 3 | (4 if allocated else 0)
    entry = root + 32
    image[entry], image[entry + 1] = 0x05, 2
    stream = entry + 32
    image[stream], image[stream + 1], image[stream + 3] = 0x40, 1 if fragmented else 3, 8
    struct.pack_into("<Q", image, stream + 8, len(content))
    struct.pack_into("<I", image, stream + 20, 4)
    struct.pack_into("<Q", image, stream + 24, len(content))
    image[entry + 64] = 0x41
    image[entry + 66 : entry + 82] = "note.pdf".encode("utf-16-le")
    restored_set = bytearray(image[entry : entry + 96])
    for at in range(0, 96, 32):
        restored_set[at] |= 0x80
    checksum = 0
    for index, byte in enumerate(restored_set):
        if index not in (2, 3):
            checksum = (((checksum & 1) << 15) + (checksum >> 1) + byte) & 0xFFFF
    struct.pack_into("<H", image, entry + 2, checksum)
    clusters = list(range(4, 4 + (len(content) + 511) // 512))
    if fragmented and len(clusters) > 1:
        clusters = [4] + list(range(8, 8 + len(clusters) - 1))
    for i, cluster in enumerate(clusters):
        pos = (heap + cluster - 2) * sector
        part = content[i * 512 : (i + 1) * 512]
        image[pos : pos + len(part)] = part
        struct.pack_into(
            "<I", image, fat + cluster * 4, clusters[i + 1] if i + 1 < len(clusters) else 0xFFFFFFFF
        )
    checksum = 0
    for index, byte in enumerate(image[: 11 * sector]):
        if index not in (106, 107, 112):
            checksum = (((checksum & 1) << 31) + (checksum >> 1) + byte) & 0xFFFFFFFF
    for at in range(11 * sector, 12 * sector, 4):
        struct.pack_into("<I", image, at, checksum)
    Path(path).write_bytes(image)
    return content


def gpt_image(path, bad_crc=False):
    image = bytearray(512 * 128)
    image[510:512] = b"\x55\xaa"
    image[450] = 0xEE
    struct.pack_into("<II", image, 454, 1, 127)
    table = bytearray(128)
    table[:16] = bytes(range(1, 17))
    struct.pack_into("<QQ", table, 32, 34, 100)
    image[1024:1152] = table
    h = bytearray(512)
    h[:8] = b"EFI PART"
    struct.pack_into("<III", h, 8, 0x10000, 92, 0)
    struct.pack_into("<QQQQ", h, 24, 1, 127, 34, 126)
    struct.pack_into("<QIII", h, 72, 2, 1, 128, zlib.crc32(table))
    struct.pack_into("<I", h, 16, zlib.crc32(h[:92]) ^ int(bad_crc))
    image[512:1024] = h
    Path(path).write_bytes(image)
