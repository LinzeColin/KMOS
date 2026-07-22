#!/usr/bin/env python3
"""Prove the P2.4 validator fails closed for the four sealed mutations."""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

import yaml


VALIDATOR = Path(__file__).with_name("validate_taskpack.py").resolve()
SOURCE_FILES = (
    "machine/canonical_facts.yaml",
    "machine/acceptance_contract.yaml",
    "machine/task_graph.yaml",
    "machine/release_policy.yaml",
    "machine/traceability.csv",
)
FIXTURE_FILES = SOURCE_FILES + (
    "machine/VALIDATION_REPORT.md",
    "machine/tools/check_traceability.py",
    "machine/tools/render_human.py",
    "machine/tools/validate_taskpack.py",
    "machine/tools/test_validate_taskpack_mutations.py",
)


def sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_validator(candidate_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(candidate_root)],
        capture_output=True,
        text=True,
        check=False,
    )


def copy_projection(source_root: Path, candidate_root: Path) -> None:
    for relative in FIXTURE_FILES:
        source = source_root / relative
        target = candidate_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copytree(source_root / "文档", candidate_root / "文档")


def mutate_missing_acceptance(candidate_root: Path) -> None:
    acceptance_path = candidate_root / "machine" / "acceptance_contract.yaml"
    acceptance = yaml.safe_load(acceptance_path.read_text(encoding="utf-8"))
    acceptance["acceptance_contracts"].pop(0)
    acceptance_path.write_text(
        yaml.safe_dump(acceptance, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def mutate_cycle(candidate_root: Path) -> None:
    graph_path = candidate_root / "machine" / "task_graph.yaml"
    graph = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
    task_by_id = {task["id"]: task for task in graph["tasks"]}
    task_by_id["T-S00-01"]["dependencies"] = ["T-S00-02"]
    graph_path.write_text(
        yaml.safe_dump(graph, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def mutate_extra_governance_file(candidate_root: Path) -> None:
    (candidate_root / "文档" / "07_额外治理.md").write_text(
        "mutation fixture: validator must reject an eighth governance file\n",
        encoding="utf-8",
    )


def mutate_evidence_directory(candidate_root: Path) -> None:
    evidence_dir = candidate_root / "EVIDENCE"
    evidence_dir.mkdir()
    (evidence_dir / "README.md").write_text(
        "mutation fixture: per-stage evidence trees are forbidden\n",
        encoding="utf-8",
    )


MUTATIONS: tuple[tuple[str, Callable[[Path], None], str], ...] = (
    ("missing_acceptance", mutate_missing_acceptance, "acceptance_contracts: expected 49, got 48"),
    ("cycle", mutate_cycle, "Task graph contains a cycle"),
    ("extra_governance_file", mutate_extra_governance_file, "extra=['07_额外治理.md']"),
    ("evidence_directory", mutate_evidence_directory, "Forbidden directory: EVIDENCE"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    args = parser.parse_args()
    source_root = Path(args.root).resolve()

    source_hashes_before = {
        relative: sha256_file(source_root / relative) for relative in SOURCE_FILES
    }
    positive = run_validator(source_root)
    if positive.returncode != 0:
        print("POSITIVE_FAIL: repository projection did not validate")
        print(positive.stdout)
        print(positive.stderr)
        return 1
    print("POSITIVE_PASS case=authorized_repository_projection")

    for name, mutate, expected_message in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix=f"kmfa-p24-{name}-") as temp_dir:
            candidate_root = Path(temp_dir) / "KMFA"
            copy_projection(source_root, candidate_root)
            mutate(candidate_root)
            result = run_validator(candidate_root)
            output = result.stdout + result.stderr
            if result.returncode == 0 or expected_message not in output:
                print(
                    f"NEGATIVE_FAIL case={name} returncode={result.returncode} "
                    f"expected={expected_message!r}"
                )
                print(output)
                return 1
            print(f"NEGATIVE_PASS case={name} returncode={result.returncode}")

    source_hashes_after = {
        relative: sha256_file(source_root / relative) for relative in SOURCE_FILES
    }
    if source_hashes_before != source_hashes_after:
        print("SOURCE_MUTATION_FAIL: mutation suite changed an authorized machine source")
        return 1
    print(
        "MUTATION_SUITE_PASS positive=1 negative=4 "
        f"source_unchanged={len(source_hashes_after)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
