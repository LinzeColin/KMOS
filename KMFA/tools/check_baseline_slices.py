#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""业务基线纵向切片：健康渲染 + 耦合治理门禁。

Owner 2026-07-26：「以后我都用 skill 管理业务基线，纵向切片；你要保证每个业务基线
端到端纵向切片运维健康正常，能看到记录，整体架构也要建立耦合治理。」

本工具做三件事：
1. **渲染**每条基线的端到端六段健康（源接入→解析→计算→校验→输出→投递）。
2. **耦合门禁**：上游任一段 blocked_by_*/not_built 时，下游依赖段不得标 healthy——
   否则报错。这条防的是"上游断了、下游还静默出数"这种最危险的假健康。
3. **引用完整性**：upstream 指向的基线/源必须存在。

退出码 0=通过；1=治理违规（CI 用它把关）。
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "machine" / "facts" / "business_baselines.json"
BAD = {"blocked_by_policy", "blocked_by_input", "not_built"}
MARK = {"healthy": "✅", "degraded": "⚠️", "blocked_by_policy": "🚫",
        "blocked_by_input": "⛔", "not_built": "⬚"}


def load():
    return json.loads(FACTS.read_text(encoding="utf-8"))


def check(d):
    fails = []
    stages = [s["id"] for s in d["stage_model"]]
    names = {s["id"]: s["name"] for s in d["stage_model"]}
    bl = {b["id"]: b for b in d["baselines"]}
    src = {s["id"] for s in d["sources"]}
    allowed = set(d["status_enum"])

    for b in d["baselines"]:
        # 段齐全 + 状态合法
        for st in stages:
            if st not in b["stages"]:
                fails.append(f"[{b['id']}] 缺段 {st}({names[st]})")
                continue
            s = b["stages"][st].get("status")
            if s not in allowed:
                fails.append(f"[{b['id']}] {names[st]} 状态非法：{s}")
            if not str(b["stages"][st].get("evidence", "")).strip():
                fails.append(f"[{b['id']}] {names[st]} 缺证据说明")
        # 引用完整性
        for up in b.get("upstream", []):
            if up not in bl and up not in src:
                fails.append(f"[{b['id']}] upstream 指向不存在的 {up}")

    # 耦合门禁：上游有断点 → 下游 compute/verify/output/deliver 不得 healthy
    for b in d["baselines"]:
        broken_ups = []
        for up in b.get("upstream", []):
            u = bl.get(up)
            if not u:
                continue
            bad = [names[st] for st in stages if u["stages"].get(st, {}).get("status") in BAD]
            if bad:
                broken_ups.append(f"{u['name']}({'/'.join(bad)})")
        if broken_ups:
            for st in ("compute", "verify", "output", "deliver"):
                if b["stages"].get(st, {}).get("status") == "healthy":
                    fails.append(
                        f"[{b['id']}] {names[st]} 标 healthy，但上游有断点：{'；'.join(broken_ups)}"
                        f" —— 耦合治理禁止上游断而下游称健康")
    return fails


def render(d):
    stages = [s["id"] for s in d["stage_model"]]
    hdr = "基线".ljust(22) + "".join(s["name"].center(8) for s in d["stage_model"])
    print(hdr)
    print("-" * (22 + 8 * len(stages)))
    for b in sorted(d["baselines"], key=lambda x: x.get("priority", "P9")):
        row = f"{b.get('priority','')} {b['name']}"[:21].ljust(22)
        for st in stages:
            row += MARK.get(b["stages"].get(st, {}).get("status"), "?").center(7)
        print(row)
    print("  图例：✅通　⚠️有缺陷　🚫按规定不通(无需动作)　⛔缺输入待催　⬚未实现")
    print()
    for b in d["baselines"]:
        for dfc in b.get("known_defects", []):
            # 兼容旧的裸字符串写法，但新写法带 ID 供 status 总览线跨线引用
            if isinstance(dfc, dict):
                print(f"  · [{b['name']}] {dfc['id']} {dfc['desc']}")
            else:
                print(f"  · [{b['name']}] {dfc}")


def main():
    if not FACTS.is_file():
        print(f"缺 {FACTS}", file=sys.stderr)
        return 1
    d = load()
    render(d)
    fails = check(d)
    print()
    if fails:
        print(f"FAIL —— 耦合治理 {len(fails)} 项违规")
        for f in fails:
            print("  ✗ " + f)
        return 1
    print(f"PASS —— {len(d['baselines'])} 条业务基线切片登记完整，耦合治理无违规")
    return 0


if __name__ == "__main__":
    sys.exit(main())
