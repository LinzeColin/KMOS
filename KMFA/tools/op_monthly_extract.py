#!/usr/bin/env python3
"""经营分析·月度平表抽取（资金流/利润/支出三表）+ 三方对账初试（DATA.0007/0016 前哨）。

「财务数据」sheet 内三张月度平表 → `_staging.op_monthly`（长表：table_tag/月份/指标/分值或原文）。
对账初试：报表「财务应收回款」vs `_staging.collection` 月度合计 vs `_staging.bank_journal`
（收支类别=营业回款）月度合计 → 聚合差值证据（公开面零明细）。
幂等 sheet+版本；金额整数分。用法：python3 KMFA/tools/op_monthly_extract.py
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"
VERSION = "op-monthly-v1"
SHEET = "财务数据"
TABLE_HEADS = {"费用项目": "contract_pnl", "时间": None}  # 时间 开头的两张按首指标区分


def norm(v):
    return unicodedata.normalize("NFKC", str(v)).strip()


def to_cents(v):
    if v in (None, ""):
        return None
    try:
        dec = Decimal(str(v).replace(",", "").strip())
        cents = (dec * 100).quantize(Decimal("1"))
        return int(cents)
    except InvalidOperation:
        return None


def month_of(v):
    t = norm(v)
    m = re.match(r"(20\d{2})年?-?(\d{1,2})", t)
    return f"{m.group(1)}-{int(m.group(2)):02d}" if m else ("total" if "总计" in t or "合计" in t else None)


def main() -> int:
    import duckdb, openpyxl
    man = [json.loads(l) for l in (REPO / "KMDatabase/data/manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    src = [r for r in man if "经营分析数据支撑" in r["original_name"]][0]
    idem = hashlib.sha256(f"{src['sha256']}|{SHEET}|{VERSION}".encode()).hexdigest()
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS _staging")
    con.execute("""CREATE TABLE IF NOT EXISTS _staging.op_monthly (
        source_sha8 VARCHAR, table_tag VARCHAR, month VARCHAR, metric VARCHAR,
        value_cents BIGINT, value_raw VARCHAR)""")
    if not con.execute("SELECT 1 FROM _staging.extraction_manifest WHERE idempotency_key=?", [idem]).fetchone():
        wb = openpyxl.load_workbook(REPO / "KMDatabase/data" / src["object_path"], read_only=True, data_only=True)
        rows = [[v for v in r] for r in wb[SHEET].iter_rows(values_only=True)]
        wb.close()
        inserted, table_tag, headers = 0, None, []
        for row in rows:
            cells = [norm(v) if v not in (None, "") else "" for v in row]
            if not any(cells):
                table_tag = None
                continue
            first = cells[0]
            if first in ("费用项目", "时间"):
                headers = [c for c in cells if c]
                joined = "".join(headers)
                table_tag = ("contract_pnl" if first == "费用项目"
                             else "cash_flow" if "资金流" in joined
                             else "expense_compare" if "总支出" in joined else None)
                continue
            if table_tag and (month := month_of(first)):
                for i, metric in enumerate(headers[1:], 1):
                    v = row[i] if i < len(row) else None
                    if v in (None, ""):
                        continue
                    con.execute("INSERT INTO _staging.op_monthly VALUES (?,?,?,?,?,?)",
                                [src["sha256"][:8], table_tag, month, metric, to_cents(v), norm(v)])
                    inserted += 1
        con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [f"sha256:{src['sha256']}", f"KMDatabase/data/{src['object_path']}",
                     hashlib.sha256((SHEET + "-monthly").encode()).hexdigest()[:12], "_staging.op_monthly",
                     inserted, 3, 0, datetime.now(), VERSION, idem])

    recon = con.execute("""
        WITH report AS (
            SELECT month, value_cents AS report_cents FROM _staging.op_monthly
            WHERE table_tag='cash_flow' AND metric='财务应收回款' AND month LIKE '2025-%'),
        coll AS (
            SELECT strftime(collection_date, '%Y-%m') AS month, sum(collection_amount_cents) AS collection_cents
            FROM _staging.collection WHERE collection_date >= DATE '2025-01-01' GROUP BY 1),
        bank AS (
            SELECT strftime(journal_date, '%Y-%m') AS month, sum(receipt_amount_cents) AS bank_yyhk_cents
            FROM _staging.bank_journal WHERE flow_category='营业回款' GROUP BY 1)
        SELECT r.month, r.report_cents, c.collection_cents, b.bank_yyhk_cents,
               r.report_cents - coalesce(b.bank_yyhk_cents,0) AS report_vs_bank_delta
        FROM report r LEFT JOIN coll c USING(month) LEFT JOIN bank b USING(month)
        ORDER BY r.month""").fetchall()
    rows_total = con.execute("SELECT count(*) FROM _staging.op_monthly").fetchone()[0]
    con.close()
    lines = [{"month": m, "report_cents": rc, "collection_cents": cc, "bank_yyhk_cents": bc,
              "report_vs_bank_delta_cents": d} for m, rc, cc, bc, d in recon]
    exact = sum(1 for l in lines if l["report_vs_bank_delta_cents"] == 0)
    out = {"task_id": "TSK.KMFA.DATA.0007/0016", "phase": "op_monthly+recon_probe", "version": VERSION,
           "op_monthly_rows": rows_total, "recon_months": len(lines),
           "report_vs_bank_exact_months": exact, "monthly": lines}
    p = REPO / "KMFA/stage_artifacts/DT5_DATA0016_recon_probe/machine/recon_probe.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "monthly"}, ensure_ascii=False))
    for l in lines[:12]:
        print(l["month"], "报表:", l["report_cents"], "回款表:", l["collection_cents"], "银行营业回款:", l["bank_yyhk_cents"], "报表-银行差:", l["report_vs_bank_delta_cents"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
