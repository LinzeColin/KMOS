#!/usr/bin/env python3
"""Run the fixed values-free DWS history probe broker inside daily-funds."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.history_probe import DailyFundsHistoryProbeBroker  # noqa: E402


def main() -> int:
    # The entrypoint redirects stdout/stderr to /dev/null.  The Access-gated
    # app receives only the strict, values-free control-volume session schema.
    DailyFundsHistoryProbeBroker().serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
