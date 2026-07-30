#!/usr/bin/env python3
"""Fetch the hash-bound private input set and publish the KMFA runtime snapshot.

Private-Database is accessed only through ``private_db_client.py``. The script
does not clone that repository, does not log private filenames, and removes the
download staging directory after every run.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


MODULE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.dont_write_bytecode = True
sys.path.insert(0, str(MODULE_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from KMDatabase.machine.tools import private_db_client  # noqa: E402
from project_cost_table.operational import (  # noqa: E402
    ProjectCostError,
    calculate_and_generate,
    pretty_json,
    verify_output,
    write_runtime_projection,
)


AREA = "Private-KMDatabase"
SCHEMA_VERSION = "kmfa.project_cost.operational_private_inputs.v1"
OPERATIONAL_VERSION = "0.0.5"
MAX_FILES = 128
MAX_TOTAL_BYTES = 512 * 1024 * 1024
ALLOWED_SUFFIXES = (".xlsx", ".zip", ".jsonl", ".jsonl.gz")
PRIVATE_INPUT_ROOT = "KMFA" + "_MetaData"
INTEGER_CONTROL_FIELDS = (
    "project_count",
    "event_count",
    "job_cost_total_cents",
    "gl_recognized_cogs_total_cents",
    "ledger_selected_book_count",
    "qualified_accrual_event_count",
    "labor_wage_component_event_count",
    "p0_review_count",
    "p1_review_count",
    "p2_review_count",
    "ledger_stale_entity_count",
)
TEXT_CONTROL_FIELDS = (
    "ledger_minimum_period_end",
    "ledger_maximum_period_end",
)
EXPECTED_CONTROL_FIELDS = INTEGER_CONTROL_FIELDS + TEXT_CONTROL_FIELDS


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative(value: Any, *, field: str) -> PurePosixPath:
    text = str(value or "")
    path = PurePosixPath(text)
    if (
        not text
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or "\\" in text
        or "\x00" in text
    ):
        raise ProjectCostError(
            "PRIVATE_MANIFEST_PATH",
            "%s must be a normalized relative POSIX path" % field,
        )
    return path


def validate_manifest(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate the private manifest before downloading any business file."""

    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ProjectCostError(
            "PRIVATE_MANIFEST_SCHEMA",
            "private input manifest schema version is unsupported",
        )
    if payload.get("operational_version") != OPERATIONAL_VERSION:
        raise ProjectCostError(
            "PRIVATE_MANIFEST_VERSION",
            "private manifest does not target this operational version",
        )
    files = payload.get("files")
    if not isinstance(files, list) or not files or len(files) > MAX_FILES:
        raise ProjectCostError(
            "PRIVATE_MANIFEST_FILE_COUNT",
            "private manifest file count is empty or over the limit",
        )
    normalized: List[Dict[str, Any]] = []
    repo_seen = set()
    local_seen = set()
    total_bytes = 0
    for index, raw in enumerate(files):
        if not isinstance(raw, dict):
            raise ProjectCostError(
                "PRIVATE_MANIFEST_FILE",
                "private manifest file row is not an object",
            )
        repo_path = _safe_relative(raw.get("repo_path"), field="repo_path")
        local_path = _safe_relative(raw.get("local_path"), field="local_path")
        if repo_path.parts[0] != PRIVATE_INPUT_ROOT:
            raise ProjectCostError(
                "PRIVATE_MANIFEST_SCOPE",
                "private source must remain inside the declared KMFA input root",
            )
        if not any(str(local_path).lower().endswith(suffix) for suffix in ALLOWED_SUFFIXES):
            raise ProjectCostError(
                "PRIVATE_MANIFEST_SUFFIX",
                "private source suffix is not allowlisted",
            )
        digest = str(raw.get("sha256") or "").lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ProjectCostError(
                "PRIVATE_MANIFEST_SHA256",
                "private source digest is invalid",
            )
        size = raw.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ProjectCostError(
                "PRIVATE_MANIFEST_SIZE",
                "private source size is invalid",
            )
        role = str(raw.get("role") or "")
        if not role:
            raise ProjectCostError(
                "PRIVATE_MANIFEST_ROLE",
                "private source role is missing",
            )
        if str(repo_path) in repo_seen or str(local_path) in local_seen:
            raise ProjectCostError(
                "PRIVATE_MANIFEST_DUPLICATE",
                "private manifest contains duplicate source or destination paths",
            )
        repo_seen.add(str(repo_path))
        local_seen.add(str(local_path))
        total_bytes += size
        normalized.append(
            {
                "index": index,
                "repo_path": str(repo_path),
                "local_path": str(local_path),
                "sha256": digest,
                "size_bytes": size,
                "role": role,
            }
        )
    if total_bytes > MAX_TOTAL_BYTES:
        raise ProjectCostError(
            "PRIVATE_MANIFEST_TOTAL_SIZE",
            "private input set is over the bounded download limit",
        )

    run = payload.get("run")
    if not isinstance(run, dict):
        raise ProjectCostError(
            "PRIVATE_MANIFEST_RUN",
            "private manifest run contract is missing",
        )
    data_root = _safe_relative(run.get("data_root"), field="run.data_root")
    ocr_path = _safe_relative(run.get("ocr_path"), field="run.ocr_path")
    payroll_paths = [
        _safe_relative(value, field="run.payroll_paths")
        for value in (run.get("payroll_paths") or [])
    ]
    attendance_roots = [
        _safe_relative(value, field="run.attendance_roots")
        for value in (run.get("attendance_roots") or [])
    ]
    local_paths = {row["local_path"] for row in normalized}
    if str(ocr_path) not in local_paths:
        raise ProjectCostError(
            "PRIVATE_MANIFEST_OCR",
            "OCR path is not bound to a manifest file",
        )
    if not payroll_paths or any(str(path) not in local_paths for path in payroll_paths):
        raise ProjectCostError(
            "PRIVATE_MANIFEST_PAYROLL",
            "payroll paths are missing or not bound to manifest files",
        )
    year = run.get("year")
    as_of = str(run.get("as_of") or "")
    if not isinstance(year, int) or year < 2000 or year > 2100:
        raise ProjectCostError("PRIVATE_MANIFEST_YEAR", "run year is invalid")
    try:
        datetime.strptime(as_of, "%Y-%m-%d")
    except ValueError as exc:
        raise ProjectCostError(
            "PRIVATE_MANIFEST_AS_OF",
            "run as_of must be YYYY-MM-DD",
        ) from exc
    expected = payload.get("expected_controls")
    if not isinstance(expected, dict) or not expected:
        raise ProjectCostError(
            "PRIVATE_MANIFEST_CONTROLS",
            "expected controls are required",
        )
    if set(expected) != set(EXPECTED_CONTROL_FIELDS):
        raise ProjectCostError(
            "PRIVATE_MANIFEST_CONTROLS",
            "expected controls must use the complete allowlisted field set",
        )
    if any(
        not isinstance(expected[field], int)
        or isinstance(expected[field], bool)
        for field in INTEGER_CONTROL_FIELDS
    ):
        raise ProjectCostError(
            "PRIVATE_MANIFEST_CONTROLS",
            "every expected control must be an integer",
        )
    if any(
        not isinstance(expected[field], str)
        or not expected[field]
        for field in TEXT_CONTROL_FIELDS
    ):
        raise ProjectCostError(
            "PRIVATE_MANIFEST_CONTROLS",
            "every expected period control must be a non-empty string",
        )
    if expected["p0_review_count"] != 0:
        raise ProjectCostError(
            "PRIVATE_MANIFEST_P0_CONTROL",
            "the production expected control must require zero P0 reviews",
        )
    return {
        "files": normalized,
        "total_bytes": total_bytes,
        "run": {
            "year": year,
            "as_of": as_of,
            "data_root": str(data_root),
            "ocr_path": str(ocr_path),
            "payroll_paths": [str(path) for path in payroll_paths],
            "attendance_roots": [str(path) for path in attendance_roots],
        },
        "expected_controls": dict(expected),
    }


def _fetch(area: str, repo_path: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()):
        private_db_client.get(area, repo_path, str(destination))


def fetch_manifest(manifest_relpath: str, staging_root: Path) -> Tuple[Dict[str, Any], str]:
    manifest_path = staging_root / "private_input_manifest.json"
    _fetch(AREA, manifest_relpath, manifest_path)
    manifest_sha256 = _sha256(manifest_path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectCostError(
            "PRIVATE_MANIFEST_UNREADABLE",
            "private input manifest cannot be parsed",
        ) from exc
    validated = validate_manifest(payload)
    input_root = staging_root / "input"
    for record in validated["files"]:
        destination = input_root / Path(record["local_path"])
        _fetch(AREA, record["repo_path"], destination)
        if destination.stat().st_size != record["size_bytes"]:
            raise ProjectCostError(
                "PRIVATE_SOURCE_SIZE",
                "downloaded private source size differs from manifest",
            )
        if _sha256(destination) != record["sha256"]:
            raise ProjectCostError(
                "PRIVATE_SOURCE_SHA256",
                "downloaded private source digest differs from manifest",
            )
    return validated, manifest_sha256


def _expectations(
    result: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> Dict[str, Any]:
    coverage = result.get("coverage") or {}
    actual = {
        "project_count": result.get("project_count"),
        "event_count": result.get("event_count"),
        "job_cost_total_cents": result.get("job_cost_total_cents"),
        "gl_recognized_cogs_total_cents": result.get(
            "gl_recognized_cogs_total_cents"
        ),
        "ledger_selected_book_count": coverage.get(
            "ledger_selected_book_count"
        ),
        "qualified_accrual_event_count": coverage.get(
            "qualified_accrual_event_count"
        ),
        "labor_wage_component_event_count": coverage.get(
            "labor_wage_component_event_count"
        ),
        "p0_review_count": result.get("p0_review_count"),
        "p1_review_count": result.get("p1_review_count"),
        "p2_review_count": result.get("p2_review_count"),
        "ledger_stale_entity_count": coverage.get(
            "ledger_stale_entity_count"
        ),
        "ledger_minimum_period_end": coverage.get(
            "ledger_minimum_period_end"
        ),
        "ledger_maximum_period_end": coverage.get(
            "ledger_logical_period_end"
        ),
    }
    drift = {
        key: {"expected": expected.get(key), "actual": actual.get(key)}
        for key in expected
        if actual.get(key) != expected.get(key)
    }
    if drift:
        raise ProjectCostError(
            "PRIVATE_EXPECTED_CONTROL_DRIFT",
            "production calculation differs from the hash-bound control set",
        )
    return actual


def _publish_sealed_workbook(
    source: Path,
    runtime_json: Path,
    snapshot_id: str,
) -> Dict[str, Any]:
    """Publish an immutable verified workbook before its runtime pointer."""

    source_path = Path(source)
    if source_path.is_symlink() or not source_path.is_file():
        raise ProjectCostError(
            "PRIVATE_WORKBOOK_SOURCE",
            "verified workbook source is unavailable or symbolic",
        )
    digest = _sha256(source_path)
    filename = "current_project_cost_%s_%s.xlsx" % (
        snapshot_id,
        digest[:16],
    )
    if PurePosixPath(filename).name != filename:
        raise ProjectCostError(
            "PRIVATE_WORKBOOK_NAME",
            "runtime workbook filename is unsafe",
        )
    destination = runtime_json.parent / filename
    runtime_json.parent.mkdir(parents=True, exist_ok=True)
    if runtime_json.parent.is_symlink() or destination.is_symlink():
        raise ProjectCostError(
            "PRIVATE_WORKBOOK_DESTINATION",
            "runtime workbook destination is unsafe",
        )
    if destination.exists():
        if not destination.is_file() or _sha256(destination) != digest:
            raise ProjectCostError(
                "PRIVATE_WORKBOOK_COLLISION",
                "immutable runtime workbook path contains different bytes",
            )
    else:
        temporary = runtime_json.parent / (
            ".%s.tmp-%s" % (filename, os.getpid())
        )
        try:
            with source_path.open("rb") as reader, temporary.open("xb") as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
                writer.flush()
                os.fsync(writer.fileno())
            temporary.chmod(0o600)
            if _sha256(temporary) != digest:
                raise ProjectCostError(
                    "PRIVATE_WORKBOOK_COPY",
                    "runtime workbook copy failed its hash control",
                )
            os.replace(str(temporary), str(destination))
        finally:
            if temporary.exists():
                temporary.unlink()
    return {
        "filename": filename,
        "sha256": digest,
        "size_bytes": source_path.stat().st_size,
    }


def refresh(
    *,
    manifest_relpath: str,
    output_root: Path,
    runtime_json: Path,
) -> Dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    if output_root.is_symlink() or runtime_json.is_symlink():
        raise ProjectCostError(
            "PRIVATE_REFRESH_OUTPUT_UNSAFE",
            "production output paths must not be symbolic links",
        )
    with tempfile.TemporaryDirectory(prefix="kmfa-project-cost-inputs-") as temporary:
        staging = Path(temporary)
        manifest, manifest_sha256 = fetch_manifest(manifest_relpath, staging)
        run = manifest["run"]
        input_root = staging / "input"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output_dir = output_root / (
            "run_%s_%s" % (stamp, manifest_sha256[:10])
        )
        staging_dir = output_root / (
            ".pending_%s_%s" % (stamp, manifest_sha256[:10])
        )
        if output_dir.exists() or staging_dir.exists():
            raise ProjectCostError(
                "PRIVATE_REFRESH_OUTPUT_COLLISION",
                "production output path already exists",
            )
        try:
            result = calculate_and_generate(
                (input_root / run["data_root"],),
                year=run["year"],
                as_of=run["as_of"],
                output_dir=staging_dir,
                ocr_jsonl=input_root / run["ocr_path"],
                payroll_workbooks=tuple(
                    input_root / path for path in run["payroll_paths"]
                ),
                attendance_roots=tuple(
                    input_root / path for path in run["attendance_roots"]
                ),
                payroll_password_env="KMFA_PAYROLL_PASSWORD",
                private_input_manifest_sha256=manifest_sha256,
            )
            controls = _expectations(result, manifest["expected_controls"])
            verify_output(
                staging_dir,
                expected_private_input_manifest_sha256=manifest_sha256,
            )
            snapshot = json.loads(
                (staging_dir / "project_cost_snapshot.json").read_text(
                    encoding="utf-8"
                )
            )
            os.replace(str(staging_dir), str(output_dir))
        except Exception:
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
            raise
        result = dict(result)
        result.update(
            {
                "output_dir": str(output_dir),
                "workbook": str(
                    output_dir / Path(str(result["workbook"])).name
                ),
                "snapshot": str(output_dir / "project_cost_snapshot.json"),
                "summary_csv": str(output_dir / "project_cost_summary.csv"),
                "pdf_directory": str(output_dir / "项目单页PDF"),
            }
        )
        verification = verify_output(
            output_dir,
            expected_private_input_manifest_sha256=manifest_sha256,
        )
        sealed_workbook = _publish_sealed_workbook(
            Path(result["workbook"]),
            runtime_json,
            str(snapshot["snapshot_id"]),
        )
        projection = write_runtime_projection(
            runtime_json,
            snapshot,
            sealed_workbook,
        )
    return {
        "status": verification["status"],
        "operational_version": OPERATIONAL_VERSION,
        "private_manifest_sha256": manifest_sha256,
        "private_file_count": len(manifest["files"]),
        "private_total_bytes": manifest["total_bytes"],
        "output_dir": str(output_dir),
        "runtime_json": str(runtime_json),
        "runtime_schema_version": projection["schema_version"],
        "sealed_workbook_sha256": sealed_workbook["sha256"],
        "controls": controls,
        "verification": verification,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="免 clone 读取 Private-Database 的封印输入并刷新 KMFA 项目成本"
    )
    parser.add_argument(
        "--manifest-relpath",
        default="project_cost/operational_input_manifest_v1.json",
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--runtime-json", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = refresh(
            manifest_relpath=args.manifest_relpath,
            output_root=Path(args.output_root).expanduser().resolve(),
            runtime_json=Path(args.runtime_json).expanduser().resolve(),
        )
    except ProjectCostError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_code": exc.code,
                    "message": exc.message,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_code": "PRIVATE_REFRESH_UNEXPECTED",
                    "message": type(exc).__name__,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 3
    print(pretty_json(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
