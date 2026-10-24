# NTFS recovery and direct Windows drive scans — 0.3.0

This upgrade adds NTFS 3.0/3.1 deleted-record recovery. It does not turn discarded SSD data into recoverable content. No scan of the user's internal drive was performed during development.

## Using the desktop

1. Run the application from a different physical disk where practical. Windows itself can still write to its mounted system drive.
2. Click **Select Windows drive…**, then choose the source letter. Discovery reads Windows storage information; it does not open the drive for sector reads.
3. Select **quick**, check authorization, and click **Start scan**. Raw access may require an explicitly elevated session. The app never requests write access or silently elevates.
4. Review each candidate's evidence. Select extractable results and choose **Recover selected to…** on another physical disk.
5. For consistency, prefer an offline image when possible. A mounted drive scan is not a snapshot.

History starts in shared process memory: closing the app loses it. **Choose folder for persistent history…** opens a history database in that folder; it transactionally merges the current session into existing history without overwriting conflicting IDs. For drive scans, the history folder must be on another physical disk. The app also rejects reports and recovered output on the source disk. Another partition on that same physical disk does not qualify.

Image scanning remains available through **Open raw image**. Deep resume is supported only for unchanged images, not mounted drives. Existing 0.1.0 history files are left untouched and are not automatically loaded.

## CLI

Use an existing external destination folder. Here, E: must be a separate physical disk; replace it with the actual destination.

~~~powershell
recoverx scan C: --drive --consent --mode quick --db E:\Recovery\history.sqlite --report E:\Recovery\scan.json
recoverx recover C: SCAN_ID E:\Recovery\Files --drive --consent --db E:\Recovery\history.sqlite
~~~

Replace SCAN_ID with the scan's returned ID. The output folder must already exist. Omit --drive for raw image files. --allow-image-disk never permits output onto a selected physical source disk.

## Implemented NTFS checks

- Validates boot geometry, NTFS version, MFT stream bounds, attribute lengths, and every 512-byte update-sequence fixup.
- Reads the MFT through its runlist, including fragmentation described in the base record.
- Discovers inactive file records and checks the MFT allocation bitmap.
- Preserves a surviving Unicode filename, preferring long-name namespaces over DOS aliases.
- Maps resident content back to source bytes, including sector-tail bytes stored in the update-sequence array.
- Decodes signed relative cluster offsets for plain nonresident streams, including fragmented files. Checks the volume bitmap for reallocated clusters.
- Rejects overlapping or out-of-volume runs, incomplete initialization, continuation attributes, sparse/compressed/encrypted streams, and torn records.
- Treats nonempty, all-zero content as uncertain and non-extractable. This is not a diagnosis that TRIM occurred; a genuine all-zero file is also withheld.
- Hashes resolved bytes during scanning and verifies the exported output against that hash. Metadata-based candidates are **Likely recoverable**, not authenticated originals.

The raw-drive reader converts bounded unaligned parser reads to aligned GENERIC_READ physical-disk reads restricted to the selected partition. A boot-sector fingerprint and device identity prevent ordinary source substitution. They do not make a changing live filesystem immutable. Export hashing rejects changes to candidate bytes; unrelated live changes may not be detected.

## Remaining limits

Attribute-list continuation and extension records, alternate data streams, sparse/compressed/EFS data, full directory-tree export and original timestamp restoration are not implemented. Original paths require surviving parents with matching sequence numbers and consistent directory allocation. Cycles, stale references and paths deeper than 64 parents remain unresolved. Deleted $I metadata (versions 1/2) can rename a uniquely matched, nonempty $R file in the same SID directory and partition, with matching size. Names remain metadata evidence. Missing or ambiguous metadata leaves the $R name unchanged; directory payloads are not reconstructed. Export always uses a normalized basename, never the recorded directory path. A split MFT mapping that needs continuation records fails explicitly. The MFT scan is bounded to 16 million records and runlists to 65,536 runs.

BitLocker-encrypted physical sectors are not decrypted by this reader, even if Windows has unlocked the mounted volume. Windows dynamic/spanned/Storage Spaces volumes that do not map to one ordinary physical partition are unsupported. The existing raw-carving limits remain.

## Validation

GitHub CI runs constructed NTFS fixtures for resident fixups, fragmented data/MFT mappings, allocation conflicts, zero-filled content, corruption, cancellation, and partition offsets. Linux CI also creates volumes with independent NTFS-3G mkntfs/ntfscp utilities, then simulates deletion by clearing the known test file's allocation flags before recovery. Reference bytes and source hashes are checked.

That independent corpus tests actual formatted NTFS layouts, but does not simulate every Windows deletion operation or SSD TRIM. Mocked Windows I/O tests cover alignment, bounds, identity changes, and separate-disk enforcement. Offscreen UI tests verify memory-only startup and selection without opening a device. The 0.3 CI additionally creates a disposable Windows-formatted fixed VHD, creates and deletes files through Windows, remounts it read-only, scans with the drive reader and exports from the detached image. It verifies reference hashes and unchanged image bytes; see VERIFICATION_0_3.md for results. Hardware, SSD TRIM, BitLocker and arbitrary clean-machine behavior remain unqualified.

## Format references

- [Microsoft NTFS master file table](https://learn.microsoft.com/en-us/windows/win32/devnotes/master-file-table)
- [Attribute record header and mapping pairs](https://learn.microsoft.com/en-us/windows/win32/devnotes/attribute-record-header)
- [File record segment header](https://learn.microsoft.com/en-us/windows/win32/devnotes/file-record-segment-header)
- [Multisector fixups](https://learn.microsoft.com/en-us/windows/win32/devnotes/multi-sector-header)
- [NTFS-3G independent test utilities](https://github.com/tuxera/ntfs-3g)

The FSCTL_GET_NTFS_FILE_RECORD API returns in-use records, so it is not used as an undelete enumerator.

Additional naming references: [Microsoft FILE_NAME](https://learn.microsoft.com/en-us/windows/win32/devnotes/file-name) and [Recycle Bin format implementation](https://github.com/EricZimmerman/RBCmd/blob/master/RecycleBin/DollarI.cs). No third-party parser code is bundled for these features.
