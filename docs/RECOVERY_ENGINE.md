# Recovery engine

## Reader and partitions

`ImageSource` opens a regular file with `rb` and a maximum 64 MiB read. It verifies size, modification time, device/inode and an initial sampled fingerprint for source continuity. This detects normal replacement, not adversarial tampering. Extraction hashes provide a second check on the exact candidate bytes. Original media should be write-blocked in forensic use.

Primary MBR and GPT partitions are bounded by image size. GPT validates the header and entry-array CRC. Extended partitions and GPT backup reconstruction are not implemented. The sector size is configurable because it cannot always be inferred from raw image bytes.

## Metadata

NTFS 3.0/3.1 reads deleted MFT base records, validates fixups and allocation bitmaps, and reconstructs resident and plain nonresident streams from explicit mappings. Fragmentation is supported when all mappings fit in the base attribute. Zero-filled content and unsupported mappings remain non-extractable. See [NTFS.md](NTFS.md) for format references, safeguards, and limits.

FAT32 walks active directory chains with cycle and count limits. Deleted short-name entries preserve size and starting cluster; the first name character is unrecoverable. Only a single currently free cluster is sufficient evidence for extraction. Larger deleted files with cleared FAT links remain uncertain. Long names, deleted directories and original timestamps are not reconstructed.

exFAT scans root file entry sets. It reads the allocation bitmap and uses NoFatChain to justify contiguous extents, otherwise follows the surviving FAT chain. All referenced clusters must currently be unallocated. Initialized length must equal data length. Files are not assumed contiguous merely because they were deleted. Subdirectories are deferred.

## Deep scanning

Default chunks are 1 MiB, with signature-sized overlap and an optional C++ matcher. A candidate reads at most 32 MiB; larger/truncated structures remain unresolved. Scanning has byte progress, duplicate suppression, cancellation, cooperative pause and persistent checkpoints. Signature density is capped at 4,096 per block. High-density adversarial data may cause a failed scan instead of consuming unbounded resources.

PNG validates CRCs and decoding; JPEG/BMP/WebP decode; GIF validates blocks and first frame; ZIP validates central directory and member CRCs within 64 MiB expanded data and 4,096 entries. OOXML classification inspects member paths and content-type presence but does not validate every XML relationship. PDF uses the first EOF and basic objects/startxref; incremental updates are not reconstructed. RIFF, ISO media, SQLite and 7z validators provide limited structural evidence only.

## Export

Candidates need resolved extents and a scan hash. Names are normalized, Windows reserved names are escaped, existing destinations are refused, and physical source/destination overlap is checked. `--allow-image-disk` is only for image files. Temporary outputs are flushed and re-read to verify SHA-256, then atomically published with a Windows no-replace rename (POSIX uses a no-replace hard link). POSIX export destinations must support hard links; Windows uses its no-replace rename semantics. No partial file is presented as successful.

Successful export means output bytes match scanned bytes, not that a deleted file is historically authentic. Structurally valid overwritten content can exist. Always compare with an independent original hash when available.

## Result browsing, naming and previews

The SQLite store applies filename/status/extractability filters before pagination and uses whitelisted deterministic SQL sort expressions. Filename matching uses Unicode case folding and literal substring semantics. Persistent-history selection merges the current session atomically; conflicts retain both original databases.

NTFS path reconstruction follows bounded parent references only when sequence numbers and allocation state match. Recycle Bin pairing additionally requires matching SID directory, partition, basename token and file size; original paths remain local and are omitted from JSON reports. Exports use only sanitized basenames.

Content previews run in a worker. They verify the scan hash before showing bounded image thumbnails or ZIP/Office central-directory listings; archive members are never opened or extracted for preview. Preview limits are intentionally smaller than the carving validator's limits.
