#!/usr/bin/env python3
"""科目编码对照母表抽取 → `_staging.subject_code_map`（双套编码现象的制度源头）。

来源：报表系列一「17底表」「Sheet1」——统一编码（编号/名称/类别）对四套公司账
（武汉开明/湖北开明/彤烨/个体户）各自编号/名称的对照矩阵。
落库为长表：一行 =（统一码 × 有码的公司），空对照如实跳过；纯文本无金额列。
幂等键=源指纹+sheet+版本。用法：python3 KMFA/tools/subject_code_map_extract.py [--out <json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRIVATE = REPO / "KMFA" / ".codex_private_runtime"
DB_PATH = PRIVATE / "duckdb" / "kmfa_staging.duckdb"
INVENTORY = PRIVATE / "imports" / "excel_sheet_inventory" / "full_inventory.json"

VERSION = "subject-code-map-v2"  # v2：无公司横幅行的 sheet（Sheet1）按册内固定公司次序回退
SHEET_NAMES = ("17底表", "Sheet1")
COMPANY_ORDER = ("武汉开明", "湖北开明", "彤烨", "个体户")  # 册内公司组固定次序（17底表横幅实证）

DDL = """CREATE TABLE IF NOT EXISTS _staging.subject_code_map (
    source_sha8 VARCHAR NOT NULL, sheet_hash VARCHAR NOT NULL, row_index INTEGER NOT NULL,
    unified_code VARCHAR, unified_name VARCHAR, category_ref VARCHAR,
    company_ref VARCHAR, company_code VARCHAR, company_name VARCHAR)"""


def norm(text) -> str:
    return unicodedata.normalize("NFKC", str(text)).strip().replace(" ", "").replace("\n", "")


def parse_sheet(rows):
    """识别公司列组：银行头行（统一/公司名）+ 列头行（编号/名称[/类别]）。"""
    company_row = header_row = None
    for idx, r in enumerate(rows[:4]):
        cells = [norm(c) if c is not None else "" for c in r]
        if "统一" in cells:
            company_row = idx
        if cells.count("编号") >= 2 and "名称" in cells:
            header_row = idx
            break
    if header_row is None:
        return None
    companies = {}
    if company_row is not None:
        current = None
        for col, c in enumerate([norm(x) if x is not None else "" for x in rows[company_row]]):
            if c and c != "统一":
                current = c
                companies[col] = current
    header = [norm(c) if c is not None else "" for c in rows[header_row]]
    unified_cols = {}
    company_groups = []
    col = 0
    while col < len(header):
        if header[col] == "编号":
            name_col = col + 1 if col + 1 < len(header) and header[col + 1] == "名称" else None
            if not unified_cols:
                cat_col = col + 2 if col + 2 < len(header) and header[col + 2] == "类别" else None
                unified_cols = {"code": col, "name": name_col, "cat": cat_col}
            else:
                comp = companies.get(col)
                if comp is None and companies:
                    near = min(companies.items(), key=lambda kv: abs(kv[0] - col))
                    comp = near[1] if abs(near[0] - col) <= 1 else None
                if comp is None:
                    idx = len(company_groups)
                    comp = COMPANY_ORDER[idx] if idx < len(COMPANY_ORDER) else f"公司列{col}"
                company_groups.append({"company": comp, "code": col, "name": name_col})
        col += 1
    records = []
    for r_i, r in enumerate(rows[header_row + 1:], header_row + 2):
        cells = list(r)
        def val(c):
            if c is None or c >= len(cells) or cells[c] in (None, ""):
                return None
            return str(cells[c]).strip()
        ucode = val(unified_cols["code"])
        if not ucode:
            continue
        uname = val(unified_cols["name"])
        ucat = val(unified_cols.get("cat"))
        for g in company_groups:
            ccode = val(g["code"])
            if not ccode:
                continue
            records.append((r_i, ucode, uname, ucat, g["company"], ccode, val(g["name"])))
    return records


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

    sheets_loaded, rows_loaded, deferred = 0, 0, []
    for f in sorted(inventory, key=lambda x: x["sha256"]):
        row = manifest[f["sha256"]]
        # 「Sheet1」名过泛：只在报表系列一两册内找（母表所在册）
        if "报表系列一" not in row["original_name"]:
            continue
        names = [s["name"] for s in f.get("sheets", [])]
        hits = [n for n in names if norm(n) in SHEET_NAMES]
        if not hits:
            continue
        path = REPO / "KMDatabase/data" / row["object_path"]
        sha8 = f["sha256"][:8]
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            for sheet_name in hits:
                sheet_hash = hashlib.sha256(sheet_name.encode()).hexdigest()[:12]
                idem = hashlib.sha256(f"{f['sha256']}|{sheet_name}|{VERSION}".encode()).hexdigest()
                if con.execute("SELECT 1 FROM _staging.extraction_manifest WHERE idempotency_key=?", [idem]).fetchone():
                    continue
                raw = [list(r) for r in wb[sheet_name].iter_rows(values_only=True)]
                records = parse_sheet(raw)
                if records is None:
                    deferred.append(f"{sha8}:{sheet_name}")
                    continue
                for r_i, ucode, uname, ucat, comp, ccode, cname in records:
                    con.execute("INSERT INTO _staging.subject_code_map VALUES (?,?,?,?,?,?,?,?,?)",
                                [sha8, sheet_hash, r_i, ucode, uname, ucat, comp, ccode, cname])
                con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                            [f"sha256:{f['sha256']}", str(Path('KMDatabase/data') / row['object_path']), sheet_hash,
                             "_staging.subject_code_map", len(records), 9, 0, datetime.now(), VERSION, idem])
                sheets_loaded += 1
                rows_loaded += len(records)
        finally:
            wb.close()

    total, = con.execute("SELECT count(*) FROM _staging.subject_code_map").fetchone()
    con.close()
    summary = {
        "task_id": "TSK.KMFA.DATA.0007", "phase": "2_extract_subject_code_map",
        "extractor_version": VERSION, "sheets_loaded": sheets_loaded,
        "rows_loaded_this_run": rows_loaded, "table_total_rows": total,
        "deferred_sheets": deferred, "note": "纯文本对照表，无金额列",
    }
    out = REPO / (args.out or "KMFA/stage_artifacts/DT5_DATA0040_subject_code_map/machine/extract_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
