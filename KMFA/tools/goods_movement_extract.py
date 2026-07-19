#!/usr/bin/env python3
"""收发明细表（存货收发存流水）抽取 → `_staging.goods_movement`（材料/存货域首件）。

来源：报表系列一两册的「8收发明细表」（56 列宽表）。
落库列：物料四键（长代码/名称/规格/批次）+ 期间/日期/单据号/凭证字号 + 四个金额列
（期初结存/收入/发出/结存金额 → 整数分）+ 基本单位与收发数量（**原文字符串**——
数量与单价非货币，不做分制转换，不引入 `float`）。
两册期间重叠（202412 册含 2023-2024、202510 册含 2024-2025）：一律入库，
`source_sha8` 区分版次，查询期用「期间取新册」纪律（同回款权威视图先例）。
幂等键=源指纹+sheet+版本。用法：python3 KMFA/tools/goods_movement_extract.py [--out <json>]
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

VERSION = "goods-movement-v1"
SHEET_KEYWORD = "收发明细"

COLUMNS = {
    "年月": ("period_label", "raw"),
    "会计期间": ("fiscal_period", "raw"),
    "物料长代码": ("material_code", "raw"),
    "物料名称": ("material_name", "raw"),
    "规格型号": ("spec", "raw"),
    "日期": ("move_date", "date"),
    "单据号码": ("doc_no", "raw"),
    "凭证字号": ("voucher_no", "raw"),
    "批次": ("batch", "raw"),
    "期初结存单位(基本)": ("unit_base", "raw"),
    "期初结存金额": ("opening_amount_cents", "cents"),
    "收入数量(基本)": ("receipt_qty_raw", "raw"),
    "收入金额": ("receipt_amount_cents", "cents"),
    "发出数量(基本)": ("issue_qty_raw", "raw"),
    "发出金额": ("issue_amount_cents", "cents"),
    "结存金额": ("closing_amount_cents", "cents"),
    "备注": ("note", "raw"),
}
SIGNATURE = ("material_code", "fiscal_period", "voucher_no")
FIELDS = ["period_label", "fiscal_period", "material_code", "material_name", "spec",
          "move_date", "doc_no", "voucher_no", "batch", "unit_base",
          "opening_amount_cents", "receipt_qty_raw", "receipt_amount_cents",
          "issue_qty_raw", "issue_amount_cents", "closing_amount_cents", "note"]

DDL = """CREATE TABLE IF NOT EXISTS _staging.goods_movement (
    source_sha8 VARCHAR NOT NULL, sheet_hash VARCHAR NOT NULL, row_index INTEGER NOT NULL,
    period_label VARCHAR, fiscal_period VARCHAR, material_code VARCHAR, material_name VARCHAR,
    spec VARCHAR, move_date DATE, doc_no VARCHAR, voucher_no VARCHAR, batch VARCHAR,
    unit_base VARCHAR, opening_amount_cents BIGINT, receipt_qty_raw VARCHAR,
    receipt_amount_cents BIGINT, issue_qty_raw VARCHAR, issue_amount_cents BIGINT,
    closing_amount_cents BIGINT, note VARCHAR)"""


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
    sheets_loaded, rows_loaded = 0, 0
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
                ws = wb[sheet_name]
                it = ws.iter_rows(values_only=True)
                header = [norm(c) if c is not None else "" for c in next(it)]
                mapping = {}
                for col, cell in enumerate(header):
                    hit = NORM_COLUMNS.get(cell)
                    if hit and hit[0] not in {v[0] for v in mapping.values()}:
                        mapping[col] = hit
                if not all(any(v[0] == s for v in mapping.values()) for s in SIGNATURE):
                    continue
                inserted = 0
                for r_i, data in enumerate(it, 2):
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
                    if not rec["material_code"] or not rec["fiscal_period"]:
                        continue
                    con.execute(f"INSERT INTO _staging.goods_movement VALUES (?,?,?{',?' * len(FIELDS)})",
                                [sha8, sheet_hash, r_i, *[rec[k] for k in FIELDS]])
                    inserted += 1
                con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                            [f"sha256:{f['sha256']}", str(Path('KMDatabase/data') / row['object_path']), sheet_hash,
                             "_staging.goods_movement", inserted, len(mapping), 56 - len(mapping),
                             datetime.now(), VERSION, idem])
                sheets_loaded += 1
                rows_loaded += inserted
        finally:
            wb.close()

    total, = con.execute("SELECT count(*) FROM _staging.goods_movement").fetchone()
    con.close()
    summary = {
        "task_id": "TSK.KMFA.DATA.0007", "phase": "2_extract_goods_movement",
        "extractor_version": VERSION, "sheets_loaded": sheets_loaded,
        "rows_loaded_this_run": rows_loaded, "table_total_rows": total,
        "amount_parse_rejections": money.rejects, "subcent_roundings": money.subcent,
        "amounts_integer_cents": True,
        "column_note": "四金额列入分；数量/单价原文（非货币不转分）；单位组其余 39 列显式缓议",
    }
    out = REPO / (args.out or "KMFA/stage_artifacts/DT5_DATA0028_goods_movement/machine/extract_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
