#!/usr/bin/env python3
"""Excel → DuckDB _staging 抽取管线（TSK.KMFA.DATA.0007 阶段二，规格注册表驱动）。

已接类别：collection（回款流水）｜receivable_aging（合同级应收台账）｜journal（银行日记账合并流水——签名含公司+资金户名，只取合并表防逐账户 sheet 重复）。
逐 sheet 决策：类别签名列全命中才抽取，否则如实 deferred。金额 Decimal→整数分（float 拒）；
比率类字段保留原文字符串（不引入 float）。幂等键=源指纹+sheet名+类别版本，重跑同指纹零 diff。
库与明细永在 .codex_private_runtime（不 tracked）；公开面只出聚合计数。

用法：python3 KMFA/tools/staging_extract.py --category collection|receivable_aging [--out <json>]
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
MAX_SCAN_COLS = 60  # openpyxl 会报出上万个幽灵格式列，截断扫描

CATEGORY_SPECS = {
    "collection": {
        "version": "collection-v1",
        "table": "collection",
        "signature": ("collection_date", "collection_amount_cents"),
        "aliases": {
            "collection_date": ("日期", "回款日期", "收款日期"),
            "customer_ref": ("公司名称", "客户名称", "客户", "单位名称"),
            "contract_ref": ("合同号", "合同编号", "合同号码"),
            "collection_amount_cents": ("回款金额（元）", "回款金额(元)", "回款金额", "收款金额"),
            "receipt_method": ("回款方式", "收款方式"),
            "owner_ref": ("负责人", "业务负责人"),
            "project_ref": ("项目内容", "项目名称", "项目"),
            "note": ("备注",),
            "row_seq": ("序列", "序号"),
        },
        "types": {"collection_date": "date", "collection_amount_cents": "cents"},
        "require_value": "collection_amount_cents",
        "ddl": """CREATE TABLE IF NOT EXISTS _staging.collection (
            source_sha8 VARCHAR NOT NULL, sheet_hash VARCHAR NOT NULL, row_index INTEGER NOT NULL,
            collection_date DATE, customer_ref VARCHAR, contract_ref VARCHAR,
            collection_amount_cents BIGINT, receipt_method VARCHAR, owner_ref VARCHAR,
            project_ref VARCHAR, note VARCHAR, row_seq VARCHAR)""",
        "columns": ["collection_date", "customer_ref", "contract_ref", "collection_amount_cents",
                     "receipt_method", "owner_ref", "project_ref", "note", "row_seq"],
    },
    "journal": {
        "version": "journal-v1",
        "table": "bank_journal",
        "signature": ("company_ref", "account_ref", "journal_date", "receipt_amount_cents", "payment_amount_cents"),
        "aliases": {
            "company_ref": ("公司", "公司名称"),
            "account_ref": ("资金户名", "账户", "银行账户"),
            "journal_date": ("日期", "交易日期"),
            "summary_text": ("摘要",),
            "flow_category": ("收支类别",),
            "receipt_amount_cents": ("收款金额", "收入金额"),
            "payment_amount_cents": ("付款金额", "支出金额"),
            "balance_cents": ("余额",),
            "note": ("备注",),
        },
        "types": {"journal_date": "date", "receipt_amount_cents": "cents",
                   "payment_amount_cents": "cents", "balance_cents": "cents"},
        "require_value": "journal_date",
        "ddl": """CREATE TABLE IF NOT EXISTS _staging.bank_journal (
            source_sha8 VARCHAR NOT NULL, sheet_hash VARCHAR NOT NULL, row_index INTEGER NOT NULL,
            company_ref VARCHAR, account_ref VARCHAR, journal_date DATE, summary_text VARCHAR,
            flow_category VARCHAR, receipt_amount_cents BIGINT, payment_amount_cents BIGINT,
            balance_cents BIGINT, note VARCHAR)""",
        "columns": ["company_ref", "account_ref", "journal_date", "summary_text", "flow_category",
                     "receipt_amount_cents", "payment_amount_cents", "balance_cents", "note"],
    },
    "receivable_aging": {
        "version": "aging-v1",
        "table": "receivable_aging",
        "signature": ("customer_ref", "contract_ref", "invoiced_amount_cents"),
        "aliases": {
            "contract_date": ("合同日期", "签订日期"),
            "customer_ref": ("客户名称",),
            "industry": ("行业",),
            "contract_ref": ("合同号", "合同编号"),
            "counterparty_contract_ref": ("对方合同号",),
            "region": ("省市", "地区"),
            "owner_ref": ("业务员", "负责人"),
            "invoiced_amount_cents": ("已开票金额", "开票金额"),
            "litigation_flag": ("是否起诉",),
            "acceptance_report": ("验收报告",),
            "signing_company": ("签订合同公司",),
            "invoice_company": ("开票公司",),
            "invoice_no": ("发票号",),
            "invoice_date": ("开票时间", "开票日期"),
            "invoiced_flag": ("是否开票",),
            "completed_flag": ("是否完工",),
            "contract_amount_cents": ("合同确定金额", "合同金额"),
            "received_amount_cents": ("累计已收款", "累计回款"),
            "remaining_amount_cents": ("剩余金额", "应收余额"),
            "collection_ratio_raw": ("回款率",),
            "note": ("备注",),
            "write_off_flag": ("是否销账",),
            "category_ref": ("归属类别",),
            "contract_type": ("合同类型",),
        },
        "types": {"contract_date": "date", "invoice_date": "date",
                   "invoiced_amount_cents": "cents", "contract_amount_cents": "cents",
                   "received_amount_cents": "cents", "remaining_amount_cents": "cents"},
        "require_value": "contract_ref",
        "ddl": """CREATE TABLE IF NOT EXISTS _staging.receivable_aging (
            source_sha8 VARCHAR NOT NULL, sheet_hash VARCHAR NOT NULL, row_index INTEGER NOT NULL,
            contract_date DATE, customer_ref VARCHAR, industry VARCHAR, contract_ref VARCHAR,
            counterparty_contract_ref VARCHAR, region VARCHAR, owner_ref VARCHAR,
            invoiced_amount_cents BIGINT, litigation_flag VARCHAR, acceptance_report VARCHAR,
            signing_company VARCHAR, invoice_company VARCHAR, invoice_no VARCHAR, invoice_date DATE,
            invoiced_flag VARCHAR, completed_flag VARCHAR, contract_amount_cents BIGINT,
            received_amount_cents BIGINT, remaining_amount_cents BIGINT, collection_ratio_raw VARCHAR,
            note VARCHAR, write_off_flag VARCHAR, category_ref VARCHAR, contract_type VARCHAR)""",
        "columns": ["contract_date", "customer_ref", "industry", "contract_ref",
                     "counterparty_contract_ref", "region", "owner_ref", "invoiced_amount_cents",
                     "litigation_flag", "acceptance_report", "signing_company", "invoice_company",
                     "invoice_no", "invoice_date", "invoiced_flag", "completed_flag",
                     "contract_amount_cents", "received_amount_cents", "remaining_amount_cents",
                     "collection_ratio_raw", "note", "write_off_flag", "category_ref", "contract_type"],
    },
}


def norm(text) -> str:
    return unicodedata.normalize("NFKC", str(text)).strip().replace(" ", "").replace("\n", "").replace("\r", "")


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


def to_iso_date(value):
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
            for row in wb[sheet_name].iter_rows(values_only=True):
                yield list(row[:MAX_SCAN_COLS])
        finally:
            wb.close()
    else:
        import xlrd
        wb = xlrd.open_workbook(str(path), on_demand=True)
        try:
            ws = wb.sheet_by_name(sheet_name)
            for i in range(ws.nrows):
                yield [ws.cell_value(i, j) for j in range(min(ws.ncols, MAX_SCAN_COLS))]
        finally:
            wb.release_resources()


def find_header(rows, alias_index, signature, limit=10):
    for idx, row in enumerate(rows[:limit]):
        mapping = {}
        for col, cell in enumerate(row):
            if cell in (None, ""):
                continue
            canonical = alias_index.get(norm(cell))
            if canonical and canonical not in mapping.values():
                mapping[col] = canonical
        if all(req in mapping.values() for req in signature):
            return idx, mapping
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", required=True, choices=sorted(CATEGORY_SPECS))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    spec = CATEGORY_SPECS[args.category]
    alias_index = {norm(a): c for c, aliases in spec["aliases"].items() for a in aliases}

    import duckdb
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    manifest = {r["sha256"]: r for r in (json.loads(l) for l in (REPO / "KMDatabase/data/manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    targets = [f for f in inventory if f["matched_category"] == args.category]

    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS _staging")
    con.execute(spec["ddl"])

    file_reports, total_rows, sheets_loaded, sheets_deferred, amount_errors = [], 0, 0, 0, 0
    for f in sorted(targets, key=lambda x: x["sha256"]):
        row = manifest[f["sha256"]]
        path = REPO / "KMDatabase/data" / row["object_path"]
        fmt = "xlsx" if row["original_name"].lower().endswith(".xlsx") else "xls"
        sha8 = f["sha256"][:8]
        loaded = 0
        for sheet in f["sheets"]:
            sheet_hash = hashlib.sha256(sheet["name"].encode("utf-8")).hexdigest()[:12]
            idem = hashlib.sha256(f"{f['sha256']}|{sheet['name']}|{spec['version']}".encode()).hexdigest()
            if con.execute("SELECT 1 FROM _staging.extraction_manifest WHERE idempotency_key=?", [idem]).fetchone():
                continue
            rows = list(iter_sheet_rows(path, sheet["name"], fmt))
            found = find_header(rows, alias_index, spec["signature"])
            if not found:
                sheets_deferred += 1
                con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                            [f"sha256:{f['sha256']}", str(Path('KMDatabase/data') / row['object_path']), sheet_hash,
                             "-", 0, 0, len(rows[0]) if rows else 0, datetime.now(), spec["version"], idem])
                continue
            header_idx, mapping = found
            inserted = 0
            for r_i, data_row in enumerate(rows[header_idx + 1:], header_idx + 2):
                record = {c: None for c in spec["columns"]}
                nonempty = 0
                for col, canonical in mapping.items():
                    value = data_row[col] if col < len(data_row) else None
                    if value in (None, ""):
                        continue
                    nonempty += 1
                    kind = spec["types"].get(canonical, "text")
                    if kind == "cents":
                        try:
                            record[canonical] = to_cents(value)
                        except ValueError:
                            amount_errors += 1
                    elif kind == "date":
                        record[canonical] = to_iso_date(value)
                    else:
                        record[canonical] = str(value).strip()
                if nonempty == 0 or record.get(spec["require_value"]) is None:
                    continue
                placeholders = ",".join("?" for _ in range(3 + len(spec["columns"])))
                con.execute(f"INSERT INTO _staging.{spec['table']} VALUES ({placeholders})",
                            [sha8, sheet_hash, r_i, *[record[c] for c in spec["columns"]]])
                inserted += 1
            mapped_cols = len(mapping)
            deferred_cols = max((max((len(r) for r in rows), default=0)) - mapped_cols, 0)
            con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                        [f"sha256:{f['sha256']}", str(Path('KMDatabase/data') / row['object_path']), sheet_hash,
                         f"_staging.{spec['table']}", inserted, mapped_cols, deferred_cols,
                         datetime.now(), spec["version"], idem])
            loaded += inserted
            sheets_loaded += 1
        total_rows += loaded
        file_reports.append({"sha8": sha8, "domain": row["domain"], "sheets": len(f["sheets"]), "rows_loaded": loaded})

    table_total = con.execute(f"SELECT count(*) FROM _staging.{spec['table']}").fetchone()[0]
    con.close()

    summary = {
        "task_id": "TSK.KMFA.DATA.0007", "phase": f"2_extract_{args.category}",
        "extractor_version": spec["version"], "files": len(targets),
        "sheets_loaded": sheets_loaded, "sheets_deferred": sheets_deferred,
        "rows_loaded_this_run": total_rows, "table_total_rows": table_total,
        "amount_parse_rejections": amount_errors, "amounts_integer_cents": True,
        "per_file": file_reports,
    }
    out = REPO / (args.out or f"KMFA/stage_artifacts/DT5_DATA0007_extract_{args.category}/machine/extract_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_file"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
