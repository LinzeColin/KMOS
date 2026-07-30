from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

import project_cost_table.operational as operational
from project_cost_table.operational import (
    ProjectCostError,
    _formal_cost_categories,
    _synthetic_ledger_book,
    _statement_buckets,
    _statement_rows,
    generate_outputs,
    labor_posted_reconciliation,
    ledger_book_metadata,
    parse_ledger_books,
    parse_ocr_paid_project_costs,
    qualify_cost_accruals,
    runtime_projection,
    sha256_bytes,
    stable_json,
    subject_source_binding,
    verify_output,
    write_runtime_projection,
)

SUBJECT_BINDING = subject_source_binding()
EMPTY_SOURCE_BINDING_DIGEST = sha256_bytes(stable_json([]))


def _snapshot() -> dict:
    return {
        "schema_version": "kmfa.project_cost.snapshot.v2",
        "snapshot_id": "kmfa-pc-2099-synthetic",
        "generated_at": "2099-02-05T00:00:00+00:00",
        "skill_version": "0.0.5",
        "core_version": "0.2.0",
        "year": 2099,
        "as_of": "2099-02-05",
        "currency": "CNY",
        "subject_binding": SUBJECT_BINDING,
        "private_input_manifest_sha256": "b" * 64,
        "input_manifest_binding": {
            "kind": "PRIVATE_MANIFEST_SHA256",
            "digest": "b" * 64,
        },
        "selected_source_binding_digest": EMPTY_SOURCE_BINDING_DIGEST,
        "sources": [],
        "project_count": 2,
        "projects": [
            {
                "canonical_contract_id": "KMX20990101-001",
                "contract_base": "KMX20990101-001",
                "project_name": "合成项目甲",
                "customer": "合成客户甲",
                "contractor": "合成企业甲",
                "contract_amount_cents": 100_000,
                "job_posted_actual_cents": 12_345,
                "cost_accrued_cents": 7_655,
                "job_cost_incurred_cents": 20_000,
                "gl_recognized_cogs_cents": 8_000,
                "business_reported_direct_cost_cents": 5_000,
                "payment_system_paid_observed_cents": None,
                "status_business_components_cents": {},
                "own_work_units": 2,
                "external_work_units": None,
                "job_cost_coverage": "FULL_SELECTED_GL_PERIOD;POSTING_PRESENT",
                "accrual_coverage": "QUALIFIED_ACCRUAL_PRESENT",
            },
            {
                "canonical_contract_id": "KMX20990102-002",
                "contract_base": "KMX20990102-002",
                "project_name": "合成项目乙",
                "customer": "合成客户乙",
                "contractor": "合成企业甲",
                "contract_amount_cents": 200_000,
                "job_posted_actual_cents": 0,
                "cost_accrued_cents": 0,
                "job_cost_incurred_cents": 0,
                "gl_recognized_cogs_cents": 0,
                "business_reported_direct_cost_cents": None,
                "payment_system_paid_observed_cents": None,
                "status_business_components_cents": {},
                "job_cost_coverage": "FULL_SELECTED_GL_PERIOD;NO_QUALIFIED_EVENT",
                "accrual_coverage": "NO_QUALIFIED_ACCRUAL_EVENT",
            },
        ],
        "events": [
            {
                "project": "KMX20990101-001",
                "plane": "JOB_POSTED_ACTUAL",
                "category": "材料",
                "amount_cents": 12_345,
            },
            {
                "project": "KMX20990101-001",
                "plane": "COST_ACCRUED",
                "category": "自有人工-工资应计",
                "amount_cents": 7_655,
            },
        ],
        "reviews": [],
        "coverage": {
            "labor_wage_component_control_cents": 0,
            "labor_allocated_accrual_cents": 0,
            "labor_unallocated_cents": 0,
            "ledger_selected_book_count": 2,
            "qualified_accrual_event_count": 1,
            "labor_wage_component_event_count": 1,
        },
        "diagnostics": {"labor": {"already_posted_cents": 0}},
        "formula_contract": {
            "JOB_COST_INCURRED": "JOB_POSTED_ACTUAL + COST_ACCRUED",
            "planes_not_combined": [
                "GL_RECOGNIZED_COGS",
                "BUSINESS_REPORTED_DIRECT_COST",
                "PAYMENT_SYSTEM_PAID_OBSERVED",
            ],
            "automatic_fixed_labor_rate": False,
            "labor_allocation": (
                "auditable wage component × approved payroll days; largest remainder"
            ),
            "labor_unallocated_preserved": True,
            "automatic_management_fee_percent": False,
            "historical_reference_in_calculate": False,
        },
    }


def test_runtime_projection_keeps_formal_cost_and_observation_planes_separate():
    projection = runtime_projection(_snapshot())
    assert projection["schema_version"] == "kmfa.project_cost.current.v3"
    assert projection["项目数"] == 2
    first, second = projection["项目"]
    assert first["项目过账实际"] == "123.45"
    assert first["项目应计"] == "76.55"
    assert first["项目已发生成本"] == "200.00"
    assert first["主营成本已结转"] == "80.00"
    assert first["毛利"] is None and first["毛利率"] is None
    assert second["项目已发生成本"] == "0.00"
    assert "固定人工单价" in projection["禁止"]
    assert "自动合同额2%管理费" in projection["禁止"]
    assert "参考报表回填" in projection["禁止"]
    assert projection["计算状态"] == "PASS"
    assert projection["待确认"]["P1开放复核数"] == 0


def test_statement_template_conserves_cents_and_leaves_policy_rows_blank():
    snapshot = _snapshot()
    categories = _formal_cost_categories(snapshot)["KMX20990101-001"]
    buckets = _statement_buckets(categories)
    rows = {
        label: (amount, note)
        for label, amount, note in _statement_rows(snapshot["projects"][0], buckets)
    }
    assert rows["（一）原材料"][0] == 12_345
    assert rows["1.管理人员工资"][0] == 7_655
    assert rows["合计支出"][0] == 20_000
    assert rows["三 1.1分摊的管理费用（合同的2%）"][0] is None
    assert "禁止" in rows["三 1.1分摊的管理费用（合同的2%）"][1]
    assert rows["（七）毛利"][0] is None
    assert "禁止" in rows["（七）毛利"][1]


def test_runtime_projection_rejects_a_one_cent_category_drift():
    snapshot = _snapshot()
    snapshot["events"][1]["amount_cents"] = 7_654
    with pytest.raises(ProjectCostError) as caught:
        runtime_projection(snapshot)
    assert caught.value.code == "RUNTIME_CATEGORY_CONSERVATION"


def test_runtime_projection_surfaces_open_p1_without_using_it_in_formulas():
    snapshot = _snapshot()
    snapshot["reviews"] = [
        {
            "severity": "P1",
            "type": "SYNTHETIC_IDENTITY_UNRESOLVED",
            "amount_cents": 999_999,
        },
        {
            "severity": "P2",
            "type": "SYNTHETIC_EXCLUDED",
            "amount_cents": 888_888,
        },
    ]
    projection = runtime_projection(snapshot)
    assert projection["计算状态"] == "PASS_WITH_OPEN_REVIEWS"
    assert projection["待确认"]["P1开放复核数"] == 1
    assert projection["待确认"]["P2已排除或提示数"] == 1
    assert projection["项目"][0]["项目已发生成本"] == "200.00"


def test_runtime_projection_blocks_any_p0_review():
    snapshot = _snapshot()
    snapshot["reviews"] = [
        {"severity": "P0", "type": "SYNTHETIC_FORMAL_SOURCE_UNAVAILABLE"}
    ]
    with pytest.raises(ProjectCostError) as caught:
        runtime_projection(snapshot)
    assert caught.value.code == "P0_REVIEW_OPEN"


def test_ledger_keeps_two_legal_identical_rows_in_one_source_view():
    payload = _synthetic_ledger_book(
        entity="合成企业甲",
        contract="KMX20990101-001",
        customer="合成客户甲",
        amount=Decimal("100.00"),
        account="5001001-生产成本_原材料",
        include_research_column=True,
        same_sheet_occurrences=2,
    )
    metadata = ledger_book_metadata("合成企业甲-明细账.xlsx", payload)
    projects = [
        {
            "canonical_contract_id": "KMX20990101-001",
            "contract_base": "KMX20990101-001",
            "year": 2099,
            "customer": "合成客户甲",
            "contractor": "合成企业甲",
            "created_date": "2099-01-01",
        }
    ]
    events, reviews, diagnostics = parse_ledger_books(
        [{"metadata": metadata, "payload": payload}],
        projects,
        2099,
        "2099-02-28",
        {},
    )
    actual = [
        event for event in events if event["plane"] == "JOB_POSTED_ACTUAL"
    ]
    assert len(actual) == 2
    assert sum(event["amount_cents"] for event in actual) == 20_000
    assert diagnostics["semantic_duplicate_rows"] == 0
    assert not [row for row in reviews if row["severity"] == "P0"]


def test_other_contract_review_is_not_multiplied_by_export_views():
    payloads = [
        _synthetic_ledger_book(
            entity="合成企业甲",
            contract="KMX20980101-999",
            customer="合成客户甲",
            amount=Decimal("100.00"),
            account="5001001-生产成本_原材料",
            include_research_column=include_research,
        )
        for include_research in (False, True)
    ]
    books = [
        {
            "metadata": ledger_book_metadata(
                "合成企业甲-明细账-%d.xlsx" % index,
                payload,
            ),
            "payload": payload,
        }
        for index, payload in enumerate(payloads, 1)
    ]
    projects = [
        {
            "canonical_contract_id": "KMX20990101-001",
            "contract_base": "KMX20990101-001",
            "year": 2099,
            "customer": "合成客户甲",
            "contractor": "合成企业甲",
            "created_date": "2099-01-01",
        }
    ]
    events, reviews, diagnostics = parse_ledger_books(
        books,
        projects,
        2099,
        "2099-02-28",
        {},
    )
    excluded = [
        row
        for row in reviews
        if row["type"] == "LEDGER_OTHER_CONTRACT_EXCLUDED"
    ]
    assert events == []
    assert len(excluded) == 1
    assert excluded[0]["amount_cents"] == 10_000
    assert diagnostics["semantic_duplicate_rows"] == 1


def test_accrual_is_not_deleted_by_unrelated_equal_amount_posting():
    posted = [
        {
            "event_id": "posted-material",
            "project": "KMX20990101-001",
            "plane": "JOB_POSTED_ACTUAL",
            "category": "材料",
            "amount_cents": 10_000,
            "posting_date": "2099-02-01",
        }
    ]
    paid = [
        {
            "event_id": "paid-labor",
            "project": "KMX20990101-001",
            "category": "劳务/人工",
            "amount_cents": 10_000,
            "posting_date": "2099-02-05",
        }
    ]
    accruals, reviews, diagnostics = qualify_cost_accruals(posted, [], paid)
    assert len(accruals) == 1
    assert accruals[0]["amount_cents"] == 10_000
    assert reviews == []
    assert diagnostics["posting_link_required_count"] == 0


def test_possible_partial_posting_requires_a_stable_link_before_accrual():
    posted = [
        {
            "event_id": "posted-material-part",
            "project": "KMX20990101-001",
            "plane": "JOB_POSTED_ACTUAL",
            "category": "材料",
            "amount_cents": 4_000,
            "posting_date": "2099-02-01",
        }
    ]
    paid = [
        {
            "event_id": "approved-material-total",
            "project": "KMX20990101-001",
            "category": "材料",
            "amount_cents": 10_000,
            "posting_date": "2099-02-05",
        }
    ]
    accruals, reviews, diagnostics = qualify_cost_accruals(
        posted,
        [],
        paid,
    )
    assert accruals == []
    assert reviews[0]["type"] == "ACCRUAL_POSTING_LINK_REQUIRED"
    assert reviews[0]["severity"] == "P1"
    assert diagnostics["posting_link_required_count"] == 1


def test_exact_same_day_amount_and_category_requires_stable_link():
    posted = [
        {
            "event_id": "posted-rental",
            "project": "KMX20990101-001",
            "plane": "JOB_POSTED_ACTUAL",
            "category": "设备租赁",
            "amount_cents": 386_500,
            "posting_date": "2099-02-05",
        }
    ]
    paid = [
        {
            "event_id": "paid-rental",
            "project": "KMX20990101-001",
            "category": "设备租赁",
            "amount_cents": 386_500,
            "posting_date": "2099-02-05",
        }
    ]
    accruals, reviews, diagnostics = qualify_cost_accruals(posted, [], paid)
    assert accruals == []
    assert reviews[0]["severity"] == "P1"
    assert reviews[0]["type"] == "ACCRUAL_POSTING_LINK_REQUIRED"
    assert reviews[0]["candidate_count"] == 1
    assert diagnostics["posting_link_required_count"] == 1


def test_dws_reaction_cannot_create_a_formal_accrual_without_authority():
    observed_reaction = [
        {
            "event_id": "dws-unverified",
            "project": "KMX20990101-001",
            "category": "材料",
            "amount_cents": 311_000,
            "posting_date": "2099-02-05",
            "approval_authority_verified": False,
        }
    ]
    accruals, reviews, diagnostics = qualify_cost_accruals(
        [],
        observed_reaction,
        [],
    )
    assert accruals == []
    assert reviews[0]["severity"] == "P1"
    assert reviews[0]["type"] == "DWS_APPROVER_AUTHORITY_UNVERIFIED_EXCLUDED"
    assert diagnostics["dws_reaction_formal_amount_use"] is False


def test_ledger_excludes_postings_after_as_of():
    payload = _synthetic_ledger_book(
        entity="合成企业甲",
        contract="KMX20990101-001",
        customer="合成客户甲",
        amount=Decimal("100.00"),
        account="5001001-生产成本_原材料",
        include_research_column=True,
    )
    metadata = ledger_book_metadata("合成企业甲-明细账.xlsx", payload)
    projects = [
        {
            "canonical_contract_id": "KMX20990101-001",
            "contract_base": "KMX20990101-001",
            "year": 2099,
            "customer": "合成客户甲",
            "contractor": "合成企业甲",
            "created_date": "2099-01-01",
        }
    ]
    events, reviews, _diagnostics = parse_ledger_books(
        [{"metadata": metadata, "payload": payload}],
        projects,
        2099,
        "2099-01-15",
        {},
    )
    assert events == []
    future = [
        row
        for row in reviews
        if row["type"] == "LEDGER_POSTING_AFTER_AS_OF_EXCLUDED"
    ]
    assert len(future) == 1
    assert future[0]["amount_cents"] == 10_000


def test_ocr_preserves_identical_legal_payments_on_distinct_pages(
    tmp_path: Path,
):
    text = "合成客户甲 合成项目甲 材料款\n2月5日\n项目成本\n100.00"
    path = tmp_path / "ocr.jsonl"
    path.write_text(
        "\n".join(
            json.dumps({"file": filename, "text": text}, ensure_ascii=False)
            for filename in ("page-1.png", "page-2.png", "page-1.png")
        )
        + "\n",
        encoding="utf-8",
    )
    projects = [
        {
            "canonical_contract_id": "KMX20990101-001",
            "contract_base": "KMX20990101-001",
            "project_name": "合成项目甲",
            "customer": "合成客户甲",
            "contractor": "合成企业甲",
            "created_date": "2099-01-01",
            "year": 2099,
        }
    ]
    events, reviews, _sources, _diagnostics = parse_ocr_paid_project_costs(
        path,
        (tmp_path,),
        projects,
        {},
        2099,
        "2099-02-28",
    )
    assert len(events) == 2
    assert sum(event["amount_cents"] for event in events) == 20_000
    duplicates = [
        row
        for row in reviews
        if row["type"]
        == "OCR_SAME_PHYSICAL_OCCURRENCE_DUPLICATE_EXCLUDED"
    ]
    assert len(duplicates) == 1


def test_one_cent_labor_posting_cannot_suppress_full_payroll_allocation():
    matched, residual = labor_posted_reconciliation(10_000, 1)
    assert matched == 1
    assert residual == 9_999
    assert matched + residual == 10_000


def test_runtime_projection_is_an_atomic_private_file(tmp_path: Path):
    destination = tmp_path / "runtime" / "recent_completed.json"
    binding = {
        "filename": "current_project_cost_synthetic_deadbeef.xlsx",
        "sha256": "a" * 64,
        "size_bytes": 123,
    }
    projection = write_runtime_projection(
        destination,
        _snapshot(),
        binding,
    )
    assert json.loads(destination.read_text(encoding="utf-8")) == projection
    assert projection["封印工作簿"]["SHA256"] == "a" * 64
    assert projection["封印工作簿"]["快照ID"] == _snapshot()["snapshot_id"]
    assert projection["封印来源"]["输入清单类型"] == "PRIVATE_MANIFEST_SHA256"
    assert projection["封印来源"]["输入清单SHA256"] == "b" * 64
    assert destination.stat().st_mode & 0o777 == 0o600
    assert not list(destination.parent.glob(".*.tmp-*"))


def test_verify_output_rejects_source_or_private_manifest_drift(
    tmp_path: Path,
    monkeypatch,
):
    derived_snapshot = _snapshot()
    derived_snapshot["private_input_manifest_sha256"] = None
    derived_snapshot["input_manifest_binding"] = {
        "kind": "SELECTED_SOURCE_DERIVED_SHA256",
        "digest": EMPTY_SOURCE_BINDING_DIGEST,
    }
    derived_output = tmp_path / "derived-sealed"
    generate_outputs(derived_output, derived_snapshot)
    derived_verification = verify_output(derived_output)
    assert derived_verification["input_manifest_binding"] == {
        "kind": "SELECTED_SOURCE_DERIVED_SHA256",
        "digest": EMPTY_SOURCE_BINDING_DIGEST,
    }
    derived_runtime = runtime_projection(derived_snapshot)
    assert derived_runtime["封印来源"]["输入清单SHA256"] == (
        EMPTY_SOURCE_BINDING_DIGEST
    )

    output = tmp_path / "sealed"
    generate_outputs(output, _snapshot())
    assert verify_output(
        output,
        expected_private_input_manifest_sha256="b" * 64,
    )["status"] == "PASS"

    with pytest.raises(ProjectCostError) as private_drift:
        verify_output(
            output,
            expected_private_input_manifest_sha256="d" * 64,
        )
    assert private_drift.value.code == "PRIVATE_MANIFEST_BINDING_MISMATCH"

    changed = dict(SUBJECT_BINDING)
    changed["digest"] = "e" * 64
    monkeypatch.setattr(operational, "subject_source_binding", lambda: changed)
    with pytest.raises(ProjectCostError) as source_drift:
        verify_output(output)
    assert source_drift.value.code == "SUBJECT_BINDING_MISMATCH"
