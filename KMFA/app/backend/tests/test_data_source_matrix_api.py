# -*- coding: utf-8 -*-
"""数据源矩阵接口的边界测试。

Owner 2026-07-27：「我根本看不到你的数据源矩阵」+「我都不知道你哪些是好了哪些没好」。
所以这个接口最该防的是**把「没到位」显示成「到位」**——那正是让人分不清好坏的东西。

尤其要防一种：文件在、但一行都读不出来（WPS 导出谎报尺寸）。
只查文件存在性的话，这种会显示成绿的。
"""
import json

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)
URL = "/api/数据源矩阵"

SAMPLE = {
    "schema_version": "kmfa.data_source_matrix.measured.v1",
    "平台数": 4, "输入总数": 13, "已接入": 11, "缺输入": 2, "读不出来": 0,
    "系统自动收集的": 2, "还靠人工放文件的": 10, "完全没接的": 1,
    "平台": [{
        "平台": "红圈", "id": "PLT-REDCIRCLE", "采集方式": "人工导出", "采集周期": "不定期",
        "输入数": 1, "已接入": 1, "自动收集": 0,
        "输入": [{"id": "IN-RC-CONTRACT", "name": "红圈主合同", "collection": "manual",
                  "文件数": 1, "行数": 4342, "数据截至": "2026-07-05",
                  "状态": "已接入", "feeds": ["项目成本"], "blocker": None}],
    }],
}


def _write(tmp_path, payload, monkeypatch):
    path = tmp_path / "data_source_matrix.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "DATA_SOURCE_MATRIX_PATH", path)
    return path


def test_missing_artifact_says_so_instead_of_an_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DATA_SOURCE_MATRIX_PATH", tmp_path / "nope.json")
    body = client.get(URL).json()
    assert body["可读"] is False and body["原因"] and body["平台"] == []


def test_serves_the_three_things_that_make_the_matrix_useful(tmp_path, monkeypatch):
    """该有什么（声明）/ 实际有什么（实测）/ 谁在收（自动化到哪一步）——缺一个都不算数。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    body = client.get(URL).json()
    slot = body["平台"][0]["输入"][0]
    assert slot["name"] and slot["状态"]                      # 该有什么 + 到没到位
    assert slot["行数"] == 4342 and slot["数据截至"]           # 实测，不是「文件在」
    assert body["系统自动收集的"] is not None                  # 谁在收
    assert body["还靠人工放文件的"] is not None


def test_collection_reality_is_not_collapsed_into_a_single_ok_number(tmp_path, monkeypatch):
    """『已接入 11』不能替代『其中只有 2 个是系统自己收的』——合并就把自动化差距抹掉了。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    body = client.get(URL).json()
    assert body["系统自动收集的"] != body["已接入"], "自动收集与已接入是两件事，不得混为一谈"


def test_unreadable_counts_separately_from_missing(tmp_path, monkeypatch):
    """文件在但读不出来 ≠ 文件不在。前者查文件存在性会显示成绿的。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    body = client.get(URL).json()
    assert "读不出来" in body and "缺输入" in body


def test_reports_when_it_was_produced(tmp_path, monkeypatch):
    _write(tmp_path, SAMPLE, monkeypatch)
    assert client.get(URL).json()["产出时间"]


def test_download_is_404_not_an_empty_file_when_absent(tmp_path, monkeypatch):
    """给一个空 CSV 比 404 更糟——下载的人会以为矩阵是空的。"""
    _write(tmp_path, SAMPLE, monkeypatch)
    monkeypatch.setattr(main, "DATA_SOURCE_MATRIX_CSV", tmp_path / "nope.csv")
    assert client.get(URL).json()["可下载"] is False
    assert client.get("/api/数据源矩阵/下载").status_code == 404


def test_download_serves_the_csv_when_present(tmp_path, monkeypatch):
    _write(tmp_path, SAMPLE, monkeypatch)
    csv = tmp_path / "m.csv"
    csv.write_text("平台,输入\n红圈,红圈主合同\n", encoding="utf-8-sig")
    monkeypatch.setattr(main, "DATA_SOURCE_MATRIX_CSV", csv)
    assert client.get(URL).json()["可下载"] is True
    response = client.get("/api/数据源矩阵/下载")
    assert response.status_code == 200 and "红圈主合同" in response.text
