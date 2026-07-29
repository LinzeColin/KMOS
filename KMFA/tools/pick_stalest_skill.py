#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""挑一个「最久没跑」的技能名打到 stdout；都跑过了就什么都不打。

为什么需要它（2026-07-28 线上实测逼出来的）：

Owner 要的是「所有 skill 主动压测，不允许等待自然时间」。第一版做成**部署后
一口气把 13 个技能全跑一遍**，结果当天把线上打下线三次——最长一次 5.5 分钟，
反复起来又掉。这台机器 3.7GB，而压测里 project-cost-refresh 要克隆私有库
再解析上千张表、self-audit 要 tar 整个仓，跟 App 抢资源。
加了 nice -n 19、把间隔从 5s 拉到 20s，**都不够**。

关键在于：**单跑一个技能是正常负载**——排程本来天天就在这么跑。
出问题的是「13 个背靠背」这个突发。所以不调参，改形状：
每个 cron tick 只挑一个最久没跑的跑一遍，摊开到一天里。
13 个技能、半小时一跳，六个多小时全覆盖——从没跑过的（mgmt-monthly 曾经
运行次数 0）几小时内就会被碰到，而不是永远轮不到。这既满足了
「不等自然时间」，又不制造任何突发。

判据只看**压测跑**之外的东西吗？不——这里看的是「上一次被跑到」，
排程跑和压测跑都算：目的是「每个技能都被碰过」，谁碰的不重要。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 技能清单的真源是 run_skill.sh 的 case 分支——排程只说「什么时候跑」，
# 不说「有哪些技能」。`a|b)` 合并分支要拆开，否则那两个会被静默漏掉。
CASE_ARM = re.compile(r"^  ([a-z0-9|-]+)\)", re.M)

#: 压测**不碰**的技能：有硬业务时点、且一跑就往外发东西的。
#:
#: 2026-07-29 Owner：「考勤通知依旧不能用」。压测挑中 attendance-evening，
#: 于是**晚间考勤在早上 07:28 发了出去**；到了真正的 17:31，去重守卫看到
#: 「今天已发过」，把该发的那次吞了。run_skill.sh 现在会给压测跑强制关投递，
#: 那是结构性的兜底；这里再把它们直接排除，理由是另一件事：
#:
#: 压测跑也会刷新「最近一次」。只要压测碰过考勤，就再也答不出
#: 「今天 08:01 那次到底跑了没」——而这恰恰是唯一能回答 Owner
#: 「我没收到」的判据。把它们留给排程独占，那根指针才有意义。
#:
#: 代价是这两个技能不再被压测覆盖。这是**故意**的：它们本来就每天准点跑两次，
#: 从不缺少「机器还转不转」的证据。
TIME_ANCHORED_DELIVERY_SKILLS = frozenset({"attendance-morning", "attendance-evening"})


def known_skills(run_skill: Path) -> set[str]:
    """runner **认识**的全部技能。故意不在这里做排除：

    「有哪些技能」和「压测跑哪些」是两件事，混成一个函数会让
    「挑选器和测试用同一条抽取规则」那条门禁失去意义——它比的就是抽取规则本身。
    """
    names: set[str] = set()
    for arm in CASE_ARM.findall(run_skill.read_text(encoding="utf-8")):
        names.update(arm.split("|"))
    return names


def sweepable_skills(run_skill: Path) -> set[str]:
    """压测**允许碰**的技能 = 认识的全部 − 有硬业务时点且会往外发的。"""
    return known_skills(run_skill) - TIME_ANCHORED_DELIVERY_SKILLS


def last_seen(ledger: Path, names: set[str]) -> dict[str, str]:
    seen: dict[str, str] = {}
    try:
        text = ledger.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return seen
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        skill, ts = row.get("skill"), row.get("ts")
        if skill in names and ts:
            seen[skill] = max(seen.get(skill, ""), str(ts))
    return seen


def pick(*, run_skill: Path, ledger: Path, min_age_hours: float, now_iso: str) -> str | None:
    names = sweepable_skills(run_skill)
    if not names:
        return None
    seen = last_seen(ledger, names)

    never = sorted(n for n in names if n not in seen)
    if never:
        # 从没跑过的优先——它们正是「只重试失败的」永远轮不到的那一类。
        return never[0]

    oldest = min(names, key=lambda n: (seen[n], n))
    # 刚跑过的不重复碰：不设这道闸，一天下来最闲的那个会被反复挑中，
    # 而真正没人碰的反而轮不上。
    if _hours_between(seen[oldest], now_iso) < min_age_hours:
        return None
    return oldest


def _hours_between(then_iso: str, now_iso: str) -> float:
    from datetime import datetime

    try:
        then = datetime.fromisoformat(then_iso)
        now = datetime.fromisoformat(now_iso)
    except ValueError:
        return float("inf")     # 读不懂就当很久没跑——宁可多碰一次，不要静默不碰
    return (now - then).total_seconds() / 3600


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-skill", default="/opt/runtime/run_skill.sh")
    ap.add_argument("--ledger", default="/var/log/kmfa/ledger.jsonl")
    # 24 小时不是拍脑袋——是模拟七天挑出来的拐点。原来写 6 小时，而
    # 13 个技能 × 每 30 分钟一跳 = 6.5 小时，跟 6 小时闸**正好共振**：
    # 一轮转完刚好过闸，于是每一跳都触发，一天 48 次额外运行、
    # 其中重活（项目成本/自检/归档）12 次。那不是把突发摊开，
    # 是把突发改成了持续负载——同一个问题的慢动作版。
    #
    #   闸(h)   额外跑/天   重活/天
    #     6       48.0      12.0
    #    12       24.0       6.0
    #    20       14.4       3.6
    #    24        5.0       1.0   ← 拐点
    #    36        3.6       0.7
    #
    # 每个值的覆盖率都是满的（七天内周/月/未排程的技能全被碰到），
    # 所以只需选负载最低的拐点。24 小时之所以是拐点：日排程技能 24 小时内
    # 会自己再跑，于是永远不够格被挑——节拍精确地只碰「等最久的那几个」，
    # 正是它该干的事。从没跑过的不受这道闸约束，30 分钟内就会被挑到。
    ap.add_argument("--min-age-hours", type=float, default=24.0)
    ap.add_argument("--now", default=None, help="ISO 时间，仅供测试注入")
    args = ap.parse_args(argv)

    if args.now:
        now_iso = args.now
    else:
        from datetime import datetime, timedelta, timezone

        now_iso = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")

    choice = pick(
        run_skill=Path(args.run_skill),
        ledger=Path(args.ledger),
        min_age_hours=args.min_age_hours,
        now_iso=now_iso,
    )
    if choice:
        sys.stdout.write(choice + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
