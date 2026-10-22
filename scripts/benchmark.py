"""Measured synthetic-image throughput; not a physical-device performance claim."""

import json
from pathlib import Path
import time
import tracemalloc

from recoverx.engine import run_scan
from recoverx.source import ImageSource
from recoverx.store import Store

path = Path("artifacts/benchmark.img")
with path.open("xb") as output:
    output.truncate(128 * 1024 * 1024)
tracemalloc.start()
start = time.perf_counter()
store = Store(":memory:")
with ImageSource(path) as source:
    scan_id = run_scan(source, store)
elapsed = time.perf_counter() - start
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
result = {
    "bytes": path.stat().st_size,
    "seconds": elapsed,
    "MiB_per_second": 128 / elapsed,
    "python_peak_allocated_bytes": peak,
    "status": store.get(scan_id)["status"],
    "candidates": store.count(scan_id),
    "scope": "128 MiB zero-filled synthetic file; warm cache possible; excludes native allocations",
}
store.close()
Path("artifacts/benchmark.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
