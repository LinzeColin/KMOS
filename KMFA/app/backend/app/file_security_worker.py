"""Bounded retry worker for durable KMFA file-security assessments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections.abc import Sequence
from pathlib import Path

from .artifact_lineage import (
    derivation_enabled,
    run_artifact_derivation_once,
)
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
    if not 0.1 <= arguments.poll_seconds <= 60.0:
        raise SystemExit("poll interval must be between 0.1 and 60 seconds")
    security_enabled = file_security_enabled()
    preview_enabled = derivation_enabled()
    if not security_enabled and not preview_enabled:
        print(
            json.dumps(
                {
                    "status": "disabled",
                    "processed": 0,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        if arguments.once:
            return 0
    processed = 0
    while True:
        scan_result = (
            run_security_scan_once(state_root=_state_root())
            if security_enabled
            else None
        )
        if scan_result is not None:
            processed += 1
            print(
                json.dumps(
                    {
                        "kind": "security_scan",
                        "artifact_ref": hashlib.sha256(
                            scan_result.artifact_version_id.encode("utf-8")
                        ).hexdigest()[:20],
                        "attempt_count": scan_result.attempt_count,
                        "reason_code": scan_result.reason_code,
                        "state": scan_result.state,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        derivative_result = (
            run_artifact_derivation_once(state_root=_state_root())
            if preview_enabled
            else None
        )
        if derivative_result is not None:
            processed += 1
            print(
                json.dumps(
                    {
                        "kind": "artifact_derivation",
                        "artifact_ref": hashlib.sha256(
                            derivative_result.source_artifact_version_id.encode(
                                "utf-8"
                            )
                        ).hexdigest()[:20],
                        "attempt_count": derivative_result.attempt_count,
                        "reason_code": derivative_result.reason_code,
                        "state": derivative_result.state,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        if arguments.once:
            break
        if scan_result is None and derivative_result is None:
            time.sleep(arguments.poll_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
