# -*- coding: utf-8 -*-
"""项目成本得是一页**打开就是数**的网页，不是 JSON、不是要下载的文件。

Owner 2026-07-29：「我说了我只要我的项目成本！」「我没有看到你说的东西」
「你不要放在本地，你推上网上去」。

在此之前出口只有两种，两种都没送到：
  · `/public-api/项目成本` 是 JSON——人打开看到的是一屏花括号；
  · 发 Excel 文件——卡片可能根本没在对话里露出来。

所以判据是「用浏览器打开这个地址，看到的是表格」。挂在 `/public-api/` 下
是因为那是既有匿名面；新起路径会被 Cloudflare Access 拦住，而 Access 策略
在 Owner 的控制台里、本仓改不掉。
"""
from __future__ import annotations

import importlib
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

SAMPLE = {
    "生成时间": "2026-07-29T09:00:00+08:00",
    "项目": [
        {"合同编号": "KMX2026001-001", "甲方名称": "甲公司", "施工状态": "已完工",
         "完工日期": "2026-06-30", "含税合同金额": "100000", "金蝶归集直接成本": "40000",
         "自有人工成本": "5000", "劳务人工成本": "0", "分摊管理费": "2000",
         "成本合计": "47000", "毛利": "53000"},
        {"合同编号": "KMX2026001-002", "甲方名称": "乙公司", "施工状态": "施工中",
         "含税合同金额": "50000", "金蝶归集直接成本": "-9000",
         "分摊管理费": "0", "成本合计": "-9000", "毛利": "59000"},
        {"合同编号": "KMX2026001-003", "甲方名称": "丙公司", "施工状态": "待入场",
         "含税合同金额": "80000", "成本合计": "0"},
        {"合同编号": "KMX2026001-004", "甲方名称": "丁公司", "成本合计": "1234",
         "合同号存疑": True, "身份来源": "⚠ 合同号与权威表冲突：本行很可能填错了"},
    ],
}


def _client(tmp_path: Path):
    artifact = tmp_path / "recent_completed.json"
    artifact.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    sys.path.insert(0, str(REPO / "KMFA/app/backend"))
    os.environ["KMFA_RECENT_COST"] = str(artifact)
    import app.main as m  # noqa: PLC0415

    importlib.reload(m)
    from fastapi.testclient import TestClient  # noqa: PLC0415

    return TestClient(m.app, raise_server_exceptions=False)


def test_it_returns_html_not_json(tmp_path):
    r = _client(tmp_path).get("/public-api/项目成本表")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html"), \
        "还是 JSON——人打开看到的是一屏花括号"
    assert "<table" in r.text


def test_it_needs_no_login(tmp_path):
    """挂在 /public-api/ 下才不会被 Access 拦。新起路径 = 打开就是登录墙。"""
    from app import main as m  # noqa: PLC0415

    _client(tmp_path)
    paths = {getattr(r, "path", "") for r in m.app.routes}
    assert "/public-api/项目成本表" in paths, "路径不在匿名面下"


def test_the_numbers_are_actually_on_the_page(tmp_path):
    r = _client(tmp_path).get("/public-api/项目成本表")
    assert "KMX2026001-001" in r.text
    assert "47,000" in r.text, "成本合计没渲出来"
    assert "甲公司" in r.text


def test_a_negative_cost_project_is_not_filtered_out(tmp_path):
    """成本为负 = 金蝶红字冲销超过借方，那是最该被看见的一条。

    按「> 0」过滤会把它连同金额一起从页面和合计里抹掉——
    这条线整晚都在修的就是这种静默过滤。
    """
    r = _client(tmp_path).get("/public-api/项目成本表")
    assert "KMX2026001-002" in r.text, "负成本项目被滤掉了"
    assert "-9,000" in r.text


def test_a_project_with_no_cost_record_is_not_padded_in(tmp_path):
    """没有成本记录的合同不列——列了就是拿「不知道」冒充「是 0」。"""
    r = _client(tmp_path).get("/public-api/项目成本表")
    assert "KMX2026001-003" not in r.text
    assert "成本不知道" in r.text, "没有说明为什么不列"


def test_a_contract_number_conflict_is_shown_not_swallowed(tmp_path):
    r = _client(tmp_path).get("/public-api/项目成本表")
    assert "KMX2026001-004" in r.text
    assert "合同号" in r.text and "对不上" in r.text


def test_it_says_so_when_there_is_no_artifact(tmp_path):
    """读不到就说读不到，不拿空表冒充「没有项目」。"""
    sys.path.insert(0, str(REPO / "KMFA/app/backend"))
    os.environ["KMFA_RECENT_COST"] = str(tmp_path / "nope.json")
    import app.main as m  # noqa: PLC0415

    importlib.reload(m)
    from fastapi.testclient import TestClient  # noqa: PLC0415

    r = TestClient(m.app, raise_server_exceptions=False).get("/public-api/项目成本表")
    assert r.status_code == 200
    assert "还没有数" in r.text
    assert "<table" not in r.text, "读不到却渲了一张空表"


def test_it_is_not_indexed(tmp_path):
    """真实客户名与合同额在这一页上，绝不能进搜索引擎。"""
    r = _client(tmp_path).get("/public-api/项目成本表")
    assert "noindex" in r.headers.get("X-Robots-Tag", "")
    # 断包含不断相等：中间件会再追加 no-transform（防边缘层注入第三方脚本），
    # 写死相等会把「中间件在干活」判成回归。
    assert "no-store" in r.headers.get("Cache-Control", "")


def test_the_page_has_a_margin_rate_column(tmp_path):
    """Owner 2026-07-29：「需要有毛利率百分比」。"""
    r = _client(tmp_path).get("/public-api/项目成本表")
    assert "毛利率" in r.text
    assert "53.0%" in r.text, "毛利 53000 ÷ 合同 100000 应当渲成 53.0%"


def test_no_margin_rate_is_invented_without_a_contract_amount(tmp_path):
    """合同额缺失/为 0 时不编一个百分比出来——除以零的地方最容易长出假数。"""
    r = _client(tmp_path).get("/public-api/项目成本表")
    # 只看表格里的那一行——存疑提示块也提到这个合同号，按整页搜会搜到那里去。
    rows = [x for x in r.text.split("<tr>") if "<td" in x]
    hit = [x for x in rows if "KMX2026001-002" in x]
    assert hit, "找不到那个没有毛利的行"
    assert 'data-v=""' in hit[0], "没有合同额却给了毛利率"


def _page_script(client) -> str:
    """跟着页面真正引的 <script src> 去取脚本——浏览器就是这么拿到它的。

    2026-07-29 教训：这两条断言原本写成 `in r.text`，于是
    「aria-sort」命中的是 CSS 规则、「空值永远沉底」命中的是脚本里的注释，
    而那整块脚本当时是内联的、被 CSP 拒绝执行，排序**从来没能用过**。
    在 HTML 文本里找字符串，证明不了浏览器会执行它。
    """
    html = client.get("/public-api/项目成本表").text
    srcs = re.findall(r"""<script[^>]*\bsrc\s*=\s*["']([^"']+)["']""", html, re.I)
    assert srcs, "页面没引任何脚本——排序是靠 JS 活的"
    return "\n".join(client.get(s).text for s in srcs)


def test_numeric_columns_sort_by_value_not_by_the_printed_string(tmp_path):
    """排序读 data-v 的数值。按显示的千分位字符串排，「1,000,000」会排在「9,000」前面。"""
    client = _client(tmp_path)
    r = client.get("/public-api/项目成本表")
    assert 'data-v="47000.0"' in r.text or 'data-v="47000"' in r.text
    assert "th[data-s]" in r.text, "表头没做成可点"
    js = _page_script(client)
    assert "parseFloat" in js, "数值列没按数值比，会退化成字符串序"
    assert "aria-sort" in js, "排序状态没写回表头"


def test_empty_cells_always_sink_to_the_bottom(tmp_path):
    """空值不管升序降序都沉底——把「没有数」排到有数的前面等于让缺失冒充最小值。"""
    js = _page_script(_client(tmp_path))
    assert "空值永远沉底" in js
    # 沉底靠的是「不参与升降序取反」：命中空值时直接返回定值
    assert "return 1;" in js and "return -1;" in js, "空值分支没有绕开升降序取反"


def test_there_is_a_download_button(tmp_path):
    r = _client(tmp_path).get("/public-api/项目成本表")
    assert 'href="/项目成本/下载"' in r.text


def test_the_download_is_a_real_workbook_shaped_like_the_owner_reference(tmp_path):
    """Owner：「你的下载产品和我的格式要保持一致」——对照物是那份 8 项目参考表，
    页签是 使用说明／项目总览／毛利复核／…。"""
    import io

    import openpyxl

    r = _client(tmp_path).get("/项目成本/下载")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]
    book = openpyxl.load_workbook(io.BytesIO(r.content))
    for must in ("使用说明", "项目总览", "毛利复核", "成本明细"):
        assert must in book.sheetnames, f"缺页签 {must}：{book.sheetnames}"
    overview = book["项目总览"]
    headers = [overview.cell(1, i).value for i in range(1, overview.max_column + 1)]
    assert "毛利率" in headers
    # 样例里 001（47000）与 002（-9000）进表；003 成本为 0 不进；
    # 004 合同号存疑——它的成本不归入任何项目，所以也不进主表。
    assert overview.max_row - 1 == 2, \
        f"主表行数不对：{overview.max_row - 1}（存疑项目不该进来，成本为 0 的也不该）"


def test_the_download_filename_survives_chinese(tmp_path):
    """中文文件名要走 RFC 5987，否则浏览器存下来是一串下划线或乱码。"""
    r = _client(tmp_path).get("/项目成本/下载")
    disposition = r.headers.get("content-disposition", "")
    assert "filename*=UTF-8''" in disposition
    assert "attachment" in disposition


def test_the_download_says_no_when_there_is_no_artifact(tmp_path):
    import importlib
    import os
    import sys

    sys.path.insert(0, str(REPO / "KMFA/app/backend"))
    os.environ["KMFA_RECENT_COST"] = str(tmp_path / "nope.json")
    import app.main as m  # noqa: PLC0415

    importlib.reload(m)
    from fastapi.testclient import TestClient  # noqa: PLC0415

    r = TestClient(m.app, raise_server_exceptions=False).get("/项目成本/下载")
    assert r.status_code == 503, "产物不在却给了一个文件——那文件里会是空的"


def test_the_homepage_link_survives_react_hydration():
    """链接必须写在 React 壳里，不能只写在静态壳里。

    2026-07-29 Owner：「和主页没有连接在一起」。此前链接只在 index.html 的静态壳，
    浏览器一加载 JS，React 接管就把整块换掉——「首页有链接」只在没有 JS 时成立。
    """
    shell = (REPO / "KMFA/app/frontend/src/PublicAppShell.jsx").read_text(encoding="utf-8")
    assert shell.count('href="/项目成本"') >= 2, "React 壳里没有项目成本入口"
    assert "data-shell-cost-entry" in shell, "入口没有可测锚点"

    built = list((REPO / "KMFA/app/frontend/dist/assets").glob("PublicAppShell-*.js"))
    assert built, "找不到构建产物"
    assert any("shell-cost-entry" in f.read_text(encoding="utf-8", errors="replace")
               for f in built), "改了源码但没重新构建，线上还是旧的"


def test_the_entry_is_in_the_component_the_root_actually_renders():
    """入口必须在 App.jsx——**根路径渲染的是它**，不是 PublicAppShell。

    2026-07-29 栽在这上面：入口写进了 PublicAppShell.jsx，而 main.jsx 里
    只有 `/workspace` 才加载那个组件，根路径加载的是 App.jsx。
    我当时只 grep 了 JS 包里有没有那个字符串，**没验它渲不渲得出来**——
    包里有 ≠ 用户看得见。Owner 连着两次说「首页依旧进不去项目成本」。
    """
    main_js = (REPO / "KMFA/app/frontend/src/main.jsx").read_text(encoding="utf-8")
    assert "loadPrivateOperationsApp()" in main_js and "isPublicWorkspace" in main_js, \
        "路由结构变了——重新确认根路径到底渲染哪个组件，别再照着旧假设放入口"

    app_jsx = (REPO / "KMFA/app/frontend/src/App.jsx").read_text(encoding="utf-8")
    assert 'href="/项目成本"' in app_jsx, "根路径渲染的组件里没有项目成本入口"
    assert 'href="/项目成本/下载"' in app_jsx, "根路径渲染的组件里没有下载入口"

    built = list((REPO / "KMFA/app/frontend/dist/assets").glob("App-*.js"))
    assert built, "找不到 App 的构建产物"
    assert any("/项目成本" in f.read_text(encoding="utf-8", errors="replace") for f in built), \
        "改了源码但没重新构建，线上还是旧的"


def test_every_row_can_be_downloaded_on_its_own(tmp_path):
    """Owner：「不支持单一合同下载」。"""
    r = _client(tmp_path).get("/public-api/项目成本表")
    assert r.text.count('class="one"') == 2, "不是每个有成本的项目都有单独下载"
    assert "/项目成本/下载?合同=" in r.text


def test_a_single_contract_download_contains_only_that_contract(tmp_path):
    import io

    import openpyxl

    r = _client(tmp_path).get("/项目成本/下载", params={"合同": "KMX2026001-001"})
    assert r.status_code == 200
    book = openpyxl.load_workbook(io.BytesIO(r.content))
    overview = book["项目总览"]
    assert overview.max_row - 1 == 1
    assert overview.cell(2, 1).value == "KMX2026001-001"
    assert "KMX2026001-001" in r.headers.get("content-disposition", "")


def test_an_unknown_contract_is_a_404_not_an_empty_workbook(tmp_path):
    """找不到就说找不到。回一份空表比报错更糟——拿到手的人会以为这个项目成本是 0。"""
    r = _client(tmp_path).get("/项目成本/下载", params={"合同": "KMX-不存在"})
    assert r.status_code == 404


def test_recompute_only_files_a_request_and_never_runs_the_job_here(tmp_path, monkeypatch):
    """「重新计算」只放标记，真正的活在 skills 容器里跑。

    让 App 容器去跑克隆私有库解析上千张表的活，就是把 2026-07-28 那次
    「压测把线上打下线」原样重演一遍，只是换了个触发器。
    """
    c = _client(tmp_path)
    import app.main as m  # noqa: PLC0415

    flag = tmp_path / ".refresh_requested"
    monkeypatch.setattr(m, "COST_REFRESH_FLAG", flag)
    r = c.post("/项目成本/重算")
    assert r.status_code == 200
    body = r.json()
    assert body["已提交"] is True
    assert body["怎么确认"], "只说「已提交」而不说怎么确认，跟没回一样"
    assert flag.exists(), "标记没落到共享卷上，skills 那边永远看不到"

    src = (REPO / "KMFA/app/backend/app/main.py").read_text(encoding="utf-8")
    tail = src.split("def public_project_cost_refresh")[1][:1400]
    assert "subprocess" not in tail, "重算端点里出现了子进程调用——重活不该在 App 容器里跑"


def test_the_flag_goes_where_the_app_can_actually_write():
    """标记必须落在 **app 可写**的卷上。

    2026-07-29 线上实测：第一版把它写进日志卷，按钮直接 503
    「共享卷不可写——app 容器没挂 kmfa-logs 卷」。两个卷的读写方向是刻意反着的：
      kmfa-logs       skills 可写 / app **只读**
      kmfa-app-state  app 可写   / skills **只读**（daily-backup 读它打包备份，「绝不写」）
    那道只读边界是有意的，不该为了一个按钮把整个日志卷对 app 开成可写。
    """
    src = (REPO / "KMFA/app/backend/app/main.py").read_text(encoding="utf-8")
    line = next(l for l in src.splitlines() if l.startswith("COST_REFRESH_FLAG"))
    assert "APP_STATE_DIR" in line, f"标记又放回 app 只读的卷上了：{line}"


def test_the_failure_message_names_the_volume_that_is_actually_involved(tmp_path, monkeypatch):
    """写失败时报的卷名必须是**真参与的那个**。

    标记从 kmfa-logs 挪到 kmfa-app-state 之后，这句报错没跟着改，
    于是失败信息把人指向一个根本没参与的卷。**指错地方的报错比不报还费时间**——
    照着它去查日志卷的挂载，会发现挂载完全正常，然后一无所获。
    """
    client = _client(tmp_path)
    from app import main as m  # noqa: PLC0415

    # 让写标记必然失败：把它指到一个「父目录是文件」的路径上
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(m, "COST_REFRESH_FLAG", blocker / "flag")

    body = client.post("/项目成本/重算").json()
    assert body["已提交"] is False
    reason = body["原因"]
    assert "app-state" in reason, f"报错没提真正涉及的卷：{reason}"
    assert "kmfa-logs" not in reason, f"报错还在指向没参与的日志卷：{reason}"


def test_the_skills_side_actually_watches_for_the_flag():
    """标记要有人看。没人看的标记 = 按钮按下去什么也不会发生。"""
    cron = (REPO / "KMFA/deploy/skills-runtime/crontab.txt").read_text(encoding="utf-8")
    line = next((l for l in cron.splitlines()
                 if "refresh_requested" in l and not l.lstrip().startswith("#")), None)
    assert line, "crontab 里没有看标记的那一跳"
    assert line.startswith("* * * * *"), "不是每分钟看一次，按下去要等很久才有反应"
    assert "nice -n" in line, "重算没让出 CPU 优先级"
    # skills 只读挂载 app-state，**删不掉**那个标记，所以只能比时间戳。
    # 写成「先删后跑」在线上会一直失败，而且失败得很安静。
    assert "rm -f" not in line, "skills 对 app-state 只读，删不掉标记"
    assert "-nt" in line, "没有比时间戳——那就分不出「这次点的」和「上次点的」"
    assert "/var/lib/kmfa/state/" in line and "/var/log/kmfa/" in line, \
        "两个卷都要用到：读 app 写的标记，写自己这边的处理记录"
