#!/usr/bin/env python3
"""Print a values-free summary of ephemeral Cloudflare Access API replies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.access_audit import CHECKS, summarize_access_audit  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--response",
        action="append",
        nargs=4,
        metavar=("CHECK", "HTTP_STATUS", "CURL_EXIT", "EPHEMERAL_FILE"),
        required=True,
        help="one temporary API reply; its contents are never printed",
    )
    args = parser.parse_args(argv)
    responses: dict[str, tuple[Path, str, str]] = {}
    for check, http_status, curl_exit, path in args.response:
        if check not in CHECKS or check in responses:
            parser.error("each supported check may appear exactly once")
        responses[check] = (Path(path), http_status, curl_exit)
    summary = summarize_access_audit(responses)
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
