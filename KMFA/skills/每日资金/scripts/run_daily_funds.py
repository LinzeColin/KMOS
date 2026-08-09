#!/usr/bin/env python3
"""Cloud-only command entrypoint for the independent daily-funds worker."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.runtime import DailyFundsRuntime  # noqa: E402
from daily_funds.log_safety import cron_event, outcome_for_result  # noqa: E402


def _running_code(job: str) -> str:
    return f"{job.upper().replace('-', '_')}_RUNNING"


def _emit_cron_event(job: str, outcome: str, machine_code: object) -> None:
    """Keep every container-visible scheduler line free of operational values."""

    print(json.dumps(cron_event(job, outcome, machine_code), ensure_ascii=True, sort_keys=True, separators=(",", ":")))


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="KMFA daily-funds deterministic worker")
    command.add_argument(
        "job",
        choices=("preflight", "bootstrap-dws-auth", "runtime-audit", "poll", "auth-probe", "keepalive", "backfill", "observer", "cold-backup", "restore-drill", "restore", "healthcheck"),
    )
    command.add_argument("--max-days", type=int, default=7, help="bounded backfill days (1-14)")
    command.add_argument("--publication-id", help="64-char immutable publication ID for a verified restore")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        runtime = DailyFundsRuntime()
    except Exception:
        # An uncaught traceback can contain a provider response or a local
        # path.  The durable state is unavailable in this branch, so emit the
        # same values-free result that the public log reader understands.
        _emit_cron_event(args.job, "NEEDS_ATTENTION", "UNHANDLED")
        return 2
    run_id = uuid.uuid4().hex
    try:
        runtime.state.record_run(run_id, args.job, "RUNNING", "START")
    except Exception:
        _emit_cron_event(args.job, "NEEDS_ATTENTION", "OPERATION_START_RECEIPT_FAILED")
        return 2
    try:
        # Persist this before any source call.  If a process is interrupted,
        # the shared owner UI can truthfully show an in-flight operation rather
        # than treating an older terminal receipt as the current poll result.
        runtime.record_operation_start(job=args.job, code=_running_code(args.job))
    except Exception:
        try:
            runtime.state.record_run(run_id, args.job, "FAILED", "OPERATION_START_RECEIPT_FAILED", finished=True)
        except Exception:
            pass
        _emit_cron_event(args.job, "NEEDS_ATTENTION", "OPERATION_START_RECEIPT_FAILED")
        return 2
    try:
        if args.job == "preflight":
            result = runtime.preflight()
        elif args.job == "bootstrap-dws-auth":
            result = runtime.bootstrap_dws_auth()
        elif args.job == "runtime-audit":
            result = runtime.runtime_audit()
        elif args.job == "poll":
            result = runtime.poll()
        elif args.job == "auth-probe":
            result = runtime.auth_probe()
        elif args.job == "keepalive":
            result = runtime.keepalive()
        elif args.job == "backfill":
            result = runtime.backfill(max_days=args.max_days)
        elif args.job == "observer":
            result = runtime.observer()
        elif args.job == "cold-backup":
            result = runtime.cold_backup()
        elif args.job == "restore-drill":
            result = runtime.restore_drill()
        elif args.job == "restore":
            # Let the fail-closed runtime record an auditable terminal status;
            # ``argparse.error`` here would leave the RUNNING journal row open.
            result = runtime.restore(publication_id=args.publication_id or "")
        else:
            result = runtime.healthcheck()
    except Exception:
        try:
            runtime.record_operation_receipt(job=args.job, succeeded=False, code="UNHANDLED")
        except Exception:
            try:
                runtime.state.record_run(run_id, args.job, "FAILED", "OPERATION_RECEIPT_FAILED", finished=True)
            except Exception:
                pass
        else:
            try:
                runtime.state.record_run(run_id, args.job, "FAILED", "UNHANDLED", finished=True)
            except Exception:
                pass
        _emit_cron_event(args.job, "NEEDS_ATTENTION", "UNHANDLED")
        return 2
    try:
        code = str(result.get("code") or result.get("machine_code") or result.get("status") or "UNKNOWN")
        if "ok" in result:
            ok = bool(result["ok"])
        elif code in {"AUTH_OK", "KEEPALIVE_OK"}:
            # Source authentication and token keepalive are independent health
            # checks.  Before the first reconciled publication the user-facing
            # funding status correctly remains "需处理", but a successful probe
            # must still be recorded as a successful scheduled job rather than
            # poisoning the runtime ledger with a false failure.
            ok = True
        elif result.get("status") == "ok":
            ok = True
        else:
            # Status-only maintenance jobs can complete while the financial
            # publication remains pending; a separately detected lock holder
            # below is not a terminal success.  ``需处理`` remains non-zero.
            ok = result.get("human_status") in {"已更新", "处理中"}
        # Seeing another holder is neither a successful terminal run nor a
        # failure of the active holder.  Keep the pre-written RUNNING receipt
        # for every job so the status centre reports an in-flight operation.
        lock_held = code.endswith("_LOCK_HELD")
        if not lock_held:
            runtime.record_operation_receipt(job=args.job, succeeded=ok, code=code)
        runtime.state.record_run(
            run_id,
            args.job,
            "SKIPPED" if lock_held else "SUCCEEDED" if ok else "FAILED",
            code,
            finished=True,
        )
    except Exception:
        # A completed job without its status receipt is not evidentially
        # complete.  Do not expose the exception in the public cron log.
        try:
            runtime.state.record_run(run_id, args.job, "FAILED", "OPERATION_RECEIPT_FAILED", finished=True)
        except Exception:
            pass
        _emit_cron_event(args.job, "NEEDS_ATTENTION", "OPERATION_RECEIPT_FAILED")
        return 2
    _emit_cron_event(args.job, outcome_for_result(ok=ok, code=code), code)
    return 75 if lock_held else 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
