#!/usr/bin/env python3
"""银行贷款一览表快照抽取 → `_staging.loan_register`（借款域首件）。

来源：loan 类工作簿中名含「贷款明细」的 sheet（如「25.12贷款明细」「贷款明细」），每工作簿一版快照。
要点：
- **混合单位**：贷款金额/结存为**万元**（×1,000,000 入分），费用与月还款为**元**（×100 入分）；
  亚分精度按半进位（`ROUND_HALF_UP`）入分并计数，原文存 `*_raw` 不丢失。
- 年利率/还款日/放款期（如「2025.09」）为非日期语义，一律原文字符串，不引入 `float`、不硬造日期。
- 快照键=源指纹；幂等键=源指纹+sheet+版本。各银行的还款计划分表（如「湖北-仲利」）本单如实缓议。
用法：python3 KMFA/tools/loan_register_extract.py [--out <json>]
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

VERSION = "loan-register-v2"  # v2：结存列改为包含匹配（表头带截止日期，逐版不同，如「贷款结存金额截止到5月25日(万元)」）
SHEET_KEYWORD = "贷款明细"
# 包含式规则（精确别名不命中时兜底）：子串 → (规范名, 单位)
CONTAINS_RULES = (("结存", ("outstanding_cents", "wan")),)

# 列别名 → (规范名, 单位)。单位: wan=万元, yuan=元, raw=原文
COLUMNS = {
    "序号": ("row_seq", "raw"),
    "公司": ("company_ref", "raw"),
    "银行": ("lender_ref", "raw"),
    "每月还款日期": ("repay_day_raw", "raw"),
    "放款时间": ("disbursed_period", "raw"),
    "期限（年）": ("term_years_raw", "raw"),
    "贷款金额（万）": ("principal_cents", "wan"),
    "贷款金额（万元）": ("principal_cents", "wan"),
    "贷款结存金额截止到5月": ("outstanding_cents", "wan"),
    "年利率": ("annual_rate_raw", "raw"),
    "每月还款金额(元）": ("monthly_payment_cents", "yuan"),
    "每月还款金额（元）": ("monthly_payment_cents", "yuan"),
    "担保费": ("guarantee_fee_cents", "yuan"),
    "过桥费": ("bridge_fee_cents", "yuan"),
    "居间费": ("agency_fee_cents", "yuan"),
    "还款方式": ("repay_method", "raw"),
    "到期日": ("maturity_period", "raw"),
}
SIGNATURE = ("company_ref", "lender_ref", "principal_cents")
FIELDS = ["row_seq", "company_ref", "lender_ref", "repay_day_raw", "disbursed_period",
          "term_years_raw", "principal_cents", "principal_raw", "outstanding_cents", "outstanding_raw",
          "annual_rate_raw", "monthly_payment_cents", "guarantee_fee_cents", "bridge_fee_cents",
          "agency_fee_cents", "repay_method", "maturity_period"]

DDL = """CREATE TABLE IF NOT EXISTS _staging.loan_register (
    source_sha8 VARCHAR NOT NULL, sheet_hash VARCHAR NOT NULL, row_index INTEGER NOT NULL,
    snapshot_label VARCHAR, row_seq VARCHAR, company_ref VARCHAR, lender_ref VARCHAR,
    repay_day_raw VARCHAR, disbursed_period VARCHAR, term_years_raw VARCHAR,
    principal_cents BIGINT, principal_raw VARCHAR, outstanding_cents BIGINT, outstanding_raw VARCHAR,
    annual_rate_raw VARCHAR, monthly_payment_cents BIGINT, guarantee_fee_cents BIGINT,
    bridge_fee_cents BIGINT, agency_fee_cents BIGINT, repay_method VARCHAR, maturity_period VARCHAR)"""


def norm(text) -> str:
    return unicodedata.normalize("NFKC", str(text)).strip().replace(" ", "").replace("\n", "")


# 表头别名与单元格走同一 NFKC 规范化（全角括号→半角），否则全角键永不命中
NORM_COLUMNS = {norm(k): v for k, v in COLUMNS.items()}


class Money:
    def __init__(self) -> None:
        self.subcent = 0
        self.rejects = 0

    def to_cents(self, value, unit: str) -> int | None:
        if value in (None, ""):
            return None
        try:
            dec = Decimal(str(value).replace(",", "").strip())
        except InvalidOperation:
            self.rejects += 1
            return None
        exact = dec * (1_000_000 if unit == "wan" else 100)
        cents = exact.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if exact != cents:
            self.subcent += 1
        return int(cents)


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
    sheets_loaded, rows_loaded, deferred = 0, 0, []
    for f in sorted(inventory, key=lambda x: x["sha256"]):
        names = [s["name"] for s in f.get("sheets", [])]
        hits = [n for n in names if SHEET_KEYWORD in norm(n)]
        if not hits:
            continue
        row = manifest[f["sha256"]]
        path = REPO / "KMDatabase/data" / row["object_path"]
        sha8 = f["sha256"][:8]
        snapshot = row["original_name"].rsplit(".xlsx", 1)[0]
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
                        cell_n = norm(cell)
                        hit = NORM_COLUMNS.get(cell_n)
                        if not hit:
                            hit = next((v for sub, v in CONTAINS_RULES if sub in cell_n), None)
                        if hit and hit[0] not in {v[0] for v in m.values()}:
                            m[col] = hit
                    if all(any(v[0] == s for v in m.values()) for s in SIGNATURE):
                        header_idx, mapping = idx, m
                        break
                if header_idx is None:
                    deferred.append(f"{sha8}:{sheet_name}")
                    continue
                inserted = 0
                for r_i, data in enumerate(raw_rows[header_idx + 1:], header_idx + 2):
                    rec = dict.fromkeys(FIELDS)
                    for col, (canon, unit) in mapping.items():
                        v = data[col] if col < len(data) else None
                        if v in (None, ""):
                            continue
                        if unit == "raw":
                            rec[canon] = str(v).strip()
                        else:
                            rec[canon] = money.to_cents(v, unit)
                            if canon in ("principal_cents", "outstanding_cents"):
                                rec[canon.replace("_cents", "_raw")] = str(v).strip()
                    if not rec["company_ref"] or not rec["lender_ref"] or rec["principal_cents"] is None:
                        continue
                    con.execute(f"INSERT INTO _staging.loan_register VALUES (?,?,?,?{',?' * len(FIELDS)})",
                                [sha8, sheet_hash, r_i, snapshot, *[rec[k] for k in FIELDS]])
                    inserted += 1
                con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                            [f"sha256:{f['sha256']}", str(Path('KMDatabase/data') / row['object_path']), sheet_hash,
                             "_staging.loan_register", inserted, len(mapping), 0, datetime.now(), VERSION, idem])
                sheets_loaded += 1
                rows_loaded += inserted
        finally:
            wb.close()

    total, = con.execute("SELECT count(*) FROM _staging.loan_register").fetchone()
    con.close()
    summary = {
        "task_id": "TSK.KMFA.DATA.0007", "phase": "2_extract_loan_register",
        "extractor_version": VERSION, "sheets_loaded": sheets_loaded,
        "rows_loaded_this_run": rows_loaded, "table_total_rows": total,
        "amount_parse_rejections": money.rejects, "subcent_roundings": money.subcent,
        "amounts_integer_cents": True, "deferred_sheets": deferred,
        "unit_note": "贷款金额/结存=万元(×1e6)，费用/月还款=元(×100)",
    }
    out = REPO / (args.out or "KMFA/stage_artifacts/DT5_DATA0026_loan_register/machine/extract_summary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
