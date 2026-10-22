# Testing strategy

`pytest` generates disposable FAT32, exFAT and GPT images with known content. Tests assert exact reference SHA-256 recovery, source hashes unchanged, invalid signatures rejected, allocation conflicts denied, fragmented exFAT extraction, GPT CRC checks, cancellation/resume, changed-source rejection, output conflicts, incomplete cleanup, bounded reads and localhost authorization.

FAT32 fixture geometry uses 65,525 data clusters. exFAT fixtures are compact generated volumes for the implemented parser scope, not a certification corpus. No fixture generator accepts a physical device identifier. The CLI fixture generator creates a new directory exclusively.

Web tests cover report versions, real empty scans, impossible progress, sensitive-field rejection and byte formatting. A true cross-system check exports a Python report and parses it through the Zod schema. HTTP/browser smoke tests cover public pages and no-auth endpoint behavior.

C++ tests cover overlapping signatures, empty inputs, invalid needles and density bounds. Assertions are enabled even for Release builds. Run through CTest.

Not yet qualified: NTFS deleted documents, ext4, encrypted volumes, real quick-formatted USB devices, hardware bad-sector behavior, disk-removal races, all fragmented file formats, multi-terabyte images, crash/power-loss atomicity, actual OAuth/database integration, and signed installer lifecycle. These are not represented by fabricated passing tests.

See VERIFICATION.md for actual executed commands, counts and failures on this host.
