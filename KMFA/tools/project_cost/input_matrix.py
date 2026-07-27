#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目成本输入矩阵：渲染 + 门禁。

Owner 2026-07-26：「输入都是固定的，如果输入缺失需要明确矩阵表格方式标注提醒我上传」。

固定输入 = 技能 `skills/项目成本表/config/input_manifest.template.yml` 声明的八个槽位，
不是本文件杜撰的。事实源 `machine/facts/project_cost_input_matrix.json`。

门禁意图（为什么不是普通渲染脚本）：
  一份说"都齐了"的矩阵表比没有矩阵表更危险——它会让人以为可以出正式结论。
  所以凡是 status 不等于 ready 的槽位，必须写清楚要 Owner 上传什么（`ask` 不得为空），
  且必须写清楚缺了会挡住报表哪几行（`blocks_rows` 不得为空）。
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

STATUS_LABEL = {
    "ready": "就绪",
    "ready_for_direct_cost": "直接成本就绪",
    "partial": "部分",
    "missing": "缺失",
}
# 只有 ready 算"无需 Owner 动作"；其余一律必须给出上传指引。
SELF_SUFFICIENT = {"ready"}


def load(root: Path) -> dict:
    p = root / "machine" / "facts" / "project_cost_input_matrix.json"
    return json.loads(p.read_text(encoding="utf-8"))


def check(data: dict) -> list[str]:
    """返回问题清单；空列表代表通过。"""
    errs: list[str] = []
    slots = data.get("slots") or []
    if not slots:
        errs.append("矩阵没有任何槽位——输入契约丢失")
    seen = set()
    for s in slots:
        name = s.get("slot") or "<未命名>"
        if name in seen:
            errs.append(f"{name}：槽位重复")
        seen.add(name)
        st = s.get("status")
        if st not in STATUS_LABEL:
            errs.append(f"{name}：status『{st}』不在允许集合 {sorted(STATUS_LABEL)}")
            continue
        if not s.get("blocks_rows"):
            errs.append(f"{name}：没写缺了会挡住报表哪几行（blocks_rows 为空）")
        if st not in SELF_SUFFICIENT and not s.get("ask"):
            errs.append(f"{name}：status={st} 却没写要 Owner 上传什么（ask 为空）——这正是本门禁要拦的")
        if st not in SELF_SUFFICIENT and s.get("priority") in (None, "", "—"):
            errs.append(f"{name}：status={st} 却没有优先级")
    for g in data.get("cross_cutting_gaps") or []:
        if not g.get("ask"):
            errs.append(f"跨槽位缺口 {g.get('id')}：没写要确认什么")
    return errs


def to_markdown(data: dict) -> str:
    rows = ["| 输入槽位 | 现状 | 已有 | 缺什么 | 缺了挡住报表哪几行 | 要你上传/确认 | 优先级 |",
            "|---|---|---|---|---|---|---|"]
    for s in data.get("slots", []):
        rows.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            s.get("label", s.get("slot", "")),
            STATUS_LABEL.get(s.get("status"), s.get("status", "")),
            s.get("have", "") or "—",
            s.get("gap", "") or "无",
            "；".join(s.get("blocks_rows") or []) or "—",
            s.get("ask") or "—",
            s.get("priority") or "—",
        ))
    out = [f"# 项目成本输入矩阵（截至 {data.get('as_of','')}）", "", data.get("purpose", ""), "",
           "\n".join(rows)]
    gaps = data.get("cross_cutting_gaps") or []
    if gaps:
        out += ["", "## 跨槽位缺口", "",
                "| 缺口 | 影响 | 要你确认 | 优先级 |", "|---|---|---|---|"]
        for g in gaps:
            out.append("| {} | {} | {} | {} |".format(
                g.get("label", ""), g.get("impact", ""), g.get("ask", ""), g.get("priority", "")))
    ev = data.get("evidence_runs") or []
    if ev:
        out += ["", "## 判据（都是真跑出来的，不是估的）", ""]
        for e in ev:
            out.append(f"- **{e.get('what','')}** —— {e.get('finding','')}")
    return "\n".join(out) + "\n"


def to_csv(data: dict) -> str:
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["输入槽位", "现状", "已有", "缺什么", "缺了挡住报表哪几行", "要你上传/确认", "优先级"])
    for s in data.get("slots", []):
        w.writerow([s.get("label", ""), STATUS_LABEL.get(s.get("status"), ""), s.get("have", ""),
                    s.get("gap", ""), "；".join(s.get("blocks_rows") or []), s.get("ask") or "",
                    s.get("priority") or ""])
    w.writerow([])
    w.writerow(["跨槽位缺口", "影响", "要你确认", "优先级"])
    for g in data.get("cross_cutting_gaps") or []:
        w.writerow([g.get("label", ""), g.get("impact", ""), g.get("ask", ""), g.get("priority", "")])
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description="项目成本输入矩阵：渲染与门禁")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--out-dir", default=None, help="给定则写出 markdown 与 csv")
    a = ap.parse_args()
    root = Path(a.root)
    data = load(root)
    errs = check(data)
    if errs:
        print("FAIL —— 输入矩阵不合格：")
        for e in errs:
            print("  ·", e)
        return 1
    if a.out_dir:
        outd = Path(a.out_dir)
        outd.mkdir(parents=True, exist_ok=True)
        (outd / "项目成本输入矩阵.md").write_text(to_markdown(data), encoding="utf-8")
        (outd / "项目成本输入矩阵.csv").write_text(to_csv(data), encoding="utf-8-sig")
        print(f"✓ 已写出 {outd}")
    n = len(data.get("slots", []))
    blocked = [s for s in data["slots"] if s.get("status") != "ready"]
    print(f"PASS —— {n} 个输入槽位登记完整；需 Owner 动作 {len(blocked)} 个："
          + "、".join(s.get("label", "") for s in blocked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
