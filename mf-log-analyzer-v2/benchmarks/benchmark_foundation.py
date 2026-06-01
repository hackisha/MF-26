from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for import_path in (PROJECT_ROOT, SRC_ROOT):
    path_text = str(import_path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from benchmarks.generate_synthetic_log import generate_synthetic_log  # noqa: E402
from mf_log_analyzer_v2.core.csv_loader import load_csv  # noqa: E402
from mf_log_analyzer_v2.core.default_profiles import mf_default_profile  # noqa: E402


def main() -> int:
    output = PROJECT_ROOT / "synthetic_300k.csv"
    if not output.exists():
        generate_synthetic_log(output)

    start = time.perf_counter()
    log = load_csv(output, mf_default_profile())
    elapsed = time.perf_counter() - start

    print(f"rows={log.frame.height}, columns={len(log.frame.columns)}, load_seconds={elapsed:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
