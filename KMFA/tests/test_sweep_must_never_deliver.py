# -*- coding: utf-8 -*-
"""压测跑绝不许做真投递。

2026-07-29 Owner：「考勤通知依旧不能用」。查实的链条：

    压测节拍（每 30 分钟挑一个最久没跑的技能）挑中 attendance-evening
      → KMFA_SWEEP_RUN=1 当时**只给台账打标签、不关投递**
      → 晚间考勤在**早上 07:28** 真发了出去（台账：最近一次 07:28:56，
         而排程锚点是 17:31）
      → 到了真正的 17:31，去重守卫看到「今天已发过」→ NOT_SENT_DUPLICATE_GUARD
      → Owner 该收到的那一次，被吞了

这不是「压测吵了一下」，是**压测把真业务挤掉了**：Owner 在错的时间收到错的
报告，然后对的时间什么也收不到。仓里早就写着分法——「排程跑问『今天这件事
办成没有』，压测跑问『机器还转不转』」——压测做真投递，等于违反自己的定义。

判据分两层，缺一不可：
  1. **结构层**：`KMFA_SWEEP_RUN=1` 一律把投递关掉，不靠维护「哪些技能会
     发消息」的名单——名单一定会漏掉下一个新技能。
  2. **池子层**：有硬业务时点的考勤技能直接不进压测池。理由不是重复保险，
     而是压测跑会刷新「最近一次」，一刷新就再也答不出「今天 08:01 那次
     跑了没」——那是回答「我没收到」的唯一判据。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN_SKILL = REPO / "KMFA/deploy/skills-runtime/run_skill.sh"
CRONTAB = REPO / "KMFA/deploy/skills-runtime/crontab.txt"
PICKER = REPO / "KMFA/tools/pick_stalest_skill.py"


def test_sweep_forces_delivery_off_in_the_runner():
    """脚本里必须有「SWEEP=1 → DELIVERY=0」这条，且在算 --send/--dry-run **之前**。"""
    text = RUN_SKILL.read_text(encoding="utf-8")
    lines = text.splitlines()

    gate = next(
        (i for i, l in enumerate(lines)
         if re.search(r'KMFA_SWEEP_RUN.*=.*"1"|"\$\{KMFA_SWEEP_RUN:-0\}" = "1"', l)),
        None)
    assert gate is not None, "run_skill.sh 里没有压测闸——压测会拿 Owner 的钉钉当靶子"

    # 闸之后必须真把投递关掉
    tail = "\n".join(lines[gate:gate + 6])
    assert re.search(r"KMFA_DELIVERY_ENABLED\s*=\s*0", tail), \
        f"压测闸里没把投递关掉：\n{tail}"

    flag = next((i for i, l in enumerate(lines) if l.startswith("DELIVERY_FLAG=")), None)
    assert flag is not None, "找不到 DELIVERY_FLAG 那一行"
    assert gate < flag, (
        f"压测闸在第 {gate + 1} 行，而 --send/--dry-run 在第 {flag + 1} 行就算好了——"
        "关晚了等于没关")


def test_the_sweep_tick_actually_sets_the_flag():
    """闸只在 KMFA_SWEEP_RUN=1 时生效，那节拍就必须真的设它。"""
    cron = CRONTAB.read_text(encoding="utf-8")
    tick = next((l for l in cron.splitlines()
                 if "pick_stalest_skill" in l and not l.lstrip().startswith("#")), None)
    assert tick, "压测节拍不在 crontab 里"
    assert "KMFA_SWEEP_RUN=1" in tick, f"节拍没标成压测跑，闸就是死的：{tick}"


def test_time_anchored_delivery_skills_are_out_of_the_sweep_pool():
    sys.path.insert(0, str(REPO / "KMFA/tools"))
    import pick_stalest_skill as picker  # noqa: PLC0415

    pool = picker.sweepable_skills(RUN_SKILL)
    for skill in ("attendance-morning", "attendance-evening"):
        assert skill not in pool, (
            f"{skill} 还在压测池里。它一跑就往外发消息，且有硬业务时点；"
            "压测碰它会刷新「最近一次」，从此答不出「今天该跑的那次跑了没」")
    # runner 仍然**认识**它们——排除的是压测，不是把技能删了
    assert {"attendance-morning", "attendance-evening"} <= picker.known_skills(RUN_SKILL)


def test_the_pool_is_not_accidentally_emptied():
    """排除名单写错（比如拼错成前缀）不能把整个池子清空——那样压测会静默失效。"""
    sys.path.insert(0, str(REPO / "KMFA/tools"))
    import pick_stalest_skill as picker  # noqa: PLC0415

    known = picker.known_skills(RUN_SKILL)
    pool = picker.sweepable_skills(RUN_SKILL)
    assert pool, "压测池空了——压测等于关了"
    # 只准少掉排除名单里那些，不许多掉一个
    assert known - pool == set(picker.TIME_ANCHORED_DELIVERY_SKILLS), (
        f"池子少掉的不止排除名单：多掉了 {sorted(known - pool - set(picker.TIME_ANCHORED_DELIVERY_SKILLS))}")


def test_the_picker_still_returns_something_runnable(tmp_path):
    """端到端跑一次真脚本：还能挑出一个不在排除名单里的技能。"""
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(PICKER), "--run-skill", str(RUN_SKILL),
         "--ledger", str(ledger), "--min-age-hours", "0"],
        capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    picked = proc.stdout.strip()
    assert picked, "一个都挑不出来——压测等于关了"
    assert picked not in {"attendance-morning", "attendance-evening"}, \
        f"挑出了被排除的技能：{picked}"


def test_dry_run_status_does_not_trip_the_duplicate_guard():
    """压测关投递后写的状态，绝不能被去重守卫当成「已投递过」。

    否则这个修法会**制造**它要修的那个 bug：压测把当天名额占掉，
    真排程照样被吞——只是这次连消息都没发出去，比原来更糟。
    """
    sys.path.insert(0, str(REPO / "KMFA/app/backend"))
    sys.path.insert(0, str(REPO.parent))
    from KMFA.tools.dingtalk_attendance.notification_targets import (  # noqa: PLC0415
        DELIVERY_ATTEMPT_STATUSES,
    )
    from KMFA.tools.dingtalk_attendance.delivery_policy import (  # noqa: PLC0415
        DELIVERY_DISABLED_STATUS,
    )

    assert DELIVERY_DISABLED_STATUS not in DELIVERY_ATTEMPT_STATUSES, (
        f"{DELIVERY_DISABLED_STATUS} 被算成投递尝试了——压测跑会占掉当天名额，"
        "真排程到点被去重守卫吞掉")
