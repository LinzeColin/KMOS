# -*- coding: utf-8 -*-
"""归档目标群勾选接口的边界测试。

Owner 2026-07-27：「dws 上游存档是增量存档，他也需要前端控制器筛选目标群」。
此前链路缺这一环：自举产出候选、归档要已确认，中间没人勾选，归档长期 rc=4。

这个接口有写入能力，所以最该防的是**从请求里凭空引入群** ——
那等于让调用方指定归档去拉任意会话。候选清单是白名单，不在里面的一律拒。
"""
import json

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)
URL = "/api/归档目标群"
CANDIDATES = {"schema_version": "kmfa.dws.candidate_groups.v1", "群数": 2,
              "群": [{"id": "cid_a", "name": "甲群"}, {"id": "cid_b", "name": "乙群"}]}


def _setup(tmp_path, monkeypatch, with_selection=None):
    cand = tmp_path / "candidate_groups.json"
    cand.write_text(json.dumps(CANDIDATES, ensure_ascii=False), encoding="utf-8")
    sel = tmp_path / "selected_groups.json"
    if with_selection is not None:
        sel.write_text(json.dumps({"已选群": with_selection}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "DWS_CANDIDATE_PATH", cand)
    monkeypatch.setattr(main, "DWS_SELECTED_PATH", sel)
    return cand, sel


def test_missing_candidates_says_so_and_does_not_pretend_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DWS_CANDIDATE_PATH", tmp_path / "nope.json")
    monkeypatch.setattr(main, "DWS_SELECTED_PATH", tmp_path / "sel.json")
    body = client.get(URL).json()
    assert body["可读"] is False and body["原因"] and body["候选"] == []


def test_lists_candidates_and_current_selection(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, with_selection=["cid_b"])
    body = client.get(URL).json()
    assert body["可读"] is True
    assert [g["id"] for g in body["候选"]] == ["cid_a", "cid_b"]
    assert body["已选"] == ["cid_b"]


def test_saving_persists_the_selection(tmp_path, monkeypatch):
    _, sel = _setup(tmp_path, monkeypatch)
    r = client.post(URL, json={"已选群": ["cid_a"]})
    assert r.status_code == 200 and r.json()["已保存"] == 1
    assert json.loads(sel.read_text(encoding="utf-8"))["已选群"] == ["cid_a"]


def test_unknown_group_id_is_rejected(tmp_path, monkeypatch):
    """写入接口最危险的一条：请求里凭空出现的群 = 让调用方指定归档去拉任意会话。"""
    _setup(tmp_path, monkeypatch)
    r = client.post(URL, json={"已选群": ["cid_a", "偷偷塞进来的群"]})
    assert r.status_code == 400 and "不在候选清单" in r.json()["detail"]


def test_malformed_body_is_rejected(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert client.post(URL, json={"已选群": "不是数组"}).status_code == 400


def test_saving_without_candidates_is_a_conflict(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DWS_CANDIDATE_PATH", tmp_path / "nope.json")
    monkeypatch.setattr(main, "DWS_SELECTED_PATH", tmp_path / "sel.json")
    assert client.post(URL, json={"已选群": []}).status_code == 409
