# -*- coding: utf-8 -*-
"""节拍绝大多数跳必须是空的——否则「摊开」就变成了「持续负载」。

差点发出去的东西（2026-07-28）：把「部署后一口气跑 13 个」改成「每 30 分钟挑一个」
之后，我就以为形状对了。**模拟一周才发现根本不对**：

    七天 336 跳 → 触发 336 次，空跳 0 次
    project-cost-refresh 被额外跑了 28 次（≈每天 4 次）

原因是共振：13 个技能 × 每跳 30 分钟 = 6.5 小时，而当时的闸是 6 小时——
一轮刚转完就又够格了，于是每一跳都触发。突发没被摊开，只是改成了持续负载，
而且最重的那几个（克隆私有库解析上千张表、tar 整个仓）一天跑四遍。
**同一个把线上打下线的问题，慢动作版。**

拿七天模拟挑出拐点：

      闸(h)   额外跑/天   重活/天
        6       48.0      12.0
       12       24.0       6.0
       20       14.4       3.6
       24        5.0       1.0   ← 拐点
       36        3.6       0.7

每个值覆盖率都满，所以选负载最低的拐点 24。它之所以是拐点：日排程技能
24 小时内会自己再跑、永远不够格被挑——节拍精确地只碰「等最久的那几个」。

本文件锚的就是这条性质：**空跳是常态**。它比「挑得对不对」更要紧——
挑错了顶多多跑一个技能，永不空跳会把机器压垮。
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from KMFA.tools.pick_stalest_skill import pick

REPO = Path(__file__).resolve().parents[2]
RUN_SKILL = REPO / "KMFA/deploy/skills-runtime/run_skill.sh"
TICK_MINUTES = 30
TZ = timezone(timedelta(hours=8))

# 各技能的真实排程频率（对着 crontab.txt 抄的）
SCHEDULE_HOURS = {
    "attendance-morning": 24, "attendance-evening": 24,
    "work-check-morning": 24, "work-check-evening": 24,
    "project-cost-refresh": 24, "upstream-archive": 24, "daily-backup": 24,
    "dws-keepalive": 4,
    "fund-weekly": 24 * 7, "self-audit": 24 * 7, "dws-bootstrap-groups": 24 * 7,
    "mgmt-monthly": 24 * 30,
    # attendance-bootstrap-targets 不在排程里，故意不列——它靠节拍碰
}
HEAVY = {"project-cost-refresh", "self-audit", "upstream-archive"}


def _simulate(min_age_hours: float, days: int = 7):
    start = datetime(2026, 7, 29, tzinfo=TZ)
    last = {s: start - timedelta(hours=min(h, 24 * 5)) for s, h in SCHEDULE_HOURS.items()}
    picked: dict[str, int] = {}
    ledger = Path(tempfile.mkdtemp()) / "ledger.jsonl"
    ticks = days * 24 * 60 // TICK_MINUTES

    for t in range(ticks):
        now = start + timedelta(minutes=TICK_MINUTES * t)
        for s, every in SCHEDULE_HOURS.items():          # 排程自己也在跑
            if (now - last[s]).total_seconds() / 3600 >= every:
                last[s] = now
        ledger.write_text(
            "".join(json.dumps({"skill": s, "ts": d.isoformat(timespec="seconds"), "rc": 0}) + "\n"
                    for s, d in last.items()), encoding="utf-8")
        got = pick(run_skill=RUN_SKILL, ledger=ledger,
                   min_age_hours=min_age_hours, now_iso=now.isoformat(timespec="seconds"))
        if got:
            picked[got] = picked.get(got, 0) + 1
            last[got] = now
    return picked, ticks


def _default_min_age() -> float:
    """从 CLI 默认值里取——测的必须是**线上真会用的**那个值。"""
    import argparse
    import inspect

    from KMFA.tools import pick_stalest_skill as mod

    src = inspect.getsource(mod.main)
    ns: dict = {"argparse": argparse}
    exec(compile(src, "<main>", "exec"), ns)                                  # noqa: S102
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-skill"); ap.add_argument("--ledger")
    for line in src.splitlines():
        if "--min-age-hours" in line and "default=" in line:
            return float(line.split("default=")[1].split(")")[0].strip())
    raise AssertionError("找不到 --min-age-hours 的默认值")


def test_most_ticks_do_nothing():
    """空跳必须是绝大多数。这是防「摊开变成持续负载」的那道锚。"""
    picked, ticks = _simulate(_default_min_age())
    fired = sum(picked.values())
    assert fired / ticks < 0.25, (
        f"{ticks} 跳里触发了 {fired} 次（{fired/ticks:.0%}）——"
        "节拍几乎不空，等于把突发改成了持续负载"
    )


def test_heavy_skills_are_not_run_more_than_once_a_day_extra():
    """重活（克隆私有库解析上千张表、tar 整个仓）一天最多额外一次。

    2026-07-28 的 6 小时闸下它们是每天 12 次——那正是把线上打下线的量级。
    """
    picked, _ = _simulate(_default_min_age())
    per_day = sum(picked.get(s, 0) for s in HEAVY) / 7
    assert per_day <= 1.5, f"重活每天被额外跑 {per_day:.1f} 次，太多"


def test_the_long_waiting_skills_still_get_covered():
    """降负载不能把覆盖降没了——月任务、周任务、没排程的都得被碰到。"""
    picked, _ = _simulate(_default_min_age())
    for s in ("mgmt-monthly", "fund-weekly", "self-audit", "dws-bootstrap-groups"):
        assert picked.get(s, 0) > 0, f"{s} 七天内一次都没被节拍碰到"


def test_a_never_run_skill_is_not_delayed_by_the_gate():
    """从没跑过的不受这道闸约束——它该在下一跳就被挑到。

    否则「不等自然时间」这条就成了空话：mgmt-monthly 那种运行次数 0 的，
    正是这套机制存在的理由。
    """
    ledger = Path(tempfile.mkdtemp()) / "l.jsonl"
    now = datetime(2026, 7, 29, tzinfo=TZ)
    ledger.write_text(
        "".join(json.dumps({"skill": s, "ts": now.isoformat(timespec="seconds"), "rc": 0}) + "\n"
                for s in SCHEDULE_HOURS), encoding="utf-8")   # 全部刚跑过
    got = pick(run_skill=RUN_SKILL, ledger=ledger,
               min_age_hours=_default_min_age(), now_iso=now.isoformat(timespec="seconds"))
    assert got == "attendance-bootstrap-targets", \
        f"从没跑过的没被优先挑中，挑的是 {got!r}"
