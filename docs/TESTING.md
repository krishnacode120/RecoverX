# Testing strategy

`pytest` generates disposable FAT32, exFAT and GPT images with known content. Tests assert exact reference SHA-256 recovery, source hashes unchanged, invalid signatures rejected, allocation conflicts denied, fragmented exFAT extraction, GPT CRC checks, cancellation/resume, changed-source rejection, output conflicts, incomplete cleanup, bounded reads and localhost authorization.

FAT32 fixture geometry uses 65,525 data clusters. exFAT fixtures are compact generated volumes for the implemented parser scope, not a certification corpus. No fixture generator accepts a physical device identifier. The CLI fixture generator creates a new directory exclusively.

Web tests cover report versions, real empty scans, impossible progress, sensitive-field rejection and byte formatting. A true cross-system check exports a Python report and parses it through the Zod schema. HTTP/browser smoke tests cover public pages and no-auth endpoint behavior.

C++ tests cover overlapping signatures, empty inputs, invalid needles and density bounds. Assertions are enabled even for Release builds. Run through CTest.

Not yet qualified: advanced NTFS continuation/sparse/compressed streams, ext4, encrypted volumes, real quick-formatted USB devices, hardware bad-sector behavior, disk-removal races, all fragmented file formats, multi-terabyte images, crash/power-loss atomicity, actual OAuth/database integration, and signed installer lifecycle. These are not represented by fabricated passing tests.

See VERIFICATION_0_3.md for the current GitHub-runner evidence, VERIFICATION_0_2.md for the previous NTFS corpus, and VERIFICATION.md for the original local milestone.

## Windows deletion and workflow coverage

The CI-only verify-windows-recovery.ps1 creates a new fixed VHD in the runner's temporary folder, verifies its path and non-system disk identity before formatting, and creates/deletes resident, nonresident and empty files through Windows. It remounts the VHD read-only, exercises DriveSource, then exports from the detached image and verifies exact bytes and unchanged source hashes. No MFT allocation bits are edited in this exercise. It does not emulate SSD TRIM or failing hardware.

The package job silently installs the unsigned build in a fresh runner directory, verifies installed startup and uninstalls it. No artifacts are downloaded to the user's SSD.

Regression tests cover Unicode filename search across pages, numeric sorting, idempotent history merges and conflict rejection, source-disk history guards, image hash/cancellation bounds, archive listing without member extraction, NTFS stale/cyclic/out-of-range parents, Recycle Bin metadata versions and ambiguous naming evidence.
