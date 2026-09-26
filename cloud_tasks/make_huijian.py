#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 C4/、C5/ 目录打成 KM00 取件格式的 回件/C<号>.txt（README.md 必须第一个）。
用法：python3 make_huijian.py      # 重新生成 回件/C4.txt、回件/C5.txt
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = {"C4": ["README.md", "人工单价.csv", "labor_cost.py"],
         "C5": ["README.md", "类别标量.csv", "样例公告.csv", "tender_volume.py"]}


def build(task):
    parts = []
    for name in ORDER[task]:
        body = open(os.path.join(HERE, task, name), encoding="utf-8-sig").read().rstrip("\n")
        if "```" in body:
            raise SystemExit(f"{task}/{name} 含 ``` 会破坏代码块切分")
        parts.append(f"=== 文件: {name} ===\n```\n{body}\n```\n")
    return "\n".join(parts)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "回件"), exist_ok=True)
    for t in ORDER:
        out = os.path.join(HERE, "回件", f"{t}.txt")
        open(out, "w", encoding="utf-8").write(build(t))
        print(out)
