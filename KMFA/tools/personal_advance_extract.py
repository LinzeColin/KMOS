#!/usr/bin/env python3
"""个人借支挂账表抽取 → `_staging.personal_advance`（其他应收款·个人户切片）。

来源：报表系列一「个人借支」sheet（202510 册为真账：截止 2025-09 在职人员挂账快照；
202412 册为空模板，如实计数）。只取左侧行式块（账套/科目名称/员工/业务日期/凭证字号/摘要/挂账金额/备注/负责人）；
右侧「汇总表」透视块不入库（可由行块聚合复算，属展示层）。
金额元→整数分；幂等键=源指纹+sheet+版本。用法：python3 KMFA/tools/personal_advance_extract.py [--out <json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRIVATE = REPO / "KMFA" / ".codex_private_runtime"
DB_PATH = PRIVATE / "duckdb" / "kmfa_staging.duckdb"
INVENTORY = PRIVATE / "imports" / "excel_sheet_inventory" / "full_inventory.json"

VERSION = "personal-advance-v1"
SHEET_KEYWORD = "个人借支"

COLUMNS = {
    "账套": ("book_ref", "raw"),
    "科目名称": ("subject_name", "raw"),
    "员工": ("employee_ref", "raw"),
    "业务日期": ("biz_date", "date"),
    "凭证字号": ("voucher_no", "raw"),
    "摘要": ("summary_text", "raw"),
    "挂账金额": ("amount_cents", "cents"),
    "备注": ("note", "raw"),
    "负责人": ("owner_ref", "raw"),
}
SIGNATURE = ("book_ref", "employee_ref", "amount_cents")
FIELDS = ["book_ref", "subject_name", "employee_ref", "biz_date", "voucher_no",
          "summary_text", "amount_cents", "note", "owner_ref"]

DDL = """CREATE TABLE IF NOT EXISTS _staging.personal_advance (
    source_sha8 VARCHAR NOT NULL, sheet_hash VARCHAR NOT NULL, row_index INTEGER NOT NULL,
    book_ref VARCHAR, subject_name VARCHAR, employee_ref VARCHAR, biz_date DATE,
    voucher_no VARCHAR, summary_text VARCHAR, amount_cents BIGINT, note VARCHAR, owner_ref VARCHAR)"""


def norm(text) -> str:
    return unicodedata.normalize("NFKC", str(text)).strip().replace(" ", "").replace("\n", "")


NORM_COLUMNS = {norm(k): v for k, v in COLUMNS.items()}


class Money:
    def __init__(self) -> None:
        self.subcent = 0
        self.rejects = 0

    def to_cents(self, value) -> int | None:
        if value in (None, ""):
            return None
        try:
            dec = Decimal(str(value).replace(",", "").strip())
        except InvalidOperation:
            self.rejects += 1
            return None
        exact = dec * 100
        cents = exact.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if exact != cents:
            self.subcent += 1
        return int(cents)


def to_iso(value):
    if value in (None, ""):
        return None
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    text = norm(value)
    for sep in ("-", "/", "."):
        parts = text.split(sep)
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            y, m, d = (int(p) for p in parts)
            if y < 100:
                y += 2000
            try:
                return date(y, m, d).isoformat()
            except ValueError:
                return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    import duckdb
    import openpyxl

    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    manifest = {r["sha256"]: r for r in (json.loads(l) for l in
                (REPO / "KMDatabase/data/manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}

    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS _staging")
    con.execute(DDL)

    money = Money()
    sheets_loaded, rows_loaded, empty_templates = 0, 0, []
    for f in sorted(inventory, key=lambda x: x["sha256"]):
        hits = [s["name"] for s in f.get("sheets", []) if SHEET_KEYWORD in norm(s["name"])]
        if not hits:
            continue
        row = manifest[f["sha256"]]
        path = REPO / "KMDatabase/data" / row["object_path"]
        sha8 = f["sha256"][:8]
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            for sheet_name in hits:
                sheet_hash = hashlib.sha256(sheet_name.encode()).hexdigest()[:12]
                idem = hashlib.sha256(f"{f['sha256']}|{sheet_name}|{VERSION}".encode()).hexdigest()
                if con.execute("SELECT 1 FROM _staging.extraction_manifest WHERE idempotency_key=?", [idem]).fetchone():
                    continue
                raw_rows = [list(r) for r in wb[sheet_name].iter_rows(values_only=True)]
                header_idx, mapping = None, {}
                for idx, r in enumerate(raw_rows[:6]):
                    m = {}
                    for col, cell in enumerate(r):
                        if cell in (None, ""):
                            continue
                        hit = NORM_COLUMNS.get(norm(cell))
                        if hit and hit[0] not in {v[0] for v in m.values()}:
                            m[col] = hit
                    if all(any(v[0] == s for v in m.values()) for s in SIGNATURE):
                        header_idx, mapping = idx, m
                        break
                if header_idx is None:
                    empty_templates.append(f"{sha8}:{sheet_name}")
                    continue
                inserted = 0
                for r_i, data in enumerate(raw_rows[header_idx + 1:], header_idx + 2):
                    rec = dict.fromkeys(FIELDS)
                    for col, (canon, kind) in mapping.items():
                        v = data[col] if col < len(data) else None
                        if v in (None, ""):
                            continue
                        if kind == "cents":
                            rec[canon] = money.to_cents(v)
                        elif kind == "date":
                            rec[canon] = to_iso(v)
                        else:
                            rec[canon] = str(v).strip()
                    if not rec["book_ref"] or not rec["employee_ref"] or rec["amount_cents"] is None:
                        continue
                    con.execute(f"INSERT INTO _staging.personal_advance VALUES (?,?,?{',?' * len(FIELDS)})",
                                [sha8, sheet_hash, r_i, *[rec[k] for k in FIELDS]])
                    inserted += 1
                con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                            [f"sha256:{f['sha256']}", str(Path('KMDatabase/data') / row['object_path']), sheet_hash,
                             "_staging.personal_advance", inserted, len(mapping), 0, datetime.now(), VERSION, idem])
                sheets_loaded += 1
                rows_loaded += inserted
        finally:
            wb.close()

    total, = con.execute("SELECT count(*) FROM _staging.personal_advance").fetchone()
    con.close()
    summary = {
        "task_id": "TSK.KMFA.DATA.0007", "phase": "2_extract_personal_advance",
        "extractor_version": VERSION, "sheets_loaded": sheets_loaded,
        "rows_loaded_this_run": rows_loaded, "table_total_rows": total,
        "amount_parse_rejections": money.rejects, "subcent_roundings": money.subcent,
        "amounts_integer_cents": True, "empty_templates": empty_templates,
        "note": "右侧透视汇总块不入库（展示层，可由行块复算）",
    }
    out = REPO / (args.out or "KMFA/stage_artifacts/DT5_DATA0036_personal_advance/machine/extract_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
