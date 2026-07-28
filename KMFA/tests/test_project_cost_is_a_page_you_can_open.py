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
