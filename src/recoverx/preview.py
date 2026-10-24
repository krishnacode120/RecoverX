"""Bounded previews. Archive members are listed without extracting their contents."""

import hashlib
from io import BytesIO
import struct
import zipfile

from .models import Control, RecoveryError

MAX_PREVIEW = 4 * 1024 * 1024
IMAGE_KINDS = {"jpg", "jpeg", "png", "gif", "bmp", "webp"}
ARCHIVE_KINDS = {"zip", "docx", "xlsx", "pptx"}


def preview_content(source, candidate, control=None):
    control = control or Control()
    if not candidate.sha256 or not 0 < candidate.size <= MAX_PREVIEW:
        raise RecoveryError("Preview requires hashed content of at most 4 MiB")
    if candidate.kind not in IMAGE_KINDS | ARCHIVE_KINDS:
        raise RecoveryError("Content preview is unavailable for this file type")
    if sum(e.length for e in candidate.extents) != candidate.size:
        raise RecoveryError("Incomplete preview extents")
    blocks = []
    for extent in candidate.extents:
        control.check()
        if extent.offset < 0 or extent.length <= 0 or extent.offset + extent.length > source.size:
            raise RecoveryError("Preview extent outside source")
        blocks.append(source.read(extent.offset, extent.length))
    data = b"".join(blocks)
    if hashlib.sha256(data).hexdigest() != candidate.sha256:
        raise RecoveryError("Content changed since scanning; preview rejected")
    source.assert_unchanged()
    control.check()
    if candidate.kind in ARCHIVE_KINDS:
        return {"text": archive_listing(data)}
    from PIL import Image

    with Image.open(BytesIO(data)) as picture:
        if picture.width * picture.height > 16_000_000:
            raise RecoveryError("Image exceeds preview pixel limit")
        picture.thumbnail((480, 240))
        output = BytesIO()
        picture.convert("RGB").save(output, "PNG")
    control.check()
    return {"png": output.getvalue()}


def archive_listing(data):
    end = data.rfind(b"PK\x05\x06", max(0, len(data) - 65557))
    if end < 0 or end + 22 > len(data):
        raise RecoveryError("ZIP end record is missing")
    disk, central_disk, on_disk, total, size, offset, comment = struct.unpack_from("<HHHHIIH", data, end + 4)
    if (
        disk or central_disk or on_disk != total or total > 1000
        or size > 512 * 1024 or offset + size > end or end + 22 + comment != len(data)
        or b"PK\x06\x07" == data[max(0, end - 20):max(0, end - 16)]
    ):
        raise RecoveryError("ZIP exceeds listing limits or requires unsupported ZIP64/multidisk parsing")
    with zipfile.ZipFile(BytesIO(data)) as archive:
        members = archive.infolist()
        if len(members) != total:
            raise RecoveryError("ZIP entry count disagrees with directory")
        lines = ["Archive members (not extracted; contents have not been validated):"]
        for item in members:
            name = repr(item.filename[:240])
            locked = " · encrypted" if item.flag_bits & 1 else ""
            lines.append(f"{name} · {item.file_size:,} bytes{locked}")
        return "\n".join(lines)
