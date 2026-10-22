# Development

Keep all disk writes in restoration/imaging code and all source opens read-only. New filesystem parsers must validate offsets, lengths, resource limits and allocation evidence before yielding extractable extents. Never turn a missing chain into an assumed contiguous extent.

Add formats in `formats.REGISTRY` and implement a structural validator. An unsupported or failed boundary returns length zero; it must not be exported. File extension recognition is not integrity verification. Use known original SHA-256 hashes for fixtures.

The desktop and CLI share `run_scan`. Pause and cancel are cooperative. Deep-scan checkpoints commit candidates and the next unread block in one SQLite transaction. A crash before the commit causes re-scan with duplicate suppression. Quick-scan resume is not supported.

Native acceleration builds with CMake and pybind11. Use `-DRECOVERX_PYTHON=ON -Dpybind11_DIR=<python -m pybind11 --cmakedir output>`. Install the resulting module into the Python environment. Run identical tests with and without it. The normal scanner works without the extension.

Use `npm run lint`, `npm run typecheck`, `npm test`, and `npm run build` for web changes. This host uses the supported webpack build path after a Turbopack subprocess failure. Lock dependency versions, inspect security advisories and do not automatically apply breaking audit fixes.

No real-media destructive tests are allowed. Update the capability matrix and verification report when expanding support. A successful build is not evidence of hardware recovery qualification or a deployment.
