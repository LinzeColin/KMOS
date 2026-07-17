#!/usr/bin/env python3
"""行级匹配引擎 v1（GOVX.0003 完整版第一件：回款台账行 ↔ 银行收款行）。

匹配规则（一对一贪心，银行行每行至多用一次）：
  P1 金额精确 + 同日
  P2 金额精确 + 日期窗 ±5 天（取最近）
输出：逐月匹配率、匹配行的银行类别分布（"报表回款落在哪些银行类别"的实证）、
未匹配两侧的聚合桶。明细进 `_staging.row_matches`（私有）；公开面零明细。
用法：python3 KMFA/tools/row_matcher.py
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"


def main() -> int:
    import duckdb
    con = duckdb.connect(str(DB_PATH))
    con.execute("""CREATE OR REPLACE VIEW _staging.v_collection_authoritative AS
        SELECT * FROM (SELECT *, row_number() OVER (
            PARTITION BY collection_date, customer_ref, contract_ref, collection_amount_cents,
                         coalesce(receipt_method,''), coalesce(row_seq,'')
            ORDER BY source_sha8, sheet_hash, row_index) rn FROM _staging.collection) WHERE rn=1
        AND source_sha8 IN ('d45324b4','5e5f46b6')""")
    ledger = con.execute("""
        SELECT source_sha8, sheet_hash, row_index, collection_date, collection_amount_cents
        FROM _staging.v_collection_authoritative
        WHERE collection_date >= DATE '2025-01-01' AND collection_date < DATE '2026-01-01'
          AND collection_amount_cents IS NOT NULL
        ORDER BY collection_date, row_index""").fetchall()
    bank = con.execute("""
        SELECT rowid, journal_date, receipt_amount_cents, flow_category
        FROM _staging.bank_journal
        WHERE receipt_amount_cents > 0 AND journal_date >= DATE '2025-01-01' AND journal_date < DATE '2026-01-01'
        ORDER BY journal_date""").fetchall()

    by_amount = defaultdict(list)
    for rid, jdate, cents, cat in bank:
        by_amount[cents].append([jdate, rid, cat, False])

    matches, p1 = [], 0
    for src, sheet, ridx, ldate, cents in ledger:
        cands = by_amount.get(cents, [])
        best = None
        for cand in cands:
            if cand[3]:
                continue
            dd = abs((cand[0] - ldate).days)
            if dd == 0:
                best = (0, cand)
                break
            if dd <= 5 and (best is None or dd < best[0]):
                best = (dd, cand)
        if best is not None:
            best[1][3] = True
            matches.append((src, sheet, ridx, str(ldate), cents, best[1][1], str(best[1][0]), best[1][2], best[0]))
            p1 += best[0] == 0

    con.execute("DROP TABLE IF EXISTS _staging.row_matches")
    con.execute("""CREATE TABLE _staging.row_matches (
        l_sha8 VARCHAR, l_sheet VARCHAR, l_row INTEGER, l_date DATE, amount_cents BIGINT,
        b_rowid BIGINT, b_date DATE, b_category VARCHAR, day_gap INTEGER)""")
    con.executemany("INSERT INTO _staging.row_matches VALUES (?,?,?,?,?,?,?,?,?)", matches)

    total_l = len(ledger)
    matched = len(matches)
    cat_dist = Counter(m[7] for m in matches)
    month_stats = defaultdict(lambda: [0, 0])
    for m in matches:
        month_stats[m[3][:7]][0] += 1
    for src, sheet, ridx, ldate, cents in ledger:
        month_stats[str(ldate)[:7]][1] += 1
    unmatched_bank = sum(1 for lst in by_amount.values() for c in lst if not c[3])
    con.close()

    out = {
        "task_id": "GOVX.0003-full/row-matcher-v1", "date": "2026-07-17", "scope": "collection↔bank 2025",
        "ledger_rows": total_l, "matched": matched, "match_rate": round(matched / total_l, 4),
        "matched_same_day": p1, "matched_window": matched - p1,
        "matched_bank_category_dist": dict(cat_dist.most_common()),
        "unmatched_ledger_rows": total_l - matched, "unmatched_bank_receipt_rows": unmatched_bank,
        "monthly_match_rate": {m: {"matched": v[0], "ledger": v[1], "rate": round(v[0]/v[1], 3) if v[1] else None}
                                for m, v in sorted(month_stats.items())},
    }
    p = REPO / "KMFA/stage_artifacts/DT5_GOVX0003_row_matcher_v1/machine/match_stats.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "monthly_match_rate"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
