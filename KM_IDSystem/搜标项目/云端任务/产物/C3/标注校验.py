"""校验人工标注并产出 难例.jsonl。

    python3 标注校验.py --待标注 本地产出/C3/待标注.jsonl --输出 本地产出/C3/难例.jsonl [--至少 200]
检查：
  1. 原文片段 ≤200 字；url 以 http 开头；同一 (url, 片段) 不重复
  2. 正确答案每项有 标段/限价元/含税；限价元为 null 时 类型 必须是 "详见文件"
  3. **防编数**：每个非空 限价元 必须能在片段里找到对应写法（阿拉伯数字按元/万元/亿元换算，或大写金额）
  4. 汇总：已标注条数、各难点标签条数；不足 --至少 时退出码 1
只有 标注状态=="已标注" 且通过 1–3 的行写入 难例.jsonl。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from 抽限价 import 大写式, 大写转数, 规整  # noqa: E402


def 片段内金额(片: str) -> set[float]:
    """片段里真实写出的金额：阿拉伯数字只按其后**实际写的单位**换算（万元→×1万、亿元→×1亿、千元→×1千、其余按元），
    表格列头写了"(万元)"时本片段内无单位数字也允许×1万；外加大写金额。"""
    t = 规整(片)
    值 = set()
    for m in 大写式.finditer(t):
        值.add(round(大写转数(m.group()), 2))
    表头万 = bool(re.search(r"\((?:单位:?)?\s*万元\)|单位:?\s*万元", t))
    for m in re.finditer(r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(亿元|亿|万元|万|千元)?", t):
        x = float(m.group(1).replace(",", ""))
        单位 = m.group(2) or ""
        倍 = {"亿元": 1e8, "亿": 1e8, "万元": 1e4, "万": 1e4, "千元": 1e3}.get(单位, 1)
        值.add(round(x * 倍, 2))
        if not 单位 and 表头万:
            值.add(round(x * 1e4, 2))
    return 值


def 校验行(d: dict) -> list[str]:
    错 = []
    片 = d.get("原文片段") or ""
    if len(片) > 200:
        错.append(f"片段 {len(片)} 字 > 200")
    if not str(d.get("url", "")).startswith("http"):
        错.append("url 非 http")
    答 = d.get("正确答案")
    if not isinstance(答, list):
        return 错 + ["正确答案 不是列表"]
    有 = 片段内金额(片)
    for x in 答:
        if not {"标段", "限价元", "含税"} <= set(x):
            错.append(f"答案项缺字段: {x}")
            continue
        if x["限价元"] is None:
            if x.get("类型") != "详见文件":
                错.append("限价元为 null 但 类型 不是 详见文件")
        elif round(float(x["限价元"]), 2) not in 有:
            错.append(f"限价元 {x['限价元']} 在片段里找不到对应写法（疑似编造或换算错）")
    if not d.get("难点标签"):
        错.append("缺难点标签")
    return 错


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--待标注", required=True, type=Path)
    ap.add_argument("--输出", required=True, type=Path)
    ap.add_argument("--至少", type=int, default=200)
    a = ap.parse_args()
    好, 坏, 未标, 见 = [], [], 0, set()
    for 行 in a.待标注.read_text(encoding="utf-8").splitlines():
        if not 行.strip():
            continue
        d = json.loads(行)
        if d.get("标注状态") != "已标注":
            未标 += 1
            continue
        键 = (d.get("url"), d.get("原文片段"))
        错 = 校验行(d) + (["重复"] if 键 in 见 else [])
        见.add(键)
        (坏 if 错 else 好).append((d, 错))
    with open(a.输出, "w", encoding="utf-8") as f:
        for d, _ in 好:
            f.write(json.dumps({k: d[k] for k in ("id", "url", "证据级别", "原文片段", "正确答案", "难点标签", "标注备注") if k in d}, ensure_ascii=False) + "\n")
    标签 = Counter(t for d, _ in 好 for t in d["难点标签"])
    def _规(xs):
        return sorted(((x.get("标段"), x.get("限价元"), x.get("含税")) for x in (xs or [])), key=str)
    同预测 = sum(1 for d, _ in 好 if _规(d.get("正确答案")) == _规(d.get("预测")))
    if 好 and 同预测 / len(好) > 0.9:
        print(f"⚠ {同预测}/{len(好)} 条答案与抽取器预测完全相同——疑似照抄预测，评测将失去意义，请抽查")
    print(json.dumps({"通过": len(好), "不通过": len(坏), "未标注": 未标, "按难点": dict(标签.most_common())}, ensure_ascii=False, indent=1))
    for d, 错 in 坏[:30]:
        print("✗", d.get("id"), "；".join(错))
    if len(好) < a.至少:
        print(f"未达标：通过 {len(好)} 条 < {a.至少}")
        sys.exit(1)


if __name__ == "__main__":
    main()
