"""在难例集上评测 抽限价()，按难点标签分组报准确率。

    python3 评测.py 难例.jsonl            # 真实难例（字段：原文片段 / 正确答案 / 难点标签）
    python3 评测.py 构造样例.jsonl        # 构造样例（字段：原文 / 答案 / 标签）
    python3 评测.py 难例.jsonl --错例 20  # 另外打印前 20 个错例

判定：一条难例"对" = 抽出的 (标段, 限价元, 含税) 集合与答案集合完全相同。
限价元允许 0.01 元误差；"详见文件"按 (标段, None, None) 比。
另报条目级 精确率 / 召回率。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from 抽限价 import 抽限价  # noqa: E402


def 规范(项: dict) -> tuple:
    值 = 项.get("限价元")
    return (项.get("标段"), None if 值 is None else round(float(值), 2), 项.get("含税"))


def 读(路径: Path) -> list[dict]:
    行们 = []
    for x in 路径.read_text(encoding="utf-8").splitlines():
        if not x.strip():
            continue
        d = json.loads(x)
        行们.append({
            "id": d.get("id") or d.get("url"),
            "原文": d.get("原文片段") or d.get("原文") or "",
            "答案": d.get("正确答案") if "正确答案" in d else d.get("答案", []),
            "标签": d.get("难点标签") or d.get("标签") or [],
        })
    return 行们


def 评测(行们: list[dict]) -> dict:
    组 = defaultdict(lambda: [0, 0])
    tp = fp = fn = 0
    错例 = []
    for r in 行们:
        预测 = {规范(x) for x in 抽限价(r["原文"])}
        答案 = {规范(x) for x in r["答案"]}
        对 = 预测 == 答案
        for t in list(r["标签"]) + ["全部"]:
            组[t][0] += 对
            组[t][1] += 1
        tp += len(预测 & 答案)
        fp += len(预测 - 答案)
        fn += len(答案 - 预测)
        if not 对:
            错例.append({"id": r["id"], "标签": r["标签"], "原文": r["原文"][:200], "多抽": sorted(map(str, 预测 - 答案)), "漏抽": sorted(map(str, 答案 - 预测))})
    return {
        "分组准确率": {k: {"对": v[0], "总": v[1], "准确率": round(v[0] / v[1], 4)} for k, v in sorted(组.items(), key=lambda kv: (kv[0] != "全部", kv[0]))},
        "条目精确率": round(tp / (tp + fp), 4) if tp + fp else None,
        "条目召回率": round(tp / (tp + fn), 4) if tp + fn else None,
        "错例": 错例,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("文件", type=Path)
    ap.add_argument("--错例", type=int, default=0)
    a = ap.parse_args()
    结果 = 评测(读(a.文件))
    错例 = 结果.pop("错例")
    print(json.dumps(结果, ensure_ascii=False, indent=1))
    for e in 错例[: a.错例]:
        print(json.dumps(e, ensure_ascii=False))


if __name__ == "__main__":
    main()
