"""Bounded S05/P5.3 upload reconciliation command."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from .consistency_reconciliation import reconcile_upload_operations


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resume or isolate partial KMFA upload operations.",
    )
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--isolate-after-attempts", type=int, default=5)
    args = parser.parse_args(argv)
    report = reconcile_upload_operations(
        limit=args.limit,
        isolate_after_attempts=args.isolate_after_attempts,
    )
    print(
        json.dumps(
            report,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
