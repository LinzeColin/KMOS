#!/usr/bin/env python3
"""Validate the KMFA v1.5.2 taskpack repository projection.

The authorized ZIP's own validator remains the authority for the packaged
PDFs, safe reference ZIPs, release policy and manifest. This read-only adapter
checks the S02 machine sources and repository gates that will actually run in
KMOS CI. It never renders, rewrites or contacts an external service.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

from check_traceability import load_documents, nonempty, validate_documents


EXPECTED_HUMAN_FILES = {
    "00_我在哪.md",
    "01_产品需求.md",
    "02_系统架构.md",
    "03_口径字典.md",
    "04_操作流程.md",
    "05_执行与验收.md",
    "06_运维手册.md",
}
EXPECTED_SOURCE_HASHES = {
    "machine/canonical_facts.yaml": "5ae070cb4105e83eec0c05b3771759e550a67f1241708810f0b4430300198552",
    "machine/acceptance_contract.yaml": "1f07bd14a382a4bad552f43e7ba281064c06bae7ab52c5e0d75139c305c43bc1",
    "machine/task_graph.yaml": "a9753e7c76dea6041b7386fd31735db869a6e371bcbce57c2fc794256a4d1306",
    "machine/traceability.csv": "ca36962746546e66c729dd564f4a3d316e47270199d5a1bec988c86949ca0727",
}
REQUIRED_PATHS = (
    "machine/canonical_facts.yaml",
    "machine/acceptance_contract.yaml",
    "machine/task_graph.yaml",
    "machine/traceability.csv",
    "machine/VALIDATION_REPORT.md",
    "machine/tools/check_traceability.py",
    "machine/tools/render_human.py",
    "machine/tools/validate_taskpack.py",
    "machine/tools/test_validate_taskpack_mutations.py",
)
FORBIDDEN_DIR_NAMES = {"EVIDENCE", "SCHEMAS"}
FORBIDDEN_FILE_NAMES = {"state_ledger.py", "catalog_builder.py"}
GENERATED_PREFIX = "<!-- 本文件由 machine/tools/render_human.py 从机器平面生成。"
RECEIPT_LIMIT_BYTES = 64 * 1024
REQUIRED_STAGE_FIELDS = {
    "id",
    "title",
    "objective",
    "deliverable",
    "gate",
    "phases",
}
REQUIRED_TASK_FIELDS = {
    "id",
    "stage_id",
    "phase_id",
    "phase",
    "title",
    "purpose",
    "inputs",
    "outputs",
    "dependencies",
    "requirement_ids",
    "acceptance_ids",
    "test",
    "evidence",
    "risk",
    "rollback",
    "stop_condition",
    "pass_gate",
    "estimate_engineer_days",
    "owner",
    "parallel_group",
}
TASK_FIELDS_ALLOWED_EMPTY = {
    "dependencies",
    "requirement_ids",
    "acceptance_ids",
    "parallel_group",
}


def sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    for relative in REQUIRED_PATHS:
        check((root / relative).is_file(), f"Missing required file: {relative}")

    human_dir = root / "文档"
    actual_human = {entry.name for entry in human_dir.iterdir() if entry.is_file()} if human_dir.is_dir() else set()
    missing_human = sorted(EXPECTED_HUMAN_FILES - actual_human)
    extra_human = sorted(actual_human - EXPECTED_HUMAN_FILES)
    check(
        actual_human == EXPECTED_HUMAN_FILES,
        f"Human plane must contain exactly seven canonical files; missing={missing_human}, extra={extra_human}",
    )
    for name in sorted(EXPECTED_HUMAN_FILES):
        document = human_dir / name
        if document.is_file():
            try:
                check(
                    document.read_text(encoding="utf-8").startswith(GENERATED_PREFIX),
                    f"Human file is not generated: 文档/{name}",
                )
            except UnicodeDecodeError as exc:
                errors.append(f"Human file is not UTF-8: 文档/{name}: {exc}")

    for candidate in root.rglob("*"):
        relative = candidate.relative_to(root)
        if candidate.is_dir() and candidate.name in FORBIDDEN_DIR_NAMES:
            errors.append(f"Forbidden directory: {relative}")
        if candidate.is_file() and candidate.name in FORBIDDEN_FILE_NAMES:
            errors.append(f"Forbidden file: {relative}")

    oversized_receipts = []
    runs_dir = root / "machine" / "runs"
    if runs_dir.is_dir():
        oversized_receipts = sorted(
            str(receipt.relative_to(root))
            for receipt in runs_dir.iterdir()
            if receipt.is_file() and receipt.stat().st_size >= RECEIPT_LIMIT_BYTES
        )
    check(not oversized_receipts, f"Compact receipt limit exceeded: {oversized_receipts}")
    report_path = root / "machine" / "VALIDATION_REPORT.md"
    if report_path.is_file():
        check(
            report_path.stat().st_size < RECEIPT_LIMIT_BYTES,
            f"Validation report must stay compact (<64KiB): {report_path.stat().st_size} bytes",
        )

    for relative, expected in EXPECTED_SOURCE_HASHES.items():
        source = root / relative
        if source.is_file():
            actual = sha256_file(source)
            check(actual == expected, f"Sealed source SHA-256 mismatch: {relative}: expected {expected}, got {actual}")

    try:
        documents = load_documents(root)
    except Exception as exc:
        errors.append(f"P2.3 machine source load failure: {exc}")
        return errors, warnings, {
            "requirements": 0,
            "acceptance_contracts": 0,
            "stages": 0,
            "phases": 0,
            "tasks": 0,
            "trace_rows": 0,
        }

    trace_errors, trace_counts = validate_documents(documents)
    errors.extend(f"Traceability: {message}" for message in trace_errors)

    graph = documents["graph"]
    stages = graph.get("stages", [])
    tasks = graph.get("tasks", [])
    graph_policy = graph.get("graph_policy", {})
    check(isinstance(graph_policy, dict), "Task graph graph_policy must be a mapping")
    if isinstance(graph_policy, dict):
        check(graph_policy.get("acyclic") is True, "Task graph policy must require acyclic=true")
        check(
            graph_policy.get("one_primary_acceptance_per_requirement") is True,
            "Task graph policy must require one primary acceptance per requirement",
        )

    stage_ids: list[str] = []
    phase_ids: list[str] = []
    phase_memberships: Counter[str] = Counter()
    for stage in stages if isinstance(stages, list) else []:
        if not isinstance(stage, dict):
            continue
        sid = stage.get("id")
        stage_ids.append(sid)
        missing = sorted(REQUIRED_STAGE_FIELDS - set(stage))
        check(not missing, f"{sid or '<unknown>'}: missing Stage fields {missing}")
        for field in REQUIRED_STAGE_FIELDS:
            check(field in stage and nonempty(stage.get(field)), f"{sid or '<unknown>'}: empty Stage field {field}")
        phases = stage.get("phases", [])
        check(isinstance(phases, list), f"{sid}: phases must be a list")
        if not isinstance(phases, list):
            continue
        check(len(phases) == 4, f"{sid}: expected exactly 4 direct Phases, got {len(phases)}")
        for phase in phases:
            if not isinstance(phase, dict):
                errors.append(f"{sid}: Phase row must be a mapping")
                continue
            pid = phase.get("id")
            phase_ids.append(pid)
            check(isinstance(pid, str) and bool(pid), f"{sid}: Phase ID missing")
            check(nonempty(phase.get("title")), f"{pid or '<unknown>'}: Phase title missing")
            listed_tasks = phase.get("task_ids", [])
            check(isinstance(listed_tasks, list), f"{pid or '<unknown>'}: task_ids must be a list")
            if isinstance(listed_tasks, list):
                check(len(listed_tasks) == 1, f"{pid or '<unknown>'}: expected exactly 1 direct Task, got {len(listed_tasks)}")
                phase_memberships.update(listed_tasks)

    duplicate_stages = sorted(key for key, count in Counter(stage_ids).items() if count > 1)
    duplicate_phases = sorted(key for key, count in Counter(phase_ids).items() if count > 1)
    check(not duplicate_stages, f"Duplicate Stage IDs: {duplicate_stages}")
    check(not duplicate_phases, f"Duplicate Phase IDs: {duplicate_phases}")

    task_ids = [task.get("id") for task in tasks if isinstance(task, dict)] if isinstance(tasks, list) else []
    task_set = {task_id for task_id in task_ids if isinstance(task_id, str) and task_id}
    for task in tasks if isinstance(tasks, list) else []:
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        missing = sorted(REQUIRED_TASK_FIELDS - set(task))
        check(not missing, f"{tid or '<unknown>'}: missing Task fields {missing}")
        for field in REQUIRED_TASK_FIELDS - TASK_FIELDS_ALLOWED_EMPTY:
            check(field in task and nonempty(task.get(field)), f"{tid or '<unknown>'}: empty Task field {field}")
        dependencies = task.get("dependencies", [])
        if isinstance(dependencies, list):
            check(tid not in dependencies, f"{tid}: self dependency")
        check(phase_memberships[tid] == 1, f"{tid}: expected one Phase membership, got {phase_memberships[tid]}")

    if len(task_ids) == len(task_set) and all(isinstance(task_id, str) and task_id for task_id in task_ids):
        indegree = {task_id: 0 for task_id in task_ids}
        outgoing: dict[str, list[str]] = defaultdict(list)
        for task in tasks:
            tid = task["id"]
            for dependency in task.get("dependencies", []):
                if dependency in task_set:
                    indegree[tid] += 1
                    outgoing[dependency].append(tid)
        queue = deque(sorted(task_id for task_id, degree in indegree.items() if degree == 0))
        visited: list[str] = []
        while queue:
            task_id = queue.popleft()
            visited.append(task_id)
            for successor in outgoing[task_id]:
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    queue.append(successor)
        check(
            len(visited) == len(task_ids),
            f"Task graph contains a cycle; topological sort visited {len(visited)}/{len(task_ids)} Tasks",
        )

    counts = {
        "requirements": trace_counts.get("requirements", 0),
        "acceptance_contracts": trace_counts.get("acceptance_contracts", 0),
        "stages": len(stages) if isinstance(stages, list) else 0,
        "phases": len(phase_ids),
        "tasks": len(tasks) if isinstance(tasks, list) else 0,
        "trace_rows": trace_counts.get("trace_rows", 0),
        "receipts": len([entry for entry in runs_dir.iterdir() if entry.is_file()]) if runs_dir.is_dir() else 0,
    }
    return errors, warnings, counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        errors, warnings, counts = validate(root)
    except Exception as exc:
        print(f"Taskpack repository projection: {root}")
        print(f"ERROR: validator execution failed: {type(exc).__name__}: {exc}")
        print("RESULT: FAIL (1 error(s), 0 warning(s))")
        return 1
    print(f"Taskpack repository projection: {root}")
    print("Counts: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"RESULT: FAIL ({len(errors)} error(s), {len(warnings)} warning(s))")
        return 1
    print(f"RESULT: PASS (0 errors, {len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
