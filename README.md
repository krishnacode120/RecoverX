# RecoverX

RecoverX is an **experimental, local-first data recovery implementation**, not a qualified forensic product. It performs genuine read-only raw-image scans, conservative deleted-entry discovery, format-aware carving, and hash-verified export. It never creates simulated production recovery results.

## Run locally

Requires Python 3.12+, Node 20.9+ (Node 22/24 recommended), and Windows x64 for the native device API. Raw image analysis is portable.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[desktop,dev]"
recoverx-desktop
```

The desktop uses PySide6 Essentials; it does not need Qt WebEngine or a cloud account. The app includes image selection, explicit authorization, background scanning, progress, pause/cancel, paginated results, image thumbnails, selection, destination selection, export verification, local history, deep-scan resume, and device imaging.

```powershell
cd apps/web
npm ci
npm run dev
```

Open the URL printed by Next.js. The website cannot read physical disk sectors. Its functional report workspace imports desktop JSON reports into browser memory. Closing/reloading clears them. Optional GitHub sign-in and PostgreSQL store aggregate summaries only after an explicit save. No disk-image uploads are enabled.

## Prove a recovery on disposable data

```powershell
python scripts/create_fixture.py artifacts/demo
recoverx scan artifacts/demo/deleted-fat32.img --mode quick --db artifacts/demo.sqlite --report artifacts/fat32-report.json
# Use the scan_id printed by the command:
recoverx recover artifacts/demo/deleted-fat32.img SCAN_ID E:\Recovered --db artifacts/demo.sqlite
pytest -q
```

For disposable image files only, `--allow-image-disk` explicitly permits output on the image's disk. It never overrides physical-device imaging protection. Reference hashes are in `artifacts/demo/expected.json`.

## Supported scope

| Area | Implemented behavior |
|---|---|
| Sources | Regular raw .img/.raw/.dd images; read-only Windows device imaging |
| Partitions | Superfloppy, primary MBR, GPT with CRC validation; configurable 512/4096-byte sector size |
| FAT32 | Active directory traversal, deleted 8.3 names; extract unallocated single-cluster files only |
| exFAT | Root deleted entry sets, allocation bitmap checks, explicit contiguous or surviving FAT extents |
| Carving | JPEG/PNG/BMP/WebP decoding, GIF structure/first frame, ZIP and Office member CRCs, limited PDF/RIFF/ISO-media/SQLite/7z structure |
| Discovery only | TIFF, RAR, MKV, MP3, FLAC signatures remain unresolved |
| Restoration | Bounded reads, normalized names, separate-disk checks, no overwrite, temporary output, atomic no-replace publication, SHA-256 re-read |
| History | SQLite candidates, checkpoints, scan state, JSON reports |
| Optional bridge | Explicit 10-minute token, exact HTTPS Origin and loopback Host, one scan's read-only results |

**Cannot recover:** overwritten data, TRIM-discarded blocks, inaccessible encryption, or physically unreadable bytes. NTFS/ext4 metadata, nested exFAT directories, EWF/VHD/VHDX/QCOW containers and fragmented raw carving are not implemented/qualified. A raw signature is not a recovered file. See [LIMITATIONS](docs/LIMITATIONS.md).

## Tests and builds

```powershell
pytest -q
ruff check src tests scripts
ruff format --check src tests scripts
cmake -S packages/recovery-core -B build/native
cmake --build build/native --config Release
ctest --test-dir build/native -C Release --output-on-failure
cd apps/web
npm test
npm run lint
npm run typecheck
npm run build
```

Native signature matching is optional: the Python fallback is functional. A compatible C++20 toolchain and pybind11 are required to build the extension. Do not mix a MinGW ABI extension into an MSVC CPython installation.

## Installers and deployment

`scripts/package-windows.ps1` builds a PyInstaller directory and, when Inno Setup is available, an installer with an uninstaller. Release artifacts must be qualified and signed before public distribution. The download page deliberately has no placeholder link.

Deploy **only `apps/web`** to Vercel. Configure GitHub OAuth and a private PostgreSQL database to enable account summaries. Copy the root `.env.example` to `apps/web/.env.local` for development. Apply `database/migrations/0000_foundation.sql` to an empty database before enabling cloud persistence. No secrets are included. See [DEPLOYMENT](docs/DEPLOYMENT.md) and the actual [verification report](docs/VERIFICATION.md).

## Documentation

[Architecture](docs/ARCHITECTURE.md) · [Installation](docs/INSTALLATION.md) · [Development](docs/DEVELOPMENT.md) · [Engine](docs/RECOVERY_ENGINE.md) · [API](docs/API.md) · [Security](docs/SECURITY.md) · [Testing](docs/TESTING.md) · [Deployment](docs/DEPLOYMENT.md) · [Limitations](docs/LIMITATIONS.md) · [Changelog](CHANGELOG.md)
