# RecoverX 0.3.0 verification — 2026-10-24 (Asia/Kolkata)

Implementation commit: 31ec47d6ee72a59fd9ba5f4893ef2210201f261f.
[PR #2](https://github.com/krishnacode120/RecoverX/pull/2).
[GitHub Actions run 40057334672](https://github.com/krishnacode120/RecoverX/actions/runs/40057334672).

## Executed on GitHub runners

| Check | Result |
| --- | --- |
| Linux Python suite | 75 passed |
| Windows Python suite | 73 passed, 2 Linux-only NTFS-3G cases skipped; both passed on Linux |
| Python lint/format and desktop startup | Passed on Windows and Linux |
| Windows deletion and raw-reader integration | Passed for resident, nonresident and empty files |
| Web | 6 tests, lint, build, type checking and production dependency audit passed |
| Native matcher | Windows CMake build and CTest passed |
| Portable package and installer | Built successfully; packaged offscreen startup passed |
| Installer lifecycle | Silent install, installed offscreen startup and uninstall passed |

The final safety regression verifies that reports from saved drive scans cannot be written back to the stored source disk, including through the standalone CLI report command.

## Windows recovery evidence

The CI script created a new 128 MiB fixed VHD on an ephemeral Windows runner and verified its image path, geometry and non-system identity before formatting it as NTFS. Windows created and deleted a 132-byte resident file, a 12,000-byte nonresident file and an empty file. These were real Windows file deletions; no MFT flags or allocation bits were patched.

The test remounted the virtual disk read-only and scanned it with DriveSource. It then detached the disk and scanned/exported through ImageSource. All three candidates matched independently known original SHA-256 values, exported bytes matched the originals, and the detached VHD hash remained unchanged after reading and extraction.

This demonstrates ordinary Windows deletion on a disposable virtual disk. It does not demonstrate recovery of TRIM-discarded SSD content, a failing physical disk, BitLocker data, or every NTFS layout. A fixed VHD is used as an internally created raw-layout fixture; arbitrary virtual-disk container support is not claimed.

## New regression coverage

- Filename search across pages, Unicode case folding, numeric sorting and extractability filters.
- Persistent-history merge, idempotence, conflict refusal, existing scan retention and physical-source destination checks.
- Bounded previews, scan-hash verification, cancellation, malformed/oversized archive refusal, and archive listings without opening member contents.
- NTFS parent paths, stale sequence numbers, cycles and out-of-range parents.
- Recycle Bin version-1/2 metadata, unsafe paths, duplicate metadata and size mismatches. These naming cases use constructed records; actual Windows Recycle Bin emptying is not a covered fixture.
- Existing NTFS/FAT32/exFAT/carving safety tests remain enabled.

## Artifact

[Unsigned 0.3.0 installer and portable archive](https://github.com/krishnacode120/RecoverX/actions/runs/40057334672/artifacts/12546395050) are stored in the private repository. GitHub sign-in is required. Recorded expiration: 2027-01-22.

Contents: RecoverX-Setup-0.3.0.exe, RecoverX-Portable-0.3.0.zip and SHA256.txt.

Installer SHA-256: 7a47910c07a9d4557b699dad5180aad62d6338b66ce41bc2a0d5d83a1c48774b.

Outer artifact ZIP SHA-256: adfec02605d62b2a9d4e7dbf6e92dfbc841ce7c1f0efa8f4b2ecaa8997b4df35.

These hashes identify different files. The final documentation-only commit does not change the tested application code.

The unsigned installer is for development validation. Runner install/startup/uninstall checks are not broad clean-machine or hardware qualification.

## Remaining scope and local state

The local source checkout and installed application were left unchanged. Development, test images, builds and installer runs were kept on GitHub; no new installer was downloaded to the user's SSD.

Advanced NTFS streams, ext4/TSK and container adapters, failing-drive imaging/resume, directory-tree export, full media previews, real OAuth/database integration, deployment and signing remain unfinished as listed in [LIMITATIONS.md](LIMITATIONS.md). This milestone does not claim the entire original production specification is complete. Software cannot recreate overwritten or inaccessible TRIM-discarded bytes.
