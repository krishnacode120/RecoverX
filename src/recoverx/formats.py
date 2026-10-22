"""Bounded format-aware carving. Unsupported boundaries stay unresolved, never guessed."""

from dataclasses import dataclass
from io import BytesIO
import struct
import warnings
import zipfile
import zlib

from .models import Status

MAX_CANDIDATE = 32 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024


@dataclass(frozen=True)
class Format:
    kind: str
    magic: bytes
    displacement: int = 0


REGISTRY = (
    Format("png", b"\x89PNG\r\n\x1a\n"),
    Format("jpg", b"\xff\xd8\xff"),
    Format("pdf", b"%PDF-"),
    Format("zip", b"PK\x03\x04"),
    Format("gif", b"GIF87a"),
    Format("gif", b"GIF89a"),
    Format("bmp", b"BM"),
    Format("riff", b"RIFF"),
    Format("sqlite", b"SQLite format 3\x00"),
    Format("mp4", b"ftyp", 4),
    Format("7z", b"7z\xbc\xaf\x27\x1c"),
    Format("rar", b"Rar!\x1a\x07"),
    Format("mkv", b"\x1a\x45\xdf\xa3"),
    Format("flac", b"fLaC"),
    Format("mp3", b"ID3"),
    Format("tiff", b"II\x2a\x00"),
    Format("tiff", b"MM\x00\x2a"),
)


def decoded_image(data):
    from PIL import Image

    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(BytesIO(data)) as im:
            if im.width * im.height > 16_000_000:
                raise ValueError("Image pixel limit exceeded")
            im.verify()
        with Image.open(BytesIO(data)) as im:
            im.load()


def subblocks(data, p):
    while p < len(data):
        n = data[p]
        p += 1
        if n == 0:
            return p
        p += n
    raise ValueError("Truncated GIF blocks")


def validate(kind, data):
    """Return (length, kind, status, evidence); length=0 means no safe boundary."""
    try:
        length, status, reason = 0, Status.LIKELY, "Structural boundary found; fragmentation remains possible"
        if kind == "png":
            p, first = 8, True
            while p + 12 <= len(data):
                n = int.from_bytes(data[p : p + 4], "big")
                tag = data[p + 4 : p + 8]
                end = p + 12 + n
                if end > len(data) or (first and (tag != b"IHDR" or n != 13)):
                    raise ValueError("Invalid PNG chunk")
                if zlib.crc32(data[p + 4 : p + 8 + n]) != int.from_bytes(data[p + 8 + n : end], "big"):
                    raise ValueError("PNG CRC mismatch")
                first, p = False, end
                if tag == b"IEND" and n == 0:
                    length = p
                    break
            if length:
                decoded_image(data[:length])
                status, reason = Status.VERIFIED, "PNG chunk checksums and image decoder passed"
        elif kind == "jpg":
            # Try at most 64 EOI markers; embedded thumbnails may contain an early EOI.
            p = 2
            for _ in range(64):
                p = data.find(b"\xff\xd9", p)
                if p < 0:
                    break
                p += 2
                try:
                    decoded_image(data[:p])
                    length = p
                    break
                except (OSError, ValueError, SyntaxError):
                    continue
            if length:
                status, reason = Status.VERIFIED, "JPEG decoder accepted the bounded file"
        elif kind == "pdf":
            p = data.find(b"%%EOF")
            if p >= 0 and data[5:8] in (
                b"1.0",
                b"1.1",
                b"1.2",
                b"1.3",
                b"1.4",
                b"1.5",
                b"1.6",
                b"1.7",
                b"2.0",
            ):
                length = p + 5
                # PDF incremental revisions are not reconstructed by this carver.
                if b"startxref" not in data[:length] or b"obj" not in data[:length]:
                    raise ValueError("PDF structure missing")
                reason = "PDF header, objects, startxref and first EOF found; renderer and later revisions unverified"
        elif kind == "zip":
            p = 0
            for _ in range(64):
                p = data.find(b"PK\x05\x06", p)
                if p < 0 or p + 22 > len(data):
                    break
                end = p + 22 + int.from_bytes(data[p + 20 : p + 22], "little")
                p += 4
                if end > len(data):
                    continue
                try:
                    with zipfile.ZipFile(BytesIO(data[:end])) as archive:
                        items = archive.infolist()
                        if len(items) > 4096 or sum(x.file_size for x in items) > MAX_EXPANDED:
                            raise ValueError("Archive resource limit exceeded")
                        # Require the first local member to start here, excluding prefixed/self-extracting data.
                        if not items or min(x.header_offset for x in items) != 0:
                            continue
                        for item in items:
                            if item.flag_bits & 1:
                                raise ValueError("Encrypted ZIP cannot be verified")
                            with archive.open(item) as member:
                                consumed = 0
                                while part := member.read(65536):
                                    consumed += len(part)
                                    if consumed > min(item.file_size, MAX_EXPANDED):
                                        raise ValueError("Archive expansion bound exceeded")
                        names = {x.filename for x in items}
                        if "[Content_Types].xml" in names:
                            for prefix, extension in (("word/", "docx"), ("xl/", "xlsx"), ("ppt/", "pptx")):
                                if any(n.startswith(prefix) for n in names):
                                    kind = extension
                        length = end
                        status, reason = Status.VERIFIED, "ZIP central directory and every member CRC passed"
                        break
                except zipfile.BadZipFile:
                    continue
        elif kind == "gif":
            if len(data) < 13:
                raise ValueError("Truncated GIF")
            p = 13 + (3 * (2 << (data[10] & 7)) if data[10] & 128 else 0)
            while p < len(data):
                tag = data[p]
                p += 1
                if tag == 0x3B:
                    length = p
                    decoded_image(data[:p])
                    reason = "GIF block structure and first frame decoder passed; later frames unverified"
                    break
                if tag == 0x21:
                    p = subblocks(data, p + 1)
                elif tag == 0x2C:
                    packed = data[p + 8]
                    p += 9 + (3 * (2 << (packed & 7)) if packed & 128 else 0)
                    p = subblocks(data, p + 1)
                else:
                    raise ValueError("Invalid GIF block")
        elif kind == "bmp":
            length = int.from_bytes(data[2:6], "little")
            if not 54 <= length <= len(data):
                raise ValueError("Invalid BMP length")
            decoded_image(data[:length])
            status, reason = Status.VERIFIED, "BMP declared length and decoder passed"
        elif kind == "riff":
            length = int.from_bytes(data[4:8], "little") + 8
            kind = {b"WAVE": "wav", b"AVI ": "avi", b"WEBP": "webp"}.get(data[8:12], "riff")
            if kind == "riff" or not 12 <= length <= len(data):
                raise ValueError("Unsupported or truncated RIFF container")
            p = 12
            while p + 8 <= length:
                n = int.from_bytes(data[p + 4 : p + 8], "little")
                p += 8 + n + (n & 1)
            if p != length:
                raise ValueError("Invalid RIFF chunks")
            if kind == "webp":
                decoded_image(data[:length])
                status, reason = Status.VERIFIED, "WebP length, RIFF chunks and decoder passed"
            else:
                reason = "RIFF length and chunk boundaries passed; media decoding unverified"
        elif kind == "sqlite":
            if len(data) < 100:
                raise ValueError("SQLite header truncated")
            page = int.from_bytes(data[16:18], "big")
            page = 65536 if page == 1 else page
            if page < 512 or page > 65536 or page & (page - 1):
                raise ValueError("Invalid SQLite page size")
            pages = int.from_bytes(data[28:32], "big")
            length = page * pages
            if not 100 <= length <= len(data) or data[24:28] != data[92:96]:
                raise ValueError("SQLite length not reliable")
            reason = "SQLite header page count is consistent; B-trees and WAL not validated"
        elif kind == "mp4":
            p, tags = 0, set()
            allowed = {
                b"ftyp",
                b"moov",
                b"mdat",
                b"free",
                b"skip",
                b"wide",
                b"uuid",
                b"moof",
                b"mfra",
                b"sidx",
                b"styp",
            }
            while p + 8 <= len(data) and data[p + 4 : p + 8] in allowed:
                n, tag = int.from_bytes(data[p : p + 4], "big"), data[p + 4 : p + 8]
                minimum = 8
                if n == 1:
                    n, minimum = int.from_bytes(data[p + 8 : p + 16], "big"), 16
                if n < minimum or p + n > len(data):
                    break
                tags.add(tag)
                p += n
            if {b"ftyp", b"moov", b"mdat"}.issubset(tags):
                length = p
                kind = "mov" if data[8:12] == b"qt  " else "mp4"
                reason = "ISO media box lengths, moov and mdat present; sample tables and decoding unverified"
        elif kind == "7z":
            if len(data) < 32 or zlib.crc32(data[12:32]) != int.from_bytes(data[8:12], "little"):
                raise ValueError("7z start-header CRC failed")
            off, size, crc = struct.unpack_from("<QQI", data, 12)
            length = 32 + off + size
            if length > len(data) or zlib.crc32(data[32 + off : length]) != crc:
                raise ValueError("7z next-header CRC failed")
            reason = "7z start and next-header CRC passed; archive members unverified"
        else:
            return 0, kind, Status.UNCERTAIN, "Signature detected; reliable boundary parser not implemented"
        if not length:
            return 0, kind, Status.UNCERTAIN, "No complete structure within configured carving limit"
        return length, kind, status, reason
    except (
        ValueError,
        OSError,
        IndexError,
        struct.error,
        SyntaxError,
        RuntimeError,
        NotImplementedError,
    ) as exc:
        return 0, kind, Status.DAMAGED, f"Validation failed: {type(exc).__name__}"
