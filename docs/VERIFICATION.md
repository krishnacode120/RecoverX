# Verification record — 2026-10-22 (Asia/Kolkata)

For the current NTFS/drive upgrade, see [0.2.0 verification](VERIFICATION_0_2.md). The record below describes the original 0.1.0 milestone and its limitations at that time. It does not claim production deployment.

## Executed locally

| Check | Actual result |
|---|---|
| Python generated-image and safety suite | 31 passed; FAT32/exFAT exact reference-hash exports, fragmented exFAT, source unchanged, malformed metadata, CRCs, bounds, cancellation/resume, output conflicts and bridge authorization |
| Python lint and formatting | Passed with Ruff |
| PySide6 source startup | Passed offscreen smoke test, exit 0 |
| C++20 native test executable | Passed, exit 0; overlap, empty input, invalid signature and density checks |
| Next.js production build | Passed on Next.js 16.4.2 with webpack |
| Web lint and TypeScript | Passed |
| Web schema unit tests | Six tests passed, including the exported Python report fixture; report also imported successfully in the live browser |
| HTTP routes | `/`, `/dashboard`, `/docs`, `/download`, `/contact`, `/account`, `/api/health`: 200; unauthenticated `/api/reports`: 401 |
| Browser workflow | Imported real generated-image JSON; two candidates, correct PNG/PDF sizes, distinct statuses and matching PNG hash visible; evidence dialog verified |
| Production npm audit | Zero reported advisories at verification time |
| Full npm audit | Nine development-tool advisories: four moderate, five high; not silently forced to breaking versions |
| Synthetic scan benchmark | 128 MiB zero-filled file in 1.905 s, 67.18 MiB/s; Python tracked allocation peak 2,119,526 bytes. Warm cache possible, not hardware recovery performance |
| GitHub repository | Source pushed to private repository https://github.com/krishnacode120/RecoverX on main |
| GitHub CI | [Run 39762643900](https://github.com/krishnacode120/RecoverX/actions/runs/39762643900) passed at commit `51218613ca706431ab91cd84841ae7e0c83fde2f`: Python tests and desktop startup on Windows and Linux, web tests/lint/build/typecheck/production audit, and native CMake/CTest. Packaging is a separate manual job and was not run by this push |

## Recovery evidence

- Deleted FAT32 `_HOTO.JPG`: 645 bytes; SHA-256 `128b03a19bbd5472af13ff72401e0f6fb9e6e1590f7ce0a131d0e6c7fe25883a` matches generated original.
- Deleted exFAT `note.pdf`: 232 bytes; SHA-256 `516879c96d542ae5392a742a04b468310f8c548e9b50b365a60602146728156e` matches generated original.
- Both source image hashes remained unchanged after extraction.
- Evidence artifacts are local under `artifacts/`; generated images and local histories are excluded from Git. A sanitized generated report fixture is committed for schema regression tests.

## Packaging investigation

PyInstaller built the portable application and Inno Setup 6.7.3 compiled an installer. The compiler's Authenticode signature was valid, publisher Pyrsys B.V. The first packaged startup failed because a toolchain ICU DLL was bundled instead of using Windows' unversioned ICU API. The checked-in spec excludes that DLL; the final rebuilt portable application's offscreen startup smoke passed, exit 0. Installer remains unsigned and intended for development validation; installation/uninstallation and clean-machine compatibility have not been qualified.

- Installer: `dist/installer/RecoverX-Setup-0.1.0.exe`, 32,430,488 bytes.
- SHA-256: `0679e3aae076034688dd6e57891c3c1ba4a8e9fabe22c0080926c6d67e00f263`.
- Review Inno Setup's commercial licensing requirements before commercial distribution.

## Environment findings and remaining gates

- The initial sandbox blocked localhost sockets and hard-link tests. The same generated tests passed with those permissions available; they were not skipped.
- Turbopack failed to start its CSS transform child process on this host. The supported webpack production build succeeded.
- GCC initially resolved incompatible runtime DLLs. Prepending its own UCRT64 runtime directory fixed the native build/test. Optional pybind11 extension packaging remains unqualified; the Python fallback is used.
- The first GitHub Linux desktop smoke failed because libEGL was absent. Installing the Linux Qt runtime libraries fixed it; the rerun passed on both operating systems.
- No physical user disk was opened or scanned. USB/hardware qualification is outstanding.
- No Vercel authorization/project, GitHub OAuth client, database connection or code-signing certificate was supplied. No live deployment URL or signed release is claimed.
- PostgreSQL migrations and authenticated owner-isolated endpoints are implemented but have not been exercised against a real hosted database.
- NTFS/ext4/TSK, EWF, advanced fragmentation, full previews and production hardening remain incomplete; see LIMITATIONS.md. Milestones 3–7 are partial, not complete.
