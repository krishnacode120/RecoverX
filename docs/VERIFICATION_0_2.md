# RecoverX 0.2.0 verification — 2026-10-23 (Asia/Kolkata)

Implementation commit: 0eb45632328d46bfc007f29c7ee0f01b682b7a14.
Merged into main through [PR #1](https://github.com/krishnacode120/RecoverX/pull/1).
[GitHub Actions run 39949186160](https://github.com/krishnacode120/RecoverX/actions/runs/39949186160) completed successfully.

## Executed on GitHub runners

| Check | Actual result |
| --- | --- |
| Linux Python suite | 55 passed, including independent NTFS-3G-formatted resident and nonresident recovery cases |
| Windows Python suite | 53 passed, 2 skipped; the skipped NTFS-3G cases are Linux-only and passed on Linux |
| Python lint and formatting | Passed |
| PySide6 startup | Passed offscreen on Windows and Linux |
| Desktop controls | Memory-only startup and drive selection without opening a device passed offscreen tests |
| Windows I/O adapter | Mocked alignment, partition bounds, identity replacement, and separate-disk safeguards passed |
| Web | 6 tests, lint, production build, type checking, and production-dependency audit passed |
| Native matcher | Windows CMake build and CTest passed |
| Windows distribution | PyInstaller portable application and Inno Setup 0.2.0 installer built |
| Packaged startup | Offscreen startup completed successfully within the timeout on the Windows runner |

The old unsupported-NTFS test was updated to expect a malformed NTFS boot rejection; unsupported-filesystem coverage remains. Formatting failures were corrected before the successful run. No failing recovery checks were removed to obtain these results.

## Recovery evidence

Constructed fixtures recovered a resident file crossing an update-sequence boundary, a fragmented nonresident file with signed backward run offsets, and an empty file. The MFT itself is fragmented. Tests checked exact original bytes and unchanged image hashes, and refused allocated/reused clusters, inconsistent record allocation, torn records, sparse data, continuation attributes, malformed geometry/runlists, and nonempty all-zero contents.

Independent fixtures were formatted with NTFS-3G mkntfs and populated with ntfscp. The tests then simulated deletion by clearing the known file's allocation flags. Resident and nonresident exports matched independently generated reference bytes, and source hashes remained unchanged during recovery. This is an independent layout check, not a real Windows deletion/TRIM test.

## Build artifact

[Unsigned installer and portable archive](https://github.com/krishnacode120/RecoverX/actions/runs/39949186160/artifacts/12499203136) are stored in the private repository's CI artifacts. GitHub authentication is required. The artifact was recorded with an expiration date of 2027-01-21.

Contents include RecoverX-Setup-0.2.0.exe, RecoverX-Portable-0.2.0.zip, and SHA256.txt.

Installer SHA-256:
b044d3a0b55595fd133d94a46ee5581e344ebf6e53a51db911d49c0228643a5b

GitHub artifact ZIP SHA-256:
1a27f253f09d3c33b04e1c3162027cff1c41492bd2317a60690277dbc4521860

These are different files and therefore different checksums. No signed public release is claimed.

## Unqualified behavior and unchanged local installation

No real user storage device was scanned. Real Windows deletion, SSD TRIM behavior, changing mounted filesystems, clean-machine installation/uninstallation, and BitLocker remain unqualified. The limitations in [NTFS.md](NTFS.md) and [LIMITATIONS.md](LIMITATIONS.md) still apply. No code can reconstruct overwritten or inaccessible TRIM-discarded bytes.

Development changes and tests for this upgrade were kept on GitHub. The user's local source checkout and installed 0.1.0 application were not updated. No new installer or test image was downloaded to the affected SSD.

Vercel deployment, live OAuth/database verification, code signing, and the other production release gates remain outstanding.
