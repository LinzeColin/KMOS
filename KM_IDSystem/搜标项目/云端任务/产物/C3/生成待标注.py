"""从已抓取的公告原文里切出"难抽"的限价片段（≤200 字），自动打难点标签并预填抽取器结果。

    python3 生成待标注.py --缓存 本地产出/C3原文 --输出 本地产出/C3/待标注.jsonl
每行：{"id","url","证据级别","原文片段","难点标签","预测","正确答案":null,"标注状态":"待标注"}
标注人要**独立**读片段填 正确答案（别照抄 预测），填完把 标注状态 改成 "已标注"，再跑 标注校验.py。
一个公告最多出 3 个片段；没有任何难点标签的片段不收（简单样例不进难例库）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 依赖既可与本目录平级（仓库布局 产物/公共、产物/C3），也可在本目录内（回件切件后 C2/公共、C2/抽限价.py）
for _p in (HERE.parent / "C3", HERE.parent / "公共", HERE / "公共", HERE):
    if _p.is_dir():
        sys.path.insert(0, str(_p))
from 抽限价 import 大写式, 标段式, 抽限价, 规整, 详见式, 限价词, 预算词, 单价词, _税式  # noqa: E402
from 抓取 import 读正文, 读索引  # noqa: E402

关键式 = re.compile("|".join(re.escape(w) for w in sorted(限价词 + 预算词 + 单价词, key=len, reverse=True)))


def 打标签(片段: str) -> list[str]:
    标 = []
    段 = {m.group(0) for m in 标段式.finditer(片段)}
    if len(段) >= 2:
        标.append("multi_lot")
    if 大写式.search(片段):
        标.append("capital")
    if re.search(r"\d\s*万元?", 片段) and re.search(r"\d\s*元", 片段.replace("万元", "")):
        标.append("unit_mix")
    if _税式.search(片段):
        标.append("tax")
    if re.search(详见式, 片段):
        标.append("see_doc")
    if any(w in 片段 for w in 预算词) and any(w in 片段 for w in 限价词):
        标.append("budget_vs_cap")
    if re.search(r"元\s*/\s*[一-龥a-zA-Z²³]", 片段):
        标.append("unit_price")
    if re.search(r"^\|.*\|$", 片段, re.M):
        标.append("table")
    return 标


def 切片段(t: str, 最长: int = 200) -> list[str]:
    """以关键词簇为中心切 ≤最长 字的片段；相邻关键词尽量放进同一片段（多标段要完整）。"""
    位 = [m.start() for m in 关键式.finditer(t)]
    # 表头行也算锚点
    位 += [m.start() for m in re.finditer(r"^\|[^\n]*(?:限价|控制价|预算)[^\n]*\|$", t, re.M)]
    位.sort()
    片段们, i = [], 0
    while i < len(位):
        起 = max(0, 位[i] - 30)
        止 = 起 + 最长
        while i < len(位) and 位[i] < 止 - 20:
            i += 1
        片 = t[起:止].strip()
        if 片:
            片段们.append(片)
    return 片段们


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--缓存", required=True, type=Path)
    ap.add_argument("--输出", required=True, type=Path)
    ap.add_argument("--每篇最多", type=int, default=3)
    a = ap.parse_args()
    a.输出.parent.mkdir(parents=True, exist_ok=True)
    计 = {"公告": 0, "片段": 0}
    with open(a.输出, "w", encoding="utf-8") as f:
        for url, 记录 in 读索引(a.缓存).items():
            if 记录["状态"] != "ok":
                continue
            t = 规整(读正文(a.缓存, url) or "")
            计["公告"] += 1
            n = 0
            for 片 in 切片段(t):
                标 = 打标签(片)
                if not 标:
                    continue
                预测 = 抽限价(片)
                f.write(json.dumps({
                    "id": hashlib.sha1((url + 片).encode()).hexdigest()[:12], "url": url, "证据级别": "一手(公告原文页面)",
                    "原文片段": 片, "难点标签": 标,
                    "预测": [{k: x[k] for k in ("标段", "限价元", "含税", "类型", "单位")} for x in 预测],
                    "正确答案": None, "标注状态": "待标注", "标注备注": "",
                }, ensure_ascii=False) + "\n")
                n += 1
                计["片段"] += 1
                for t_ in 标:
                    计[t_] = 计.get(t_, 0) + 1
                if n >= a.每篇最多:
                    break
    print(json.dumps(计, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
