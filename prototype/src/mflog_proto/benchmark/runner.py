"""Benchmark command-line entry point."""

from __future__ import annotations

import json

from mflog_proto.benchmark.metrics import collect_environment


def main() -> None:
    print(json.dumps(collect_environment().to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

