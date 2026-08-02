#!/usr/bin/env python3
"""Run the one-time daily-funds DWS device-auth broker inside its own container."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.auth_broker import DailyFundsAuthBroker  # noqa: E402


def main() -> int:
    # The entrypoint redirects this process's stdout/stderr to /dev/null.
    # All owner-visible state is the strict control-volume schema, never a
    # terminal transcript that could contain a device code or OAuth output.
    DailyFundsAuthBroker().serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
