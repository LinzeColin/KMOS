"""Separately credentialed KMFA retention/deletion worker."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Sequence

from .retention_lifecycle import (
    LifecycleError,
    LifecycleWorkerBusyError,
    due_deletion_request_ids,
    process_deletion_request,
)
from .structured_store import open_structured_store


def _state_root() -> Path:
    explicit = os.environ.get("KMFA_WALKING_SKELETON_STATE_DIR", "").strip()
    if explicit:
        return Path(explicit)
    return Path(
        os.environ.get("KMFA_APP_STATE_DIR", "/var/lib/kmfa/state")
    ) / "walking-skeleton"


def _open_connection():
    root = _state_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    return open_structured_store(root / "walking_skeleton.sqlite3")


def run_once(limit: int) -> dict[str, int]:
    connection = _open_connection()
    try:
        request_ids = due_deletion_request_ids(connection, limit=limit)
    finally:
        connection.close()
    completed = 0
    retryable = 0
    blocked = 0
    busy = 0
    for request_id in request_ids:
        try:
            result = process_deletion_request(
                open_connection=_open_connection,
                state_root=_state_root(),
                deletion_request_id=request_id,
            )
            completed += int(result["state"] == "completed")
        except LifecycleWorkerBusyError:
            busy += 1
        except LifecycleError as error:
            if str(error) == "workspace_legal_hold":
                blocked += 1
            else:
                retryable += 1
    return {
        "claimed": len(request_ids),
        "completed": completed,
        "retryable": retryable,
        "blocked_hold": blocked,
        "busy": busy,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.limit < 1 or arguments.limit > 1000:
        raise SystemExit("limit must be from 1 through 1000")
    if arguments.poll_seconds < 0.25 or arguments.poll_seconds > 300:
        raise SystemExit("poll-seconds must be from 0.25 through 300")
    while True:
        result = run_once(arguments.limit)
        print(json.dumps(result, sort_keys=True), flush=True)
        if arguments.once:
            return int(result["retryable"] > 0)
        time.sleep(arguments.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
