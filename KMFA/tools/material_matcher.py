#!/usr/bin/env python3
"""材料轴凭证匹配引擎（DT5_DATA0029-0032 的机械化固化，可复跑）。

三层匹配（凭证粒度 = 月 + 规范化凭证号）。`--side receipt`（默认）：收发收入 vs 金蝶 1401/1403 **借方**；
`--side issue`：收发发出（领料出库）vs 金蝶 1401/1403 **贷方**（他科目探针相应取贷方池）。
  L1 全额等；L2 子集和（金蝶部分行之和 = 收发合计）；L3 双向差额定位（两侧合计差 = 对侧单行/行子集）。
两项假设探针随跑随记：同月异号金额全等（重编号）、缺口在其他科目（分流——曾定量否定，保留探针防回归）。
组合穷举上限 18 行（超限如实计数）。输出机器摘要 JSON；自带 --selftest（合成数据覆盖三层与探针）。
用法：python3 KMFA/tools/material_matcher.py [--side receipt|issue] [--edition d46f77b0] [--from 2025-01-01 --to 2025-11-01] [--out <json>]
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"
BOOKS = ("湖北开明", "武汉开明")
COMBO_CAP = 18


def subset_hit(target: int, lines: list[int], cap: int = COMBO_CAP) -> bool | None:
    """target 是否为 lines 的非空子集和；行数超限返回 None（未试）。"""
    if target <= 0:
        return False
    if len(lines) > cap:
        return None
    return any(sum(c) == target for r in range(1, len(lines) + 1) for c in combinations(lines, r))


def match_groups(gmap, kmat, kother):
    """核心匹配。gmap: {(mo,v): [收发行分]}；kmat: {(book,mo,v): [材料借方行分]}；
    kother: {(book,mo,v): [(科目根, 行分)]}。返回逐组判定与汇总。"""
    stats = {"L1_全额等": 0, "L2_子集和": 0, "L3_双向差额": 0, "超限未试": 0,
             "同月异号": 0, "他科目命中": 0, "未解": 0}
    month_amounts = {}
    for (book, mo, v), lines in kmat.items():
        month_amounts.setdefault(mo, {}).setdefault(sum(lines), []).append((book, v))
    verdicts = []
    for (mo, v), gl in sorted(gmap.items()):
        g_amt = sum(gl)
        verdict = None
        for book in BOOKS:
            ls = kmat.get((book, mo, v), [])
            if not ls:
                continue
            if sum(ls) == g_amt:
                verdict = ("L1_全额等", book)
                break
            s = subset_hit(g_amt, ls)
            if s is None:
                verdict = ("超限未试", book)
                break
            if s:
                verdict = ("L2_子集和", book)
                break
        if verdict is None or verdict[0] == "超限未试":
            for book in BOOKS:
                ls = kmat.get((book, mo, v), [])
                if not ls:
                    continue  # 金蝶无材料行时差额=收发全额，membership 恒真——必须跳过
                d = g_amt - sum(ls)
                if d > 0 and (d in gl or subset_hit(d, gl)):
                    verdict = ("L3_双向差额", book)
                    break
                if d < 0 and (-d in ls or subset_hit(-d, ls)):
                    verdict = ("L3_双向差额", book)
                    break
        if verdict is None:
            others = [x for x in month_amounts.get(mo, {}).get(g_amt, []) if x[1] != v]
            if others:
                verdict = ("同月异号", others[0][0])
        if verdict is None:
            for book in BOOKS:
                ls = kmat.get((book, mo, v), [])
                d = g_amt - sum(ls) if ls else g_amt
                if d <= 0:
                    continue
                pool = kother.get((book, mo, v), [])
                if any(a == d for _, a in pool) or subset_hit(d, [a for _, a in pool]):
                    verdict = ("他科目命中", book)
                    break
        if verdict is None:
            verdict = ("未解", None)
        stats[verdict[0]] += 1
        verdicts.append({"mo": mo, "voucher": v, "amount_cents": g_amt,
                         "layer": verdict[0], "book": verdict[1]})
    return stats, verdicts


def load_from_db(edition: str, dfrom: str, dto: str, side: str = "receipt"):
    import duckdb
    sys.path.insert(0, str(REPO))
    from KMFA.tools.recon_common import normalize_voucher_no
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.create_function("norm_vno", normalize_voucher_no, ["VARCHAR"], "VARCHAR", null_handling="special")
    amount_col = "receipt_amount_cents" if side == "receipt" else "issue_amount_cents"
    gmap = {}
    for mo, v, a in con.execute(
            f"""SELECT strftime(move_date,'%Y-%m'), norm_vno(voucher_no), {amount_col}
               FROM _staging.goods_movement
               WHERE source_sha8=? AND move_date>=? AND move_date<?
                 AND coalesce({amount_col},0)<>0 AND voucher_no IS NOT NULL""",
            [edition, dfrom, dto]).fetchall():
        gmap.setdefault((mo, v), []).append(a)
    k_col = "debit_cents" if side == "receipt" else "credit_cents"
    kmat, kother = {}, {}
    for book, mo, v, subj, a in con.execute(
            f"""SELECT book, strftime(entry_date,'%Y-%m'), norm_vno(voucher_no),
                      split_part(subject_sheet,'_',1)[:4], coalesce({k_col},0)
               FROM _staging.kingdee_ledger
               WHERE row_kind='detail' AND coalesce({k_col},0)>0""").fetchall():
        key = (book, mo, v)
        if subj in ("1401", "1403"):
            kmat.setdefault(key, []).append(a)
        else:
            kother.setdefault(key, []).append((subj, a))
    con.close()
    return gmap, kmat, kother


def _selftest() -> int:
    gmap = {
        ("2025-01", "记-1"): [100, 200],            # L1：全额等
        ("2025-01", "记-2"): [300],                 # L2：子集和（500 中取 300）
        ("2025-01", "记-3"): [400, 50],             # L3：收发多 50（差=收发单行）
        ("2025-01", "记-4"): [700],                 # 同月异号（记-9 同额）
        ("2025-01", "记-5"): [130],                 # 他科目命中（缺口 30 在 2221）
        ("2025-01", "记-6"): [999],                 # 未解
    }
    kmat = {
        ("湖北开明", "2025-01", "记-1"): [100, 200],
        ("湖北开明", "2025-01", "记-2"): [300, 200],
        ("湖北开明", "2025-01", "记-3"): [400],
        ("湖北开明", "2025-01", "记-9"): [700],
        ("湖北开明", "2025-01", "记-5"): [100],
        ("湖北开明", "2025-01", "记-6"): [1],
    }
    kother = {("湖北开明", "2025-01", "记-5"): [("2221", 30)]}
    stats, _ = match_groups(gmap, kmat, kother)
    expect = {"L1_全额等": 1, "L2_子集和": 1, "L3_双向差额": 1, "超限未试": 0,
              "同月异号": 1, "他科目命中": 1, "未解": 1}
    assert stats == expect, f"selftest 失败: {stats}"
    assert subset_hit(5, list(range(1, 25))) is None
    print("selftest: 全部通过")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--side", choices=("receipt", "issue"), default="receipt")
    parser.add_argument("--edition", default="d46f77b0")
    parser.add_argument("--from", dest="dfrom", default="2025-01-01")
    parser.add_argument("--to", dest="dto", default="2025-11-01")
    parser.add_argument("--out", default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return _selftest()

    gmap, kmat, kother = load_from_db(args.edition, args.dfrom, args.dto, args.side)
    stats, verdicts = match_groups(gmap, kmat, kother)
    total = len(verdicts)
    matched = stats["L1_全额等"] + stats["L2_子集和"] + stats["L3_双向差额"]
    summary = {
        "task_id": "TSK.KMFA.DATA.0007", "phase": "material_matcher",
        "side": args.side, "edition": args.edition, "window": [args.dfrom, args.dto],
        "voucher_groups": total, "matched": matched,
        "match_rate": f"{matched}/{total}",
        "stats": stats,
        "unresolved_amount_cents": sum(v["amount_cents"] for v in verdicts if v["layer"] == "未解"),
    }
    default_out = f"KMFA/stage_artifacts/DT5_DATA0033_material_matcher_tool/machine/match_summary_{args.side}.json"
    out = REPO / (args.out or default_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
