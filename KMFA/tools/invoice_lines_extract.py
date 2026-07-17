#!/usr/bin/env python3
"""开票明细抽取（经营分析·客户分析 sheet 系，DATA.0007 收尾件）。

表头第 1 行：开票日期/发票单位/税率/含税合计/公司（透视列忽略）；
连续空行即止（sheet 维度虚标至百万行，实测数百行）。金额整数分；sheet 级幂等。
用法：python3 KMFA/tools/invoice_lines_extract.py
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"
VERSION = "invoice-lines-v1"
WANT = {"开票日期": "invoice_date", "发票单位": "counterparty", "税率": "tax_rate_raw",
        "含税合计": "amount_incl_tax_cents", "公司": "company_ref"}


def norm(v):
    return unicodedata.normalize("NFKC", str(v)).strip()


def to_cents(v):
    if v in (None, ""):
        return None
    try:
        dec = Decimal(str(v).replace(",", "").strip())
        cents = (dec * 100).quantize(Decimal("1"))
        return int(cents) if abs(dec * 100 - cents) < Decimal("0.5") else None
    except InvalidOperation:
        return None


def to_iso(v):
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    t = norm(v) if v not in (None, "") else ""
    p = t.replace("/", "-").split("-")
    if len(p) >= 3 and p[0][:4].isdigit():
        try:
            return date(int(p[0]), int(p[1]), int(p[2][:2])).isoformat()
        except ValueError:
            return None
    return None


def main() -> int:
    import duckdb, openpyxl
    man = [json.loads(l) for l in (REPO / "KMDatabase/data/manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    src = [r for r in man if "经营分析数据支撑" in r["original_name"]][0]
    con = duckdb.connect(str(DB_PATH))
    con.execute("""CREATE TABLE IF NOT EXISTS _staging.invoice_lines (
        source_sha8 VARCHAR, sheet VARCHAR, row_index INTEGER, invoice_date DATE,
        counterparty VARCHAR, tax_rate_raw VARCHAR, amount_incl_tax_cents BIGINT, company_ref VARCHAR)""")
    wb = openpyxl.load_workbook(REPO / "KMDatabase/data" / src["object_path"], read_only=True, data_only=True)
    report = []
    for sn in wb.sheetnames:
        if "客户分析" not in sn:
            continue
        idem = hashlib.sha256(f"{src['sha256']}|{sn}|{VERSION}".encode()).hexdigest()
        if con.execute("SELECT 1 FROM _staging.extraction_manifest WHERE idempotency_key=?", [idem]).fetchone():
            report.append({"sheet_hash": hashlib.sha256(sn.encode()).hexdigest()[:8], "status": "skip"})
            continue
        ws = wb[sn]
        rows_iter = ws.iter_rows(values_only=True)
        header = {norm(h): i for i, h in enumerate(next(rows_iter)) if h not in (None, "")}
        cols = {canon: header.get(zh) for zh, canon in WANT.items()}
        inserted, empty_streak = 0, 0
        for r_i, r in enumerate(rows_iter, 2):
            vals = {c: (r[i] if i is not None and i < len(r) else None) for c, i in cols.items()}
            if all(v in (None, "") for v in vals.values()):
                empty_streak += 1
                if empty_streak >= 5:
                    break
                continue
            empty_streak = 0
            amt = to_cents(vals["amount_incl_tax_cents"])
            if amt is None:
                continue
            con.execute("INSERT INTO _staging.invoice_lines VALUES (?,?,?,?,?,?,?,?)",
                        [src["sha256"][:8], sn, r_i, to_iso(vals["invoice_date"]),
                         norm(vals["counterparty"]) if vals["counterparty"] not in (None, "") else None,
                         norm(vals["tax_rate_raw"]) if vals["tax_rate_raw"] not in (None, "") else None,
                         amt, norm(vals["company_ref"]) if vals["company_ref"] not in (None, "") else None])
            inserted += 1
        con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [f"sha256:{src['sha256']}", f"KMDatabase/data/{src['object_path']}",
                     hashlib.sha256(sn.encode()).hexdigest()[:12], "_staging.invoice_lines",
                     inserted, len(WANT), 0, datetime.now(), VERSION, idem])
        report.append({"sheet_hash": hashlib.sha256(sn.encode()).hexdigest()[:8], "rows": inserted})
    wb.close()
    total, amt_sum = con.execute("SELECT count(*), coalesce(sum(amount_incl_tax_cents),0) FROM _staging.invoice_lines").fetchone()
    con.close()
    out = {"task_id": "TSK.KMFA.DATA.0007", "phase": "invoice_lines", "version": VERSION,
           "sheets": report, "table_total_rows": total, "amount_incl_tax_total_cents": amt_sum}
    p = REPO / "KMFA/stage_artifacts/DT5_DATA0007_invoice_lines/machine/extract_summary.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
