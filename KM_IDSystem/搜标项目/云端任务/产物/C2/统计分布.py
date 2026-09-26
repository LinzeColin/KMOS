"""下浮率分布：按 评标办法 × 项目类型 × 金额档 分组给 P25/P50/P75 与样本数（仅标准库）。

    python3 统计分布.py --样本 本地产出/C2/下浮率样本.csv --输出 本地产出/C2/下浮率分布.csv [--含存疑]
默认只用 质检=ok 的样本。除三维交叉外，还输出每个单维度和"全部"的边际分组（维度值写"(全部)"），
样本不足 5 条的格子在 备注 里标"样本不足"，不要拿来直接定价。
分位数用线性插值（与 numpy 默认、Excel PERCENTILE.INC 一致）。
"""
from __future__ import annotations

import argparse
import csv
import itertools
from pathlib import Path

维度 = ["评标办法", "项目类型", "金额档"]
全 = "(全部)"


def 分位(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def 统计(样本: list[dict]) -> list[dict]:
    组: dict[tuple, list[float]] = {}
    for s in 样本:
        r = float(s["下浮率"])
        for 掩码 in itertools.product([0, 1], repeat=len(维度)):
            键 = tuple(s[d] if m else 全 for d, m in zip(维度, 掩码))
            组.setdefault(键, []).append(r)
    输出 = []
    for 键, xs in 组.items():
        n = len(xs)
        输出.append({
            **dict(zip(维度, 键)),
            "样本数": n,
            "P25": round(分位(xs, 0.25), 4),
            "P50": round(分位(xs, 0.50), 4),
            "P75": round(分位(xs, 0.75), 4),
            "均值": round(sum(xs) / n, 4),
            "备注": "样本不足(<5)，仅供参考" if n < 5 else "",
        })
    输出.sort(key=lambda r: (sum(r[d] == 全 for d in 维度) * -1, r["评标办法"], r["项目类型"], r["金额档"]))
    return 输出


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--样本", required=True, type=Path)
    ap.add_argument("--输出", required=True, type=Path)
    ap.add_argument("--含存疑", action="store_true", help="把 质检=存疑 的样本也算进去（异常样本始终排除）")
    a = ap.parse_args()
    with open(a.样本, encoding="utf-8-sig") as f:
        样本 = [r for r in csv.DictReader(f) if r["质检"] == "ok" or (a.含存疑 and r["质检"].startswith("存疑"))]
    结果 = 统计(样本)
    with open(a.输出, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=维度 + ["样本数", "P25", "P50", "P75", "均值", "备注"])
        w.writeheader()
        w.writerows(结果)
    print(f"纳入样本 {len(样本)} 条，输出分组 {len(结果)} 个 → {a.输出}")


if __name__ == "__main__":
    main()
