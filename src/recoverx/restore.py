import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from .models import Control, RecoveryError, Status, no_progress
from .windows import volume_disks


def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")[:160]
    if not name or name.split(".")[0].upper() in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(10)),
        *(f"LPT{i}" for i in range(10)),
    }:
        name = "recovered_" + name
    return name


def check_destination(source, destination, allow_image_disk=False):
    destination = Path(destination).resolve(strict=True)
    if not destination.is_dir():
        raise RecoveryError("Destination must be an existing directory")
    if hasattr(source, "disk_number"):
        if source.disk_number in volume_disks(destination):
            raise RecoveryError("Destination is on the physical source device")
    elif not allow_image_disk:
        if volume_disks(source.path) & volume_disks(destination):
            raise RecoveryError(
                "Choose a separate physical disk, or explicitly allow same-disk output for an image file"
            )
    return destination


def publish_no_replace(temp, destination):
    """Publish on the same volume without replacement, even if another writer races us."""
    try:
        if os.name == "nt":
            # Windows rename refuses an existing target (unlike POSIX rename).
            os.rename(temp, destination)
        else:
            os.link(temp, destination)
            os.unlink(temp)
    except OSError as exc:
        raise RecoveryError(
            "Atomic no-replace publication failed; check destination support and conflicts"
        ) from exc


def recover(source, candidate, destination, control=None, progress=no_progress, allow_image_disk=False):
    control = control or Control()
    destination = check_destination(source, destination, allow_image_disk)
    if candidate.status not in (Status.VERIFIED, Status.LIKELY) or not candidate.sha256:
        raise RecoveryError("Candidate has no validated extractable content")
    if sum(e.length for e in candidate.extents) != candidate.size or candidate.size < 0:
        raise RecoveryError("Unresolved extent size")
    for extent in candidate.extents:
        if extent.offset < 0 or extent.length <= 0 or extent.offset + extent.length > source.size:
            raise RecoveryError("Candidate extent outside source")
    name = safe_name(candidate.name)
    target = destination / name
    if target.exists():
        raise RecoveryError("Destination exists; rename or choose another directory")
    handle, temp = tempfile.mkstemp(prefix=".recoverx-", suffix=".partial", dir=destination)
    try:
        digest, done = hashlib.sha256(), 0
        with os.fdopen(handle, "wb") as output:
            for extent in candidate.extents:
                for pos in range(extent.offset, extent.offset + extent.length, 1024 * 1024):
                    control.check()
                    data = source.read(pos, min(1024 * 1024, extent.offset + extent.length - pos))
                    output.write(data)
                    digest.update(data)
                    done += len(data)
                    progress(done, candidate.size, "Extracting")
            output.flush()
            os.fsync(output.fileno())
        if digest.hexdigest() != candidate.sha256:
            raise RecoveryError("Source content differs from the scan hash; output rejected")
        verify = hashlib.sha256()
        with open(temp, "rb") as stream:
            while block := stream.read(1024 * 1024):
                control.check()
                verify.update(block)
        if verify.hexdigest() != candidate.sha256:
            raise RecoveryError("Written output hash mismatch")
        control.check()
        source.assert_unchanged()
        publish_no_replace(temp, target)
        return {
            "filename": target.name,
            "sha256": verify.hexdigest(),
            "bytes": done,
            "status": "export verified",
            "content_status": candidate.status,
            "meaning": "Output matches scanned bytes; this does not authenticate the original file",
        }
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def image_device(source, destination, control=None, progress=no_progress):
    control = control or Control()
    target = Path(destination).absolute()
    check_destination(source, target.parent)
    if target.exists():
        raise RecoveryError("Image destination already exists")
    handle, temp = tempfile.mkstemp(prefix=".recoverx-image-", suffix=".partial", dir=target.parent)
    digest = hashlib.sha256()
    try:
        with os.fdopen(handle, "wb") as output:
            for offset in range(0, source.size, 1024 * 1024):
                control.check()
                data = source.read(offset, min(1024 * 1024, source.size - offset))
                output.write(data)
                digest.update(data)
                progress(offset + len(data), source.size, "Imaging read-only source")
            output.flush()
            os.fsync(output.fileno())
        check = hashlib.sha256()
        with open(temp, "rb") as stream:
            while data := stream.read(1024 * 1024):
                control.check()
                check.update(data)
        if check.digest() != digest.digest():
            raise RecoveryError("Image output verification failed")
        publish_no_replace(temp, target)
        return {"sha256": check.hexdigest(), "bytes": source.size}
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def write_json_exclusive(path, data):
    with open(path, "x", encoding="utf-8") as output:
        json.dump(data, output, indent=2)
