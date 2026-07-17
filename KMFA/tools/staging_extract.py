#!/usr/bin/env python3
"""Excel → DuckDB _staging 抽取管线（TSK.KMFA.DATA.0007 阶段二，首类：collection 回款）。

逐 sheet 决策：表头签名匹配（必须含 日期 与 回款金额 同义列）→ 按别名映射抽行入
`_staging.collection`；不匹配的 sheet 如实登记 deferred（汇总表/空表）。
金额一律整数分（Decimal 精确换算，float 拒绝）；幂等键=源指纹+sheet名哈希+抽取器版本，
重跑同指纹零 diff。库与明细永在 .codex_private_runtime（不 tracked）；公开面只出聚合计数。

用法：python3 KMFA/tools/staging_extract.py --category collection [--out <公开摘要 json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRIVATE = REPO / "KMFA" / ".codex_private_runtime"
DB_PATH = PRIVATE / "duckdb" / "kmfa_staging.duckdb"
INVENTORY = PRIVATE / "imports" / "excel_sheet_inventory" / "full_inventory.json"
EXTRACTOR_VERSION = "collection-v1"

COLLECTION_ALIASES = {
    "collection_date": ("日期", "回款日期", "收款日期"),
    "customer_ref": ("公司名称", "客户名称", "客户", "单位名称"),
    "contract_ref": ("合同号", "合同编号", "合同号码"),
    "collection_amount_cents": ("回款金额（元）", "回款金额(元)", "回款金额", "收款金额"),
    "receipt_method": ("回款方式", "收款方式"),
    "owner_ref": ("负责人", "业务负责人"),
    "project_ref": ("项目内容", "项目名称", "项目"),
    "note": ("备注",),
    "row_seq": ("序列", "序号"),
}
REQUIRED_SIGNATURE = ("collection_date", "collection_amount_cents")


def norm(text) -> str:
    return unicodedata.normalize("NFKC", str(text)).strip().replace(" ", "")


def build_alias_index() -> dict[str, str]:
    index = {}
    for canonical, aliases in COLLECTION_ALIASES.items():
        for alias in aliases:
            index[norm(alias)] = canonical
    return index


ALIAS_INDEX = build_alias_index()


def to_cents(value) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError("bool 不是金额")
    try:
        dec = Decimal(str(value).replace(",", "").replace("￥", "").replace("¥", "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"金额不可解析: {value!r}") from exc
    cents = (dec * 100).quantize(Decimal("1"))
    if (dec * 100) != cents:
        raise ValueError(f"金额超过分精度: {value!r}")
    return int(cents)


def to_iso_date(value) -> str | None:
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


def iter_sheet_rows(path: Path, sheet_name: str, fmt: str):
    if fmt == "xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            ws = wb[sheet_name]
            for row in ws.iter_rows(values_only=True):
                yield list(row)
        finally:
            wb.close()
    else:
        import xlrd
        wb = xlrd.open_workbook(str(path), on_demand=True)
        try:
            ws = wb.sheet_by_name(sheet_name)
            for i in range(ws.nrows):
                yield [ws.cell_value(i, j) for j in range(ws.ncols)]
        finally:
            wb.release_resources()


def find_header(rows: list[list], limit: int = 10) -> tuple[int, dict[int, str]] | None:
    for idx, row in enumerate(rows[:limit]):
        mapping = {}
        for col, cell in enumerate(row):
            if cell in (None, ""):
                continue
            canonical = ALIAS_INDEX.get(norm(cell))
            if canonical:
                mapping[col] = canonical
        if all(req in mapping.values() for req in REQUIRED_SIGNATURE):
            return idx, mapping
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", default="collection", choices=["collection"])
    parser.add_argument("--out", default="KMFA/stage_artifacts/DT5_DATA0007_extract_collection/machine/extract_summary.json")
    args = parser.parse_args()

    import duckdb
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    manifest = {r["sha256"]: r for r in (json.loads(l) for l in (REPO / "KMDatabase/data/manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    targets = [f for f in inventory if f["matched_category"] == args.category]

    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS _staging")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS _staging.collection (
            source_sha8 VARCHAR NOT NULL,
            sheet_hash VARCHAR NOT NULL,
            row_index INTEGER NOT NULL,
            collection_date DATE,
            customer_ref VARCHAR,
            contract_ref VARCHAR,
            collection_amount_cents BIGINT,
            receipt_method VARCHAR,
            owner_ref VARCHAR,
            project_ref VARCHAR,
            note VARCHAR,
            row_seq VARCHAR
        )
        """
    )

    file_reports, total_rows, sheets_loaded, sheets_deferred, amount_errors = [], 0, 0, 0, 0
    for f in sorted(targets, key=lambda x: x["sha256"]):
        row = manifest[f["sha256"]]
        path = REPO / "KMDatabase/data" / row["object_path"]
        fmt = "xlsx" if row["original_name"].lower().endswith(".xlsx") else "xls"
        sha8 = f["sha256"][:8]
        loaded, deferred = 0, []
        for sheet in f["sheets"]:
            sheet_hash = hashlib.sha256(sheet["name"].encode("utf-8")).hexdigest()[:12]
            idem = hashlib.sha256(f"{f['sha256']}|{sheet['name']}|{EXTRACTOR_VERSION}".encode()).hexdigest()
            already = con.execute("SELECT 1 FROM _staging.extraction_manifest WHERE idempotency_key=?", [idem]).fetchone()
            if already:
                continue
            rows = list(iter_sheet_rows(path, sheet["name"], fmt))
            found = find_header(rows)
            if not found:
                deferred.append(sheet_hash)
                sheets_deferred += 1
                con.execute(
                    "INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [f"sha256:{f['sha256']}", str(Path('KMDatabase/data') / row['object_path']), sheet_hash,
                     "-", 0, 0, len(rows[0]) if rows else 0, datetime.now(), EXTRACTOR_VERSION, idem])
                continue
            header_idx, mapping = found
            inserted = 0
            for r_i, data_row in enumerate(rows[header_idx + 1:], header_idx + 2):
                record = {canonical: None for canonical in COLLECTION_ALIASES}
                nonempty = 0
                for col, canonical in mapping.items():
                    value = data_row[col] if col < len(data_row) else None
                    if value in (None, ""):
                        continue
                    nonempty += 1
                    if canonical == "collection_amount_cents":
                        try:
                            record[canonical] = to_cents(value)
                        except ValueError:
                            amount_errors += 1
                            record[canonical] = None
                    elif canonical == "collection_date":
                        record[canonical] = to_iso_date(value)
                    else:
                        record[canonical] = str(value).strip()
                if nonempty == 0 or record["collection_amount_cents"] is None:
                    continue
                con.execute(
                    "INSERT INTO _staging.collection VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [sha8, sheet_hash, r_i, record["collection_date"], record["customer_ref"],
                     record["contract_ref"], record["collection_amount_cents"], record["receipt_method"],
                     record["owner_ref"], record["project_ref"], record["note"], record["row_seq"]])
                inserted += 1
            mapped_cols = len(mapping)
            deferred_cols = (max((len(r) for r in rows), default=0)) - mapped_cols
            con.execute(
                "INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                [f"sha256:{f['sha256']}", str(Path('KMDatabase/data') / row['object_path']), sheet_hash,
                 "_staging.collection", inserted, mapped_cols, max(deferred_cols, 0), datetime.now(), EXTRACTOR_VERSION, idem])
            loaded += inserted
            sheets_loaded += 1
        total_rows += loaded
        file_reports.append({"sha8": sha8, "domain": row["domain"], "sheets": len(f["sheets"]),
                             "rows_loaded": loaded, "sheets_deferred_in_file": len(deferred)})

    grand_total = con.execute("SELECT count(*), coalesce(sum(collection_amount_cents),0) % 100 FROM _staging.collection").fetchone()
    con.close()

    summary = {
        "task_id": "TSK.KMFA.DATA.0007", "phase": "2_extract_collection", "extractor_version": EXTRACTOR_VERSION,
        "files": len(targets), "sheets_loaded": sheets_loaded, "sheets_deferred": sheets_deferred,
        "rows_loaded_this_run": total_rows, "table_total_rows": grand_total[0],
        "amount_parse_rejections": amount_errors, "amounts_integer_cents": True,
        "per_file": file_reports,
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_file"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
