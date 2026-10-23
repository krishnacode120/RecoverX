# RecoverX

[![Verify RecoverX](https://github.com/krishnacode120/RecoverX/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/krishnacode120/RecoverX/actions/workflows/ci.yml)

**Local Windows-drive and disk-image recovery with a desktop application and a web report workspace.**

RecoverX scans explicitly selected Windows drives and raw disk images for deleted filesystem entries and recognizable file content, records the evidence for each candidate, and verifies exported bytes with SHA-256. Storage analysis runs locally. The Next.js website displays imported reports and can optionally store account summaries.

**Status: 0.2.0 development upgrade — NTFS and Windows drive selection.** The core works against generated disk images, with Windows and Linux CI coverage. Hardware qualification, several filesystem features, cloud integration testing, and signed distribution remain outstanding. There is no verified production deployment or published signed installer. See the [verification record](docs/VERIFICATION.md) for completed checks.

## What works

| Component | Implemented scope |
| --- | --- |
| Image analysis | Read-only raw `.img`, `.raw`, and `.dd` files; superfloppy, primary MBR, and CRC-validated GPT layouts; 512/4096-byte sector sizes |
| Quick scan | Conservative NTFS, FAT32, and exFAT deleted-entry analysis within the limits below |
| Deep scan | Streaming signature discovery, bounded contiguous carving, format validation, progress, cancellation, and persisted resume checkpoints |
| Export | Destination checks, normalized filenames, no overwrite, temporary output, atomic publication, and SHA-256 verification after writing |
| Desktop | PySide6 interface for scanning, pause/cancel, paginated results, image thumbnails, selection/export, local history, reports, and Windows device imaging |
| Web | Next.js dashboard with JSON report import, search, filters, charts, and candidate evidence; reports stay in browser memory until explicitly saved as cloud summaries |
| Optional local agent | Token-protected, time-limited, read-only access to one scan's report; the desktop does not start it automatically |
| Optional cloud accounts | GitHub authentication and PostgreSQL summary endpoints; require configuration and live integration testing |

### Filesystem and format coverage

- **NTFS 3.0/3.1:** deleted base records, surviving Unicode names, resident files, and plain fragmented nonresident streams with allocation checks. [Scope and workflow](docs/NTFS.md).

- **FAT32:** traverses active directories and discovers deleted short-name entries. Extraction is limited to unallocated, single-cluster files.
- **exFAT:** analyzes deleted entry sets in the root directory, checks allocation state, and uses explicit contiguous extents or surviving FAT chains.
- **Carving and validation:** JPEG, PNG, BMP, WebP, GIF, ZIP/Office archives, PDF, WAV/AVI, MP4/MOV, SQLite, and 7z have varying levels of decoding or structural validation. These checks do not establish complete semantic integrity for every format.
- **Discovery only:** TIFF, RAR, MKV, MP3, and FLAC signatures are reported as unresolved; signature detection alone does not make a file exportable.

NTFS continuation/sparse/compressed/encrypted streams, ext4 metadata recovery, nested exFAT directories, FAT32 long-name reconstruction, EWF/VHD/VHDX/QCOW containers, and fragmented raw carving are not implemented. Contiguous carving is capped at 32 MiB. The optional TSK dependency does not enable a working TSK adapter. See [all limitations](docs/LIMITATIONS.md).

## Data handling and recovery limits

RecoverX opens analysis sources read-only. Keep the application, scan database, reports, and recovered output on a different physical disk from the media being recovered. Prefer an offline image or a write-blocked source; a mounted disk can change while it is being read.

Export verification proves that the written bytes match the candidate bytes read from the image. It does **not** prove those bytes match the original file before deletion. The generated test fixtures provide independent original hashes for that stronger comparison.

Overwritten bytes, TRIM-discarded blocks, inaccessible encrypted content, and physically unreadable data cannot be reconstructed by this implementation. Windows imaging stops at the first read error and has not been qualified on failing hardware. Only access media you own or are authorized to examine.

## Quick start

### Requirements

| Requirement | Used for |
| --- | --- |
| Git and access to this repository | Cloning the source |
| Python 3.12+ | Recovery engine, CLI, and desktop; CI uses Python 3.12 |
| Windows x64 | Windows desktop distribution and native device APIs; raw-image engine tests also run on Linux |
| Node.js 22 and npm | Web development; Node 22 is the CI baseline |
| CMake 3.28+ and a C++20 compiler | Optional native matcher build and tests |
| Inno Setup 6 | Windows installer creation |

The following commands use PowerShell and start at the repository root. They use the virtual environment directly, so activation is optional.

### Desktop application

```powershell
git clone https://github.com/krishnacode120/RecoverX.git
cd RecoverX
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[desktop,dev]"
.\.venv\Scripts\python.exe -m recoverx.desktop
```

Click **Select Windows drive…** to choose a drive, or **Open raw image** for an image file. Select **quick** for NTFS/FAT32/exFAT metadata recovery, authorize the source, and start. History begins in memory; choose an external history folder to keep future scans after exit. Drive scans, persistent history, and export rules are explained in [NTFS and drive recovery](docs/NTFS.md).

Ordinary image-file scans do not require administrator rights. Direct drive reading and physical-device imaging may require an explicitly elevated session; RecoverX does not elevate itself. Recovery output must be on another physical disk. See [installation and device imaging](docs/INSTALLATION.md).

For a CLI-only environment, install `.[dev]` instead. On Linux, use `.venv/bin/python`; Qt desktop smoke tests additionally need platform runtime libraries, including `libegl1` and `libopengl0` on Ubuntu.

### Web workspace

In a separate terminal, from the repository root:

```powershell
cd apps/web
npm ci
npm run dev
```

Open the local URL printed by Next.js and visit `/dashboard`. Import a JSON report exported by the desktop or CLI. Reloading or closing the page clears browser-held reports. The browser cannot scan physical disks, and no disk-image upload is implemented. Public pages and local report viewing work without cloud credentials.

## Try a recovery with disposable data

Run these commands from the repository root after installing the Python dependencies. The fixture generator creates a new directory and refuses to overwrite an existing one; use fresh paths when repeating the example.

```powershell
.\.venv\Scripts\python.exe scripts/create_fixture.py artifacts/quickstart
$scan = .\.venv\Scripts\python.exe -m recoverx.cli scan artifacts/quickstart/deleted-fat32.img --mode quick --db artifacts/quickstart.sqlite --report artifacts/quickstart-report.json | ConvertFrom-Json
New-Item -ItemType Directory -Path artifacts/quickstart-output
.\.venv\Scripts\python.exe -m recoverx.cli recover artifacts/quickstart/deleted-fat32.img $scan.scan_id artifacts/quickstart-output --db artifacts/quickstart.sqlite --allow-image-disk
```

This recovers the generated deleted JPEG as `artifacts/quickstart-output/_HOTO.JPG`. Compare its hash with the independently generated reference:

```powershell
$expected = Get-Content artifacts/quickstart/expected.json -Raw | ConvertFrom-Json
$actual = (Get-FileHash artifacts/quickstart-output/_HOTO.JPG -Algorithm SHA256).Hash
if ($actual -ne $expected.'_HOTO.JPG') { throw 'Recovered file does not match the reference' }
```

Import `artifacts/quickstart-report.json` into the web workspace to inspect the scan. The `--allow-image-disk` option is used here only because the source is a disposable generated image. It does not override physical-device imaging protection.

For other CLI commands and options:

```powershell
.\.venv\Scripts\python.exe -m recoverx.cli --help
.\.venv\Scripts\python.exe -m recoverx.cli scan --help
.\.venv\Scripts\python.exe -m recoverx.cli recover --help
```

## Development and verification

Run Python checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
```

Build and test the optional C++ matcher with CMake on your PATH:

```powershell
cmake -S packages/recovery-core -B build/native
cmake --build build/native --config Release
ctest --test-dir build/native -C Release --output-on-failure
```

The engine works with the Python matcher fallback. Building the pybind11 extension is a separate optional step; its packaged integration is not yet qualified. Use a compiler ABI compatible with your Python installation.

Run web checks from `apps/web`:

```powershell
npm test
npm run lint
npm run build
npm run typecheck
npm audit --omit=dev --audit-level=high
```

The original 0.1.0 milestone passed **31 Python tests**, **6 web tests**, native tests, lint/type checks, and the Next.js production build. Generated FAT32 and exFAT recoveries matched known original hashes and left source images unchanged. CI covers Python and desktop startup on Windows/Linux, the web build, and native CMake/CTest. These results do not constitute real-device qualification. The 0.2.0 upgrade adds NTFS, drive-reader, and desktop safety tests; see the PR checks for its current validation status. Detailed results, dependency audit findings, and outstanding tests are in [VERIFICATION.md](docs/VERIFICATION.md) and [TESTING.md](docs/TESTING.md).

## Build the Windows installer

After installing `.[desktop,dev]` into `.venv`, install Inno Setup 6 and make `ISCC.exe` discoverable, or set `RECOVERX_ISCC` to its full path. From the repository root:

```powershell
.\scripts\package-windows.ps1
```

Outputs:

- `dist/RecoverX/RecoverX.exe` — application executable; keep the entire `dist/RecoverX` directory together.
- `dist/installer/RecoverX-Setup-0.2.0.exe` — installer, when Inno Setup is available.

The 0.1.0 local unsigned package passed startup testing. For 0.2.0, pull-request CI builds an unsigned installer and portable archive and tests packaged startup on the GitHub Windows runner; inspect the run's actual result before using its artifacts. Installation/uninstallation and clean-machine compatibility remain unqualified. Build outputs are excluded from Git, and no signed GitHub Release has been published. Review signing, dependency redistribution obligations, and Inno Setup licensing before distribution.

## Deploy the web application

Configure Vercel with **`apps/web` as the project root**, the Next.js framework, Node 22, and `npm run build`. The native recovery engine does not run on Vercel.

Cloud summaries additionally require a PostgreSQL database, the [initial migration](database/migrations/0000_foundation.sql), and these environment variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Private database connection |
| `AUTH_SECRET` | Authentication secret |
| `AUTH_GITHUB_ID` | GitHub OAuth client ID |
| `AUTH_GITHUB_SECRET` | GitHub OAuth client secret |
| `AUTH_URL` | Canonical application origin |

For local cloud development, copy `.env.example` to `apps/web/.env.local` and supply your own values. Never commit credentials. Follow [DEPLOYMENT.md](docs/DEPLOYMENT.md) for the callback URL, migrations, and verification steps. Hosted authentication, owner isolation, save/delete operations, and production deployment still require live verification.

## Repository layout

```text
apps/desktop/            Desktop entry point and Windows packaging
apps/web/                Next.js website and report workspace
src/recoverx/            Recovery engine, CLI, desktop UI, and local agent
packages/recovery-core/  C++ signature matcher and native tests
database/migrations/    PostgreSQL migrations
tests/                   Generated-image and safety tests
scripts/                 Fixture, verification, benchmark, and build tools
docs/                    Architecture, usage, security, and verification records
.github/workflows/       CI and manually triggered packaging
```

## Documentation

[Architecture](docs/ARCHITECTURE.md) · [Installation](docs/INSTALLATION.md) · [Development](docs/DEVELOPMENT.md) · [Recovery engine](docs/RECOVERY_ENGINE.md) · [NTFS and drives](docs/NTFS.md) · [API](docs/API.md) · [Security](docs/SECURITY.md) · [Testing](docs/TESTING.md) · [Deployment](docs/DEPLOYMENT.md) · [Verification](docs/VERIFICATION.md) · [Limitations](docs/LIMITATIONS.md) · [Changelog](CHANGELOG.md)

## License and dependencies

A project license has not yet been selected. Do not assume an open-source license applies to RecoverX. Dependency notices and distribution review requirements are tracked in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
