# -*- coding: utf-8 -*-
"""项目毛利接口的边界测试。

这个接口最该防的不是算错，是**让一个 88% 裸奔出去**。
两个成本口径都不含（或不全含）人工，所以那 88% 是毛利上限、不是毛利率——
数字一旦脱离口径说明，读的人必然把它当毛利率读，那比不给数还糟。
"""
import json

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)
URL = "/api/项目毛利"

CALIBER = "两个成本口径都是残的——业务台账那四项不含人工，成本必然被低估，这里给的是毛利上限。"

SAMPLE = {
    "schema_version": "kmfa.project_margin.v1",
    "⚠这不是毛利": CALIBER,
    "口径": {"收入": "含税合同金额", "毛利上限": "含税合同金额 − 已知成本下限"},
    "项目数": 1,
    "分阶段汇总": {"已完工": {"项目数": 1, "毛利上限率": "88.0%", "其中无成本数据的项目数": 0}},
    "项目": [{
        "合同编号": "KMX2099120-904", "甲方名称": "合成甲公司", "阶段": "已完工",
        "含税合同金额": "123456.78", "业务台账成本": "12000.00", "金蝶归集成本": "11500.00",
        "已知成本下限": "12000.00", "毛利上限": "111456.78", "毛利上限率": "90.3%",
        "成本数据": "两口径均有数", "数据提示": [],
    }],
}


def _write(tmp_path, payload, monkeypatch):
    path = tmp_path / "project_margin.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "PROJECT_MARGIN_PATH", path)
    return path


def test_missing_artifact_says_so_instead_of_returning_an_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "PROJECT_MARGIN_PATH", tmp_path / "nope.json")
    body = client.get(URL).json()
    assert body["可读"] is False and body["原因"] and body["项目"] == []


def test_unparseable_artifact_is_reported_not_swallowed(tmp_path, monkeypatch):
    path = tmp_path / "project_margin.json"
    path.write_text("{ 这不是 JSON", encoding="utf-8")
    monkeypatch.setattr(main, "PROJECT_MARGIN_PATH", path)
    assert "无法解析" in client.get(URL).json()["原因"]


def test_numbers_never_ship_without_the_caliber_warning(tmp_path, monkeypatch):
    """口径说明丢了就整份不发——宁可页面说读不到，也不让 88% 裸奔。"""
    stripped = {k: v for k, v in SAMPLE.items() if k != "⚠这不是毛利"}
    _write(tmp_path, stripped, monkeypatch)
    body = client.get(URL).json()
    assert body["可读"] is False
    assert "口径说明" in body["原因"]
    assert body["项目"] == [], "缺口径时一行数据都不该出去"


def test_caliber_warning_travels_with_the_data(tmp_path, monkeypatch):
    _write(tmp_path, SAMPLE, monkeypatch)
    body = client.get(URL).json()
    assert body["可读"] is True
    assert body["⚠这不是毛利"] == CALIBER


def test_both_cost_calibers_are_served_without_being_merged(tmp_path, monkeypatch):
    """两个口径的差异本身就是要看的东西，合并成一个总数会把它抹掉。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    row = client.get(URL).json()["项目"][0]
    assert row["业务台账成本"] == "12000.00" and row["金蝶归集成本"] == "11500.00"
    assert row["已知成本下限"] == "12000.00", "取大者——成本本就被低估，取小会让上限更虚高"
    assert not any(k in row for k in ("成本合计", "总成本"))


def test_cost_data_confidence_is_served_so_the_page_can_rank_by_it(tmp_path, monkeypatch):
    """「成本为 0 所以率 100%」不能排在真有数据的项目前面——页面得拿得到这个字段。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    assert client.get(URL).json()["项目"][0]["成本数据"] == "两口径均有数"


def test_reports_when_the_artifact_was_produced(tmp_path, monkeypatch):
    _write(tmp_path, SAMPLE, monkeypatch)
    assert client.get(URL).json()["产出时间"]
