# -*- coding: utf-8 -*-
"""最近完工项目成本接口的边界测试。

Owner 2026-07-27：「我根本没有看到项目成本，我说了我要最近完工的项目成本」。
所以这个接口存在的意义是**把数送上页面**，那么它最该防的就是「页面看着正常、其实没数」：

  · 产物缺失时返回空数组 → 页面显示"没有已完工项目"，与"还没算出来"长得一模一样，
    意思却完全相反。必须 `可读:false` + 具名原因。
  · 两个口径被合并成一个总数 → 差异被抹掉，而差异正是要看的东西。
"""
import json

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)
URL = "/api/项目成本/完工"

SAMPLE = {
    "schema_version": "kmfa.project_cost.recent_completed.v1",
    "口径": {"业务台账": "红圈自填四项", "金蝶归集": "按销售合同号归集"},
    "锁定的算法": ["账簿按名去重", "取借方发生额而非净额"],
    "项目数": 1,
    "项目": [{
        "合同编号": "KMX20251119-079", "甲方名称": "某水泥", "完工日期": "2026-03-07",
        "完工排序": "2026-03-07", "含税合同金额": "228900.00",
        "材料费": "4195.00", "交通费": "7399.04", "生活住宿费": "15500.00", "其他费用": "80.00",
        "业务台账成本合计": "27174.04", "台账口径毛利": "201725.96",
        "金蝶归集直接成本": "64653.90", "两口径差额": "37479.86",
        "金蝶成本明细": {"（一）原材料": "7400.53", "（四）现场管理费": "54948.14"},
    }],
}


def _write(tmp_path, payload, monkeypatch):
    path = tmp_path / "recent_completed.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "RECENT_COST_PATH", path)
    return path


def test_missing_artifact_says_so_instead_of_returning_an_empty_list(tmp_path, monkeypatch):
    """空数组和读不到在页面上长得一样，意思完全相反——必须分得开。"""
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


def test_serves_both_calibers_without_merging_them(tmp_path, monkeypatch):
    _write(tmp_path, SAMPLE, monkeypatch)
    body = client.get(URL).json()
    assert body["可读"] is True
    row = body["项目"][0]
    assert row["业务台账成本合计"] == "27174.04"
    assert row["金蝶归集直接成本"] == "64653.90"
    assert "两口径差额" in row, "差异必须保留——它本身就是要看的东西"
    assert not any(k in row for k in ("成本合计", "总成本")), "两个口径不得被合并成一个总数"


def test_reports_when_the_artifact_was_produced(tmp_path, monkeypatch):
    """没有产出时间就分不出「今天的数」和「三个月前的数」。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    assert client.get(URL).json()["产出时间"]


def test_caliber_and_algorithm_locks_travel_with_the_data(tmp_path, monkeypatch):
    """口径与算法锁必须跟着数走；只给数字不给口径，等于给了一个不能引用的数。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    body = client.get(URL).json()
    assert body["口径"]["业务台账"] and body["口径"]["金蝶归集"]
    assert body["锁定的算法"]
