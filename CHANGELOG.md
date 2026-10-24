# Changelog

## 0.3.0 — 2026-10-24

- Preserve session history when switching to a persistent folder; reject conflicting IDs and source-disk destinations.
- Search filenames (Unicode case folding), filter status/extractable files, and sort across all result pages.
- Run hash-checked image and bounded ZIP/Office directory previews in a worker.
- Reconstruct NTFS paths through sequence-matched parent directories; conservatively pair deleted Recycle Bin metadata with nonempty contents.
- Add Windows-formatted VHD real-deletion and read-only drive/image recovery CI, plus installed startup and uninstall validation.
- Advanced filesystem/container features and production release gates remain listed in LIMITATIONS.md.


## 0.2.0 — development upgrade, 2026-10-23

Adds NTFS deleted-record recovery for resident and plain fragmented nonresident data, update-sequence validation, allocation checks, and uncertain classification for nonempty all-zero content. Adds explicit Windows drive selection, bounded aligned read-only access, CLI drive consent, in-memory desktop history by default, and separate-physical-disk enforcement for persistent drive-scan history, reports and exports. Mounted-drive resume is rejected.

Adds NTFS-3G-generated image checks in Linux CI, synthetic malformed/fragmented/allocation fixtures, mocked Windows reader tests, offscreen desktop tests, and CI packaging/startup checks. SSD TRIM, overwritten bytes, NTFS continuation/sparse/compressed/encrypted streams and real-device qualification remain limits. No local app update, signed release, or production deployment is implied.

## 0.1.0 — 2026-10-22

Initial implementation: read-only raw image analysis; partition parsing; conservative FAT32/exFAT deleted candidates; bounded format carving; SQLite checkpoints; hash-verified no-overwrite export; native PySide6 workspace; optional report-only pairing; Next.js private report viewer, documentation and optional cloud summaries; PostgreSQL foundation; native C++ matcher; generated-image tests; CI and release packaging definitions.

Known limitations and incomplete production milestones are explicitly tracked in docs/LIMITATIONS.md and docs/VERIFICATION.md. No verified public deployment or signed release is claimed.
