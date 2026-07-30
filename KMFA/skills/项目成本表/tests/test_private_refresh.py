from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from project_cost_table.operational import ProjectCostError


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_private_refresh.py"
SPEC = importlib.util.spec_from_file_location("run_private_refresh", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _manifest() -> dict:
    private_root = "KMFA" + "_MetaData"
    return {
        "schema_version": "kmfa.project_cost.operational_private_inputs.v1",
        "operational_version": "0.0.5",
        "files": [
            {
                "repo_path": private_root + "/合成输入.xlsx",
                "local_path": "data/合成输入.xlsx",
                "sha256": "a" * 64,
                "size_bytes": 123,
                "role": "project_master",
            },
            {
                "repo_path": private_root + "/合成工资.xlsx",
                "local_path": "data/合成工资.xlsx",
                "sha256": "b" * 64,
                "size_bytes": 456,
                "role": "payroll",
            },
            {
                "repo_path": private_root + "/合成OCR.jsonl",
                "local_path": "ocr/dingtalk_ocr.jsonl",
                "sha256": "c" * 64,
                "size_bytes": 789,
                "role": "ocr",
            },
        ],
        "run": {
            "year": 2099,
            "as_of": "2099-02-05",
            "data_root": "data",
            "ocr_path": "ocr/dingtalk_ocr.jsonl",
            "payroll_paths": ["data/合成工资.xlsx"],
            "attendance_roots": ["data/dingtalk_attendance"],
        },
        "expected_controls": {
            "project_count": 2,
            "event_count": 3,
            "job_cost_total_cents": 100,
            "gl_recognized_cogs_total_cents": 0,
            "ledger_selected_book_count": 1,
            "qualified_accrual_event_count": 0,
            "labor_wage_component_event_count": 0,
            "p0_review_count": 0,
            "p1_review_count": 1,
            "p2_review_count": 2,
            "ledger_stale_entity_count": 0,
            "ledger_minimum_period_end": "2099-02",
            "ledger_maximum_period_end": "2099-02",
        },
    }


def test_private_manifest_is_bounded_and_hash_bound():
    result = MODULE.validate_manifest(_manifest())
    assert len(result["files"]) == 3
    assert result["total_bytes"] == 1368
    assert result["run"]["year"] == 2099


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repo_path", "../outside.xlsx"),
        ("local_path", "/absolute.xlsx"),
        ("local_path", "data\\windows.xlsx"),
    ],
)
def test_private_manifest_rejects_path_escape(field, value):
    manifest = _manifest()
    manifest["files"][0][field] = value
    with pytest.raises(ProjectCostError) as caught:
        MODULE.validate_manifest(manifest)
    assert caught.value.code == "PRIVATE_MANIFEST_PATH"


def test_private_control_drift_blocks_runtime_publish():
    expected = _manifest()["expected_controls"]
    result = {
        "project_count": 2,
        "event_count": 3,
        "job_cost_total_cents": 101,
        "gl_recognized_cogs_total_cents": 0,
        "p0_review_count": 0,
        "p1_review_count": 1,
        "p2_review_count": 2,
        "coverage": {
            "ledger_selected_book_count": 1,
            "qualified_accrual_event_count": 0,
            "labor_wage_component_event_count": 0,
            "ledger_stale_entity_count": 0,
            "ledger_minimum_period_end": "2099-02",
            "ledger_logical_period_end": "2099-02",
        },
    }
    with pytest.raises(ProjectCostError) as caught:
        MODULE._expectations(result, expected)
    assert caught.value.code == "PRIVATE_EXPECTED_CONTROL_DRIFT"


def test_control_drift_removes_staging_and_leaves_no_formal_run(
    tmp_path: Path,
    monkeypatch,
):
    manifest = _manifest()
    monkeypatch.setattr(
        MODULE,
        "fetch_manifest",
        lambda _relpath, _staging: (manifest, "d" * 64),
    )

    def fake_calculate(*_args, output_dir: Path, **_kwargs):
        output_dir.mkdir()
        workbook = output_dir / "synthetic.xlsx"
        workbook.write_bytes(b"not publishable")
        return {
            "project_count": 2,
            "event_count": 3,
            "job_cost_total_cents": 101,
            "gl_recognized_cogs_total_cents": 0,
            "p0_review_count": 0,
            "p1_review_count": 1,
            "p2_review_count": 2,
            "coverage": {},
            "workbook": str(workbook),
        }

    monkeypatch.setattr(MODULE, "calculate_and_generate", fake_calculate)
    output_root = tmp_path / "runs"
    runtime = tmp_path / "runtime" / "recent_completed.json"
    with pytest.raises(ProjectCostError) as caught:
        MODULE.refresh(
            manifest_relpath="project_cost/synthetic.json",
            output_root=output_root,
            runtime_json=runtime,
        )
    assert caught.value.code == "PRIVATE_EXPECTED_CONTROL_DRIFT"
    assert list(output_root.iterdir()) == []
    assert not runtime.exists()


def test_verified_workbook_is_published_immutably_before_runtime_pointer(
    tmp_path: Path,
):
    source = tmp_path / "run" / "verified.xlsx"
    source.parent.mkdir()
    source.write_bytes(b"synthetic sealed workbook")
    runtime = tmp_path / "runtime" / "recent_completed.json"
    binding = MODULE._publish_sealed_workbook(
        source,
        runtime,
        "kmfa-pc-2099-synthetic",
    )
    published = runtime.parent / binding["filename"]
    assert published.read_bytes() == source.read_bytes()
    assert published.stat().st_mode & 0o777 == 0o600
    assert binding["sha256"] == MODULE._sha256(source)

    source.write_bytes(b"a different verified workbook")
    second = MODULE._publish_sealed_workbook(
        source,
        runtime,
        "kmfa-pc-2099-synthetic",
    )
    assert second["filename"] != binding["filename"]
    assert (runtime.parent / binding["filename"]).read_bytes() == (
        b"synthetic sealed workbook"
    )
