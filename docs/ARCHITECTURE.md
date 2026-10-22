# Architecture

The implementation is a monorepo with deliberately separate trust boundaries:

- `src/recoverx`: Python image readers, filesystem parsers, format validators, scan orchestration, SQLite, restoration, Windows APIs, optional read-only report bridge, and native UI adapter.
- `apps/desktop/main.py`: packaging entry point. The desktop launches QThread workers; long-running scans and recovery never run in UI callbacks. `src/recoverx/desktop.py` owns the native view composition.
- `packages/recovery-core`: C++20 bounded signature matcher, native tests, optional pybind11 extension. No C++ component writes to storage.
- `apps/web`: Next.js/TypeScript UI, Zod report validation, TanStack Query cloud metadata, Zustand in-memory report state, Recharts, Motion, Tailwind, and a shadcn-style Radix/CVA Button.
- `database/migrations`: normalized PostgreSQL metadata. SQLite retains detailed candidates locally.
- `tests`: generated disposable FAT32/exFAT/GPT fixtures, parser and restoration tests, bridge authorization tests.

Data path: ImageSource → partition discovery or raw scan → Candidate evidence/extents/hash → SQLite → selected extraction → temporary output → hash re-read → no-replace publication. Reports are independently imported in the browser. Cloud writes include only counts, mode, status, size and timestamps.

The optional local HTTP bridge can expose one chosen scan's results for ten minutes. It never opens a source device or accepts a path from HTTP. Browser import is the default because browser localhost restrictions vary.

The small Python package consolidates filesystem/carving/validation modules instead of creating several separately distributed packages. Interfaces are dataclasses on the native side and Zod-inferred types on the web side. JSON report version 1 is their wire boundary. Duplicate schema definitions are covered by export/import integration checks.

Cloud authentication uses Auth.js JWT sessions with GitHub. Database queries always include the signed-in stable subject ID. Detailed filenames are never persisted in cloud summaries. Cloud source images and background workers are intentionally absent.
