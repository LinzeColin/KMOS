# -*- coding: utf-8 -*-
"""压测改成「每跳一个」，不再一口气跑 13 个。

2026-07-28 实测：部署后一口气全跑一遍，当天把线上打下线三次
（最长 5.5 分钟，恢复后又掉）。这台机器 3.7GB，而压测里
project-cost-refresh 要克隆私有库解析上千张表、self-audit 要 tar 整个仓。
加 nice -n 19、间隔 5s→20s **都不够**——所以不是调参能解决的，是形状不对。

关键在于：**单跑一个技能是正常负载**，排程本来天天就在这么跑。
出问题的是「13 个背靠背」这个突发。改成每跳挑一个最久没跑的，
摊开到一天里，既满足「不等自然时间」（从没跑过的几小时内会被碰到，
不是永远轮不到），又不制造任何突发。
"""
from __future__ import annotations

import json
from pathlib import Path

from KMFA.tools.pick_stalest_skill import known_skills, pick

REPO = Path(__file__).resolve().parents[2]
RUN_SKILL = REPO / "KMFA/deploy/skills-runtime/run_skill.sh"
CRONTAB = REPO / "KMFA/deploy/skills-runtime/crontab.txt"
ENTRY = REPO / "KMFA/deploy/skills-runtime/entrypoint.sh"

NOW = "2026-07-28T20:00:00+08:00"



def _tick_cron_line():
    """取节拍那条**可执行**的 cron 行。

    按内容找行会找到注释——注释里也提到 pick_stalest_skill.py。
    这个坑今晚踩了两次（前一次是 run_skill.sh 里那条幽灵路径的测试）：
    判断「代码里有没有」时，一律先把注释剔掉。
    """
    return next(l for l in CRONTAB.read_text(encoding="utf-8").splitlines()
                if "pick_stalest_skill" in l and not l.lstrip().startswith("#"))

def _ledger(tmp_path: Path, rows: list[tuple[str, str]]) -> Path:
    p = tmp_path / "ledger.jsonl"
    p.write_text(
        "".join(json.dumps({"skill": s, "ts": t, "rc": 0}, ensure_ascii=False) + "\n"
                for s, t in rows),
        encoding="utf-8",
    )
    return p


def test_it_still_knows_all_thirteen_skills():
    """清单真源仍是 run_skill.sh 的 case 分支，合并分支要拆开。"""
    names = known_skills(RUN_SKILL)
    assert len(names) >= 13, f"只认出 {len(names)} 个：{sorted(names)}"
    for must in ("work-check-morning", "work-check-evening", "mgmt-monthly",
                 "attendance-bootstrap-targets"):
        assert must in names


def test_a_never_run_skill_wins(tmp_path):
    """从没跑过的排最前——它们正是「只重试失败的」永远轮不到的那一类。"""
    names = known_skills(RUN_SKILL)
    rows = [(n, "2026-07-28T19:00:00+08:00") for n in names if n != "mgmt-monthly"]
    got = pick(run_skill=RUN_SKILL, ledger=_ledger(tmp_path, rows),
               min_age_hours=6.0, now_iso=NOW)
    assert got == "mgmt-monthly"


def test_the_stalest_wins_when_everyone_has_run(tmp_path):
    names = sorted(known_skills(RUN_SKILL))
    rows = [(n, "2026-07-28T19:00:00+08:00") for n in names]
    rows[0] = (names[0], "2026-07-20T01:00:00+08:00")      # 八天没跑
    got = pick(run_skill=RUN_SKILL, ledger=_ledger(tmp_path, rows),
               min_age_hours=6.0, now_iso=NOW)
    assert got == names[0]


def test_nothing_is_picked_when_everything_is_fresh(tmp_path):
    """都刚跑过就什么都不挑——不设这道闸，最闲的那个会被反复挑中，
    真正没人碰的反而轮不上。"""
    rows = [(n, "2026-07-28T19:30:00+08:00") for n in known_skills(RUN_SKILL)]
    got = pick(run_skill=RUN_SKILL, ledger=_ledger(tmp_path, rows),
               min_age_hours=6.0, now_iso=NOW)
    assert got is None


def test_a_missing_ledger_still_picks_something(tmp_path):
    """台账读不到时不能静默什么都不做——那就等于压测没了。"""
    got = pick(run_skill=RUN_SKILL, ledger=tmp_path / "nope.jsonl",
               min_age_hours=6.0, now_iso=NOW)
    assert got in known_skills(RUN_SKILL)


def test_an_unparsable_timestamp_is_treated_as_very_stale(tmp_path):
    """读不懂时间就当很久没跑——宁可多碰一次，不要静默不碰。"""
    p = tmp_path / "ledger.jsonl"
    p.write_text(json.dumps({"skill": "self-audit", "ts": "不是时间", "rc": 0}) + "\n",
                 encoding="utf-8")
    got = pick(run_skill=RUN_SKILL, ledger=p, min_age_hours=6.0, now_iso=NOW)
    assert got is not None


def test_the_burst_is_gone_from_the_entrypoint():
    """启动时不再一口气全跑——那是把线上打下线的那个形状。"""
    text = ENTRY.read_text(encoding="utf-8")
    assert "全量压测开始" not in text, "启动时的一次性全量压测还在"


def test_the_tick_is_scheduled_and_marked_as_a_sweep():
    """摊开的压测要进排程，并且标成压测跑——否则又会污染业务结论。"""
    cron = CRONTAB.read_text(encoding="utf-8")
    assert "pick_stalest_skill" in cron, "没有摊开的压测节拍，等于压测整个没了"
    assert "KMFA_SWEEP_RUN=1" in cron, "节拍跑的没标成压测，会顶掉排程结论"


def test_the_tick_has_a_kill_switch_that_actually_works():
    """压测要能被关掉——2026-07-28 它把线上打下线时就是靠关它止的血。

    开关必须由 entrypoint 在**渲染 crontab 时**落地，不能写在 cron 行里：
    cron.d 不做变量展开、cron 也不继承容器 ENV（这仓已为此栽过两次）。
    """
    text = ENTRY.read_text(encoding="utf-8")
    assert "KMFA_BOOT_SWEEP" in text, "压测没有总闸，出事时只能改代码重新部署"
    assert "grep -v pick_stalest_skill" in text, \
        "关掉时没有真把节拍行从 crontab 里摘掉"


def test_turning_the_tick_off_does_not_touch_the_real_schedule():
    """关压测不能顺手把业务排程一起关了。"""
    text = ENTRY.read_text(encoding="utf-8")
    off = text[text.index("KMFA_BOOT_SWEEP=0 关闭"):][:400]
    assert "pick_stalest_skill" in off, "关的应当只是节拍那一行"
    for business in ("attendance-morning", "upstream-archive", "project-cost-refresh"):
        assert business not in off, f"关压测把 {business} 也过滤掉了"


def test_an_empty_tick_is_not_an_error():
    """挑不到东西是**常态**：一天 48 跳、只有 13 个技能，绝大多数跳都该是空的。

    少了兜底，正常的空跳会让整行以非零退出，cron 每半小时记一笔像失败的东西，
    真失败就淹在里面了——「红灯天天亮又次次不是真问题」的另一种长法。
    """
    line = _tick_cron_line()
    assert "|| true" in line or line.rstrip().endswith("fi"), \
        f"空跳会让 cron 记成失败：{line}"
