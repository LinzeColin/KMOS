# -*- coding: utf-8 -*-
"""项目成本正式运行态接口的边界测试。

Owner 2026-07-27：「我根本没有看到项目成本，我说了我要最近完工的项目成本」。
所以这个接口存在的意义是**把数送上页面**，那么它最该防的就是「页面看着正常、其实没数」：

  · 产物缺失时返回空数组 → 页面显示"没有已完工项目"，与"还没算出来"长得一模一样，
    意思却完全相反。必须 `可读:false` + 具名原因。
  · 独立观察面被并入正式成本 → 造成重复或错算。观察面必须并排保留。
"""
import json
import hashlib

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)
URL = "/api/项目成本/完工"

SAMPLE = {
    "schema_version": "kmfa.project_cost.current.v4",
    "快照ID": "kmfa-pc-2099-recent",
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
        "完工排序": "2099-01-31", "含税合同金额": "100000.00",
        "项目过账实际": "1234.56", "项目应计": "765.44",
        "项目已发生成本": "2000.00", "项目成本": "2000.00",
        "有效合同额": "5000.00", "毛利": "3000.00",
        "毛利率": "60.00%", "毛利率基点": 6000,
        "收入与毛利状态": "READY",
        "主营成本已结转": "321.00", "状态表已报直接成本": "654.00",
        "支付系统已付观察": None,
        "项目成本覆盖": "FULL_SELECTED_GL_PERIOD;POSTING_PRESENT",
        "报表归类": {"material": "500.00", "own_labor": "1500.00"},
    }],
}


def _write(tmp_path, payload, monkeypatch):
    payload = json.loads(json.dumps(payload, ensure_ascii=False))
    workbook = tmp_path / "sealed-recent.xlsx"
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


def test_serves_formal_cost_and_independent_observations_without_merging(tmp_path, monkeypatch):
    _write(tmp_path, SAMPLE, monkeypatch)
    body = client.get(URL).json()
    assert body["可读"] is True
    row = body["项目"][0]
    assert row["项目过账实际"] == "1234.56"
    assert row["项目应计"] == "765.44"
    assert row["项目已发生成本"] == "2000.00"
    assert row["主营成本已结转"] == "321.00"
    assert row["状态表已报直接成本"] == "654.00"
    assert row["项目成本覆盖"]
    assert not any(k in row for k in ("成本合计", "总成本")), "不得生成无来源的合并总数"


def test_reports_when_the_artifact_was_produced(tmp_path, monkeypatch):
    """没有产出时间就分不出「今天的数」和「三个月前的数」。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    assert client.get(URL).json()["产出时间"]


def test_caliber_and_algorithm_locks_travel_with_the_data(tmp_path, monkeypatch):
    """口径与算法锁必须跟着数走；只给数字不给口径，等于给了一个不能引用的数。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    body = client.get(URL).json()
    assert body["口径"]["正式成本"] and body["口径"]["独立观察面"]
    assert body["锁定的算法"]
