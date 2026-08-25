#!/usr/bin/env python3
"""Exit successfully only when startup must run the raw-archive audit."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.startup import raw_archive_audit_required  # noqa: E402


def main() -> int:
    return 0 if raw_archive_audit_required() else 1


if __name__ == "__main__":
    raise SystemExit(main())
