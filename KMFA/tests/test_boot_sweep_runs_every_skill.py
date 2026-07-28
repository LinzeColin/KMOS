# -*- coding: utf-8 -*-
"""每个技能都要被主动跑到，但不能靠一次性突发。

Owner 2026-07-28：「所有的 skill 你全部都要主动 手动 压力检查运行状态，
不允许等待自然时间，那会浪费搁置很多时间」。

原来冷启动只做两件事，都不够：
  · 只重试**最近一次失败**的技能——从未跑过的（mgmt-monthly 运行次数 0）永远
    轮不到，因为它「没失败过」；上次侥幸成功、这次代码改动弄坏的，也轮不到；
  · 项目成本判据是「产物不在才算」——产物一旦存在就再不重算，于是新代码部署上去
    页面还显示旧算法的旧结果，要等次日 05:45。

第一版的解法是「部署后一口气把 13 个技能全跑一遍」。**那一版把线上打下线三次**
（最长 5.5 分钟，恢复后又掉；私有库台账证实掉线期间压测正在跑）。
nice -n 19 加上把间隔从 5s 拉到 20s 都不够——问题不在参数在形状：
这台机器 3.7GB，而压测里 project-cost-refresh 要克隆私有库解析上千张表、
self-audit 要 tar 整个仓。

现在的形状：压测摊成 crontab 节拍，每跳只跑**一个**最久没跑的。
单跑一个是正常负载（排程本来天天这么跑），13 个背靠背才是突发。
本文件锚的是「覆盖不能丢」——不管用什么形状，每个技能都得被碰到。
"""
import re
from pathlib import Path

ENTRY = Path(__file__).resolve().parents[1] / "deploy" / "skills-runtime" / "entrypoint.sh"
CRONTAB = Path(__file__).resolve().parents[1] / "deploy" / "skills-runtime" / "crontab.txt"
RUN_SKILL = Path(__file__).resolve().parents[1] / "deploy" / "skills-runtime" / "run_skill.sh"


def _entry():
    return ENTRY.read_text(encoding="utf-8")


def test_project_cost_is_recomputed_on_every_deploy():
    """判据不能再是「产物不在」——那等于新代码永远配旧结果。"""
    text = _entry()
    assert "每次部署都算" in text
    assert not re.search(r"\[\s*!\s*-s\s+/var/log/kmfa/project_cost/recent_completed\.json\s*\]", text), \
        "项目成本仍按「产物不在」判定，部署后不会重算"


def test_the_startup_burst_is_gone():
    """启动时一口气全跑 = 把线上打下线的那个形状，不许复活。"""
    text = _entry()
    assert "全量压测开始" not in text, "启动时的一次性全量压测又回来了"
    assert "打下线" in text, "拿掉了却没写明为什么——下一个人会照着原样加回来"


def test_the_tick_exists_and_marks_itself_as_a_sweep():
    cron = CRONTAB.read_text(encoding="utf-8")
    assert "pick_stalest_skill" in cron, "摊开的压测节拍没了，等于压测整个消失"
    assert "KMFA_SWEEP_RUN=1" in cron, "节拍跑没标成压测，会顶掉排程的业务结论"


def test_the_tick_runs_one_skill_at_a_time():
    """一跳一个——多跑几个就退回突发了。"""
    line = next(l for l in CRONTAB.read_text(encoding="utf-8").splitlines()
                if "pick_stalest_skill" in l)
    assert line.count("run_skill.sh") == 1, f"一跳跑了不止一个技能：{line}"
    assert "nice -n" in line, "节拍没让出 CPU 优先级"


def _known_skills():
    """技能清单的真源是 run_skill.sh 的 case 分支，`a|b)` 要拆开。

    2026-07-28 两次抓获：只看 crontab 会漏掉 `attendance-bootstrap-targets`
    （不在排程里，只由前置补跑触发）；把两条 work-check 合并成 `a|b)` 之后，
    不认 `|` 的规则会让清单从 13 静默掉到 11。两种漏法的表现都是
    「那个技能一直没跑」，跟排程没配一模一样、极难查。
    """
    runner = RUN_SKILL.read_text(encoding="utf-8")
    names = set()
    for arm in re.findall(r"^  ([a-z0-9|-]+)\)", runner, re.M):
        names.update(arm.split("|"))
    return names


def test_the_picker_and_the_tests_use_the_same_extraction_rule():
    """挑选器和测试必须按同一条规则抽技能名，否则测试对着一份线上不用的清单报绿。"""
    from KMFA.tools.pick_stalest_skill import known_skills

    assert known_skills(RUN_SKILL) == _known_skills()


def test_every_skill_is_reachable_by_the_tick():
    swept = _known_skills()
    assert len(swept) >= 13, f"只抓到 {len(swept)} 个技能"
    for must in ("attendance-morning", "attendance-evening", "self-audit",
                 "upstream-archive", "project-cost-refresh", "mgmt-monthly",
                 "work-check-morning", "work-check-evening"):
        assert must in swept, f"{must} 扫不到"


def test_the_skill_that_is_not_in_the_schedule_is_still_reachable():
    """`attendance-bootstrap-targets` 不在 crontab 的技能行里——只看排程就会漏掉它。"""
    scheduled = set(re.findall(r"run_skill\.sh ([a-z0-9-]+)",
                               CRONTAB.read_text(encoding="utf-8")))
    swept = _known_skills()
    assert "attendance-bootstrap-targets" not in scheduled, \
        "它现在进排程了——那这条测试的前提变了，重新审一遍提取来源"
    assert "attendance-bootstrap-targets" in swept


def test_the_never_run_skill_is_covered():
    """mgmt-monthly 运行次数 0——它正是「只重试失败的」永远漏掉的那一类。"""
    assert "mgmt-monthly" in _known_skills()
