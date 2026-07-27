#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""科目→报表行 映射：加载、校验、按项目汇总。

为什么单独成一张表而不是写死在代码里：
  这是业务判定（Owner 已授权 agent 拍板），业务随时可能纠正。写在事实文件里，
  改一行就生效、且改动看得见；写在代码里就成了埋在实现细节中的隐形口径。

门禁拦的四件事：
  1. 映射到一个模板里不存在的行——那笔钱会被静默丢掉，报表还看着正常；
  2. 同一科目登记两次——会重复计入；
  3. 把握不足却不写理由——以后没人知道这行为什么这么归；
  4. 报表某一行无人认领——既没人往里填，也没说它是上卷/派生/算不出。

真正的覆盖率检查（账上出现的每个子科目都必须已登记）在私有库的计算作业里做，
因为科目全集要读真账。`summarize()` 遇到未登记科目会抛错，绝不静默丢弃。
"""
from __future__ import annotations
import argparse, json, sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_report import TPL_A, TPL_B  # noqa: E402

VALID_CONFIDENCE = {"high", "medium", "low"}
TEMPLATES = {"A": TPL_A, "B": TPL_B}


def load(root: Path) -> dict:
    return json.loads((root / "machine" / "facts" / "project_cost_account_map.json")
                      .read_text(encoding="utf-8"))


def _template_rows(tpl: str | None = None) -> set[str]:
    """tpl 为空时返回两套模板的并集；给定 A/B 时只返回该模板的行。"""
    if tpl:
        return {label for label, _ in TEMPLATES[tpl]}
    return {label for label, _ in TPL_A} | {label for label, _ in TPL_B}


def check(data: dict) -> list[str]:
    errs: list[str] = []
    rows = _template_rows()
    seen: set[str] = set()
    maps = data.get("mappings") or []
    if not maps:
        errs.append("映射表是空的——按项目算出来的钱无处可填")
    for m in maps:
        acct = m.get("account", "<空>")
        if acct in seen:
            errs.append(f"{acct}：科目重复登记，会被重复计入")
        seen.add(acct)
        rows_by_tpl = m.get("rows") or {}
        if set(rows_by_tpl) != set(TEMPLATES):
            errs.append(f"{acct}：必须同时给出 A/B 两套模板的落点（现有 {sorted(rows_by_tpl)}）"
                        "——只写一套，另一套版式的报表会让这笔钱无处可归、直接蒸发")
            continue
        for tpl, spec in rows_by_tpl.items():
            row = spec.get("row")
            if row not in _template_rows(tpl):
                errs.append(f"{acct}：模板 {tpl} 的目标行『{row}』在该模板里不存在——这笔钱会被静默丢掉")
            conf = spec.get("confidence")
            if conf not in VALID_CONFIDENCE:
                errs.append(f"{acct}（模板 {tpl}）：confidence『{conf}』不在 {sorted(VALID_CONFIDENCE)}")
            elif conf in ("medium", "low") and not spec.get("note"):
                errs.append(f"{acct}（模板 {tpl}）：把握是 {conf} 却没写理由")

    for u in data.get("unmappable_rows") or []:
        if not u.get("why"):
            errs.append(f"不可映射行『{u.get('row')}』没写原因")
        if u.get("row") not in rows:
            errs.append(f"不可映射行『{u.get('row')}』在模板里不存在——登记了一个不存在的行")
    for d in data.get("derived_rows") or []:
        if not d.get("how"):
            errs.append(f"派生行『{d.get('row')}』没写怎么算出来的")
        if d.get("row") not in rows:
            errs.append(f"派生行『{d.get('row')}』在模板里不存在")
    for r in data.get("rolled_up_rows") or []:
        if not r.get("from"):
            errs.append(f"上卷行『{r.get('row')}』没写从哪几行汇总来的")
        if r.get("row") not in rows:
            errs.append(f"上卷行『{r.get('row')}』在模板里不存在")

    # 闭环：两套模板各自的每一行都必须有交代。一行没交代，就是一行钱可能被忘掉。
    other = ({u.get("row") for u in data.get("unmappable_rows") or []}
             | {d.get("row") for d in data.get("derived_rows") or []}
             | {r.get("row") for r in data.get("rolled_up_rows") or []})
    for tpl in TEMPLATES:
        mapped = {m["rows"][tpl]["row"] for m in maps if isinstance(m.get("rows"), dict)
                  and tpl in m["rows"]}
        for label in sorted(_template_rows(tpl)):
            if label not in mapped | other:
                errs.append(f"模板 {tpl} 的行『{label}』既没有科目映射、也不是上卷行/派生行、"
                            "也没声明算不出——无人认领")
        for label in sorted(mapped & {u.get("row") for u in data.get("unmappable_rows") or []}):
            errs.append(f"模板 {tpl} 的行『{label}』既被映射又被声明算不出，自相矛盾")
    return errs


def summarize(data: dict, account_amounts: dict[str, str | Decimal],
              template: str = "A") -> dict[str, Decimal]:
    """把 {科目: 金额} 汇总成 {报表行: 金额}。必须指定模板——两套版式行集不同。

    遇到未登记科目直接抛错，不静默丢钱。
    """
    table = {m["account"]: m["rows"][template]["row"] for m in data.get("mappings", [])}
    out: dict[str, Decimal] = {}
    unknown = [a for a in account_amounts if a not in table]
    if unknown:
        raise KeyError(f"这些科目没在映射表里登记，拒绝静默丢弃：{sorted(unknown)}")
    for acct, amt in account_amounts.items():
        row = table[acct]
        out[row] = out.get(row, Decimal(0)) + Decimal(str(amt))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="科目→报表行 映射门禁")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    a = ap.parse_args()
    data = load(Path(a.root))
    errs = check(data)
    if errs:
        print("FAIL —— 科目映射不合格：")
        for e in errs:
            print("  ·", e)
        return 1
    maps = data["mappings"]
    low = [m for m in maps for t in TEMPLATES if m["rows"][t]["confidence"] != "high"]
    print(f"PASS —— {len(maps)} 个成本子科目 × 两套模板已映射到报表行；"
          f"其中 {len(low)} 个落点把握不足待业务纠正")
    print(f"        {len(data.get('rolled_up_rows', []))} 行由下级上卷、"
          f"{len(data.get('derived_rows', []))} 行由公式派生、"
          f"{len(data.get('unmappable_rows', []))} 行现阶段算不出（已具名原因）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
