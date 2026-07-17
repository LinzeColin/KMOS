#!/usr/bin/env python3
"""对账收敛批次工具（TSK.KMFA.DATA.0018 批次 #1）。

- 建 `_staging.v_collection_dedup`：业务键（日期/客户/合同/金额/方式/序号）去重视角
  ——化解「月度明细+累计 sheet 双份入库」（质量初评 844 组重复的根源）。
- 三方月度对账：报表财务应收回款 vs 去重回款合计 vs 银行营业回款，输出收敛报告
  （matched=三方或两方一致；差值全部整数分；公开面零明细）。
用法：python3 KMFA/tools/recon_batch.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"


def main() -> int:
    import duckdb
    con = duckdb.connect(str(DB_PATH))
    con.execute("""
        CREATE OR REPLACE VIEW _staging.v_collection_dedup AS
        SELECT * EXCLUDE rn FROM (
            SELECT *, row_number() OVER (
                PARTITION BY collection_date, customer_ref, contract_ref,
                             collection_amount_cents, coalesce(receipt_method,''), coalesce(row_seq,'')
                ORDER BY source_sha8, sheet_hash, row_index) AS rn
            FROM _staging.collection)
        WHERE rn = 1""")
    dedup_rows, orig_rows = con.execute(
        "SELECT (SELECT count(*) FROM _staging.v_collection_dedup), (SELECT count(*) FROM _staging.collection)").fetchone()

    # 源优先级（DATA.0005 落地一例）：快照型多文件源取「权威台账组合」——
    # d45324b4=主台账(2024~2026.01，其 2025-01 与报表/银行三方全等)；5e5f46b6=2026 年度接续。
    # ccbc2859/65da0afa 为变体台账，进差异分析（不混入权威视角）。
    con.execute("""
        CREATE OR REPLACE VIEW _staging.v_collection_authoritative AS
        SELECT * FROM _staging.v_collection_dedup
        WHERE source_sha8 IN ('d45324b4', '5e5f46b6')""")

    rows = con.execute("""
        WITH report AS (
            SELECT month, value_cents AS report_cents FROM _staging.op_monthly
            WHERE table_tag='cash_flow' AND metric='财务应收回款' AND month LIKE '2025-%'),
        coll AS (
            SELECT strftime(collection_date, '%Y-%m') AS month, sum(collection_amount_cents) AS coll_dedup_cents
            FROM _staging.v_collection_authoritative WHERE collection_date >= DATE '2025-01-01' GROUP BY 1),
        bank AS (
            SELECT strftime(journal_date, '%Y-%m') AS month, sum(receipt_amount_cents) AS bank_cents
            FROM _staging.bank_journal WHERE flow_category='营业回款' GROUP BY 1)
        SELECT r.month, r.report_cents, c.coll_dedup_cents, b.bank_cents
        FROM report r LEFT JOIN coll c USING(month) LEFT JOIN bank b USING(month) ORDER BY 1""").fetchall()
    con.close()

    monthly, matched = [], 0
    for m, rep, coll, bank in rows:
        d_rb = (rep - bank) if (rep is not None and bank is not None) else None
        d_rc = (rep - coll) if (rep is not None and coll is not None) else None
        status = "matched" if d_rb == 0 else ("two_way_gap" if d_rb is not None else "missing_side")
        matched += status == "matched"
        monthly.append({"month": m, "report_cents": rep, "collection_auth_cents": coll,
                        "bank_cents": bank, "report_vs_bank": d_rb, "report_vs_collection": d_rc,
                        "status": status})
    out = {"task_id": "TSK.KMFA.DATA.0018", "batch": 1,
           "collection_rows": orig_rows, "collection_dedup_rows": dedup_rows,
           "dedup_removed": orig_rows - dedup_rows,
           "months": len(monthly), "matched_report_vs_bank": matched, "monthly": monthly}
    p = REPO / "KMFA/stage_artifacts/DT5_DATA0018_recon_batch1/machine/recon_batch1.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "monthly"}, ensure_ascii=False))
    for l in monthly:
        print(l["month"], "报表-银行差:", l["report_vs_bank"], "报表-去重回款差:", l["report_vs_collection"], l["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
