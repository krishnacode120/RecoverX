"""Windows discovery and read-only imaging. Never invoked automatically at startup."""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import subprocess

from .models import RecoveryError


def enumerate_devices():
    if os.name != "nt":
        return []
    script = """
    $ErrorActionPreference = 'Stop'
    @(Get-Disk | ForEach-Object {
      $disk = $_
      $parts = @(Get-Partition -DiskNumber $disk.Number -ErrorAction SilentlyContinue | ForEach-Object {
        $part = $_; $vol = $part | Get-Volume -ErrorAction SilentlyContinue
        [pscustomobject]@{number=$part.PartitionNumber; offset=$part.Offset; size=$part.Size;
          mount=$part.DriveLetter; filesystem=$(if ($vol) { $vol.FileSystemType.ToString() } else { $null })}
      })
      [pscustomobject]@{number=$disk.Number; name=$disk.FriendlyName; serial=$disk.SerialNumber; size=$disk.Size;
        sector_size=$disk.LogicalSectorSize; bus=$disk.BusType.ToString();
        read_only=$disk.IsReadOnly; partitions=$parts}
    }) | ConvertTo-Json -Depth 6 -Compress
    """
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        devices = json.loads(result.stdout or "[]")
        return devices if isinstance(devices, list) else [devices]
    except (subprocess.SubprocessError, ValueError) as exc:
        raise RecoveryError(
            "Windows device discovery unavailable; check Storage service and permissions"
        ) from exc


def volume_disks(path):
    """Resolve all physical disks backing a mounted Windows volume via IOCTL."""
    if os.name != "nt":
        return {os.stat(Path(path).resolve()).st_dev}
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetVolumePathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetVolumeNameForVolumeMountPointW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    root, volume = ctypes.create_unicode_buffer(1024), ctypes.create_unicode_buffer(1024)
    if not kernel.GetVolumePathNameW(str(Path(path).resolve()), root, 1024):
        raise RecoveryError("Cannot resolve destination volume")
    if not kernel.GetVolumeNameForVolumeMountPointW(root.value, volume, 1024):
        raise RecoveryError("Cannot resolve physical volume identity")
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.DeviceIoControl.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    handle = kernel.CreateFileW(volume.value.rstrip("\\"), 0, 3, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise RecoveryError("Cannot open volume for physical disk identity")
    try:
        buffer, returned = ctypes.create_string_buffer(65536), wintypes.DWORD()
        if not kernel.DeviceIoControl(
            handle, 0x00560000, None, 0, buffer, len(buffer), ctypes.byref(returned), None
        ):
            raise RecoveryError("Physical source/destination relationship cannot be verified")
        count = int.from_bytes(buffer.raw[:4], "little")
        if count < 1 or 8 + count * 24 > returned.value:
            raise RecoveryError("Invalid volume disk extents")
        return {int.from_bytes(buffer.raw[8 + i * 24 : 12 + i * 24], "little") for i in range(count)}
    finally:
        kernel.CloseHandle(handle)


class WindowsRawSource:
    def __init__(self, number, size, sector_size):
        if os.name != "nt" or not re.fullmatch(r"\d{1,5}", str(number)):
            raise RecoveryError("Invalid Windows physical disk")
        if sector_size not in (512, 4096) or size <= 0 or size % sector_size:
            raise RecoveryError("Invalid device geometry")
        self.disk_number, self.size, self.sector_size = int(number), size, sector_size
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        k = self.kernel
        k.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        k.CreateFileW.restype = wintypes.HANDLE
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.SetFilePointerEx.argtypes = [wintypes.HANDLE, ctypes.c_longlong, ctypes.c_void_p, wintypes.DWORD]
        k.ReadFile.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
        ]
        # GENERIC_READ only; no write permission and no volume lock/dismount/repair calls.
        self.handle = k.CreateFileW(f"\\\\.\\PhysicalDrive{number}", 0x80000000, 3, None, 3, 0, None)
        if self.handle == ctypes.c_void_p(-1).value:
            raise RecoveryError(
                "Read-only device open denied. Run as administrator only with explicit authorization."
            )

    def read(self, offset, length):
        if offset < 0 or length < 0 or offset + length > self.size or length > 16 * 1024 * 1024:
            raise RecoveryError("Raw read outside bounded range")
        if offset % self.sector_size or length % self.sector_size:
            raise RecoveryError("Raw reads must be sector aligned")
        buffer, returned = ctypes.create_string_buffer(length), wintypes.DWORD()
        if not self.kernel.SetFilePointerEx(self.handle, offset, None, 0):
            raise RecoveryError("Device seek failed")
        if (
            not self.kernel.ReadFile(self.handle, buffer, length, ctypes.byref(returned), None)
            or returned.value != length
        ):
            raise RecoveryError(f"Device read failed at {offset}; specialist imaging may be necessary")
        return buffer.raw

    def close(self):
        self.kernel.CloseHandle(self.handle)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
