#!/usr/bin/env python3
"""经营分析·关键指标带状表抽取（TSK.KMFA.DATA.0007 阶段二·op 类首件）。

来源：经营分析数据支撑.xlsx 的「财务数据」sheet——重复带状：
  表头带（主体/关键指标/2024年/2025年/同比变化 ×2 平行栏组）→ 主体行 → 合计行 → 空行。
入 `_staging.op_key_indicators`：金额 元→整数分（Decimal），同比/异常值（#DIV/0!）存原文；
栏组语义（累计 vs 当期）不猜——band/group 索引如实入库，命名交给口径字典（DATA.0015）。
幂等：sheet 级（源指纹+sheet+版本）。用法：python3 KMFA/tools/op_indicators_extract.py
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"
VERSION = "op-indicators-v3"
SHEET = "财务数据"


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
    return int(cents) if abs(dec * 100 - cents) < Decimal("0.5") else None


def main() -> int:
    import duckdb, openpyxl
    man = [json.loads(l) for l in (REPO / "KMDatabase/data/manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    src = [r for r in man if "经营分析数据支撑" in r["original_name"]][0]
    idem = hashlib.sha256(f"{src['sha256']}|{SHEET}|{VERSION}".encode()).hexdigest()

    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS _staging")
    con.execute("""CREATE TABLE IF NOT EXISTS _staging.op_key_indicators (
        source_sha8 VARCHAR NOT NULL, band_index INTEGER NOT NULL, group_index INTEGER NOT NULL,
        row_index INTEGER NOT NULL, entity VARCHAR NOT NULL, indicator VARCHAR,
        y2024_cents BIGINT, y2025_cents BIGINT, y2024_raw VARCHAR, y2025_raw VARCHAR,
        yoy_raw VARCHAR, is_total BOOLEAN NOT NULL)""")
    if con.execute("SELECT 1 FROM _staging.extraction_manifest WHERE idempotency_key=?", [idem]).fetchone():
        print(json.dumps({"status": "IDEMPOTENT_NOOP"}, ensure_ascii=False))
        con.close()
        return 0

    wb = openpyxl.load_workbook(REPO / "KMDatabase/data" / src["object_path"], read_only=True, data_only=True)
    ws = wb[SHEET]
    rows = [[v for v in r] for r in ws.iter_rows(values_only=True)]
    wb.close()

    inserted, band = 0, -1
    groups: list[int] = []
    for r_i, row in enumerate(rows, 1):
        cells = [norm(v) if v not in (None, "") else "" for v in row]
        header_cols = [i for i, v in enumerate(cells)
                       if v == "主体" and i + 3 < len(cells) and cells[i + 1] == "关键指标"
                       and any("年" in cells[i + k] for k in (2, 3))]
        if header_cols:
            band += 1
            groups = header_cols
            continue
        # 任何其他表头行（主体占比带/费用项目/时间 等异构表）→ 关闭当前带，防串行
        nonempty = sum(1 for v in cells if v)
        if nonempty >= 3 and cells and (cells[0] in ("主体", "费用项目", "时间") or "占" in "".join(cells[:6])):
            groups = []
            continue
        if not groups:
            continue
        for g_i, c in enumerate(groups):
            entity = cells[c] if c < len(cells) else ""
            if not entity:
                continue
            try:  # 实体列出现纯数值=串行漂移，跳过该组该行
                Decimal(entity.replace(",", "").replace("%", ""))
                continue
            except InvalidOperation:
                pass
            def raw(off):
                i = c + off
                return (norm(row[i]) if i < len(row) and row[i] not in (None, "") else None)
            con.execute("INSERT INTO _staging.op_key_indicators VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        [src["sha256"][:8], band, g_i, r_i, entity, raw(1),
                         to_cents(row[c + 2] if c + 2 < len(row) else None),
                         to_cents(row[c + 3] if c + 3 < len(row) else None),
                         raw(2), raw(3), raw(4), entity == "合计"])
            inserted += 1
    con.execute("INSERT INTO _staging.extraction_manifest VALUES (?,?,?,?,?,?,?,?,?,?)",
                [f"sha256:{src['sha256']}", f"KMDatabase/data/{src['object_path']}",
                 hashlib.sha256(SHEET.encode()).hexdigest()[:12], "_staging.op_key_indicators",
                 inserted, 12, 0, datetime.now(), VERSION, idem])
    bands, indicators = con.execute("SELECT max(band_index)+1, count(DISTINCT indicator) FROM _staging.op_key_indicators").fetchone()
    con.close()
    summary = {"status": "EXTRACTED", "rows": inserted, "bands": bands, "indicators": indicators}
    out = REPO / "KMFA/stage_artifacts/DT5_DATA0007_extract_op_indicators/machine/extract_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"task_id": "TSK.KMFA.DATA.0007", "phase": "2_extract_op_key_indicators",
                                "version": VERSION, **summary}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
