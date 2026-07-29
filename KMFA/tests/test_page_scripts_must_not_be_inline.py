# -*- coding: utf-8 -*-
"""服务端渲染页面里的 <script> 必须是外链，内联的一律当**没写**。

2026-07-29 Owner：「排序功能无法使用」。

代码是对的、渲染是对的、`data-v` 全在、⇅ 箭头也在，但点下去没反应。
线上判据：`th.getAttribute('role')` 是 `null`、`th.tabIndex` 是 `-1` ——
脚本给表头挂 role/tabIndex 的那两行从没执行过，监听器从没挂上去。

原因是本站 CSP：

    script-src 'self'                    ← 没有 'unsafe-inline'
    style-src  'self' 'unsafe-inline'    ← 样式**是**放行的

两条不对称，制造了一种最难发现的坏法：**内联样式生效、内联脚本被拒**。
于是页面长得跟能用一模一样——手型光标、hover 变色、排序箭头，全是 CSS——
只有行为是死的。排序和「重新计算」两个功能是一起哑掉的（同一个 <script> 块）。

这也是为什么此前的排序测试全绿：
  · `assert "aria-sort" in r.text` —— 命中的是 CSS 规则 `th[aria-sort=...]::after`；
  · `assert "空值永远沉底" in r.text` —— 命中的是**脚本里的注释**。
两条都只证明「字符串在 HTML 里」，而 CSP 恰恰是在「字符串在 HTML 里」之后
才把它拦掉的。所以门禁必须建在**浏览器真正的执行边界**上，而不是文本包含上。

修法只有两个方向，本仓选后者：
  a) 给 CSP 加 'unsafe-inline' —— 等于为了一个排序按钮把 XSS 防线拆了；
  b) 把脚本挪成同源外链文件 —— `'self'` 本来就放行。
所以下面还有一条反向门禁：**不许通过放宽 CSP 来让本文件变绿**。
"""
from __future__ import annotations

import importlib
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "KMFA/app/backend"

SCRIPT_TAG = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S | re.I)
SRC_ATTR = re.compile(r"""\bsrc\s*=\s*["']([^"']+)["']""", re.I)


def _client(tmp_path: Path):
    artifact = tmp_path / "recent_completed.json"
    artifact.write_text(
        json.dumps(
            {"生成时间": "2026-07-29T09:00:00+08:00",
             "项目": [{"合同编号": "KMX2026001-001", "甲方名称": "甲公司",
                       "含税合同金额": "100000", "成本合计": "47000", "毛利": "53000"}]},
            ensure_ascii=False),
        encoding="utf-8")
    sys.path.insert(0, str(BACKEND))
    os.environ["KMFA_RECENT_COST"] = str(artifact)
    import app.main as m  # noqa: PLC0415

    importlib.reload(m)
    from fastapi.testclient import TestClient  # noqa: PLC0415

    return TestClient(m.app, raise_server_exceptions=False)


# 服务端自己拼 HTML 的页面。React 那套走 /assets 下的哈希产物，天然是外链。
SERVER_RENDERED_PAGES = ("/项目成本", "/public-api/项目成本表")


def test_no_page_ships_an_inline_script(tmp_path):
    """CSP 会拒掉内联 <script>，所以内联等于**写了不执行**。"""
    client = _client(tmp_path)
    for path in SERVER_RENDERED_PAGES:
        html = client.get(path).text
        for attrs, body in SCRIPT_TAG.findall(html):
            assert not body.strip(), (
                f"{path} 里有内联 <script>（{len(body.strip())} 字符）。"
                "CSP script-src 'self' 会拒绝执行它——页面看着正常，行为是死的。"
                "把它挪去 app/static/ 下的 .js 文件再用 src 引。")
            assert SRC_ATTR.search(attrs), f"{path} 里有个既没内容也没 src 的 <script>"


def test_every_script_src_is_same_origin_and_actually_routed(tmp_path):
    """`'self'` 只放行同源。外链地址还必须真能取到，否则一样是空气。"""
    client = _client(tmp_path)
    seen = 0
    for path in SERVER_RENDERED_PAGES:
        html = client.get(path).text
        for attrs, _ in SCRIPT_TAG.findall(html):
            match = SRC_ATTR.search(attrs)
            if not match:
                continue
            src = match.group(1)
            assert src.startswith("/"), f"{src} 不是同源路径，CSP 'self' 不放行"
            resp = client.get(src)
            assert resp.status_code == 200, f"{path} 引了 {src}，但它返回 {resp.status_code}"
            ctype = resp.headers["content-type"].lower()
            assert "javascript" in ctype or "ecmascript" in ctype, (
                f"{src} 的 Content-Type 是 {ctype}；本站带 nosniff，"
                "非 JS MIME 会被浏览器直接拒绝执行")
            seen += 1
    assert seen, "一个外链脚本都没有——排序和重算是靠 JS 活的，不该一个都不引"


def _inline_scripts(text: str) -> list[str]:
    """挑出**带内容**的 <script>……</script>。

    过滤掉正则字面量：main.py 里有一条正则在**描述** <script id="kmfa-app-module">，
    它不是要发给浏览器的 HTML。真 HTML 的属性里不会出现 `[^>]` `\\b` 这类元字符。
    """
    found = []
    for attrs, body in SCRIPT_TAG.findall(text):
        if any(token in attrs for token in ("[^>]", "\\b", "\\s")):
            continue
        if body.strip():
            found.append(body.strip())
    return found


def test_no_html_template_in_the_source_carries_an_inline_script():
    """源码级兜底：上面两条只走了我**知道**的那两个地址。

    以后新加一个服务端渲染页面，它未必在 SERVER_RENDERED_PAGES 里，
    于是又能悄悄内联一块脚本、又一次「看着能用、点了没反应」。
    所以直接在源码里禁掉这个写法本身。

    只看**字符串字面量**，不看注释：注释里出现 `<script>` 三个字（比如本文件、
    比如 main.py 里解释这条规矩的那段）不是 bug，而发出去的 HTML 里有才是。
    按整份文件做文本扫描分不开这两者——第一版就是这么把自己的注释判红的。
    """
    import ast  # noqa: PLC0415

    module = ast.parse((BACKEND / "app/main.py").read_text(encoding="utf-8"))
    literals = [
        node.value for node in ast.walk(module)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    # 文档字符串是给人读的，不会被发出去
    docstrings = {ast.get_docstring(n) for n in ast.walk(module)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}

    sources: list[tuple[str, str]] = [
        ("main.py 的字符串字面量", text)
        for text in literals if text not in docstrings
    ]
    fragment = BACKEND / "app/workspace_shell_fragment.html"
    if fragment.exists():
        sources.append((fragment.name, fragment.read_text(encoding="utf-8")))

    for label, text in sources:
        for body in _inline_scripts(text):
            raise AssertionError(
                f"{label} 里有内联 <script>（{len(body)} 字符，开头：{body[:60]!r}）。"
                "CSP script-src 'self' 不会执行它——页面看着正常、行为是死的。"
                "放到 app/static/*.js，再用 <script src=...> 引。")


def test_the_sort_behaviour_lives_in_the_file_the_page_actually_loads(tmp_path):
    """真正挂监听器的那几行，得在页面引的那个文件里——不是在 HTML 里、也不是在注释里。"""
    client = _client(tmp_path)
    html = client.get("/项目成本").text
    srcs = [SRC_ATTR.search(a).group(1) for a, _ in SCRIPT_TAG.findall(html) if SRC_ATTR.search(a)]
    js = "\n".join(client.get(s).text for s in srcs)

    assert "addEventListener('click'" in js.replace('"', "'"), "没有点击监听器"
    assert "tHead" in js and "tBodies" in js, "没有真去重排表体"
    assert "aria-sort" in js, "没有写回排序状态"
    # 空值沉底：升降序都返回固定的 1 / -1，不参与比较
    assert "空值永远沉底" in js, "空值沉底那条规则不在会被执行的文件里"
    assert "recalc" in js, "「重新计算」的监听器也在同一块——别只救回来一半"


def test_the_fix_is_not_to_weaken_the_csp():
    """反向门禁：不许靠给 CSP 开 'unsafe-inline' 来让上面几条变绿。

    那等于为了一个排序按钮，把整站对注入脚本的防线拆掉——
    而本页公开在互联网上、且匿名可达。
    """
    sys.path.insert(0, str(BACKEND))
    from app.secret_hygiene import CONTENT_SECURITY_POLICY  # noqa: PLC0415

    directive = next(
        (d.strip() for d in CONTENT_SECURITY_POLICY.split(";") if d.strip().startswith("script-src")),
        None)
    assert directive, "CSP 里没有 script-src——那 default-src 说了算，同样别放宽"
    assert "unsafe-inline" not in directive, f"script-src 被放宽了：{directive}"
    assert "unsafe-eval" not in directive, f"script-src 被放宽了：{directive}"


def test_the_static_route_only_serves_js_and_cannot_walk_out(tmp_path):
    """新开的 /static/ 是个能读文件的口子，先把边界钉死。"""
    client = _client(tmp_path)
    assert client.get("/static/project-cost.js").status_code == 200
    for evil in ("../main.py", "..%2fmain.py", "../../requirements.txt"):
        assert client.get(f"/static/{evil}").status_code in (307, 404), f"{evil} 走出去了"
    assert client.get("/static/nope.js").status_code == 404


def test_the_script_is_not_cached_forever(tmp_path):
    """文件名里没有内容哈希。若按 /assets 那样 immutable，
    一次改错的 JS 会永久钉在浏览器里，改好了也下不来。"""
    r = _client(tmp_path).get("/static/project-cost.js")
    cache = r.headers.get("cache-control", "")
    assert "immutable" not in cache, f"没有内容哈希却 immutable：{cache}"
    assert "no-cache" in cache or "max-age=0" in cache or "no-store" in cache, \
        f"没要求回源核对：{cache}"
