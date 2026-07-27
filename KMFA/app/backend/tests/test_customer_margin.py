# -*- coding: utf-8 -*-
"""客户毛利接口的边界测试。

这一页存在的前提是：项目维度救不回来，而客户维度是完整的。
它最该防的是**把关联方混进外部客户**——集团自有公司之间的往来不是经营成果，
混算会把毛利率拉到失真（实测关联方约 68%、外部客户约 42%）。
"""
import json

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)
URL = "/api/客户毛利"

SAMPLE = {
    "schema_version": "kmfa.customer_margin.v1",
    "口径": {"收入": "主营业务收入贷方发生额", "成本": "生产成本借方发生额", "边界": "已入账口径"},
    "分档说明": "看对外经营真实性请只读『外部客户』那一档",
    "分档汇总": {
        "外部客户": {"家数": 2, "收入": "1000", "成本": "600", "毛利": "400", "毛利率": "40.0%"},
        "关联方": {"家数": 1, "收入": "9000", "成本": "100", "毛利": "8900", "毛利率": "98.9%"},
    },
    "客户数": 3,
    "客户": [
        {"客户": "11.049_某开明公司", "类别": "关联方", "收入": "9000", "已入账成本": "100",
         "毛利": "8900", "毛利率": "98.9%", "涉及项目数": 1, "活跃月份数": 12, "数据提示": []},
        {"客户": "29.005_某碱业", "类别": "外部客户", "收入": "600", "已入账成本": "900",
         "毛利": "-300", "毛利率": "-50.0%", "涉及项目数": 28, "活跃月份数": 15, "数据提示": []},
        {"客户": "19.023_某钢铁", "类别": "外部客户", "收入": "400", "已入账成本": "-300",
         "毛利": "700", "毛利率": "175.0%", "涉及项目数": 10, "活跃月份数": 15,
         "数据提示": ["成本为负（红冲多于发生），毛利率不是真实经营结果"]},
    ],
}


def _write(tmp_path, payload, monkeypatch):
    path = tmp_path / "customer_margin.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "CUSTOMER_MARGIN_PATH", path)


def test_missing_artifact_is_not_an_empty_customer_list(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "CUSTOMER_MARGIN_PATH", tmp_path / "nope.json")
    body = client.get(URL).json()
    assert body["可读"] is False and body["原因"] and body["客户"] == []


def test_related_parties_are_kept_separate_from_external(tmp_path, monkeypatch):
    """混算会把毛利率拉到失真——分档必须原样送到前端。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    body = client.get(URL).json()
    assert set(body["分档汇总"]) == {"外部客户", "关联方"}
    assert body["分档汇总"]["外部客户"]["毛利率"] == "40.0%"
    assert "合计" not in body["分档汇总"], "四档不得被合并成一个总数"


def test_data_flags_travel_with_each_customer(tmp_path, monkeypatch):
    """成本为负的那家毛利率 175%——必须带着提示，不能当成经营成果。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    row = next(c for c in client.get(URL).json()["客户"] if c["客户"].startswith("19.023"))
    assert row["数据提示"], "异常客户必须带数据提示"


def test_caliber_and_production_time_are_present(tmp_path, monkeypatch):
    _write(tmp_path, SAMPLE, monkeypatch)
    body = client.get(URL).json()
    assert body["口径"]["收入"] and body["口径"]["成本"]
    assert body["产出时间"]
