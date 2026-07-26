"""Bounded retry worker for durable KMFA file-security assessments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections.abc import Sequence
from pathlib import Path

from .file_security import (
    file_security_enabled,
    run_security_scan_once,
)


def _state_root() -> Path:
    explicit = os.environ.get(
        "KMFA_WALKING_SKELETON_STATE_DIR",
        "",
    ).strip()
    if explicit:
        return Path(explicit).resolve()
    app_state = Path(
        os.environ.get("KMFA_APP_STATE_DIR", "/var/lib/kmfa/state")
    )
    return (app_state / "walking-skeleton").resolve()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=5.0,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if not file_security_enabled():
        print(
            json.dumps(
                {
                    "status": "disabled",
                    "processed": 0,
                },
                sort_keys=True,
            )
        )
        return 0
    if not 0.1 <= arguments.poll_seconds <= 60.0:
        raise SystemExit("poll interval must be between 0.1 and 60 seconds")
    processed = 0
    while True:
        result = run_security_scan_once(state_root=_state_root())
        if result is not None:
            processed += 1
            print(
                json.dumps(
                    {
                        "artifact_ref": hashlib.sha256(
                            result.artifact_version_id.encode("utf-8")
                        ).hexdigest()[:20],
                        "attempt_count": result.attempt_count,
                        "reason_code": result.reason_code,
                        "state": result.state,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        if arguments.once:
            break
        if result is None:
            time.sleep(arguments.poll_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
