# Known limits — 0.1.0

This is a tested development milestone, not a complete production recovery suite.

- Filesystems: FAT32 single-cluster deleted extraction; exFAT root-directory entries only. NTFS/ext4, deleted directory reconstruction, original timestamps and FAT32 long names are not implemented. TSK optional dependency is declared but no tested TSK adapter is shipped; installing it does not enable unsupported features.
- Sources: raw regular images. EWF, VHD/VHDX/QCOW, compressed images and encrypted containers need conversion/unlocking outside RecoverX. GPT backup recovery and extended MBR partitions are not implemented.
- Carving: contiguous only, maximum 32 MiB. TIFF/RAR/MKV/MP3/FLAC matches are discovery-only. PDF uses first EOF. MP4/MOV do not validate sample tables; SQLite does not run integrity_check or merge WAL. GIF previews only the first frame. No arbitrary text carving.
- Imaging: Windows read-only code is implemented, but hardware qualification is outstanding. The first I/O error aborts imaging; partial temporary images are deleted. No fault-tolerant imaging map or persisted imaging resume. Mounted volumes can change concurrently, so use a write blocker/offline source for consistency.
- Extraction: complete candidates only. No hierarchy reconstruction, automatic overwrite, partial-file recovery or interrupted-export resume. Windows uses no-replace rename on the destination volume. POSIX output requires hard-link support.
- Metadata recovery checks present allocation, not historical authenticity. Previously overwritten bytes may look valid. A scan hash is not an original reference hash.
- Reports: at most 10,000 candidates per exported JSON and 10 MiB per browser import; browser holds at most ten reports in memory. Native detailed results remain in SQLite with 200-row pages. Native filename filtering/sorting is not yet implemented.
- Preview: bounded images and metadata only; PDF/video/audio playback, waveforms and safe archive listing UI are not implemented.
- Bridge: optional read-only report API, no browser-controlled scanning or recovery. Default workflow imports reports. HTTP-loopback browser compatibility is unverified.
- Cloud: auth and metadata endpoints require real credentials/migrations. Not an image-processing service. Database integration, quotas and abuse controls need production testing.
- Distribution: build scripts do not imply a signed installer or public release. No live URL exists until actual deployment succeeds.

No software recovery of overwritten bytes, TRIM-discarded blocks, inaccessible encryption or unreadable hardware is promised.
