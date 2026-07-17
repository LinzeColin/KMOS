#!/usr/bin/env python3
"""金蝶 KIS 老版 .xls 抽取（TSK.KMFA.DATA.0009 v2：彤烨/曦悦）。

- 明细分类账（单 sheet）：科目代码/名称前向填充；日期为 Excel 序列数（xldate 转换）；
  行分型同 v1（年初余额/本期合计/本年累计/明细）→ `_staging.kingdee_ledger`
- 会计分录序时簿：日期/会计期间/凭证字号前向填充 → `_staging.kingdee_voucher`
金额整数分；文件级幂等；凭证级借=贷校验。用法：python3 KMFA/tools/kingdee_xls_extract.py
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRIV = REPO / "KMFA" / ".codex_private_runtime"
DB_PATH = PRIV / "duckdb" / "kmfa_staging.duckdb"
UNPACK = PRIV / "kingdee_unpack"
VERSION = "kingdee-xls-v2"
MARKERS = ("年初余额", "期初余额", "本期合计", "本年累计")


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


def book_of(name):
    return "彤烨" if "彤烨" in name else ("曦悦" if ("曦悦" in name or "曦月" in name) else name[:4])


def main() -> int:
    import duckdb, xlrd
    con = duckdb.connect(str(DB_PATH))
    reports = []
    for path in sorted(p for p in UNPACK.rglob("*.xls") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        idem = hashlib.sha256(f"{digest}|{VERSION}".encode()).hexdigest()
        if con.execute("SELECT 1 FROM _staging.extraction_manifest WHERE idempotency_key=?", [idem]).fetchone():
            reports.append({"file": book_of(path.name), "status": "idempotent_skip"})
            continue
        book, sha8 = book_of(path.name), digest[:8]
        wb = xlrd.open_workbook(str(path), on_demand=True)
        ws = wb.sheet_by_index(0)
        header = {norm(ws.cell_value(0, j)): j for j in range(ws.ncols) if ws.cell_value(0, j) not in (None, "")}

        def date_of(v):
            if v in (None, ""):
                return None
            if isinstance(v, float) and v > 20000:
                return xlrd.xldate_as_datetime(v, wb.datemode).strftime("%Y-%m-%d")
            t = norm(v).replace("/", "-").split("-")
            return f"{int(t[0]):04d}-{int(t[1]):02d}-{int(t[2][:2]):02d}" if len(t) >= 3 and t[0][:4].isdigit() else None

        inserted, kind_note = 0, ""
        if "明细分类账" in ws.name or "明细账" in path.name:
            kind_note = "ledger"
            need = {"科目代码", "科目名称", "日期", "摘要", "借方", "贷方"}
            if not need <= set(header):
                need = {"科目代码", "科目名称", "日期", "摘要"}  # 宽容：借贷列名探测
            g = lambda r, k: ws.cell_value(r, header[k]) if k in header and header[k] < ws.ncols else None
            debit_col = next((k for k in header if k in ("借方", "借方金额")), None)
            credit_col = next((k for k in header if k in ("贷方", "贷方金额")), None)
            bal_col = next((k for k in header if k in ("余额", "方向余额")), None)
            subj_code = subj_name = None
            batch = []
            for r in range(1, ws.nrows):
                code, name_ = norm(g(r, "科目代码") or ""), norm(g(r, "科目名称") or "")
                if code:
                    subj_code = code
                if name_:
                    subj_name = name_
                summary = norm(g(r, "摘要") or "")
                d = date_of(g(r, "日期"))
                kind = next((m for m in MARKERS if m in summary), None) or ("detail" if d else None)
                if kind is None:
                    continue
                batch.append([book, sha8, f"{subj_code or ''}_{(subj_name or '')[:20]}", r + 1, kind, d,
                              norm(g(r, "凭证字号") or "") or None, summary or None,
                              to_cents(g(r, debit_col)) if debit_col else None,
                              to_cents(g(r, credit_col)) if credit_col else None,
                              None, to_cents(g(r, bal_col)) if bal_col else None])
                inserted += 1
            con.executemany("INSERT INTO _staging.kingdee_ledger VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", batch)
            con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                        [f"sha256:{digest}", f"private:kingdee_unpack/{path.name}", "-", "_staging.kingdee_ledger",
                         inserted, len(header), 0, datetime.now(), VERSION, idem])
        else:
            kind_note = "voucher"
            g = lambda r, k: ws.cell_value(r, header[k]) if k in header and header[k] < ws.ncols else None
            cur_date = cur_vno = None
            batch = []
            for r in range(1, ws.nrows):
                d = date_of(g(r, "日期"))
                vno = norm(g(r, "凭证字号") or "")
                if d:
                    cur_date = d
                if vno:
                    cur_vno = vno
                subj = " ".join(x for x in (norm(g(r, "科目代码") or ""), norm(g(r, "科目名称") or "")) if x)
                debit, credit = to_cents(g(r, "借方")), to_cents(g(r, "贷方"))
                if not subj and debit is None and credit is None:
                    continue
                batch.append([book, sha8, r + 1, cur_date, cur_vno,
                              norm(g(r, "摘要") or "") or None, subj or None,
                              debit, credit, None, norm(g(r, "制单") or "") or None])
                inserted += 1
            con.executemany("INSERT INTO _staging.kingdee_voucher VALUES (?,?,?,?,?,?,?,?,?,?,?)", batch)
            con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                        [f"sha256:{digest}", f"private:kingdee_unpack/{path.name}", "-", "_staging.kingdee_voucher",
                         inserted, len(header), 0, datetime.now(), VERSION, idem])
        wb.release_resources()
        reports.append({"file": path.name[:24], "book": book, "kind": kind_note, "rows": inserted})
    # 平衡核验（v2 两账套）
    checks = []
    for book in ("彤烨", "曦悦"):
        row = con.execute("""SELECT coalesce(sum(CASE WHEN row_kind='detail' THEN debit_cents END),0),
                                    coalesce(sum(CASE WHEN row_kind='detail' THEN credit_cents END),0)
                             FROM _staging.kingdee_ledger WHERE book=?""", [book]).fetchone()
        vch = con.execute("""SELECT coalesce(sum(debit_cents),0), coalesce(sum(credit_cents),0),
                                    count(DISTINCT voucher_no) FROM _staging.kingdee_voucher WHERE book=?""", [book]).fetchone()
        unb = con.execute("""SELECT count(*) FROM (SELECT voucher_date, voucher_no,
                                sum(coalesce(debit_cents,0)) d, sum(coalesce(credit_cents,0)) c
                             FROM _staging.kingdee_voucher WHERE book=? GROUP BY 1,2 HAVING d != c)""", [book]).fetchone()[0]
        checks.append({"book": book, "ledger_debit": row[0], "ledger_credit": row[1], "ledger_delta": row[0]-row[1],
                       "voucher_debit": vch[0], "voucher_credit": vch[1], "voucher_delta": vch[0]-vch[1],
                       "unbalanced_vouchers": unb})
    con.close()
    out = {"task_id": "TSK.KMFA.DATA.0009", "phase": "v2_xls", "version": VERSION,
           "files": reports, "balance_checks": checks}
    p = REPO / "KMFA/stage_artifacts/DT5_DATA0009_xls_v2/machine/xls_extract_summary.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
