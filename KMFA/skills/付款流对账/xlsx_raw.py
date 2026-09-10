#!/usr/bin/env python3
"""原始 xlsx 读取。

不用 openpyxl：WPS 生成的文件会让它崩。这里直接解 xl/worksheets 的 XML，
按 <c r="B7"> 的列字母定位，所以中间的空单元格不会让整行错位 ——
按顺序读是历史上出过错的写法。
"""
import re, zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_CELL = re.compile(
    r'<c r="([A-Z]+)(\d+)"((?:(?!/?>).)*)>(?:(.*?))</c>|<c r="([A-Z]+)(\d+)"((?:(?!/?>).)*)/>',
    re.S)
_V = re.compile(r"<v>(.*?)</v>", re.S)
_IS = re.compile(r"<is>.*?<t[^>]*>(.*?)</t>.*?</is>", re.S)
_ROW = re.compile(r"<row[^>]*?r=\"(\d+)\"[^>]*>(.*?)</row>", re.S)


def _unescape(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&"))


def read_sheet(path, sheet_index=0):
    """返回 (headers: {列字母: 表头文字}, rows: [{列字母: 值}]) —— 值一律是 str。"""
    z = zipfile.ZipFile(path)
    shared = []
    for n in z.namelist():
        if "sharedStrings" in n:
            root = ET.fromstring(z.read(n))
            for si in root.iter(NS + "si"):
                shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
            break
    sheets = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
    data = z.read(sheets[sheet_index]).decode("utf-8", "replace")

    out = []
    for _rnum, body in _ROW.findall(data):
        cells = {}
        for m in _CELL.finditer(body):
            if m.group(1):
                col, attrs, inner = m.group(1), m.group(3) or "", m.group(4) or ""
            else:
                col, attrs, inner = m.group(5), m.group(7) or "", ""
            typ = ""
            tm = re.search(r't="(\w+)"', attrs)
            if tm:
                typ = tm.group(1)
            val = ""
            if typ == "inlineStr":
                im = _IS.search(inner)
                val = _unescape(im.group(1)) if im else ""
            else:
                vm = _V.search(inner)
                if vm:
                    raw = vm.group(1)
                    if typ == "s" and raw.isdigit() and int(raw) < len(shared):
                        val = shared[int(raw)]
                    else:
                        val = _unescape(raw)
            if val != "":
                cells[col] = val
        out.append(cells)
    if not out:
        return {}, []
    return out[0], out[1:]


def column_map(headers, wanted):
    """{要找的表头文字: 列字母}。找不到的键就不出现 —— 调用方必须自己检查。"""
    inv = {}
    for col, text in headers.items():
        inv.setdefault(text.strip(), col)
    got = {}
    for w in wanted:
        for text, col in inv.items():
            if text == w or text.startswith(w):
                got[w] = col
                break
    return got
