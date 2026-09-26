"""从任意公告列表页抽取候选公告链接（仅标准库），追加到候选链接 jsonl（按 url 去重）。

    # C2：抽中标/成交结果里的维修类
    python3 列表抽链接.py --列表页 "https://站点/jyxx/zbjg/index_{页}.html" --页 1-20 \
        --必含 "中标|成交|候选人|结果" --且含 "检修|维修|大修|维保|修复|安装|改造|技改|探伤|检测" \
        --输出 ../C2/候选链接.jsonl
    # C3：抽招标公告（任意行业，后续由 生成待标注.py 挑难例）
    python3 列表抽链接.py --列表页 "https://站点/list?page={页}" --页 1-10 --必含 "招标|采购|比选|询价" --排除 "结果|中标|成交" --输出 ../C3/候选链接.jsonl
--列表页 里的 {页} 会被 --页 范围逐个替换；不含 {页} 就只抓这一页。也可用 --列表文件 每行一个列表页 URL。
只能处理"静态 HTML 列表"；遇到 JS 渲染/反爬，会打印抓取状态，别当成"没有公告"。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from 抓取 import 抓一个, 识别障碍  # noqa: E402
from 网页文本 import 解码, 转文本  # noqa: E402


class _A(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href = None
        self._buf: list[str] = []
        self._title = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            a = dict(attrs)
            self._href = a.get("href")
            self._title = a.get("title") or ""
            self._buf = []

    def handle_data(self, data):
        if self._href is not None:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            txt = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            self.links.append((self._href, self._title if len(self._title) > len(txt) else txt))
            self._href = None


def 抽链接(html: str, 基址: str, 必含: str, 且含: str = "", 排除: str = "") -> list[dict]:
    p = _A()
    try:
        p.feed(html)
    except Exception:
        pass
    出, 见 = [], set()
    for href, 标题 in p.links:
        if not href or href.startswith(("javascript:", "#", "mailto:")) or len(标题) < 6:
            continue
        if not re.search(必含, 标题) or (且含 and not re.search(且含, 标题)) or (排除 and re.search(排除, 标题)):
            continue
        url = urllib.parse.urljoin(基址, href)
        if url in 见:
            continue
        见.add(url)
        出.append({"url": url, "title": 标题, "site": urllib.parse.urlparse(url).netloc, "来源列表页": 基址})
    return 出


def 展开页(模板: str, 页: str) -> list[str]:
    if "{页}" not in 模板:
        return [模板]
    a, _, b = 页.partition("-")
    return [模板.replace("{页}", str(i)) for i in range(int(a), int(b or a) + 1)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--列表页", action="append", default=[])
    ap.add_argument("--列表文件", type=Path)
    ap.add_argument("--页", default="1")
    ap.add_argument("--必含", required=True)
    ap.add_argument("--且含", default="")
    ap.add_argument("--排除", default="")
    ap.add_argument("--输出", required=True, type=Path)
    ap.add_argument("--间隔", type=float, default=3.0)
    a = ap.parse_args()
    模板们 = list(a.列表页) + ([x.strip() for x in a.列表文件.read_text(encoding="utf-8").splitlines() if x.strip()] if a.列表文件 else [])
    已有 = set()
    if a.输出.exists():
        已有 = {json.loads(x)["url"] for x in a.输出.read_text(encoding="utf-8").splitlines() if x.strip()}
    新增 = 0
    with open(a.输出, "a", encoding="utf-8") as f:
        for 模板 in 模板们:
            for url in 展开页(模板, a.页):
                r = 抓一个(url)
                原始 = 解码(r["数据"], r["ct"]) if r["数据"] else ""
                状态 = 识别障碍(r["http"], 原始, 转文本(原始) if 原始 else "", r["最终url"]) if r["http"] else "连接失败"
                n = 0
                if 状态 == "ok":
                    for d in 抽链接(原始, r["最终url"], a.必含, a.且含, a.排除):
                        if d["url"] not in 已有:
                            已有.add(d["url"])
                            f.write(json.dumps(d, ensure_ascii=False) + "\n")
                            n += 1
                    f.flush()
                新增 += n
                print(f"{状态}\t+{n}\t{url}", flush=True)
                time.sleep(a.间隔)
    print(f"新增 {新增} 条 → {a.输出}（累计 {len(已有)}）")


if __name__ == "__main__":
    main()
