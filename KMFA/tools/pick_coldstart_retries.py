#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""挑「冷启动该重试哪些技能」，一行一个打到 stdout。

冷启动重试本身是对的（Owner 2026-07-27：「你已经浪费了我一个月的时间都还没有
修好考勤」——「等明天那次排程」正是把一个月耗掉的那个模式）。修好的代码要能
立刻被跑到，不等排程。

**但对「有硬业务时点、且一跑就往外发东西」的技能，无条件重试是错的。**

2026-07-29 发现的第二道门（第一道是压测节拍，已由 PR #282 关掉）：
这里直接调 `run_skill.sh <skill>`，**没带 KMFA_SWEEP_RUN=1**，所以投递是开的。
于是 attendance-evening 只要失败过一次，之后**每次部署**都会在部署发生的那个
时刻真发一次考勤——而部署时间是任意的，可能是凌晨三点。
当时没爆，只是因为两个考勤技能恰好都是 rc=0、没进重试名单。**那是运气不是设计。**

修法**不是**照抄 #282 把投递一律关掉：
「补发一次失败的投递」本身可能正是想要的——晚间报告 17:31 挂了，18:30 补上
比不发好。错的从来不是「补发」，是「在任意时刻补发」。所以规则按窗口来：

    时间锚定的技能，只有在**今天**、且**从锚点起算 GRACE 小时之内**，才允许补发。

三条边界，每条都有它挡住的具体坏事：
  · 早于锚点        —— 「晚间报告在早上发出去」，正是 #282 那个 bug 的形状；
  · 晚于锚点+GRACE  —— 凌晨三点被推一份当天的考勤；
  · 失败的那次不是今天 —— 补发一份过期报告，比不发更糟：
                        收到的人会以为那是今天的数。

锚点**从 crontab 里读**，不在这里写死：排程改了窗口要跟着改，
两处各写一份必然漂移。锚点读不到就**不补发**（fail closed）——
不知道窗口的时候，「不发」是唯一安全的默认。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pick_stalest_skill import TIME_ANCHORED_DELIVERY_SKILLS  # noqa: E402

#: 补发宽限：锚点之后多久内还算「有意义的补发」。
#:
#: 3 小时的来由：考勤报告讲的是「今天的出勤」，同一个半天内补上，收到的人对
#: 「这是刚才那件事」还有上下文。再晚就变成一条突然冒出来的旧消息了。
#: 这个值可以调，但**不能取消**——没有上界就等于回到「任意时刻补发」。
LATE_GRACE_HOURS = 3.0

#: crontab 行：分 时 日 月 周 用户 命令。只认**定点**的（分与时都是纯数字）；
#: `*/30` 这类节拍没有业务锚点，不参与窗口判断。
CRON_LINE = re.compile(
    r"^\s*(\d{1,2})\s+(\d{1,2})\s+\S+\s+\S+\s+\S+\s+\S+\s+.*?run_skill\.sh\s+([a-z0-9-]+)",
    re.M)


def scheduled_anchors(crontab: Path) -> dict[str, tuple[int, int]]:
    """技能名 → (时, 分)。真源是 crontab，本文件不另存一份。"""
    anchors: dict[str, tuple[int, int]] = {}
    text = crontab.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = CRON_LINE.match(line)
        if m:
            minute, hour, skill = int(m.group(1)), int(m.group(2)), m.group(3)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                anchors[skill] = (hour, minute)
    return anchors


def failed_skills(ledger: Path) -> dict[str, dict]:
    """每个技能最近一次运行；只留 rc 非 0 的。"""
    last: dict[str, dict] = {}
    try:
        text = ledger.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except (ValueError, TypeError):
            continue
        if row.get("skill"):
            last[row["skill"]] = row
    return {name: row for name, row in last.items() if row.get("rc") not in (0, None)}


def _parse_ts(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def may_retry(skill: str, row: dict, now: datetime,
              anchors: dict[str, tuple[int, int]]) -> tuple[bool, str]:
    """能不能补发，以及**不能的时候为什么**——理由要能写进日志给人看。"""
    if skill not in TIME_ANCHORED_DELIVERY_SKILLS:
        return True, ""

    anchor = anchors.get(skill)
    if anchor is None:
        return False, "读不到它的排程锚点——不知道窗口就不补发"

    failed_at = _parse_ts(row.get("ts"))
    if failed_at is None:
        return False, "台账时间戳解析不了——判不出是不是今天的失败"
    if failed_at.date() != now.date():
        return False, (f"失败的那次是 {failed_at.date()} 的，不是今天——"
                       "补发一份过期报告比不发更糟")

    hour, minute = anchor
    today_anchor = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now < today_anchor:
        return False, f"还没到今天的锚点 {hour:02d}:{minute:02d}"
    deadline = today_anchor + timedelta(hours=LATE_GRACE_HOURS)
    if now > deadline:
        return False, (f"已过补发窗口（锚点 {hour:02d}:{minute:02d} + "
                       f"{LATE_GRACE_HOURS:g}h，到 {deadline:%H:%M}）")
    return True, ""


def pick(*, ledger: Path, crontab: Path, now: datetime) -> tuple[list[str], list[str]]:
    anchors = scheduled_anchors(crontab)
    retry, skipped = [], []
    for skill, row in sorted(failed_skills(ledger).items()):
        ok, why = may_retry(skill, row, now, anchors)
        (retry if ok else skipped).append(skill if ok else f"{skill}：{why}")
    return retry, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default="/var/log/kmfa/ledger.jsonl")
    ap.add_argument("--crontab", default="/opt/runtime/crontab.txt")
    ap.add_argument("--now", default=None, help="ISO 时间，仅供测试注入")
    args = ap.parse_args()

    now = datetime.fromisoformat(args.now) if args.now else datetime.now()
    retry, skipped = pick(ledger=Path(args.ledger), crontab=Path(args.crontab), now=now)

    # 跳过的理由走 stderr：**不能藏**。「什么也没发生」和「因为在窗口外没发」
    # 在日志里长得一样，而后者是设计、前者可能是故障。
    for line in skipped:
        print(f"冷启动重试跳过 {line}", file=sys.stderr)
    for skill in retry:
        print(skill)
    return 0


if __name__ == "__main__":
    sys.exit(main())
