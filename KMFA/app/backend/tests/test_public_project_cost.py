# -*- coding: utf-8 -*-
"""项目成本接口的受控应用路由。

路由名因历史兼容仍保留 `/public-api/*`。当前 Owner 公开面合同关闭源站
登录守卫；本文件只在本地开发模式测试业务响应，不能作为项目成本金额验收。

这组测试钉死三件事：
  · 历史兼容路由必须保留；
  · 读不到要说读不到，不能拿空列表冒充「没有项目」；
  · 正式成本及独立观察面必须原样出，不能因为「公开」就悄悄砍字段。
"""
import json
import hashlib

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)
URL = "/public-api/项目成本"

SAMPLE = {
    "schema_version": "kmfa.project_cost.current.v4",
    "快照ID": "kmfa-pc-2099-api",
    "计算状态": "PASS",
    "待确认": {
        "状态": "PASS",
        "P0阻断数": 0,
        "P1开放复核数": 0,
        "P2已排除或提示数": 0,
    },
    "口径": {
        "正式成本": "项目已发生成本＝项目过账实际＋合格应计",
        "独立观察面": "主营成本、状态表、支付系统不并入正式成本",
    },
    "锁定的算法": ["原始凭证明细去重", "工资应计最大余数法守恒到分"],
    "项目数": 1,
    "封印来源": {
        "源码摘要算法": "kmfa.project_cost.subject_tree.v1",
        "源码SHA256": "a" * 64,
        "源码文件数": 1,
        "输入清单类型": "PRIVATE_MANIFEST_SHA256",
        "输入清单SHA256": "b" * 64,
        "私有输入清单SHA256": "b" * 64,
        "选中来源绑定SHA256": "c" * 64,
    },
    "项目": [{
        "合同编号": "KMX20990101-001", "甲方名称": "合成客户甲", "完工日期": "2099-01-31",
        "含税合同金额": "100000.00", "项目过账实际": "1234.56",
        "项目应计": "765.44", "项目已发生成本": "2000.00",
        "项目成本": "2000.00",
        "有效合同额": "5000.00", "毛利": "3000.00",
        "毛利率": "60.00%", "毛利率基点": 6000,
        "收入与毛利状态": "READY",
        "主营成本已结转": "321.00", "状态表已报直接成本": "654.00",
        "支付系统已付观察": None,
        "项目成本覆盖": "FULL_SELECTED_GL_PERIOD;POSTING_PRESENT",
    }],
}


def _write(tmp_path, monkeypatch, payload=None):
    payload = json.loads(json.dumps(payload or SAMPLE, ensure_ascii=False))
    workbook = tmp_path / "sealed-api.xlsx"
    workbook.write_bytes(b"synthetic sealed workbook")
    payload["封印工作簿"] = {
        "文件名": workbook.name,
        "SHA256": hashlib.sha256(workbook.read_bytes()).hexdigest(),
        "字节数": workbook.stat().st_size,
        "快照ID": payload["快照ID"],
    }
    path = tmp_path / "recent_completed.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "RECENT_COST_PATH", path)
    return path


def test_keeps_the_legacy_compatible_route():
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


def test_legacy_runtime_schema_is_rejected_instead_of_reinterpreted(
    tmp_path,
    monkeypatch,
):
    legacy = json.loads(json.dumps(SAMPLE, ensure_ascii=False))
    legacy["schema_version"] = "kmfa.project_cost.recent_completed.v2"
    _write(tmp_path, monkeypatch, legacy)
    response = client.get(URL)
    assert response.status_code == 503
    body = response.json()
    assert body["可读"] is False
    assert body["项目"] == []
    assert "版本不兼容" in body["原因"]


def test_runtime_without_sealed_source_binding_is_rejected(
    tmp_path,
    monkeypatch,
):
    unbound = json.loads(json.dumps(SAMPLE, ensure_ascii=False))
    unbound.pop("封印来源")
    _write(tmp_path, monkeypatch, unbound)
    response = client.get(URL)
    assert response.status_code == 503
    body = response.json()
    assert body["可读"] is False
    assert body["项目"] == []
    assert "版本不兼容" in body["原因"]


def test_serves_the_same_payload_as_the_gated_route(tmp_path, monkeypatch):
    """公开面不是删减面：正式口径、观察面、覆盖与算法锁都必须原样在。"""
    _write(tmp_path, monkeypatch)
    body = client.get(URL).json()
    assert body["可读"] is True
    row = body["项目"][0]
    assert row["项目过账实际"] == "1234.56"
    assert row["项目应计"] == "765.44"
    assert row["项目已发生成本"] == "2000.00"
    assert row["主营成本已结转"] == "321.00"
    assert row["状态表已报直接成本"] == "654.00"
    assert row["项目成本覆盖"]
    assert body["口径"]["正式成本"] and body["锁定的算法"]
    assert body["产出时间"]


def test_declares_that_production_access_is_required(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch)
    assert client.get(URL).json()["需要登录"] is True


def test_is_not_indexable_and_not_cached(tmp_path, monkeypatch):
    """公开不等于该被搜索引擎收录；缓存则会把真金额留在中间层。"""
    _write(tmp_path, monkeypatch)
    headers = client.get(URL).headers
    assert "noindex" in headers.get("x-robots-tag", "")
    assert headers.get("cache-control") == "no-store"
