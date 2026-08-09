#!/usr/bin/env python3
"""Print a values-free summary of a Coolify application log response."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.log_safety import summarize_coolify_logs  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="ephemeral Coolify response file")
    parser.add_argument("--http-status", required=True)
    parser.add_argument("--curl-exit", required=True)
    args = parser.parse_args(argv)
    summary = summarize_coolify_logs(
        args.input,
        http_status=args.http_status,
        curl_exit=args.curl_exit,
    )
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
