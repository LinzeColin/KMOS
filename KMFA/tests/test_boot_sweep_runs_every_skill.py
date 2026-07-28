# -*- coding: utf-8 -*-
"""每次部署把所有技能跑一遍，不等自然排程。

Owner 2026-07-28：「所有的 skill 你全部都要主动 手动 压力检查运行状态，
不允许等待自然时间，那会浪费搁置很多时间」。

原来冷启动只做两件事，都不够：
  · 只重试**最近一次失败**的技能——从未跑过的（mgmt-monthly 运行次数 0）永远
    轮不到，因为它「没失败过」；上次侥幸成功、这次代码改动弄坏的，也轮不到；
  · 项目成本判据是「产物不在才算」——产物一旦存在就再不重算，于是新代码部署上去
    页面还显示旧算法的旧结果，要等次日 05:45。

周任务要等一周、月任务要等一月才知道死活，「改一版等一天」正是把一个月耗掉的模式。
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


def test_boot_sweep_exists_and_is_on_by_default():
    text = _entry()
    assert "KMFA_BOOT_SWEEP" in text
    assert '"${KMFA_BOOT_SWEEP:-1}" = "1"' in text, "默认必须是开——默认关等于没有这功能"


def test_the_skill_list_comes_from_run_skill_not_the_schedule():
    """清单的真源是 `run_skill.sh` 的 case 分支，不是排程。

    排程只说「什么时候跑」，不是「有哪些技能」。2026-07-28 真跑提取逻辑抓到：
    只看 crontab 会漏掉 `attendance-bootstrap-targets`（不在排程里，只由前置
    补跑触发），排程 12 个而台账 13 个。写死清单同样不行。
    """
    sweep = _entry()
    block = sweep[sweep.index("全量压测开始"):sweep.index("全量压测结束")]
    assert "run_skill.sh" in block and "crontab.txt" not in block, \
        "清单仍从排程取——会漏掉不在排程里的技能"


def test_the_sweep_is_serial_not_parallel():
    """并发会让多个技能同时抢 dws 登录态和稀疏克隆，
    把「压测」变成「制造假故障」。"""
    sweep = _entry()
    block = sweep[sweep.index("全量压测开始"):sweep.index("全量压测结束")]
    assert "sleep 20" in block, "技能之间没有间隔，flock 会互相踩"
    assert "&" not in block.replace("2>&1", "").replace("&&", ""), "压测块里有后台符号，会并发"


def test_the_sweep_yields_to_the_app():
    """压测不能把 Owner 的页面打下线。

    2026-07-28 首次全量压测跑到一半，线上连续 503 约 3 分钟才恢复
    （Coolify 同期报 running:healthy，也没有部署在进行中）。3.7GB 的机器上
    压测要克隆私有库、解析上千张表、tar 整个仓，跟 App 抢资源。
    """
    block = _entry()[_entry().index("全量压测开始"):_entry().index("全量压测结束")]
    assert "nice -n" in block, "压测没让出 CPU 优先级，App 会被挤掉"
    assert "sleep 20" in block, "技能之间只隔几秒，内存来不及回收"


def test_a_failing_skill_never_blocks_the_sweep():
    """一个技能挂了不能挡住后面的——否则第一个失败就等于压测没做。"""
    sweep = _entry()
    block = sweep[sweep.index("全量压测开始"):sweep.index("全量压测结束")]
    assert "|| true" in block


def _swept_skills():
    """按 entrypoint 里的同一条规则，从 run_skill.sh 抽技能名。

    `a|b)` 这种合并分支要拆开——2026-07-28 把两条 work-check 合并共用同一段
    源缺失守卫时，旧规则不认 `|`，压测清单会从 13 静默掉到 11。
    """
    runner = RUN_SKILL.read_text(encoding="utf-8")
    names = set()
    for arm in re.findall(r"^  ([a-z0-9|-]+)\)", runner, re.M):
        names.update(arm.split("|"))
    return names


def test_the_extraction_rule_matches_the_entrypoint_exactly():
    """测试里的抽取规则必须和 entrypoint 里那行**是同一条**。

    两边分头演化的话，测试会对着一份线上根本不会用的清单报绿。
    """
    entry_line = next(
        line for line in _entry().splitlines() if "grep -oE" in line and "run_skill.sh" in line
    )
    assert "[a-z0-9|-]+" in entry_line, "entrypoint 的抽取正则不认合并分支"
    assert "tr '|'" in _entry(), "entrypoint 抽出来后没把合并分支拆开"


def test_the_sweep_covers_every_skill_run_skill_knows():
    swept = _swept_skills()
    assert len(swept) >= 13, f"只抓到 {len(swept)} 个技能"
    for must in ("attendance-morning", "attendance-evening", "self-audit",
                 "upstream-archive", "project-cost-refresh", "mgmt-monthly"):
        assert must in swept, f"{must} 扫不到"


def test_the_skill_that_is_not_in_the_schedule_is_still_swept():
    """`attendance-bootstrap-targets` 不在 crontab 里——只看排程就会漏掉它。
    这条正是把提取来源从排程改成 run_skill.sh 的原因。"""
    scheduled = set(re.findall(r"run_skill\.sh ([a-z0-9-]+)",
                               CRONTAB.read_text(encoding="utf-8")))
    swept = _swept_skills()
    assert "attendance-bootstrap-targets" not in scheduled, \
        "它现在进排程了——那这条测试的前提变了，重新审一遍提取来源"
    assert "attendance-bootstrap-targets" in swept


def test_the_never_run_skill_is_covered():
    """mgmt-monthly 运行次数 0——它正是「只重试失败的」永远漏掉的那类。"""
    assert "mgmt-monthly" in _swept_skills()
