#!/usr/bin/env python3
"""Production-image S05/P5.3 crash/timeout/duplicate convergence Oracle."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

POSTGRES_IMAGE = (
    "postgres:17.10-alpine3.23@"
    "sha256:8189a1f6e40904781fc9e2612687877791d21679866db58b1de996b31fc312e4"
)
MINIO_IMAGE = (
    "minio/minio:RELEASE.2025-09-07T16-13-09Z@"
    "sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e"
)
MC_IMAGE = (
    "minio/mc:RELEASE.2025-08-13T08-35-41Z@"
    "sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727"
)
FAULT_EXIT = 86
UPLOAD_FAULTS = (
    "effect_pending",
    "primary_effect_applied",
    "effect_applied",
    "commit_pending",
    "outbox_committed",
    "converged",
)
GENERIC_FAULTS = UPLOAD_FAULTS
OUTBOX_FAULTS = (
    "outbox_leased",
    "outbox_effect_applied",
    "outbox_receipt_recorded",
    "outbox_delivered",
)
ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "KMFA" / "app" / "object-store-policy.json"


def _timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _run(
    *command: str,
    check: bool = True,
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if check and completed.returncode != 0:
        output = (completed.stdout + "\n" + completed.stderr)[-5000:]
        raise RuntimeError(
            f"command failed ({completed.returncode}): {command[0]}\n{output}"
        )
    return completed


def _wait_until(label: str, command: Sequence[str], *, attempts: int = 60) -> None:
    for _ in range(attempts):
        if _run(*command, check=False, timeout=10).returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError(f"{label} did not become ready")


def _parse_json(output: str) -> dict[str, Any]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("worker did not produce JSON")
    parsed = json.loads(lines[-1])
    if not isinstance(parsed, dict):
        raise RuntimeError("worker JSON is not an object")
    return parsed


class Oracle:
    def __init__(
        self,
        *,
        image: str,
        state_dir: Path,
        out_dir: Path,
        prefix: str,
    ) -> None:
        self.image = image
        self.state_dir = state_dir.resolve()
        self.out_dir = out_dir.resolve()
        self.prefix = prefix
        self.network = f"{prefix}-net"
        self.postgres = f"{prefix}-pg"
        self.object_store = f"{prefix}-object"
        self.pg_volume = f"{prefix}-pgdata"
        self.object_volume = f"{prefix}-objectdata"
        self.database_password = "p53-postgres-synthetic-only"
        self.object_root_user = "p53-root-synthetic"
        self.object_root_password = "p53-root-password-synthetic-only"
        self.object_app_user = "p53-app-synthetic"
        self.object_app_secret = "p53-app-secret-synthetic-only"
        self.worker_outputs: list[dict[str, Any]] = []

    def cleanup(self) -> None:
        for container in (self.postgres, self.object_store):
            _run("docker", "rm", "-f", container, check=False, timeout=30)
        for volume in (self.pg_volume, self.object_volume):
            _run("docker", "volume", "rm", volume, check=False, timeout=30)
        _run("docker", "network", "rm", self.network, check=False, timeout=30)

    def start(self) -> None:
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.out_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.cleanup()
        _run("docker", "network", "create", self.network)
        _run("docker", "volume", "create", self.pg_volume)
        _run("docker", "volume", "create", self.object_volume)
        _run(
            "docker",
            "run",
            "-d",
            "--name",
            self.postgres,
            "--network",
            self.network,
            "-e",
            "POSTGRES_DB=kmfa",
            "-e",
            "POSTGRES_USER=kmfa",
            "-e",
            f"POSTGRES_PASSWORD={self.database_password}",
            "-v",
            f"{self.pg_volume}:/var/lib/postgresql/data",
            POSTGRES_IMAGE,
        )
        _run(
            "docker",
            "run",
            "-d",
            "--name",
            self.object_store,
            "--network",
            self.network,
            "--network-alias",
            "object-store",
            "-e",
            f"MINIO_ROOT_USER={self.object_root_user}",
            "-e",
            f"MINIO_ROOT_PASSWORD={self.object_root_password}",
            "-v",
            f"{self.object_volume}:/data",
            MINIO_IMAGE,
            "server",
            "/data",
            "--console-address",
            ":9001",
        )
        _wait_until(
            "PostgreSQL",
            (
                "docker",
                "exec",
                self.postgres,
                "pg_isready",
                "-U",
                "kmfa",
                "-d",
                "kmfa",
            ),
        )
        _wait_until(
            "object store",
            (
                "docker",
                "exec",
                self.object_store,
                "curl",
                "--fail",
                "--silent",
                "http://127.0.0.1:9000/minio/health/ready",
            ),
        )
        bootstrap = """
set -eu
mc alias set local http://object-store:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mb --ignore-existing "local/$KMFA_S3_BUCKET"
mc anonymous set none "local/$KMFA_S3_BUCKET"
mc version enable "local/$KMFA_S3_BUCKET"
mc admin user add local "$KMFA_S3_ACCESS_KEY_ID" "$KMFA_S3_SECRET_ACCESS_KEY"
mc admin policy create local kmfa-p53-private /policy/object-store-policy.json
mc admin policy attach local kmfa-p53-private --user "$KMFA_S3_ACCESS_KEY_ID"
"""
        _run(
            "docker",
            "run",
            "--rm",
            "--network",
            self.network,
            "-e",
            f"MINIO_ROOT_USER={self.object_root_user}",
            "-e",
            f"MINIO_ROOT_PASSWORD={self.object_root_password}",
            "-e",
            "KMFA_S3_BUCKET=kmfa-private-artifacts",
            "-e",
            f"KMFA_S3_ACCESS_KEY_ID={self.object_app_user}",
            "-e",
            f"KMFA_S3_SECRET_ACCESS_KEY={self.object_app_secret}",
            "-v",
            f"{POLICY}:/policy/object-store-policy.json:ro",
            "--entrypoint",
            "/bin/sh",
            MC_IMAGE,
            "-ec",
            bootstrap,
        )

    def _worker_command(self, arguments: Sequence[str]) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "--network",
            self.network,
            "-e",
            "KMFA_WALKING_SKELETON_ENABLED=1",
            "-e",
            "PYTHONPATH=/opt/kmfa/KMOS/KMFA/app/backend",
            "-e",
            "KMFA_WALKING_SKELETON_STATE_DIR=/var/lib/kmfa/state",
            "-e",
            "KMFA_STRUCTURED_DATABASE_MODE=postgresql-primary",
            "-e",
            (
                "KMFA_STRUCTURED_DATABASE_URL="
                f"postgresql://kmfa:{self.database_password}@"
                f"{self.postgres}:5432/kmfa"
            ),
            "-e",
            "KMFA_ARTIFACT_STORAGE_MODE=s3",
            "-e",
            "KMFA_S3_ENDPOINT_URL=http://object-store:9000",
            "-e",
            "KMFA_S3_BUCKET=kmfa-private-artifacts",
            "-e",
            "KMFA_S3_REGION=us-east-1",
            "-e",
            "KMFA_S3_PREFIX=kmfa/private/v1",
            "-e",
            f"KMFA_S3_ACCESS_KEY_ID={self.object_app_user}",
            "-e",
            f"KMFA_S3_SECRET_ACCESS_KEY={self.object_app_secret}",
            "-e",
            "KMFA_S3_ADDRESSING_STYLE=path",
            "-e",
            "KMFA_S3_ALLOW_INSECURE_LOCAL=1",
            "-e",
            (
                "KMFA_CONSISTENCY_ORACLE_SINK="
                "/var/lib/kmfa/state/oracle-effects.sqlite3"
            ),
            "-v",
            f"{self.state_dir}:/var/lib/kmfa/state",
            self.image,
            "python",
            "/opt/kmfa/KMOS/KMFA/app/e2e/consistency_fault_worker.py",
            *arguments,
        ]

    def worker(
        self,
        arguments: Sequence[str],
        *,
        expected_returncode: int = 0,
    ) -> dict[str, Any] | None:
        completed = _run(
            *self._worker_command(arguments),
            check=False,
            timeout=180,
        )
        if completed.returncode != expected_returncode:
            output = (completed.stdout + "\n" + completed.stderr)[-5000:]
            raise RuntimeError(
                "fault worker returned "
                f"{completed.returncode}, expected {expected_returncode}\n"
                f"{output}"
            )
        if expected_returncode != 0:
            return None
        parsed = _parse_json(completed.stdout)
        self.worker_outputs.append(parsed)
        return parsed

    def fault_then_recover(
        self,
        base_arguments: Sequence[str],
        fault: str,
    ) -> dict[str, Any]:
        self.worker(
            [*base_arguments, "--fault", fault],
            expected_returncode=FAULT_EXIT,
        )
        recovered = self.worker(base_arguments)
        assert recovered is not None
        return recovered

    def execute_matrix(self) -> dict[str, Any]:
        fault_rows: list[dict[str, Any]] = []
        for fault in UPLOAD_FAULTS:
            scenario = f"upload-{fault}"
            recovered = self.fault_then_recover(
                ["--mode", "upload", "--scenario", scenario],
                fault,
            )
            if recovered["result"] != "converged":
                raise RuntimeError("upload did not converge")
            fault_rows.append(
                {
                    "flow": "upload",
                    "fault": fault,
                    "outcome": "converged",
                }
            )

        for operation_kind in ("process", "index", "export"):
            for fault in GENERIC_FAULTS:
                scenario = f"{operation_kind}-{fault}"
                recovered = self.fault_then_recover(
                    [
                        "--mode",
                        "generic",
                        "--operation-kind",
                        operation_kind,
                        "--scenario",
                        scenario,
                    ],
                    fault,
                )
                if recovered["result"] != "converged":
                    raise RuntimeError("generic operation did not converge")
                fault_rows.append(
                    {
                        "flow": operation_kind,
                        "fault": fault,
                        "outcome": "converged",
                    }
                )

        for fault in OUTBOX_FAULTS:
            scenario = f"outbox-{fault}"
            recovered = self.fault_then_recover(
                [
                    "--mode",
                    "outbox",
                    "--operation-kind",
                    "process",
                    "--scenario",
                    scenario,
                ],
                fault,
            )
            if recovered["result"] not in {"delivered", "idle"}:
                raise RuntimeError("outbox did not converge")
            fault_rows.append(
                {
                    "flow": "outbox",
                    "fault": fault,
                    "outcome": "delivered",
                }
            )

        generic_timeout = self.worker(
            [
                "--mode",
                "generic",
                "--operation-kind",
                "process",
                "--scenario",
                "generic-timeout-after-apply",
                "--timeout-once",
            ]
        )
        if generic_timeout is None or generic_timeout["result"] != "converged":
            raise RuntimeError("generic timeout did not converge")
        outbox_timeout_first = self.worker(
            [
                "--mode",
                "outbox",
                "--operation-kind",
                "index",
                "--scenario",
                "outbox-timeout-after-apply",
                "--timeout-once",
            ]
        )
        outbox_timeout_second = self.worker(
            [
                "--mode",
                "outbox",
                "--operation-kind",
                "index",
                "--scenario",
                "outbox-timeout-after-apply",
                "--timeout-once",
            ]
        )
        if (
            outbox_timeout_first is None
            or outbox_timeout_first["result"] != "retry"
            or outbox_timeout_second is None
            or outbox_timeout_second["result"] != "delivered"
        ):
            raise RuntimeError("outbox timeout did not retry and converge")

        mismatch = self.worker(
            [
                "--mode",
                "generic",
                "--operation-kind",
                "export",
                "--scenario",
                "export-explicit-mismatch",
                "--mismatch",
            ]
        )
        if mismatch is None or mismatch["result"] != "isolated":
            raise RuntimeError("mismatch was not isolated")
        orphan = self.worker(
            ["--mode", "orphan", "--scenario", "orphan-object"]
        )
        if (
            orphan is None
            or orphan["result"] != "isolated"
            or orphan["quarantined"] < 1
            or orphan["raw_object_deletes"] != 0
        ):
            raise RuntimeError("orphan quarantine failed")

        delivered = 0
        for _ in range(100):
            drained = self.worker(["--mode", "drain"])
            if drained is None:
                raise RuntimeError("drain returned no result")
            if drained["result"] == "idle":
                break
            if drained["result"] == "delivered":
                delivered += 1
                continue
            raise RuntimeError("bounded drain did not deliver")
        else:
            raise RuntimeError("outbox drain did not become idle")

        final = self.worker(["--mode", "report"])
        if final is None:
            raise RuntimeError("final report missing")
        reconciliation = final["reconciliation"]
        expected_operations = 31
        expected_outbox = 30
        required = {
            "operation_count": expected_operations,
            "partial_operation_count": 0,
            "outbox_event_count": expected_outbox,
            "partial_outbox_count": 0,
            "unexplained_terminal_states": 0,
            "duplicate_effect_receipts": 0,
        }
        for key, expected in required.items():
            if reconciliation[key] != expected:
                raise RuntimeError(
                    f"final reconciliation mismatch: {key}="
                    f"{reconciliation[key]} expected {expected}"
                )
        if reconciliation["operation_state_counts"] != {
            "converged": 30,
            "isolated": 1,
        }:
            raise RuntimeError("operation terminal state matrix mismatch")
        if reconciliation["outbox_state_counts"] != {"delivered": 30}:
            raise RuntimeError("outbox terminal state matrix mismatch")
        if (
            final["duplicate_external_side_effects"] != 0
            or final["raw_object_deletes"] != 0
            or reconciliation["quarantined_object_count"] < 1
        ):
            raise RuntimeError("side-effect or quarantine invariant failed")
        if final["traced_operation_count"] != expected_operations:
            raise RuntimeError("not every operation has a trace")
        staged_part_count = sum(
            1
            for path in self.state_dir.rglob("*.part")
            if path.is_file() or path.is_symlink()
        )
        if staged_part_count:
            raise RuntimeError("converged Oracle left staged upload residue")

        return {
            "schema_version": "kmfa.s05.p53.consistency-state-oracle.v1",
            "status": "PASS",
            "completed_at": _timestamp(),
            "synthetic_only": True,
            "application_image_id": _run(
                "docker",
                "image",
                "inspect",
                self.image,
                "--format",
                "{{.Id}}",
            ).stdout.strip(),
            "postgres_image_id": _run(
                "docker",
                "image",
                "inspect",
                POSTGRES_IMAGE,
                "--format",
                "{{.Id}}",
            ).stdout.strip(),
            "object_image_id": _run(
                "docker",
                "image",
                "inspect",
                MINIO_IMAGE,
                "--format",
                "{{.Id}}",
            ).stdout.strip(),
            "fault_matrix": fault_rows,
            "fault_injection_count": len(fault_rows),
            "timeout_injection_count": 2,
            "explicit_isolation_count": 2,
            "outbox_events_drained_after_fault_matrix": delivered,
            "recovery_mode": "immediate_fault_replay",
            "wall_clock_gate_used": False,
            "reconciliation": reconciliation,
            "trace_count": final["trace_count"],
            "traced_operation_count": final["traced_operation_count"],
            "external_effect_count": final["external_effect_count"],
            "external_effect_attempt_count": final[
                "external_effect_attempt_count"
            ],
            "duplicate_external_side_effects": final[
                "duplicate_external_side_effects"
            ],
            "raw_object_deletes": 0,
            "staged_part_count": staged_part_count,
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="kmfa-p53-local")
    args = parser.parse_args(argv)
    if re.fullmatch(r"kmfa-p53-[a-z0-9][a-z0-9-]{1,20}", args.prefix) is None:
        raise SystemExit("invalid Docker resource prefix")
    oracle = Oracle(
        image=args.image,
        state_dir=args.state_dir,
        out_dir=args.out_dir,
        prefix=args.prefix,
    )
    try:
        oracle.start()
        report = oracle.execute_matrix()
        encoded = json.dumps(
            report,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        forbidden = (
            oracle.database_password,
            oracle.object_root_user,
            oracle.object_root_password,
            oracle.object_app_user,
            oracle.object_app_secret,
            "kmfa/private/v1/artifacts/",
        )
        if any(value in encoded for value in forbidden):
            raise RuntimeError("Oracle evidence contains a credential or raw key")
        (oracle.out_dir / "consistency-state-report.json").write_text(
            encoded + "\n",
            encoding="utf-8",
        )
        matrix = {
            "schema_version": "kmfa.s05.p53.fault-matrix.v1",
            "rows": report["fault_matrix"],
            "raw_object_deletes": 0,
        }
        (oracle.out_dir / "fault-matrix.json").write_text(
            json.dumps(matrix, ensure_ascii=True, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        print(encoded)
    finally:
        oracle.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
