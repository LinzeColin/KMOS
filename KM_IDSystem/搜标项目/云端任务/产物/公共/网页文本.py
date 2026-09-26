"""HTML → 纯文本（仅标准库）。

表格按行输出为 `| 单元格 | 单元格 |`，供 抽限价.py 的表格模式识别；
<br>/<p>/<div>/<li> 变换行；script/style 丢弃。
"""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser

_BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "ul", "ol", "table", "tbody", "thead"}
_SKIP = {"script", "style", "noscript", "template"}


class _Conv(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _SKIP:
            self.skip += 1
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []
        elif tag in _BLOCK and self.cell is None:
            self.out.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in ("td", "th"):
            if self.cell is not None and self.row is not None:
                self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None
        elif tag == "tr":
            if self.row:
                self.out.append("\n| " + " | ".join(self.row) + " |\n")
            self.row = None
        elif tag in _BLOCK and self.cell is None:
            self.out.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        if self.cell is not None:
            self.cell.append(data)
        else:
            self.out.append(data)


def 转文本(源: str) -> str:
    """HTML 或纯文本 → 规整后的纯文本（多空行压成一行）。"""
    if "<" not in 源:
        return 源
    c = _Conv()
    try:
        c.feed(源)
        c.close()
    except Exception:  # 残缺 HTML 退化为粗暴去标签
        return html.unescape(re.sub(r"<[^>]+>", "\n", 源))
    文本 = "".join(c.out).replace("\xa0", " ").replace("　", " ")
    行 = [re.sub(r"[ \t]+", " ", x).strip() for x in 文本.split("\n")]
    return "\n".join(x for x in 行 if x)


def 解码(字节: bytes, content_type: str = "") -> str:
    """按 Content-Type → <meta charset> → utf-8 → gb18030 顺序解码。"""
    候选: list[str] = []
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    if m:
        候选.append(m.group(1))
    m = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", 字节[:4096], re.I)
    if m:
        候选.append(m.group(1).decode("ascii", "ignore"))
    候选 += ["utf-8", "gb18030"]
    for enc in 候选:
        enc = enc.lower()
        if enc in ("gb2312", "gbk"):
            enc = "gb18030"
        try:
            return 字节.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return 字节.decode("utf-8", "replace")
