# -*- coding: utf-8 -*-
"""免登录项目成本接口。

Owner 2026-07-28：「kmfa 没有登录的地方」「取消登陆功能」。

`/api/项目成本/完工` 在 Cloudflare Access 后面，未登录是 302 跳登录墙，而 Access 应用
配在 Owner 的控制台里、本仓改不掉。所以出口挪到既有的匿名面 `/public-api/*`。

这组测试钉死三件事：
  · 它必须真的在匿名面上——挪回 `/api/*` 就等于登录墙又回来了；
  · 读不到要说读不到，不能拿空列表冒充「没有项目」；
  · 数必须原样出，不能因为「公开」就悄悄砍字段——砍了页面就少一块，且没人会发现。
"""
import json

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)
URL = "/public-api/项目成本"

SAMPLE = {
    "schema_version": "kmfa.project_cost.recent_completed.v1",
    "口径": {"业务台账": "红圈自填四项", "金蝶归集": "按销售合同号归集"},
    "锁定的算法": ["账簿按名去重", "取借方发生额而非净额"],
    "项目数": 1,
    "项目": [{
        "合同编号": "KMX20251119-079", "甲方名称": "某水泥", "完工日期": "2026-03-07",
        "含税合同金额": "228900.00", "业务台账成本合计": "27174.04",
        "金蝶归集直接成本": "64653.90", "两口径差额": "37479.86",
    }],
}


def _write(tmp_path, monkeypatch, payload=SAMPLE):
    path = tmp_path / "recent_completed.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "RECENT_COST_PATH", path)
    return path


def test_lives_on_the_anonymous_surface():
    """路由前缀就是这个改动的全部意义——挪回 /api/ 登录墙就又回来了。"""
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert URL in paths
    assert URL.startswith("/public-api/")


def test_missing_artifact_says_so_instead_of_an_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "RECENT_COST_PATH", tmp_path / "nope.json")
    body = client.get(URL).json()
    assert body["可读"] is False
    assert body["原因"]
    assert body["项目"] == []


def test_unparseable_artifact_is_reported_not_swallowed(tmp_path, monkeypatch):
    path = tmp_path / "recent_completed.json"
    path.write_text("{ 这不是 JSON", encoding="utf-8")
    monkeypatch.setattr(main, "RECENT_COST_PATH", path)
    body = client.get(URL).json()
    assert body["可读"] is False and "无法解析" in body["原因"]


def test_serves_the_same_payload_as_the_gated_route(tmp_path, monkeypatch):
    """公开面不是删减面：两个口径、差额、口径与算法锁都必须原样在。"""
    _write(tmp_path, monkeypatch)
    body = client.get(URL).json()
    assert body["可读"] is True
    row = body["项目"][0]
    assert row["业务台账成本合计"] == "27174.04"
    assert row["金蝶归集直接成本"] == "64653.90"
    assert "两口径差额" in row
    assert body["口径"]["业务台账"] and body["锁定的算法"]
    assert body["产出时间"]


def test_declares_it_needs_no_login(tmp_path, monkeypatch):
    """页面靠这个字段决定要不要弹「请先登录」——它错了，人就被挡在门外。"""
    _write(tmp_path, monkeypatch)
    assert client.get(URL).json()["需要登录"] is False


def test_is_not_indexable_and_not_cached(tmp_path, monkeypatch):
    """公开不等于该被搜索引擎收录；缓存则会把真金额留在中间层。"""
    _write(tmp_path, monkeypatch)
    headers = client.get(URL).headers
    assert "noindex" in headers.get("x-robots-tag", "")
    assert headers.get("cache-control") == "no-store"
