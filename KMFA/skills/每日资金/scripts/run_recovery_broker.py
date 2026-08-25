#!/usr/bin/env python3
"""Run the fixed values-free daily-funds recovery broker inside the worker."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.recovery import DailyFundsRecoveryBroker  # noqa: E402


def main() -> int:
    DailyFundsRecoveryBroker().serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
