#!/usr/bin/env python3
"""P2.3 focused gate for Acceptance/Task/Traceability closure.

This deliberately does not validate DAG cycles, forbidden paths, the full
taskpack tree, or CI wiring. Those are T-S02-04 responsibilities.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc


EXPECTED_COUNTS = {
    "requirements": 49,
    "acceptance_contracts": 49,
    "stages": 14,
    "tasks": 56,
    "trace_rows": 49,
}
REQUIRED_AC_FIELDS = (
    "id",
    "requirement_id",
    "title",
    "environment",
    "preconditions",
    "input",
    "procedure",
    "threshold",
    "evidence",
    "automation",
    "observation_window",
    "test_id",
    "artifact",
    "task_ids",
    "pass_gate",
)
TRACE_FIELDS = (
    "requirement_id",
    "area",
    "priority",
    "requirement",
    "acceptance_id",
    "oracle_threshold",
    "task_ids",
    "test_id",
    "evidence",
    "artifact",
    "owner",
)


def nonempty(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def duplicates(values: Iterable[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def load_documents(root: Path) -> dict[str, Any]:
    """Load the four P2.3 machine sources without changing them."""

    def load_yaml(relative: str) -> dict[str, Any]:
        path = root / relative
        with path.open("r", encoding="utf-8") as handle:
            value = yaml.safe_load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"{relative}: expected YAML mapping")
        return value

    trace_path = root / "machine" / "traceability.csv"
    with trace_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        trace_fields = tuple(reader.fieldnames or ())
        trace_rows = list(reader)

    return {
        "canonical": load_yaml("machine/canonical_facts.yaml"),
        "acceptance": load_yaml("machine/acceptance_contract.yaml"),
        "graph": load_yaml("machine/task_graph.yaml"),
        "trace_fields": trace_fields,
        "trace_rows": trace_rows,
    }


def validate_documents(documents: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    """Validate the exact P2.3 closure and return readable deterministic errors."""
    errors: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    facts = documents.get("canonical", {})
    ac_doc = documents.get("acceptance", {})
    graph = documents.get("graph", {})
    trace_fields = tuple(documents.get("trace_fields", ()))
    trace_rows = documents.get("trace_rows", [])

    for label, document in (
        ("canonical", facts),
        ("acceptance", ac_doc),
        ("task graph", graph),
    ):
        check(isinstance(document, dict), f"{label}: top level must be a mapping")
    if not all(isinstance(document, dict) for document in (facts, ac_doc, graph)):
        return errors, {"trace_gaps": len(errors), "ac_field_completeness": "0%"}

    requirements = facts.get("requirements", [])
    acceptances = ac_doc.get("acceptance_contracts", [])
    stages = graph.get("stages", [])
    tasks = graph.get("tasks", [])
    for label, rows in (
        ("requirements", requirements),
        ("acceptance_contracts", acceptances),
        ("stages", stages),
        ("tasks", tasks),
        ("trace_rows", trace_rows),
    ):
        check(isinstance(rows, list), f"{label}: expected list")
    if not all(isinstance(rows, list) for rows in (requirements, acceptances, stages, tasks, trace_rows)):
        return errors, {"trace_gaps": len(errors), "ac_field_completeness": "0%"}

    counts = {
        "requirements": len(requirements),
        "acceptance_contracts": len(acceptances),
        "stages": len(stages),
        "tasks": len(tasks),
        "trace_rows": len(trace_rows),
    }
    for label, expected in EXPECTED_COUNTS.items():
        check(counts[label] == expected, f"{label}: expected {expected}, got {counts[label]}")
    for label, document in (
        ("Canonical Facts", facts),
        ("Acceptance Contract", ac_doc),
        ("Task Graph", graph),
    ):
        check(str(document.get("taskpack_version")) == "1.5.2", f"{label}: taskpack_version must be 1.5.2")

    collections = {
        "requirement": requirements,
        "acceptance": acceptances,
        "stage": stages,
        "task": tasks,
    }
    ids: dict[str, list[str]] = {}
    for label, rows in collections.items():
        malformed = sum(not isinstance(row, dict) for row in rows)
        check(malformed == 0, f"{label}: {malformed} row(s) are not mappings")
        current = [row.get("id") for row in rows if isinstance(row, dict)]
        check(all(isinstance(value, str) and value for value in current), f"{label}: every ID must be a non-empty string")
        string_ids = [value for value in current if isinstance(value, str) and value]
        repeated = duplicates(string_ids)
        check(not repeated, f"{label}: duplicate IDs {repeated}")
        ids[label] = string_ids

    req_set = set(ids["requirement"])
    ac_set = set(ids["acceptance"])
    stage_set = set(ids["stage"])
    task_set = set(ids["task"])
    req_by_id = {row["id"]: row for row in requirements if isinstance(row, dict) and row.get("id")}
    task_by_id = {row["id"]: row for row in tasks if isinstance(row, dict) and row.get("id")}

    phase_to_stage: dict[str, str] = {}
    phase_memberships: Counter[str] = Counter()
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        sid = stage.get("id")
        phases = stage.get("phases", [])
        check(isinstance(phases, list), f"{sid}: phases must be a list")
        if not isinstance(phases, list):
            continue
        for phase in phases:
            if not isinstance(phase, dict):
                errors.append(f"{sid}: phase row must be a mapping")
                continue
            pid = phase.get("id")
            check(isinstance(pid, str) and bool(pid), f"{sid}: phase ID missing")
            if not isinstance(pid, str) or not pid:
                continue
            check(pid not in phase_to_stage, f"duplicate phase ID: {pid}")
            phase_to_stage[pid] = sid
            listed_tasks = phase.get("task_ids", [])
            check(isinstance(listed_tasks, list), f"{pid}: task_ids must be a list")
            if not isinstance(listed_tasks, list):
                continue
            for tid in listed_tasks:
                check(tid in task_set, f"{pid}: unknown task reference {tid}")
                if tid in task_set:
                    phase_memberships[tid] += 1

    for task in tasks:
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        sid = task.get("stage_id")
        pid = task.get("phase_id")
        check(sid in stage_set, f"{tid}: unknown stage {sid}")
        check(pid in phase_to_stage, f"{tid}: unknown phase {pid}")
        if pid in phase_to_stage:
            check(phase_to_stage[pid] == sid, f"{tid}: phase {pid} belongs to {phase_to_stage[pid]}, not {sid}")
        for field, valid_ids in (
            ("dependencies", task_set),
            ("requirement_ids", req_set),
            ("acceptance_ids", ac_set),
        ):
            refs = task.get(field, [])
            check(isinstance(refs, list), f"{tid}: {field} must be a list")
            if isinstance(refs, list):
                for reference in refs:
                    check(reference in valid_ids, f"{tid}: {field} has unknown reference {reference}")
        check(phase_memberships[tid] == 1, f"{tid}: expected one phase membership, got {phase_memberships[tid]}")

    req_ac_count: Counter[str] = Counter()
    ac_by_requirement: dict[str, dict[str, Any]] = {}
    test_ids: list[str] = []
    complete_ac_fields = 0
    ac_field_slots = len(acceptances) * len(REQUIRED_AC_FIELDS)
    for acceptance in acceptances:
        if not isinstance(acceptance, dict):
            continue
        aid = acceptance.get("id")
        for field in REQUIRED_AC_FIELDS:
            is_complete = field in acceptance and nonempty(acceptance.get(field))
            complete_ac_fields += int(is_complete)
            check(is_complete, f"{aid or '<unknown>'}: empty or missing acceptance field {field}")
        rid = acceptance.get("requirement_id")
        req_ac_count[rid] += 1
        check(rid in req_set, f"{aid}: unknown requirement {rid}")
        if rid in req_set and rid not in ac_by_requirement:
            ac_by_requirement[rid] = acceptance
        test_id = acceptance.get("test_id")
        if isinstance(test_id, str) and test_id:
            test_ids.append(test_id)
        task_refs = acceptance.get("task_ids", [])
        check(isinstance(task_refs, list) and bool(task_refs), f"{aid}: task_ids must be a non-empty list")
        if isinstance(task_refs, list):
            for tid in task_refs:
                check(tid in task_set, f"{aid}: unknown task reference {tid}")
                task = task_by_id.get(tid, {})
                check(rid in task.get("requirement_ids", []), f"{aid}: task {tid} lacks requirement back-reference {rid}")
                check(aid in task.get("acceptance_ids", []), f"{aid}: task {tid} lacks acceptance back-reference")

    repeated_tests = duplicates(test_ids)
    check(len(test_ids) == len(acceptances), "acceptance: every contract must have a test ID")
    check(not repeated_tests, f"acceptance: duplicate test IDs {repeated_tests}")
    for rid in ids["requirement"]:
        check(req_ac_count[rid] == 1, f"{rid}: expected exactly one primary acceptance, got {req_ac_count[rid]}")
        requirement = req_by_id.get(rid, {})
        primary_task = requirement.get("task")
        check(primary_task in task_set, f"{rid}: canonical primary task is unknown: {primary_task}")
        acceptance = ac_by_requirement.get(rid, {})
        check(primary_task in acceptance.get("task_ids", []), f"{rid}: primary task {primary_task} is not linked by its acceptance")

    check(trace_fields == TRACE_FIELDS, f"traceability.csv fields must be {list(TRACE_FIELDS)}, got {list(trace_fields)}")
    trace_req_ids = [row.get("requirement_id", "") for row in trace_rows if isinstance(row, dict)]
    check(len(trace_req_ids) == len(trace_rows), "traceability.csv: every row must be a mapping")
    check(set(trace_req_ids) == req_set, "traceability.csv: requirement coverage mismatch")
    repeated_trace = duplicates(trace_req_ids)
    check(not repeated_trace, f"traceability.csv: duplicate requirements {repeated_trace}")
    trace_by_requirement = {
        row.get("requirement_id"): row
        for row in trace_rows
        if isinstance(row, dict) and row.get("requirement_id")
    }
    for rid in ids["requirement"]:
        requirement = req_by_id.get(rid, {})
        acceptance = ac_by_requirement.get(rid, {})
        row = trace_by_requirement.get(rid)
        if row is None:
            errors.append(f"traceability.csv: missing row for {rid}")
            continue
        expected = {
            "requirement_id": rid,
            "area": requirement.get("area"),
            "priority": requirement.get("priority"),
            "requirement": requirement.get("statement"),
            "acceptance_id": acceptance.get("id"),
            "oracle_threshold": acceptance.get("threshold"),
            "task_ids": ";".join(acceptance.get("task_ids", [])),
            "test_id": acceptance.get("test_id"),
            "evidence": acceptance.get("evidence"),
            "artifact": acceptance.get("artifact"),
            "owner": requirement.get("owner"),
        }
        for field in TRACE_FIELDS:
            actual = row.get(field)
            check(nonempty(actual), f"traceability.csv {rid}: empty {field}")
            check(actual == expected[field], f"traceability.csv {rid}: {field} does not match its authority")

    completeness = (100.0 * complete_ac_fields / ac_field_slots) if ac_field_slots else 0.0
    counts.update(
        {
            "ac_field_slots": ac_field_slots,
            "ac_fields_complete": complete_ac_fields,
            "ac_field_completeness": f"{completeness:.2f}%",
            "trace_gaps": len(errors),
        }
    )
    return errors, counts


def load_and_validate(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load a repository projection and fail closed for renderer reuse."""
    documents = load_documents(root)
    errors, counts = validate_documents(documents)
    if errors:
        preview = "; ".join(errors[:5])
        raise ValueError(f"P2.3 traceability gate failed ({len(errors)}): {preview}")
    return documents, counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        documents = load_documents(root)
        errors, counts = validate_documents(documents)
    except Exception as exc:
        print(f"TRACEABILITY_FAIL errors=1: {exc}")
        return 1

    if errors:
        print(
            "TRACEABILITY_FAIL "
            f"errors={len(errors)} ac_field_completeness={counts.get('ac_field_completeness', '0%')}"
        )
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        "TRACEABILITY_PASS "
        f"requirements={counts['requirements']} acceptance_contracts={counts['acceptance_contracts']} "
        f"tasks={counts['tasks']} trace_rows={counts['trace_rows']} "
        f"ac_field_completeness={counts['ac_field_completeness']} trace_gaps=0"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
