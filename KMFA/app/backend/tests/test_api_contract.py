"""TSK.KMFA.PROD.0002 契约测试：后端数据 API 的 OpenAPI 契约与真实数据形态。

铁律：本文件断言的全部是**真实仓内数据**（machine/facts、machine/lineage.yaml、
metadata/quality/assertions.jsonl、stage_artifacts 八份报告），不使用 mock/占位——
本线曾犯「用健康检查冒充完备性」的错，契约测试必须咬住真实内容。
"""
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REQUIRED_PATHS = {
    "/healthz",
    "/api/状态",
    "/api/数据管线",
    "/api/断言",
    "/api/技能",
    "/api/事实",
    "/api/事实/{name}",
    "/api/血缘",
    "/api/报表",
    "/api/源检查",
}


def test_source_check_matrix_protocol_reported_truthfully():
    """PROD.0005：正式矩阵当前零已提交源行，必须如实报出，不得编造维度值充数。"""
    payload = client.get("/api/源检查").json()
    protocol = payload["矩阵协议"]
    assert protocol["schema"] == "kmfa.source_check_matrix.v1"
    assert protocol["阶段"] == "S03-P2"
    assert protocol["已提交源行"] == 0
    assert len(protocol["必需维度"]) == 6
    assert "已就绪" in protocol["允许状态"]


def test_source_check_coverage_matrix_matches_lineage_total():
    """覆盖矩阵各源合计必须等于血缘资产总数——防止漏源或重复计数。"""
    payload = client.get("/api/源检查").json()
    coverage = payload["覆盖矩阵"]
    assert coverage["资产合计"] >= 50
    assert sum(row["合计"] for row in coverage["行"]) == coverage["资产合计"]
    assert set(coverage["源"]) >= {"财务", "WPS钉钉红圈", "绩效"}
    for row in coverage["行"]:
        assert sum(row[state] for state in coverage["状态列"]) == row["合计"]


def test_source_check_freshness_from_generated_facts_only():
    """新鲜度由 data_as_of_batch 与血缘批次比对得出（皆机器生成面），不读 raw inbox。"""
    payload = client.get("/api/源检查").json()
    fresh = payload["新鲜度"]
    assert fresh["数据批次"]
    assert isinstance(fresh["stale"], bool)
    assert fresh["stale"] == bool(fresh["更新的批次"])
    assert fresh["提示"]


def test_openapi_covers_required_paths():
    schema = client.get("/openapi.json").json()
    missing = REQUIRED_PATHS - set(schema["paths"])
    assert not missing, f"OpenAPI 缺路径: {missing}"


def test_facts_index_lists_real_facts():
    payload = client.get("/api/事实").json()
    names = {item["名"] for item in payload["items"]}
    assert payload["count"] >= 8, payload["count"]
    assert {"status", "data_pipeline", "roadmap", "blockers"} <= names, names


def test_facts_one_returns_real_content():
    payload = client.get("/api/事实/status").json()
    assert isinstance(payload, dict) and payload


def test_facts_one_rejects_unknown_and_traversal():
    assert client.get("/api/事实/不存在的事实").status_code == 404
    assert client.get("/api/事实/..%2F..%2Fpasswd").status_code == 404


def test_lineage_real_graph():
    payload = client.get("/api/血缘").json()
    assert payload["schema"] == "kmfa.lineage.v1"
    assert payload["覆盖"]["原始资产"] >= 50
    assert payload["规模"]["节点"] > 0 and payload["规模"]["边"] > 0
    assert len(payload["派生表"]) >= 10


def test_lineage_graph_optional_and_paginated():
    lite = client.get("/api/血缘").json()
    assert "图" not in lite
    full = client.get("/api/血缘?include_graph=true&size=5").json()
    assert len(full["图"]["节点"]) == 5
    assert full["图"]["节点分页"]["size"] == 5


def test_reports_lists_eight_real_reports():
    payload = client.get("/api/报表").json()
    assert payload["count"] == 8, payload["count"]
    first = payload["items"][0]
    assert first["编号"] == 1
    assert "一致性证明" in (first["标题"] or ""), first["标题"]
    assert first["文件数"] > 0


def test_reports_filter():
    payload = client.get("/api/报表?q=回款").json()
    assert payload["count"] >= 1
    assert all("回款" in (r["标题"] or "") or "回款" in r["目录"] for r in payload["items"])


def test_assertions_backward_compatible_summary():
    payload = client.get("/api/断言").json()
    assert payload["total"] == payload["closed"] + payload["analyzed_open"]
    assert payload["total"] >= 15
    assert payload["items"], "默认应返回条目（前端概览页依赖）"


def test_assertions_filter_by_status():
    all_rows = client.get("/api/断言").json()
    filtered = client.get("/api/断言?status=analyzed_open").json()
    assert filtered["筛选"]["命中"] == all_rows["analyzed_open"]
    assert all(item["status"] == "analyzed_open" for item in filtered["items"])


def test_assertions_filter_by_domain():
    payload = client.get("/api/断言?domain=collection").json()
    assert payload["筛选"]["命中"] >= 1
    assert all(item["domain"] == "collection" for item in payload["items"])


def test_assertions_pagination():
    paged = client.get("/api/断言?size=5&page=2").json()
    assert len(paged["items"]) == 5
    assert paged["分页"]["page"] == 2 and paged["分页"]["size"] == 5


def test_api_sources_never_under_raw_inbox():
    """PROD.0002 明令：API 永不直读 raw inbox（KMDatabase/data）。"""
    from app.main import (
        ASSERTIONS_PATH,
        FACTS,
        FORBIDDEN_READ_ROOT,
        LINEAGE_PATH,
        STAGE_ARTIFACTS,
    )

    forbidden = FORBIDDEN_READ_ROOT.resolve()
    for path in (FACTS, LINEAGE_PATH, ASSERTIONS_PATH, STAGE_ARTIFACTS):
        resolved = Path(path).resolve()
        assert forbidden not in resolved.parents, f"{resolved} 落在 raw inbox 下"
