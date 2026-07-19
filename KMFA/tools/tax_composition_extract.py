#!/usr/bin/env python3
"""税费构成表（税负率明细）带状解析 → `_staging.tax_composition`（长表）。

来源：报表系列一两册的「7税费构成表」「7.2025年税负率明细表」。
版式：标题行（含年份）→ 公司带头（列0=公司简称、列1=收入、列2=增值税）→ 12 个月行 + 合计行。
规则：
- 长表一行 = 公司×年×月×税种；金额列入整数分，比率列（税负率）只存原文字符串（不引入 float）。
- 源表存在亚分精度单元（公式算出），按四舍五入（`ROUND_HALF_UP`）入分并**计数**，原文进 `amount_raw` 不丢失。
- 「合计」行不入库，改做带内交叉脚验（各月之和 vs 合计），差异计数进摘要。
- 幂等键 = 源指纹 + sheet 名 + 版本；重跑同指纹零 diff。
用法：python3 KMFA/tools/tax_composition_extract.py [--out <json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRIVATE = REPO / "KMFA" / ".codex_private_runtime"
DB_PATH = PRIVATE / "duckdb" / "kmfa_staging.duckdb"
INVENTORY = PRIVATE / "imports" / "excel_sheet_inventory" / "full_inventory.json"

VERSION = "tax-composition-v2"  # v2：同一税种多列命中只取首列（尾部辅助列曾致合计双计）
SHEET_KEYWORDS = ("税费构成", "税负率明细")
MONTHS = {f"{i}月": i for i in range(1, 13)}
COMPANY_MAP = {"湖北": "湖北开明", "武汉": "武汉开明", "彤烨": "彤烨", "岚丹": "湖北岚丹", "信茂": "信茂"}
# 金额税种（入分）；比率税种（原文）
AMOUNT_KINDS = ("收入", "增值税", "城建税", "教育费附加", "地方教育附加", "印花税",
                "企业所得税", "房产税土地使用税", "税费合计", "个人所得税", "工会经费")
RATIO_KINDS = ("增值税税负率", "综合所得税税负率")
KIND_ALIASES = {"合计": "税费合计", "印花税未核定": "印花税"}

DDL = """CREATE TABLE IF NOT EXISTS _staging.tax_composition (
    source_sha8 VARCHAR NOT NULL, sheet_hash VARCHAR NOT NULL, row_index INTEGER NOT NULL,
    company_label VARCHAR, company_ref VARCHAR, fiscal_year INTEGER, month INTEGER,
    tax_kind VARCHAR, kind_raw VARCHAR, amount_cents BIGINT, amount_raw VARCHAR, ratio_raw VARCHAR)"""


def norm(text) -> str:
    return unicodedata.normalize("NFKC", str(text)).strip().replace(" ", "").replace("\n", "").replace("\r", "")


class Rounding:
    def __init__(self) -> None:
        self.subcent = 0

    def to_cents(self, value) -> int | None:
        if value in (None, "", "-"):
            return None
        if isinstance(value, bool):
            raise ValueError("bool 不是金额")
        try:
            dec = Decimal(str(value).replace(",", "").strip())
        except InvalidOperation as exc:
            raise ValueError(f"金额不可解析: {value!r}") from exc
        exact = dec * 100
        cents = exact.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if exact != cents:
            self.subcent += 1
        return int(cents)


def parse_sheet(rows, sha8, sheet_hash, rounding):
    """产出 (记录列表, 交叉脚验结果)。带 = 公司头行到下一公司头/表尾。"""
    year = None
    for row in rows[:3]:
        for cell in row:
            text = norm(cell) if cell is not None else ""
            if "年" in text and any(ch.isdigit() for ch in text):
                digits = "".join(ch for ch in text.split("年")[0] if ch.isdigit())
                if len(digits) == 4:
                    year = int(digits)
                    break
        if year:
            break
    records, crossfoot = [], []
    band_company = None
    band_kinds: dict[int, str] = {}
    band_sum: dict[str, int] = {}
    band_total: dict[str, int] = {}

    def close_band():
        if band_company is None:
            return
        for kind, total in band_total.items():
            crossfoot.append({
                "company": band_company, "kind": kind,
                "months_sum_cents": band_sum.get(kind, 0), "sheet_total_cents": total,
                "delta_cents": band_sum.get(kind, 0) - total,
            })

    for r_i, row in enumerate(rows, 1):
        cells = [norm(c) if c is not None else "" for c in row]
        head = cells[0] if cells else ""
        if head in COMPANY_MAP and len(cells) > 2 and cells[1] == "收入" and cells[2] == "增值税":
            close_band()
            band_company = head
            band_sum, band_total = {}, {}
            band_kinds = {}
            for col, cell in enumerate(cells):
                if col == 0 or not cell:
                    continue
                kind = KIND_ALIASES.get(cell, cell)
                if (kind in AMOUNT_KINDS or kind in RATIO_KINDS) and \
                        kind not in {k for k, _ in band_kinds.values()}:
                    band_kinds[col] = (kind, cell)
            continue
        if band_company is None or not band_kinds:
            continue
        if head in MONTHS:
            month = MONTHS[head]
            for col, (kind, kind_raw) in band_kinds.items():
                raw = row[col] if col < len(row) else None
                if raw in (None, ""):
                    continue
                if kind in RATIO_KINDS:
                    records.append((sha8, sheet_hash, r_i, band_company, COMPANY_MAP[band_company],
                                    year, month, kind, kind_raw, None, None, str(raw).strip()))
                    continue
                cents = rounding.to_cents(raw)
                if cents is None:
                    continue
                band_sum[kind] = band_sum.get(kind, 0) + cents
                records.append((sha8, sheet_hash, r_i, band_company, COMPANY_MAP[band_company],
                                year, month, kind, kind_raw, cents, str(raw).strip(), None))
        elif head == "合计":
            for col, (kind, _) in band_kinds.items():
                if kind in RATIO_KINDS:
                    continue
                raw = row[col] if col < len(row) else None
                cents = rounding.to_cents(raw) if raw not in (None, "") else None
                if cents is not None:
                    band_total[kind] = cents
    close_band()
    return records, crossfoot


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

    rounding = Rounding()
    sheets_loaded, rows_loaded, crossfoot_all, amount_errors = 0, 0, [], 0
    for f in sorted(inventory, key=lambda x: x["sha256"]):
        hits = [s["name"] for s in f.get("sheets", [])
                if any(k in norm(s["name"]) for k in SHEET_KEYWORDS)]
        if not hits:
            continue
        row = manifest[f["sha256"]]
        path = REPO / "KMDatabase/data" / row["object_path"]
        sha8 = f["sha256"][:8]
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            for sheet_name in hits:
                sheet_hash = hashlib.sha256(sheet_name.encode("utf-8")).hexdigest()[:12]
                idem = hashlib.sha256(f"{f['sha256']}|{sheet_name}|{VERSION}".encode()).hexdigest()
                if con.execute("SELECT 1 FROM _staging.extraction_manifest WHERE idempotency_key=?", [idem]).fetchone():
                    continue
                raw_rows = [list(r) for r in wb[sheet_name].iter_rows(values_only=True)]
                try:
                    records, crossfoot = parse_sheet(raw_rows, sha8, sheet_hash, rounding)
                except ValueError:
                    amount_errors += 1
                    continue
                for rec in records:
                    con.execute("INSERT INTO _staging.tax_composition VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", list(rec))
                con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                            [f"sha256:{f['sha256']}", str(Path('KMDatabase/data') / row['object_path']), sheet_hash,
                             "_staging.tax_composition", len(records), len(AMOUNT_KINDS) + len(RATIO_KINDS), 0,
                             datetime.now(), VERSION, idem])
                sheets_loaded += 1
                rows_loaded += len(records)
                crossfoot_all.extend(crossfoot)
        finally:
            wb.close()

    table_total = con.execute("SELECT count(*) FROM _staging.tax_composition").fetchone()[0]
    con.close()

    exact = sum(1 for c in crossfoot_all if c["delta_cents"] == 0)
    summary = {
        "task_id": "TSK.KMFA.DATA.0007", "phase": "2_extract_tax_composition",
        "extractor_version": VERSION, "sheets_loaded": sheets_loaded,
        "rows_loaded_this_run": rows_loaded, "table_total_rows": table_total,
        "amount_parse_rejections": amount_errors, "amounts_integer_cents": True,
        "subcent_roundings": rounding.subcent,
        "crossfoot_bands_exact": exact, "crossfoot_bands_total": len(crossfoot_all),
        "crossfoot_mismatches": [c for c in crossfoot_all if c["delta_cents"] != 0],
    }
    out = REPO / (args.out or "KMFA/stage_artifacts/DT5_DATA0022_tax_composition/machine/extract_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "crossfoot_mismatches"}, ensure_ascii=False))
    print(f"crossfoot 不平条目: {len(summary['crossfoot_mismatches'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
