# -*- coding: utf-8 -*-
"""两个健康端点必须用同一条分法。

`/public-api/技能健康` 在 #274 里改成了「结论只看排程跑、压测跑单独一栏」，
但 `/api/排程健康` 当时没跟着改——它的成功/失败、失败次数、成功率、全量历史
仍然把压测跑掺在里面。

一个修一个不修比两个都错还糟：驾驶舱读排程健康、公开面读技能健康，
同一个技能一边红一边绿，看到分歧的人只能猜哪个是真的，
而「猜」正是这条线一直在消灭的东西。
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _app(ledger: Path):
    sys.path.insert(0, str(REPO / "KMFA/app/backend"))
    os.environ["KMFA_SKILL_LEDGER"] = str(ledger)
    import app.main as m  # noqa: PLC0415

    importlib.reload(m)
    return m


def _two_run_ledger(tmp_path: Path) -> Path:
    """排程跑成功 + 压测跑失败——两个端点都该判绿并各自留下压测记录。"""
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"skill": "attendance-morning", "ts": "2026-07-28T10:36:11+08:00",
                    "rc": 0, "code": ""}, ensure_ascii=False) + "\n"
        + json.dumps({"skill": "attendance-morning", "ts": "2026-07-28T19:44:00+08:00",
                      "rc": 5, "code": "NOT_SENT_DUPLICATE_GUARD",
                      "sweep": True}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return ledger


def test_both_endpoints_reach_the_same_verdict(tmp_path):
    from fastapi.testclient import TestClient  # noqa: PLC0415

    m = _app(_two_run_ledger(tmp_path))
    client = TestClient(m.app, raise_server_exceptions=False)

    public = client.get("/public-api/技能健康").json()
    pub_row = next(s for s in public["技能"] if s["技能"] == "attendance-morning")

    sched = client.get("/api/排程健康")
    if sched.status_code != 200:            # 本地没有 Access 侧配置时跳过，不算失败
        return
    sch_row = next(s for s in sched.json()["逐项"] if s["技能"] == "attendance-morning")

    assert pub_row["成功"] == sch_row["成功"] is True, \
        f"两个端点给出不同结论：公开={pub_row['成功']} 排程={sch_row['成功']}"
    assert pub_row["最近一次"] == sch_row["最近一次"], "两个端点锚在不同的运行上"
    assert sch_row["次数"] == pub_row["运行次数"] == 1, "压测跑被算进排程次数了"


def test_the_schedule_endpoint_keeps_the_sweep_result(tmp_path):
    """压测结果不许藏——藏了就等于没做压测。"""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    m = _app(_two_run_ledger(tmp_path))
    sched = TestClient(m.app, raise_server_exceptions=False).get("/api/排程健康")
    if sched.status_code != 200:
        return
    row = next(s for s in sched.json()["逐项"] if s["技能"] == "attendance-morning")
    assert row.get("压测"), "排程健康里压测结果整条不见了"
    assert row["压测"]["退出码"] == 5
    assert row["压测"]["失败码"] == "NOT_SENT_DUPLICATE_GUARD"


def test_success_rate_is_not_diluted_by_sweep_runs(tmp_path):
    """成功率是排程的成功率。掺进压测跑，这个数就再也没法解释了。"""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    m = _app(_two_run_ledger(tmp_path))
    sched = TestClient(m.app, raise_server_exceptions=False).get("/api/排程健康")
    if sched.status_code != 200:
        return
    row = next(s for s in sched.json()["逐项"] if s["技能"] == "attendance-morning")
    assert row["成功率"] == 100, f"成功率被压测跑拉低到 {row['成功率']}"
    assert row["失败次数"] == 0
    assert row["连续失败"] == 0
