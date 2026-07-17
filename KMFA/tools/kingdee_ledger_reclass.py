#!/usr/bin/env python3
"""KIS 明细账行分型细化（DATA.0009 收尾：彤烨父级滚存 / 曦悦块重复）。

- 彤烨：科目码为他码前缀（非叶子）的 detail 行 → row_kind='parent_rollup'
- 曦悦：业务键（科目/日期/凭证号/摘要/借/贷）第二次及以后出现 → row_kind='block_duplicate'
- 复验：两账套 叶子/去重后 detail 借=贷
KIS 账套权威视角=凭证（五账套 0 不平已证）；明细账视角供科目下钻。幂等（重跑 UPDATE 结果不变）。
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
        UPDATE _staging.kingdee_ledger SET row_kind='parent_rollup'
        WHERE book='彤烨' AND row_kind IN ('detail','parent_rollup')
          AND split_part(subject_sheet,'_',1) IN (
            SELECT DISTINCT c1 FROM (
              SELECT split_part(subject_sheet,'_',1) c1 FROM _staging.kingdee_ledger WHERE book='彤烨') a
            WHERE EXISTS (
              SELECT 1 FROM (SELECT DISTINCT split_part(subject_sheet,'_',1) c2
                             FROM _staging.kingdee_ledger WHERE book='彤烨') b
              WHERE b.c2 LIKE a.c1 || '.%'))""")
    con.execute("""
        UPDATE _staging.kingdee_ledger SET row_kind='detail'
        WHERE book='彤烨' AND row_kind='parent_rollup'
          AND split_part(subject_sheet,'_',1) NOT IN (
            SELECT DISTINCT c1 FROM (
              SELECT split_part(subject_sheet,'_',1) c1 FROM _staging.kingdee_ledger WHERE book='彤烨') a
            WHERE EXISTS (
              SELECT 1 FROM (SELECT DISTINCT split_part(subject_sheet,'_',1) c2
                             FROM _staging.kingdee_ledger WHERE book='彤烨') b
              WHERE b.c2 LIKE a.c1 || '.%'))""")
    con.execute("""
        UPDATE _staging.kingdee_ledger SET row_kind = CASE WHEN rn=1 THEN 'detail' ELSE 'block_duplicate' END
        FROM (SELECT rowid rid, row_number() OVER (
                 PARTITION BY subject_sheet, entry_date, coalesce(voucher_no,''), coalesce(summary_text,''),
                              coalesce(debit_cents,-1), coalesce(credit_cents,-1)
                 ORDER BY row_index) rn
              FROM _staging.kingdee_ledger WHERE book='曦悦' AND row_kind IN ('detail','block_duplicate')) t
        WHERE _staging.kingdee_ledger.rowid = t.rid AND book='曦悦'""")
    checks = []
    for book in ("彤烨", "曦悦"):
        d, c = con.execute("""SELECT coalesce(sum(debit_cents),0), coalesce(sum(credit_cents),0)
                              FROM _staging.kingdee_ledger WHERE book=? AND row_kind='detail'""", [book]).fetchone()
        kinds = dict(con.execute("SELECT row_kind, count(*) FROM _staging.kingdee_ledger WHERE book=? GROUP BY 1", [book]).fetchall())
        checks.append({"book": book, "detail_debit": d, "detail_credit": c, "delta": d - c, "row_kinds": kinds})
    con.close()
    out = {"task_id": "TSK.KMFA.DATA.0009", "phase": "kis_ledger_reclass", "checks": checks,
           "authority_note": "KIS 账套权威视角=凭证列表（0 不平已证）；明细账视角供科目下钻"}
    p = REPO / "KMFA/stage_artifacts/DT5_DATA0009_kis_reclass/machine/reclass_result.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
