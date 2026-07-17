#!/usr/bin/env python3
"""金蝶明细账流式抽取（TSK.KMFA.DATA.0009 阶段二）。

私有解包区五账套明细账 → `_staging.kingdee_ledger`（每科目一 sheet，一次遍历全部 sheet）。
行含 row_kind（detail/期初余额/本期合计/本年累计）；金额 Decimal→整数分。
幂等：文件级（成员 sha256+版本）。平衡初检：每账套 明细行 借方合计 vs 贷方合计。
公开面只出聚合。用法：python3 KMFA/tools/kingdee_extract.py
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRIV = REPO / "KMFA" / ".codex_private_runtime"
DB_PATH = PRIV / "duckdb" / "kmfa_staging.duckdb"
UNPACK = PRIV / "kingdee_unpack"
VERSION = "kingdee-v1"
HEADER_ROW = 3
EXPECT = {"科目": "subject", "日期": "entry_date", "凭证字号": "voucher_no", "摘要": "summary_text",
          "借方": "debit_cents", "贷方": "credit_cents", "方向": "direction", "余额": "balance_cents"}
MARKERS = ("期初余额", "本期合计", "本年累计")


def norm(v):
    return unicodedata.normalize("NFKC", str(v)).strip()


def to_cents(v):
    if v in (None, ""):
        return None
    try:
        dec = Decimal(str(v).replace(",", "").strip())
    except InvalidOperation:
        return None
    cents = (dec * 100).quantize(Decimal("1"))
    return int(cents) if (dec * 100) == cents else None


def to_iso(v):
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    t = norm(v) if v not in (None, "") else ""
    if len(t) >= 8 and t[:4].isdigit():
        for sep in ("-", "/", "."):
            p = t.split(sep)
            if len(p) >= 3 and all(x[:2].isdigit() for x in p[:3]):
                try:
                    return date(int(p[0]), int(p[1]), int(p[2][:2])).isoformat()
                except ValueError:
                    return None
    return None


def sheets(path):
    if path.suffix.lower() == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            for ws in wb.worksheets:
                yield ws.title, ([c for c in row] for row in ws.iter_rows(values_only=True))
        finally:
            wb.close()
    else:
        import xlrd
        wb = xlrd.open_workbook(str(path), on_demand=True)
        try:
            for name in wb.sheet_names():
                ws = wb.sheet_by_name(name)
                yield name, ([ws.cell_value(i, j) for j in range(ws.ncols)] for i in range(ws.nrows))
                wb.unload_sheet(name)
        finally:
            wb.release_resources()


def book_of(name: str) -> str:
    stem = name.split("公司")[0].split("-")[0].split("_")[0]
    for known in ("彤烨", "曦悦", "武汉开明", "湖北岚丹", "湖北开明"):
        if known in name:
            return known
    return stem[:6]


def main() -> int:
    import duckdb
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS _staging")
    con.execute("""CREATE TABLE IF NOT EXISTS _staging.kingdee_ledger (
        book VARCHAR NOT NULL, member_sha8 VARCHAR NOT NULL, subject_sheet VARCHAR NOT NULL,
        row_index INTEGER NOT NULL, row_kind VARCHAR NOT NULL, entry_date DATE,
        voucher_no VARCHAR, summary_text VARCHAR, debit_cents BIGINT, credit_cents BIGINT,
        direction VARCHAR, balance_cents BIGINT)""")

    ledgers = sorted(p for p in UNPACK.rglob("*") if p.is_file() and "明细账" in p.name)
    report = []
    for path in ledgers:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        idem = hashlib.sha256(f"{digest}|{VERSION}".encode()).hexdigest()
        if con.execute("SELECT 1 FROM _staging.extraction_manifest WHERE idempotency_key=?", [idem]).fetchone():
            report.append({"book": book_of(path.name), "status": "idempotent_skip"})
            continue
        book = book_of(path.name)
        sha8 = digest[:8]
        rows_ins, sheets_n, skipped_sheets = 0, 0, 0
        batch = []
        for sheet_name, row_iter in sheets(path):
            sheets_n += 1
            rows = list(row_iter)
            if len(rows) < HEADER_ROW:
                skipped_sheets += 1
                continue
            header = {norm(v): i for i, v in enumerate(rows[HEADER_ROW - 1]) if v not in (None, "")}
            cols = {canon: header.get(zh) for zh, canon in EXPECT.items()}
            if cols["debit_cents"] is None or cols["credit_cents"] is None:
                skipped_sheets += 1
                continue
            for r_i, r in enumerate(rows[HEADER_ROW:], HEADER_ROW + 1):
                def get(c):
                    i = cols.get(c)
                    return r[i] if i is not None and i < len(r) else None
                summary = norm(get("summary_text")) if get("summary_text") not in (None, "") else ""
                kind = next((m for m in MARKERS if m in summary), None) or ("detail" if to_iso(get("entry_date")) else None)
                if kind is None:
                    continue
                batch.append([book, sha8, sheet_name, r_i, kind, to_iso(get("entry_date")),
                              norm(get("voucher_no")) if get("voucher_no") not in (None, "") else None,
                              summary or None, to_cents(get("debit_cents")), to_cents(get("credit_cents")),
                              norm(get("direction")) if get("direction") not in (None, "") else None,
                              to_cents(get("balance_cents"))])
                rows_ins += 1
            if len(batch) >= 5000:
                con.executemany("INSERT INTO _staging.kingdee_ledger VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", batch)
                batch = []
        if batch:
            con.executemany("INSERT INTO _staging.kingdee_ledger VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [f"sha256:{digest}", f"private:kingdee_unpack/{path.name}", "-", "_staging.kingdee_ledger",
                     rows_ins, len(EXPECT), 0, datetime.now(), VERSION, idem])
        d, c = con.execute("SELECT coalesce(sum(debit_cents),0), coalesce(sum(credit_cents),0) FROM _staging.kingdee_ledger WHERE book=? AND member_sha8=? AND row_kind='detail'", [book, sha8]).fetchone()
        report.append({"book": book, "sheets": sheets_n, "sheets_skipped": skipped_sheets,
                       "rows": rows_ins, "detail_debit_cents": d, "detail_credit_cents": c,
                       "balance_delta_cents": d - c})
    total = con.execute("SELECT count(*) FROM _staging.kingdee_ledger").fetchone()[0]
    con.close()
    out = {"task_id": "TSK.KMFA.DATA.0009", "phase": "2_extract", "version": VERSION,
           "books": report, "table_total_rows": total}
    p = REPO / "KMFA/stage_artifacts/DT5_DATA0009_kingdee_extract/machine/extract_summary.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
