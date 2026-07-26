#!/usr/bin/env python3
"""S06/P6.4 deterministic final-image upload quality validation.

The validation adds quota competition, cross-workspace write isolation and a fixed
synthetic fixture replay to the existing P6.1-P6.3 exact-image Oracles. It
emits a compact benchmark, negative matrix and explicit invariants without a
real-time soak, observation window or wall-clock promotion threshold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from resumable_upload_flow import Api, Container, MAX_FILE_BYTES

CONTAINER_RE = re.compile(r"^kmfa-p64-[a-z0-9-]+$")
FIXTURE_SAMPLES_DEFAULT = 12
FIXTURE_SAMPLES_MIN = 3
FIXTURE_SAMPLES_MAX = 12
RECEIPT_MAX_BYTES = 64 * 1024


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(arguments),
        check=True,
        capture_output=True,
        text=True,
    )


def _session_id(result: Any) -> str:
    assert result.status == 201, result.body
    session_id = str(result.json()["upload_session"]["upload_session_id"])
    assert session_id.startswith("operation_")
    return session_id


def _cancel(
    api: Api,
    workspace_id: str,
    token: str,
    actor: dict[str, str],
    session_id: str,
) -> None:
    cancelled = api.request(
        "DELETE",
        f"/workspaces/{workspace_id}/upload-sessions/{session_id}",
        headers=api.auth(token, actor),
    )
    assert cancelled.status == 204, cancelled.body


def _quota_competition(
    api: Api,
    *,
    max_total_bytes: int,
    max_file_bytes: int,
) -> dict[str, Any]:
    assert max_file_bytes == MAX_FILE_BYTES
    assert max_total_bytes % max_file_bytes == 0
    total_slots = max_total_bytes // max_file_bytes
    assert 2 <= total_slots <= 15
    declared_sha256 = hashlib.sha256(
        b"synthetic declared capacity only"
    ).hexdigest()

    sessions: list[tuple[str, str, dict[str, str], str]] = []
    for index in range(total_slots - 1):
        workspace_id, token, actor = api.create_workspace(
            f"P6.4 quota reserve {index}"
        )
        created = api.create_session(
            workspace_id,
            token,
            actor,
            name=f"quota-{index}.synthetic",
            media_type="application/octet-stream",
            payload=b"",
            size_bytes=max_file_bytes,
            sha256=declared_sha256,
            key=f"p64-quota-reserve-{index:04d}",
        )
        sessions.append((workspace_id, token, actor, _session_id(created)))

    contenders_owners = [
        api.create_workspace(f"P6.4 quota contender {index}")
        for index in range(2)
    ]

    def compete(index: int) -> tuple[Any, tuple[str, str, dict[str, str]]]:
        workspace_id, token, actor = contenders_owners[index]
        return (
            api.create_session(
                workspace_id,
                token,
                actor,
                name=f"quota-race-{index}.synthetic",
                media_type="application/octet-stream",
                payload=b"",
                size_bytes=max_file_bytes,
                sha256=declared_sha256,
                key=f"p64-quota-race-{index:04d}",
            ),
            (workspace_id, token, actor),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        contenders = list(pool.map(compete, range(2)))
    assert sorted(result.status for result, _ in contenders) == [201, 429]
    blocked = next(
        result for result, _ in contenders if result.status == 429
    )
    assert blocked.json()["detail"] == "artifact_capacity_reached"
    winner, winner_owner = next(
        item for item in contenders if item[0].status == 201
    )
    workspace_id, token, actor = winner_owner
    winner_session = _session_id(winner)
    sessions.append((workspace_id, token, actor, winner_session))

    _, outsider_token, outsider_actor, _ = sessions[0]
    cross_workspace = api.chunk(
        workspace_id,
        outsider_token,
        outsider_actor,
        winner_session,
        offset=0,
        chunk=b"x",
    )
    assert cross_workspace.status == 404
    assert cross_workspace.json()["detail"] == "workspace_not_found"
    owner_status = api.session(
        workspace_id,
        token,
        actor,
        winner_session,
    )
    assert owner_status.status == 200
    assert owner_status.json()["upload_session"]["offset_bytes"] == 0

    for owner_id, owner_token, owner_actor, session_id in sessions:
        _cancel(
            api,
            owner_id,
            owner_token,
            owner_actor,
            session_id,
        )
    release_workspace, release_token, release_actor = api.create_workspace(
        "P6.4 quota release"
    )
    released = api.create_session(
        release_workspace,
        release_token,
        release_actor,
        name="quota-released.synthetic",
        media_type="application/octet-stream",
        payload=b"",
        size_bytes=max_file_bytes,
        sha256=declared_sha256,
        key="p64-quota-released-0001",
    )
    released_session = _session_id(released)
    _cancel(
        api,
        release_workspace,
        release_token,
        release_actor,
        released_session,
    )
    return {
        "declared_slot_bytes": max_file_bytes,
        "total_capacity_bytes": max_total_bytes,
        "reserved_before_race": total_slots - 1,
        "reservation_workspaces": total_slots - 1,
        "concurrent_contenders": 2,
        "race_successes": 1,
        "capacity_rejections": 1,
        "capacity_rejection_detail": "artifact_capacity_reached",
        "durable_bytes_written": 0,
        "cross_workspace_write_attempts": 1,
        "cross_workspace_bytes_written": 0,
        "reservations_cancelled": len(sessions) + 1,
        "capacity_released_after_cancel": True,
        "status": "PASS",
    }


def _fixture_payload(index: int) -> bytes:
    sizes = (1024, 64 * 1024, 256 * 1024)
    size = sizes[index % len(sizes)]
    seed = hashlib.sha256(f"kmfa-p64-fixture-{index}".encode()).digest()
    return (seed * ((size // len(seed)) + 1))[:size]


def _deterministic_fixture_replay(
    api: Api,
    *,
    sample_count: int,
) -> tuple[dict[str, Any], list[tuple[str, str, dict[str, str], bytes]]]:
    records: list[tuple[str, str, dict[str, str], bytes]] = []
    total_bytes = 0
    for index in range(sample_count):
        workspace_id, token, actor = api.create_workspace(
            f"P6.4 deterministic fixture {index}"
        )
        payload = _fixture_payload(index)
        uploaded = api.request(
            "PUT",
            f"/workspaces/{workspace_id}/artifact",
            body=payload,
            headers={
                **api.auth(token, actor),
                "Content-Type": "application/octet-stream",
                "X-KMFA-Filename": f"fixture-{index}.synthetic",
                "Idempotency-Key": f"p64-fixture-upload-{index:04d}",
            },
        )
        assert uploaded.status == 200, uploaded.body
        assert uploaded.json()["artifact"]["sha256"] == hashlib.sha256(
            payload
        ).hexdigest()
        downloaded = api.download(workspace_id, token, actor)
        assert downloaded.status == 200
        assert downloaded.body == payload
        records.append((workspace_id, token, actor, payload))
        total_bytes += len(payload)

    return (
        {
            "mode": "deterministic_fixture_replay",
            "real_time_soak_used": False,
            "wall_clock_promotion_threshold_used": False,
            "fixture_samples": len(records),
            "successful_uploads": len(records),
            "failed_uploads": 0,
            "download_hash_mismatches": 0,
            "total_upload_bytes": total_bytes,
            "thresholds": {
                "fixture_samples_exact": sample_count,
                "failed_uploads_max": 0,
                "download_hash_mismatches_max": 0,
            },
            "production_capacity_claimed": False,
            "status": "PASS",
        },
        records,
    )


def _database_invariants(
    state_dir: Path,
    *,
    expected_versions: int,
) -> dict[str, int]:
    root = state_dir / "walking-skeleton"
    database = root / "walking_skeleton.sqlite3"
    assert database.is_file()
    with sqlite3.connect(database) as connection:
        versions = int(
            connection.execute(
                "SELECT COUNT(*) FROM artifact_versions"
            ).fetchone()[0]
        )
        distinct_keys = int(
            connection.execute(
                "SELECT COUNT(DISTINCT storage_key) FROM artifact_versions"
            ).fetchone()[0]
        )
        lineage_gaps = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM (
                  SELECT project_id
                  FROM artifact_versions
                  GROUP BY project_id
                  HAVING MIN(version_number) <> 1
                     OR MAX(version_number) <> COUNT(*)
                     OR COUNT(DISTINCT version_number) <> COUNT(*)
                )
                """
            ).fetchone()[0]
        )
        active_reservations = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM consistency_operations
                WHERE operation_kind = 'upload'
                  AND state NOT IN ('converged', 'isolated')
                """
            ).fetchone()[0]
        )
    object_files = len(list((root / "objects").glob("*.blob")))
    request_parts = len(list((root / "tmp").glob("request-*.part")))
    chunk_parts = len(list((root / "tmp").glob("*.chunk")))
    assert versions == expected_versions
    assert distinct_keys == versions
    assert object_files == versions
    assert lineage_gaps == 0
    assert active_reservations == 0
    assert request_parts == 0
    assert chunk_parts == 0
    return {
        "artifact_versions": versions,
        "distinct_storage_keys": distinct_keys,
        "object_files": object_files,
        "version_lineage_gaps": lineage_gaps,
        "active_upload_reservations": active_reservations,
        "request_parts": request_parts,
        "chunk_parts": chunk_parts,
    }


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise AssertionError(f"missing {label} evidence")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS", (label, payload.get("status"))
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    assert path.stat().st_size <= RECEIPT_MAX_BYTES


def _component_evidence(arguments: argparse.Namespace) -> dict[str, dict[str, Any]]:
    return {
        "resumable": _load_json(arguments.resumable, "resumable"),
        "file_security": _load_json(
            arguments.file_security,
            "file-security",
        ),
        "object_storage": _load_json(
            arguments.object_storage,
            "object-storage",
        ),
        "lineage": _load_json(arguments.lineage, "lineage"),
    }


def _assert_component_contracts(
    components: dict[str, dict[str, Any]],
    image_id: str,
) -> None:
    component_image_ids = {
        components["resumable"]["image_id"],
        components["file_security"]["image_id"],
        components["object_storage"]["application_image_id"],
        components["lineage"]["image_id"],
    }
    assert component_image_ids == {image_id}
    resumable = components["resumable"]
    assert resumable["interruption"]["mid_chunk_disconnect_count"] == 1
    assert resumable["interruption"]["partial_chunk_accepted"] == 0
    assert resumable["concurrency"]["durable_chunk_copies"] == 1
    assert all(value == 0 for value in resumable["negative_oracles"].values())
    security = components["file_security"]
    assert security["malicious_or_malformed_escape_count"] == 0
    assert security["legal_false_rejections"] == 0
    assert security["scanner_backlog"]["status"] == "PASS"
    assert security["scanner_backlog"]["remaining_retryable"] == 0
    object_storage = components["object_storage"]
    object_fault = object_storage["object_store_fault_injection"]
    assert object_fault["status"] == "PASS"
    assert object_fault["initial_request_status"] == 503
    assert object_fault["idempotent_replay_status"] == 200
    assert object_fault["duplicate_versions"] == 0
    assert object_fault["real_time_stall_used"] is False
    lineage = components["lineage"]
    assert lineage["original_overwrite_count"] == 0
    assert lineage["version_parent_gaps"] == 0
    assert lineage["lineage_gaps"] == 0


def _build_outputs(
    *,
    image_id: str,
    fixture_replay: dict[str, Any],
    quota: dict[str, Any],
    database: dict[str, int],
    components: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    scanner = components["file_security"]["scanner_backlog"]
    object_fault = components["object_storage"][
        "object_store_fault_injection"
    ]
    resumable = components["resumable"]
    lineage = components["lineage"]
    benchmark = {
        "schema_version": "kmfa.s06.p64.upload-benchmark.v2",
        "status": "PASS",
        "image_id": image_id,
        "synthetic_only": True,
        "deterministic_fixture_replay": fixture_replay,
        "scanner_backlog": scanner,
        "object_store_fault_injection": object_fault,
        "real_time_soak_used": False,
        "production_capacity_claimed": False,
        "production_capacity_stage": "S11/P11.3",
    }
    matrix_rows = [
        {
            "case": "arbitrary-file fixtures",
            "observed": resumable["file_type_cases"],
            "expected": "all attachment-only, exact hash download",
            "status": "PASS",
        },
        {
            "case": "mid-chunk disconnect and restart",
            "observed": resumable["interruption"],
            "expected": "partial bytes rejected; exact offset recovery",
            "status": "PASS",
        },
        {
            "case": "overlimit and checksum tamper",
            "observed": resumable["negative_oracles"],
            "expected": "zero bytes/version published",
            "status": "PASS",
        },
        {
            "case": "duplicate concurrent chunk",
            "observed": resumable["concurrency"],
            "expected": "two safe replies, one durable copy",
            "status": "PASS",
        },
        {
            "case": "quota competition",
            "observed": quota,
            "expected": "one winner, one bounded rejection, release on cancel",
            "status": "PASS",
        },
        {
            "case": "cross-workspace upload write",
            "observed": quota["cross_workspace_bytes_written"],
            "expected": 0,
            "status": "PASS",
        },
        {
            "case": "scanner unavailable fault",
            "observed": {
                "unavailable_retry": components["file_security"][
                    "unavailable_retry_converged"
                ],
                "real_time_window_wait_used": scanner[
                    "real_time_window_wait_used"
                ],
            },
            "expected": "never clean; retry converges; no window wait",
            "status": "PASS",
        },
        {
            "case": "scanner retry backlog",
            "observed": scanner,
            "expected": "all drained; zero preview/processing exposure",
            "status": "PASS",
        },
        {
            "case": "object-store unavailable fault",
            "observed": object_fault,
            "expected": "503 then replay; one DB and native object version",
            "status": "PASS",
        },
        {
            "case": "version lineage preservation",
            "observed": {
                "overwrite": lineage["original_overwrite_count"],
                "parent_gaps": lineage["version_parent_gaps"],
                "lineage_gaps": lineage["lineage_gaps"],
                "quality_gate_database": database,
            },
            "expected": "zero overwrite and gaps",
            "status": "PASS",
        },
    ]
    negative_matrix = {
        "schema_version": "kmfa.s06.p64.negative-matrix.v1",
        "status": "PASS",
        "image_id": image_id,
        "synthetic_only": True,
        "rows": matrix_rows,
        "failed_rows": 0,
        "unexplained_failures": 0,
    }
    status_contract = resumable["contract"]
    thresholds = {
        "schema_version": "kmfa.s06.p64.capacity-thresholds.v2",
        "status": "PASS",
        "image_id": image_id,
        "product_contract": {
            "max_file_bytes": status_contract["max_file_bytes"],
            "max_chunk_bytes": status_contract["max_chunk_bytes"],
            "max_sessions_per_workspace": status_contract[
                "max_sessions_per_workspace"
            ],
            "max_total_artifact_bytes": quota["total_capacity_bytes"],
        },
        "quality_gate": {
            "deterministic_fixture_replay": fixture_replay["thresholds"],
            "scanner_backlog": scanner["thresholds"],
            "object_store_fault_injection": object_fault["thresholds"],
            "data_invariants": {
                "cross_workspace_bytes_written_max": 0,
                "duplicate_object_versions_max": 0,
                "version_lineage_gaps_max": 0,
                "active_upload_reservations_max": 0,
                "temporary_parts_max": 0,
            },
        },
        "rollback": {
            "reduce_upload_concurrency_or_size": True,
            "queue_or_degrade_scanning": True,
            "preserve_existing_downloads": True,
            "delete_state_or_volumes": False,
        },
        "real_time_soak_used": False,
        "required_validation_mode": (
            "fixture_replay_fake_clock_fault_injection"
        ),
        "production_capacity_claimed": False,
        "production_capacity_stage": "S11/P11.3",
    }
    summary = {
        "schema_version": "kmfa.s06.p64.upload-quality-gate.v2",
        "status": "PASS",
        "task": "T-S06-04",
        "phase": "P6.4",
        "image_id": image_id,
        "synthetic_only": True,
        "component_oracles": {
            name: "PASS" for name in sorted(components)
        },
        "benchmark": "benchmark.json",
        "negative_matrix": "negative-matrix.json",
        "capacity_thresholds": "capacity-thresholds.json",
        "negative_rows": len(matrix_rows),
        "failed_rows": 0,
        "unexplained_failures": 0,
        "data_invariant_failures": 0,
        "isolation_failures": 0,
        "real_time_soak_used": False,
        "production_capacity_claimed": False,
        "next_capacity_stage": "S11/P11.3",
    }
    return benchmark, negative_matrix, thresholds, summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--container-name", default="kmfa-p64-e2e")
    parser.add_argument("--port", type=int, default=18109)
    parser.add_argument(
        "--fixture-samples",
        type=int,
        default=FIXTURE_SAMPLES_DEFAULT,
    )
    parser.add_argument("--resumable", type=Path, required=True)
    parser.add_argument("--file-security", type=Path, required=True)
    parser.add_argument("--object-storage", type=Path, required=True)
    parser.add_argument("--lineage", type=Path, required=True)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    assert CONTAINER_RE.fullmatch(arguments.container_name)
    assert (
        FIXTURE_SAMPLES_MIN
        <= arguments.fixture_samples
        <= FIXTURE_SAMPLES_MAX
    )
    arguments.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert not any(arguments.state_dir.iterdir())
    arguments.out_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert not any(arguments.out_dir.iterdir())
    image_id = _run(
        "docker",
        "image",
        "inspect",
        "--format",
        "{{.Id}}",
        arguments.image,
    ).stdout.strip()
    assert image_id.startswith("sha256:")
    components = _component_evidence(arguments)
    _assert_component_contracts(components, image_id)

    container = Container(
        name=arguments.container_name,
        image=arguments.image,
        state_dir=arguments.state_dir.resolve(),
        port=arguments.port,
    )
    capabilities: list[str] = []
    try:
        container.start(resumable=True)
        api = Api(container.base_url, capabilities)
        status_contract = api.request("GET", "/status").json()
        quota = _quota_competition(
            api,
            max_total_bytes=int(
                status_contract["limits"]["max_total_artifact_bytes"]
            ),
            max_file_bytes=int(
                status_contract["resumable_upload"]["max_file_bytes"]
            ),
        )
        fixture_replay, records = _deterministic_fixture_replay(
            api,
            sample_count=arguments.fixture_samples,
        )
        container.restart()
        restarted_api = Api(container.base_url, capabilities)
        for workspace_id, token, actor, payload in (records[0], records[-1]):
            downloaded = restarted_api.download(workspace_id, token, actor)
            assert downloaded.status == 200
            assert downloaded.body == payload
        fixture_replay["restart_hash_checks"] = 2
        logs = container.logs()
        assert not any(value in logs for value in capabilities)
        container.remove()

        database = _database_invariants(
            arguments.state_dir,
            expected_versions=arguments.fixture_samples,
        )
        persisted = b"".join(
            path.read_bytes()
            for path in (arguments.state_dir / "walking-skeleton").rglob("*")
            if path.is_file()
        )
        assert not any(
            value.encode("utf-8") in persisted for value in capabilities
        )
        benchmark, matrix, thresholds, summary = _build_outputs(
            image_id=image_id,
            fixture_replay=fixture_replay,
            quota=quota,
            database=database,
            components=components,
        )
        _write_json(arguments.out_dir / "benchmark.json", benchmark)
        _write_json(arguments.out_dir / "negative-matrix.json", matrix)
        _write_json(
            arguments.out_dir / "capacity-thresholds.json",
            thresholds,
        )
        _write_json(arguments.out_dir / "summary.json", summary)
        scanner_backlog = components["file_security"]["scanner_backlog"]
        object_fault = components["object_storage"][
            "object_store_fault_injection"
        ]
        report = (
            "# S06/P6.4 final-image upload quality validation\n\n"
            f"- image: `{image_id}`\n"
            "- result: **PASS**\n"
            "- real-time soak / observation window / wall-clock gate: "
            "`not used`\n"
            f"- deterministic fixture replay: "
            f"`{fixture_replay['fixture_samples']}` uploads, failures `0`, "
            "hash mismatches `0`\n"
            "- quota race: one winner, one capacity rejection; cancellation "
            "released capacity; cross-workspace bytes written `0`\n"
            f"- scanner backlog drained: `{scanner_backlog['drained']}`; "
            "remaining `0`\n"
            "- object-store unavailable fault: immediate `503`, replay "
            f"`{object_fault['idempotent_replay_status']}`; duplicate "
            "versions `0`; no real-time stall\n"
            f"- negative matrix: `{len(matrix['rows'])}/{len(matrix['rows'])}` PASS; "
            "data invariant/isolation failures `0/0`\n"
            "- this is an immediate fixture/fault-injection validation, not a "
            "production capacity claim; later capacity work must use "
            "deterministic replay rather than elapsed-time promotion\n"
        )
        report_path = arguments.out_dir / "report.md"
        report_path.write_text(report, encoding="utf-8")
        assert report_path.stat().st_size <= RECEIPT_MAX_BYTES
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        container.remove()


if __name__ == "__main__":
    raise SystemExit(main())
