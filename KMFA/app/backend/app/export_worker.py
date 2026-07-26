"""Separately invoked, bounded worker for S07/P7.3 report exports.

Tests and one-shot operations call ``run_once`` with a fixed clock.  The
optional service loop is an operational queue consumer, never an acceptance
soak or observation-window gate; each business job still has a database-
enforced three-attempt ceiling.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Sequence

from fastapi import HTTPException

from . import app_state
from .export_jobs import (
    MAX_ACTIVE_EXPORT_JOBS,
    ClaimedExportJob,
    ExportJobCapacity,
    ExportJobError,
    ExportJobLeaseLost,
    ExportJobRepository,
    StoredExportArtifact,
    actual_cost_units,
    export_jobs_enabled,
    utc_now,
)


@dataclass(frozen=True)
class InjectedExportFailure(RuntimeError):
    """Static failure used by deterministic fixtures and adapters."""

    error_code: str
    retryable: bool


ExportFaultHook = Callable[[str, ClaimedExportJob], None]


def _failure_from_http(error: HTTPException) -> InjectedExportFailure:
    if error.status_code == 404:
        return InjectedExportFailure("export_source_missing", False)
    if error.status_code >= 500:
        return InjectedExportFailure(
            "export_renderer_unavailable",
            True,
        )
    return InjectedExportFailure("export_source_invalid", False)


def _record_failure(
    repository: ExportJobRepository,
    claim: ClaimedExportJob,
    failure: InjectedExportFailure,
    *,
    now: datetime,
) -> str:
    try:
        row = repository.fail(
            claim,
            error_code=failure.error_code,
            retryable=failure.retryable,
            now=now,
        )
    except ExportJobLeaseLost:
        return "lease_lost"
    return str(row["state"])


def run_once(
    limit: int = 2,
    *,
    now: datetime | None = None,
    fault_hook: ExportFaultHook | None = None,
) -> dict[str, object]:
    """Process at most ``limit`` jobs without waiting for real time."""

    if limit < 1 or limit > MAX_ACTIVE_EXPORT_JOBS:
        raise ValueError("limit must be within the active queue bound")
    clock = now or utc_now()
    if not export_jobs_enabled():
        return {
            "enabled": False,
            "claimed": 0,
            "succeeded": 0,
            "retry": 0,
            "failed": 0,
            "lease_lost": 0,
            "expired": 0,
        }

    # Import after the flag gate so a disabled worker never initializes app
    # state merely by being probed.
    from . import main as report_runtime

    app_state.init(report_runtime.APP_DB_PATH)
    repository = ExportJobRepository(
        report_runtime.APP_DB_PATH,
        report_runtime._export_artifacts_root(),
    )
    expired = repository.sweep_expired(now=clock)
    counts = {
        "claimed": 0,
        "succeeded": 0,
        "retry": 0,
        "failed": 0,
        "lease_lost": 0,
    }

    for _ in range(limit):
        claim = repository.claim_next(now=clock)
        if claim is None:
            break
        counts["claimed"] += 1
        artifact: StoredExportArtifact | None = None
        try:
            if fault_hook is not None:
                fault_hook("before_snapshot", claim)
            snapshot = report_runtime._report_export_snapshot(
                claim.report_no,
                claim.artifact_format,
            )
            if (
                str(snapshot["source_fingerprint"])
                != claim.source_fingerprint
            ):
                raise InjectedExportFailure(
                    "export_source_changed",
                    False,
                )
            if fault_hook is not None:
                fault_hook("before_render", claim)
            payload, media_type = report_runtime._render_report_export(
                snapshot
            )
            actual_units = actual_cost_units(
                estimated_units=claim.estimated_cost_units,
                artifact_size_bytes=len(payload),
            )
            artifact = repository.store_artifact(claim, payload)
            if fault_hook is not None:
                fault_hook("after_store", claim)

            digest = f"sha256:{artifact.sha256}"
            header = dict(snapshot["header"])
            mark = snapshot["watermark"]
            export_record = {
                "job_id": claim.job_id,
                "报告": claim.report_no,
                "标题": str(snapshot["title"]),
                "格式": claim.artifact_format,
                "sha256": digest,
                "字节": artifact.size_bytes,
                "水印已加": mark is not None,
                "水印文案": mark,
                "报告等级": header["报告等级"],
                "质量等级": header["质量等级"],
                "delivery_allowed": header["delivery_allowed"],
                "提交进公开仓": False,
                "导出时间": clock.astimezone(
                    report_runtime.BEIJING
                ).isoformat(timespec="seconds"),
            }
            audit_event = report_runtime._audit_payload(
                "export",
                subject_ref=(
                    f"report_no{claim.report_no}:"
                    f"{claim.artifact_format}"
                ),
                result_status="OK",
                evidence_ref="app-state:export_records",
                at=clock,
                job_id=claim.job_id,
                sha256=digest,
                bytes=artifact.size_bytes,
                report_grade=header["报告等级"],
                quality_grade=header["质量等级"],
                delivery_allowed=header["delivery_allowed"],
                watermark_applied=mark is not None,
                estimated_cost_units=claim.estimated_cost_units,
                actual_cost_units=actual_units,
                stage_phase="S07-P7.3",
            )
            repository.complete(
                claim,
                artifact=artifact,
                media_type=media_type,
                actual_units=actual_units,
                report_grade=str(header["报告等级"]),
                quality_grade=str(header["质量等级"]),
                delivery_allowed=bool(header["delivery_allowed"]),
                watermark_applied=mark is not None,
                export_record=export_record,
                audit_event=audit_event,
                now=clock,
            )
            counts["succeeded"] += 1
        except InjectedExportFailure as error:
            if artifact is not None:
                repository.remove_artifact(artifact)
            state = _record_failure(
                repository,
                claim,
                error,
                now=clock,
            )
            counts[state] += 1
        except HTTPException as error:
            if artifact is not None:
                repository.remove_artifact(artifact)
            state = _record_failure(
                repository,
                claim,
                _failure_from_http(error),
                now=clock,
            )
            counts[state] += 1
        except ExportJobCapacity as error:
            if artifact is not None:
                repository.remove_artifact(artifact)
            state = _record_failure(
                repository,
                claim,
                InjectedExportFailure(str(error), False),
                now=clock,
            )
            counts[state] += 1
        except ExportJobLeaseLost:
            if artifact is not None:
                repository.remove_artifact(artifact)
            counts["lease_lost"] += 1
        except ExportJobError:
            if artifact is not None:
                repository.remove_artifact(artifact)
            state = _record_failure(
                repository,
                claim,
                InjectedExportFailure(
                    "export_worker_internal_error",
                    True,
                ),
                now=clock,
            )
            counts[state] += 1
        except Exception:
            # Do not copy exception strings into durable state or stdout: they
            # may contain a private source path or adapter response.
            if artifact is not None:
                repository.remove_artifact(artifact)
            state = _record_failure(
                repository,
                claim,
                InjectedExportFailure(
                    "export_worker_internal_error",
                    True,
                ),
                now=clock,
            )
            counts[state] += 1

    return {
        "enabled": True,
        **counts,
        "expired": expired,
        "metrics": repository.metrics(now=clock),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.limit < 1 or arguments.limit > MAX_ACTIVE_EXPORT_JOBS:
        raise SystemExit(
            f"limit must be from 1 through {MAX_ACTIVE_EXPORT_JOBS}"
        )
    if arguments.poll_seconds < 0.25 or arguments.poll_seconds > 300:
        raise SystemExit("poll-seconds must be from 0.25 through 300")
    if not export_jobs_enabled():
        print(
            json.dumps(
                {
                    "enabled": False,
                    "detail": "export_jobs_disabled",
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 0
    while True:
        result = run_once(arguments.limit)
        print(json.dumps(result, sort_keys=True), flush=True)
        if arguments.once:
            return int(result["failed"] > 0)
        time.sleep(arguments.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
