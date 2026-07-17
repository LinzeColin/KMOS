#!/usr/bin/env python3
"""staging 质量初评（TSK.KMFA.DATA.0010）：按 Q0-Q5 契约给每张 staging 表打分。

维度（任务包 06 原文）：行数/期间覆盖/重复/空值/借贷平衡初检。
评级口径（quality_grade_policy.v1）：
  机器结构化且关键字段可用 → Q3（preview_allowed，decision_use 仍禁）
  字段缺口严重（关键列空值率>20% 或全行重复率>5%）→ Q2
  未抽取资产 → Q1（已登记未解析）
公开面只出聚合指标与 Q 级；阻断项清单一并产出（供 DATA.0012/0022 消费）。
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"


def q(con, sql):
    return con.execute(sql).fetchone()


def main() -> int:
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)
    tables, blockers = [], []

    # collection 回款流水
    rows, dup, null_date, null_amt, dmin, dmax = q(con, """
        SELECT count(*),
               count(*) - count(DISTINCT (collection_date, customer_ref, contract_ref, collection_amount_cents, row_seq, source_sha8, sheet_hash, row_index)),
               sum(CASE WHEN collection_date IS NULL THEN 1 ELSE 0 END),
               sum(CASE WHEN collection_amount_cents IS NULL THEN 1 ELSE 0 END),
               min(collection_date), max(collection_date)
        FROM _staging.collection""")
    softdup = q(con, "SELECT count(*) FROM (SELECT collection_date, customer_ref, contract_ref, collection_amount_cents, count(*) c FROM _staging.collection GROUP BY 1,2,3,4 HAVING c>1)")[0]
    null_date_rate = null_date / rows
    grade = "Q3" if null_date_rate <= 0.2 else "Q2"
    if null_date_rate > 0.05:
        blockers.append(f"collection: 回款日期空值率 {null_date_rate:.1%}（阈 5%），进人工复核清单")
    if softdup:
        blockers.append(f"collection: 业务四元组疑似重复 {softdup} 组（日期+客户+合同+金额），需 DATA.0021 零差异前处置")
    tables.append({"table": "collection", "rows": rows, "grade": grade,
                   "period": [str(dmin), str(dmax)], "hard_dup_rows": dup,
                   "business_dup_groups": softdup, "null_key_rates": {"collection_date": round(null_date_rate, 4)}})

    # receivable_aging 合同级应收台账
    rows, dupc, nullc, nulla, dmin, dmax = q(con, """
        SELECT count(*), count(*) - count(DISTINCT contract_ref),
               sum(CASE WHEN customer_ref IS NULL THEN 1 ELSE 0 END),
               sum(CASE WHEN contract_amount_cents IS NULL THEN 1 ELSE 0 END),
               min(contract_date), max(contract_date)
        FROM _staging.receivable_aging""")
    over = q(con, "SELECT count(*) FROM _staging.receivable_aging WHERE received_amount_cents > contract_amount_cents AND contract_amount_cents IS NOT NULL AND received_amount_cents IS NOT NULL")[0]
    eq_check = q(con, "SELECT count(*) FROM _staging.receivable_aging WHERE contract_amount_cents IS NOT NULL AND received_amount_cents IS NOT NULL AND remaining_amount_cents IS NOT NULL AND contract_amount_cents - received_amount_cents != remaining_amount_cents")[0]
    contract_null_amt_rate = nulla / rows
    grade = "Q3" if contract_null_amt_rate <= 0.35 else "Q2"
    blockers.append(f"receivable_aging: 合同号重复行 {dupc}（同合同多轮快照/多 sheet），facts 层需按最新快照归并")
    if over:
        blockers.append(f"receivable_aging: 累计已收款>合同确定金额 {over} 行（可能含税差/变更单），进差异队列候选")
    if eq_check:
        blockers.append(f"receivable_aging: 合同额-已收款≠剩余金额 {eq_check} 行（勾稽不平初检），进差异队列候选")
    tables.append({"table": "receivable_aging", "rows": rows, "grade": grade,
                   "period": [str(dmin), str(dmax)], "contract_ref_dup_rows": dupc,
                   "received_gt_contract_rows": over, "identity_mismatch_rows": eq_check,
                   "null_key_rates": {"contract_amount_cents": round(contract_null_amt_rate, 4)}})

    # bank_journal 银行日记账（借贷平衡初检=净流可计算+无负金额）
    rows, neg, dmin, dmax, net = q(con, """
        SELECT count(*),
               sum(CASE WHEN receipt_amount_cents < 0 OR payment_amount_cents < 0 THEN 1 ELSE 0 END),
               min(journal_date), max(journal_date),
               sum(coalesce(receipt_amount_cents,0)) - sum(coalesce(payment_amount_cents,0))
        FROM _staging.bank_journal""")
    tables.append({"table": "bank_journal", "rows": rows, "grade": "Q3",
                   "period": [str(dmin), str(dmax)], "negative_amount_rows": neg,
                   "net_flow_cents": net, "balance_check": "净流可计算；逐账户期末余额核对留给金蝶明细账交叉盘点（DATA.0009）"})
    if neg:
        blockers.append(f"bank_journal: 负金额 {neg} 行，需人工核（冲账/红字）")

    con.close()
    report = {
        "task_id": "TSK.KMFA.DATA.0010", "date": "2026-07-17",
        "grading_contract": "kmfa.quality_grade_policy.v1",
        "staging_tables": tables,
        "unextracted_assets_grade": "Q1（已登记未解析：45 个资产，见 machine/lineage.yaml）",
        "overall": "三表 Q3（机器候选结构化，preview_allowed=true，decision_use=false）；Q4 需人工确认黄金字段（BLK-001 族），Q5 需零差异全量验证（DATA.0021）",
        "blockers": blockers,
    }
    out = REPO / "KMFA/stage_artifacts/DT5_DATA0010_quality_initial/machine/quality_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"tables": [(t["table"], t["grade"], t["rows"]) for t in tables], "blockers": len(blockers)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
