"""把 产物/ 与 本地产出/ 打成 KM00 取件格式的 回件/C<号>.txt（仅标准库）。

    python3 打包回件.py            # 生成 回件/C1.txt C2.txt C3.txt
    python3 打包回件.py --只 C2    # 只打一个
格式（KM00 自动切件，别改）：第一个文件是 README.md；每个文件上一行写 `=== 文件: <文件名> ===`，内容放在一个代码块里。
本地跑出真实数据后（本地产出/C<号>/…）再打一次，数据文件会自动并入/替换初版。
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
产物 = ROOT / "产物"
本地 = ROOT / "本地产出"

公共 = ["公共/抓取.py", "公共/网页文本.py", "公共/列表抽链接.py"]
清单 = {
    # (回件里的文件名, 源路径)；本地产出同名文件优先
    "C1": [("README.md", "C1/README.md"), ("平台普查.csv", "C1/平台普查.csv"), ("平台探测.py", "C1/平台探测.py"), ("生成普查初版.py", "C1/生成普查初版.py"),
           ("搜索记录/集团平台.jsonl", "C1/搜索记录/集团平台.jsonl"), ("搜索记录/省级与全国平台.jsonl", "C1/搜索记录/省级与全国平台.jsonl")] + [(p, p) for p in 公共],
    "C2": [("README.md", "C2/README.md"), ("下浮率样本.csv", None), ("下浮率分布.csv", None), ("候选链接.jsonl", "C2/候选链接.jsonl"),
           ("解析结果.py", "C2/解析结果.py"), ("统计分布.py", "C2/统计分布.py"), ("抽限价.py", "C3/抽限价.py")] + [(p, p) for p in 公共],
    "C3": [("README.md", "C3/README.md"), ("难例.jsonl", None), ("抽限价.py", "C3/抽限价.py"), ("评测.py", "C3/评测.py"),
           ("test_抽限价.py", "C3/test_抽限价.py"), ("构造样例.jsonl", "C3/构造样例.jsonl"), ("盲测样例.jsonl", "C3/盲测样例.jsonl"), ("复审刁钻样例.jsonl", "C3/复审刁钻样例.jsonl"),
           ("候选链接.jsonl", "C3/候选链接.jsonl"), ("生成待标注.py", "C3/生成待标注.py"), ("标注校验.py", "C3/标注校验.py")] + [(p, p) for p in 公共],
}
语言 = {".py": "python", ".md": "markdown", ".csv": "csv", ".jsonl": "json"}


def 打包(号: str) -> tuple[Path, list[str], list[str]]:
    块, 收, 缺 = [], [], []
    for 名, 源 in 清单[号]:
        本地版 = 本地 / 号 / 名
        p = 本地版 if 本地版.exists() else (产物 / 源 if 源 else None)
        if p is None or not p.exists():
            缺.append(名)
            continue
        内容 = p.read_text(encoding="utf-8-sig")
        最长 = max([len(m) for m in re.findall(r"`{3,}", 内容)] + [2])
        围 = "`" * (最长 + 1)
        块.append(f"=== 文件: {名} ===\n{围}{语言.get(p.suffix, '')}\n{内容.rstrip()}\n{围}\n")
        收.append(名 + ("（本地产出）" if p == 本地版 else ""))
    出 = ROOT / "回件" / f"{号}.txt"
    出.parent.mkdir(exist_ok=True)
    出.write_text("\n".join(块), encoding="utf-8")
    return 出, 收, 缺


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--只", choices=list(清单))
    a = ap.parse_args()
    for 号 in [a.只] if a.只 else 清单:
        出, 收, 缺 = 打包(号)
        print(f"{号}: {出.relative_to(ROOT)}  {len(收)} 个文件  {出.stat().st_size // 1024} KB")
        if 缺:
            print(f"    尚缺（本地跑完后再打包）：{', '.join(缺)}")


if __name__ == "__main__":
    main()
