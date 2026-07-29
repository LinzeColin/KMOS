# -*- coding: utf-8 -*-
"""压测跑的结果不能顶掉排程跑的结论。

2026-07-28 全量压测第三次踩到同一类坑：**时间锚定的技能被拉到窗口外跑，
合法的拒绝被记成失败**。

  · attendance-evening 19:30 重跑 → 去重守卫拦下（17:32 已确认送达）
  · attendance-morning 19:44 重跑 → REALTIME_REMINDER_INTEGRITY_FAILED
    （晚上七点四十跑早班实时提醒，完整性当然对不上）

前两条已在 #273 里按「成因分开」处理，但根子在这儿：
「压测跑」和「排程跑」问的是两个不同的问题——

  排程跑问：**今天这件事办成了没有**。这是 Owner 要看的业务真相。
  压测跑问：**这个技能的机器还转不转**。Owner 要的「不等自然时间」是这个。

把两者混在一个时间线里，压测就会持续污染业务结论：早上真发成功了，
晚上压测一跑，页面变红。反过来把压测结果藏起来也不行——
那就等于没做压测，回到「改一版等一天」。

所以两条都留，但**分开报**：✅/❌ 只由排程跑决定，压测结果单独一栏。
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENTRY = REPO / "KMFA/deploy/skills-runtime/entrypoint.sh"
CRONTAB = REPO / "KMFA/deploy/skills-runtime/crontab.txt"
RUN_SKILL = REPO / "KMFA/deploy/skills-runtime/run_skill.sh"
MAIN = REPO / "KMFA/app/backend/app/main.py"


def test_the_sweep_marks_its_own_runs():
    """压测得先认领自己跑的那些，下游才分得开。

    压测在 #275 从 entrypoint 的一次性突发改成了 crontab 节拍（那一版把线上打下线三次），
    这条测试当时漏改、于是在 main 上一直红着。**主干上常红的测试是噪音**——
    它会盖住真失败，而且没人会去看第二次。判据跟着实现走：现在标记打在 crontab 那一跳上。
    """
    cron = CRONTAB.read_text(encoding="utf-8")
    ticks = [l for l in cron.splitlines()
             if "run_skill.sh" in l and not l.lstrip().startswith("#")
             and ("pick_stalest_skill" in l or ".refresh_requested" in l)]
    assert ticks, "找不到压测/重算那几跳"
    for line in ticks:
        assert "KMFA_SWEEP_RUN=1" in line, f"这一跳没打标，台账里分不出来：{line[:70]}"


def test_the_ledger_carries_the_mark():
    runner = RUN_SKILL.read_text(encoding="utf-8")
    assert "KMFA_SWEEP_RUN" in runner and '"sweep"' in runner, \
        "台账行里没有 sweep 字段，端点无从区分"


def _health(monkey_ledger: Path):
    """把台账指到临时文件后取一次公开健康。"""
    import importlib
    import os
    import sys

    sys.path.insert(0, str(REPO / "KMFA/app/backend"))
    os.environ["KMFA_SKILL_LEDGER"] = str(monkey_ledger)
    import app.main as m  # noqa: PLC0415

    importlib.reload(m)
    from fastapi.testclient import TestClient  # noqa: PLC0415

    return TestClient(m.app).get("/public-api/技能健康").json()


def test_a_sweep_failure_does_not_turn_a_successful_scheduled_run_red(tmp_path):
    """今天排程跑成功了，晚上压测因为窗口外失败——结论必须还是绿。"""
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"skill": "attendance-morning", "ts": "2026-07-28T10:36:11+08:00",
                    "rc": 0, "code": ""}, ensure_ascii=False) + "\n"
        + json.dumps({"skill": "attendance-morning", "ts": "2026-07-28T19:44:00+08:00",
                      "rc": 5, "code": "NOT_SENT_REALTIME_REMINDER_INTEGRITY_FAILED",
                      "sweep": True}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    row = next(s for s in _health(ledger)["技能"] if s["技能"] == "attendance-morning")
    assert row["成功"] is True, "压测在窗口外的失败把当天真成功的排程结论顶红了"
    assert row["最近一次"] == "2026-07-28T10:36:11+08:00", "结论该锚在排程跑那一次"


def test_the_sweep_result_is_still_reported(tmp_path):
    """压测结果不许藏起来——藏了就等于没做压测，回到「改一版等一天」。"""
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"skill": "attendance-morning", "ts": "2026-07-28T10:36:11+08:00",
                    "rc": 0, "code": ""}, ensure_ascii=False) + "\n"
        + json.dumps({"skill": "attendance-morning", "ts": "2026-07-28T19:44:00+08:00",
                      "rc": 5, "code": "NOT_SENT_REALTIME_REMINDER_INTEGRITY_FAILED",
                      "sweep": True}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    row = next(s for s in _health(ledger)["技能"] if s["技能"] == "attendance-morning")
    assert row.get("压测"), "压测结果整条不见了"
    assert row["压测"]["退出码"] == 5
    assert row["压测"]["失败码"] == "NOT_SENT_REALTIME_REMINDER_INTEGRITY_FAILED"


def test_a_skill_only_ever_swept_is_not_reported_as_scheduled_success(tmp_path):
    """只被压测跑过、排程从没跑过——不许显示成「排程正常」。

    这条防的是把压测当排程用：mgmt-monthly 那种从未真跑过的，
    绝不能因为压测碰过一次就显示成健康。
    """
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"skill": "mgmt-monthly", "ts": "2026-07-28T19:37:51+08:00",
                    "rc": 8, "code": "NOT_BUILT", "sweep": True}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    row = next(s for s in _health(ledger)["技能"] if s["技能"] == "mgmt-monthly")
    assert row["成功"] is None, "排程从没跑过却给了成功/失败的结论"
    assert row["最近一次"] is None
    assert row["压测"]["退出码"] == 8, "压测跑过这件事本身要留着"


def test_an_unmarked_ledger_behaves_exactly_as_before(tmp_path):
    """老台账行没有 sweep 字段——必须当排程跑处理，不能因为改造把历史判没了。"""
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"skill": "self-audit", "ts": "2026-07-28T16:51:03+08:00",
                    "rc": 0, "code": ""}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    row = next(s for s in _health(ledger)["技能"] if s["技能"] == "self-audit")
    assert row["成功"] is True
    assert row["运行次数"] == 1
