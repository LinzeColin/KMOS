#!/usr/bin/env python3
"""Deterministic production-policy probe for distributed low-speed traffic.

This runs inside the final application image against the exact P4.4 admission
engine. It uses a temporary control store and synthetic keyed tags only; no
business row, capability or external service is touched.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile

from app import anti_abuse as abuse


def _signals(index: int) -> abuse.RequestSignals:
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("ascii")).hexdigest()

    return abuse.RequestSignals(
        ip_tag=digest(f"probe-ip-{index}"),
        device_tag=digest(f"probe-device-{index}"),
        actor_tag=digest(f"probe-actor-{index}"),
        workspace_tag=None,
    )


def main() -> int:
    policy = abuse.POLICIES["identity"]
    sustained = next(window for window in policy.windows if window.seconds == 3600)
    base = (1_800_000_000 // sustained.seconds) * sustained.seconds + 1
    with tempfile.TemporaryDirectory(prefix="kmfa-p44-policy-") as state:
        os.environ["KMFA_WALKING_SKELETON_STATE_DIR"] = state
        allowed = 0
        for index in range(sustained.global_limit):
            admission = abuse.admit_request(
                operation="identity",
                signals=_signals(index),
                proof_header=None,
                # Five seconds keeps at most two requests in each 10-second
                # burst window while exhausting the one-hour global budget.
                now_value=base + (index * 5),
            )
            if not admission.allowed:
                raise AssertionError(f"early block at synthetic request {index}")
            abuse.release_lease(admission.lease_id)
            allowed += 1

        blocked = abuse.admit_request(
            operation="identity",
            signals=_signals(sustained.global_limit + 1),
            proof_header=None,
            now_value=base + (sustained.global_limit * 5),
        )
        recovered = abuse.admit_request(
            operation="identity",
            signals=_signals(sustained.global_limit + 2),
            proof_header=None,
            now_value=base + sustained.seconds,
        )
        abuse.release_lease(recovered.lease_id)
        snapshot = abuse.operations_snapshot()

    assert allowed == sustained.global_limit
    assert not blocked.allowed
    assert blocked.decision == "capacity-blocked"
    assert blocked.reason == "global-3600s"
    assert blocked.challenge is None
    assert recovered.allowed
    assert snapshot["raw_identifiers_stored"] is False
    max_counter_rows = sustained.global_limit * 3 + 32
    counter_rows = int(snapshot["state_counts"]["rate_counters"])
    assert counter_rows <= max_counter_rows
    print(
        json.dumps(
            {
                "scenario": "distributed-low-speed",
                "request_interval_seconds": 5,
                "unique_actor_signals": sustained.global_limit + 2,
                "allowed_before_bound": allowed,
                "global_sustained_limit": sustained.global_limit,
                "blocked_after_bound": 1,
                "challenge_bypass_offered": False,
                "recovered_next_window": True,
                "rate_counter_rows": counter_rows,
                "rate_counter_row_bound": max_counter_rows,
                "raw_identifiers_stored": False,
                "status": "PASS",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
