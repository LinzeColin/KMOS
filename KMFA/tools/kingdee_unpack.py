#!/usr/bin/env python3
"""金蝶明细账 zip 安全解包与覆盖矩阵（TSK.KMFA.DATA.0009 阶段一）。

- 安全解包（拒绝绝对路径/上级穿越）到 .codex_private_runtime/kingdee_unpack/（不 tracked）
- 从成员文件名机械解析 账套×期间 覆盖矩阵（public-safe：账套名/期间/成员类型/sheet 数）
- 输出 stage_artifacts/DT5_DATA0009_kingdee_matrix/machine/coverage_matrix.json

用法：python3 KMFA/tools/kingdee_unpack.py
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRIV = REPO / "KMFA" / ".codex_private_runtime" / "kingdee_unpack"


def sheet_count(path: Path) -> int:
    if path.suffix.lower() == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True)
        n = len(wb.sheetnames)
        wb.close()
        return n
    import xlrd
    wb = xlrd.open_workbook(str(path), on_demand=True)
    n = wb.nsheets
    wb.release_resources()
    return n


def main() -> int:
    man = [json.loads(l) for l in (REPO / "KMDatabase/data/manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    src = [r for r in man if "金蝶" in r["original_name"]][0]
    zip_path = REPO / "KMDatabase/data" / src["object_path"]
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            parts = Path(info.filename).parts
            if info.filename.startswith("/") or ".." in parts:
                raise SystemExit(f"zip 安全规则拒绝: {info.filename}")
        PRIV.mkdir(parents=True, exist_ok=True)
        zf.extractall(PRIV)

    entries = []
    for p in sorted(q for q in PRIV.rglob("*") if q.is_file() and q.suffix.lower() in (".xls", ".xlsx")):
        name = p.name
        stem = re.split(r"[-_0-9]", name)[0].strip()
        for suffix in ("公司明细账", "明细账", "公司凭证", "凭证", "建设公司", "公司"):
            if stem.endswith(suffix) and len(stem) > len(suffix):
                stem = stem[: -len(suffix)]
                break
        book = stem.strip()
        kind = "detail_ledger" if "明细账" in name else ("voucher_list" if "凭证" in name else "other")
        period = re.search(r"(20\d{2}).{0,3}第?\s*(\d+)\s*期?\s*至\s*第?\s*(20\d{2})?年?第?(\d+)期?", name)
        period_label = period.group(0) if period else re.search(r"2\d[\d.\-年月至]+", name).group(0) if re.search(r"2\d[\d.\-年月至]+", name) else "?"
        entries.append({
            "book": book, "kind": kind, "format": p.suffix.lstrip("."),
            "period_label": period_label, "sheet_count": sheet_count(p),
            "size_bytes": p.stat().st_size,
        })

    books = sorted({e["book"] for e in entries})
    matrix = {
        "task_id": "TSK.KMFA.DATA.0009", "phase": "1_unpack_and_matrix",
        "source_sha8": src["sha256"][:8], "members": len(entries),
        "books": books,
        "coverage": [{"book": b,
                       "detail_ledger": next((e for e in entries if e["book"] == b and e["kind"] == "detail_ledger"), None) is not None,
                       "voucher_list": next((e for e in entries if e["book"] == b and e["kind"] == "voucher_list"), None) is not None}
                      for b in books],
        "entries": entries,
        "structure_note": "明细账=每科目一 sheet（单账套 2,811 sheet 实测）；表头固定第 3 行：科目/客户/职员/供应商/部门/销售合同号/研发项目/往来/日期/凭证字号/摘要/借方/贷方/方向/余额（以侦察记录为准）",
        "next": "阶段二：kingdee 规格接入 staging_extract（海量 sheet 流式抽取）+ 借贷平衡初检 + 与 bank_journal 交叉盘点",
    }
    out = REPO / "KMFA/stage_artifacts/DT5_DATA0009_kingdee_matrix/machine/coverage_matrix.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"members": len(entries), "books": books}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
