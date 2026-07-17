#!/usr/bin/env python3
"""金蝶凭证列表抽取 + 凭证级借贷平衡（TSK.KMFA.DATA.0009 阶段三）。

凭证列表（单 sheet 平表，表头第 3 行：日期/凭证字号/摘要/科目/借方金额/贷方金额/…）
→ `_staging.kingdee_voucher`。红字负数原样保留（整数分）。
凭证级平衡：每(账套,月,凭证字号) 借合计=贷合计 校验——复式记账的凭证视角。
幂等文件级。用法：python3 KMFA/tools/kingdee_voucher_extract.py
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRIV = REPO / "KMFA" / ".codex_private_runtime"
DB_PATH = PRIV / "duckdb" / "kmfa_staging.duckdb"
UNPACK = PRIV / "kingdee_unpack"
VERSION = "kingdee-voucher-v1"
HEADER_ROW = 3


def norm(v):
    return unicodedata.normalize("NFKC", str(v)).strip()


def to_cents(v):
    if v in (None, ""):
        return None
    try:
        dec = Decimal(str(v).replace(",", "").strip())
        cents = (dec * 100).quantize(Decimal("1"))
        return int(cents) if (dec * 100) == cents else None
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


def book_of(name):
    for known in ("彤烨", "曦悦", "武汉开明", "湖北岚丹", "湖北开明"):
        if known in name:
            return known
    return name[:6]


def main() -> int:
    import duckdb, openpyxl
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS _staging")
    con.execute("""CREATE TABLE IF NOT EXISTS _staging.kingdee_voucher (
        book VARCHAR, member_sha8 VARCHAR, row_index INTEGER, voucher_date DATE,
        voucher_no VARCHAR, summary_text VARCHAR, subject VARCHAR,
        debit_cents BIGINT, credit_cents BIGINT, doc_no VARCHAR, preparer VARCHAR)""")
    reports = []
    for path in sorted(p for p in UNPACK.rglob("*") if p.is_file() and "凭证" in p.name and p.suffix.lower() == ".xlsx"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        idem = hashlib.sha256(f"{digest}|{VERSION}".encode()).hexdigest()
        if con.execute("SELECT 1 FROM _staging.extraction_manifest WHERE idempotency_key=?", [idem]).fetchone():
            reports.append({"book": book_of(path.name), "status": "idempotent_skip"})
            continue
        book, sha8, inserted = book_of(path.name), digest[:8], 0
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for ws in wb.worksheets:
            rows = ws.iter_rows(values_only=True)
            for _ in range(HEADER_ROW):
                header = next(rows, None)
            if header is None:
                continue
            idx = {norm(h): i for i, h in enumerate(header) if h not in (None, "")}
            need = {"日期", "凭证字号", "科目", "借方金额", "贷方金额"}
            if not need <= set(idx):
                continue
            batch = []
            for r_i, r in enumerate(rows, HEADER_ROW + 1):
                def g(k):
                    i = idx.get(k)
                    return r[i] if i is not None and i < len(r) else None
                vdate = to_iso(g("日期"))
                if vdate is None and g("凭证字号") in (None, ""):
                    continue
                batch.append([book, sha8, r_i, vdate,
                              norm(g("凭证字号")) if g("凭证字号") not in (None, "") else None,
                              norm(g("摘要")) if g("摘要") not in (None, "") else None,
                              norm(g("科目")) if g("科目") not in (None, "") else None,
                              to_cents(g("借方金额")), to_cents(g("贷方金额")),
                              norm(g("原单据编号")) if g("原单据编号") not in (None, "") else None,
                              norm(g("制单人")) if g("制单人") not in (None, "") else None])
                if len(batch) >= 5000:
                    con.executemany("INSERT INTO _staging.kingdee_voucher VALUES (?,?,?,?,?,?,?,?,?,?,?)", batch)
                    inserted += len(batch); batch = []
            if batch:
                con.executemany("INSERT INTO _staging.kingdee_voucher VALUES (?,?,?,?,?,?,?,?,?,?,?)", batch)
                inserted += len(batch)
        wb.close()
        con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [f"sha256:{digest}", f"private:kingdee_unpack/{path.name}", "-",
                     "_staging.kingdee_voucher", inserted, 8, 0, datetime.now(), VERSION, idem])
        unbalanced = con.execute("""
            SELECT count(*) FROM (
              SELECT strftime(voucher_date,'%Y-%m') m, voucher_no,
                     sum(coalesce(debit_cents,0)) d, sum(coalesce(credit_cents,0)) c
              FROM _staging.kingdee_voucher WHERE member_sha8=? AND voucher_no IS NOT NULL
              GROUP BY 1,2 HAVING d != c)""", [sha8]).fetchone()[0]
        vd, vc = con.execute("SELECT coalesce(sum(debit_cents),0), coalesce(sum(credit_cents),0) FROM _staging.kingdee_voucher WHERE member_sha8=?", [sha8]).fetchone()
        reports.append({"book": book, "rows": inserted, "unbalanced_vouchers": unbalanced,
                        "total_debit_cents": vd, "total_credit_cents": vc, "delta": vd - vc})
    total = con.execute("SELECT count(*) FROM _staging.kingdee_voucher").fetchone()[0]
    con.close()
    out = {"task_id": "TSK.KMFA.DATA.0009", "phase": "3_voucher", "version": VERSION,
           "books": reports, "table_total_rows": total}
    p = REPO / "KMFA/stage_artifacts/DT5_DATA0009_voucher_extract/machine/voucher_summary.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
