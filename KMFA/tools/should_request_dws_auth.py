#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判断「现在该不该向 Owner 请求 dws 数据授权」。是则退 0，否则退 1（理由走 stderr）。

为什么做成自愈而不是一个开关（2026-07-29）：

第一版做成了环境变量 `KMFA_DWS_DATA_AUTH_REQUEST`——线上不生效。
排查到最后：开关在 Coolify 里、compose 里也声明了、部署用的确实是含改动的
提交，但技能从没进过台账。**这正是 `KMFA_BOOT_SWEEP` 那次的重演**：
变量看着设了，实际没到容器。仓里那条门禁只能验「compose 里写没写」，
验不了「Coolify 有没有重新读 compose」。
**一个不管用的开关比没有更糟**——真出事时会去按它。所以那条路整个删掉。

第二版考虑过做成 App 上的一个按钮（复用项目成本重算那套已验证的
「app 写标记 → skills 每分钟查」）。否决了：那个端点是匿名可达的，
而「给 Owner 的钉钉弹窗」被反复触发就是骚扰。**不该为了省事开一个
能被陌生人按的门。**

所以改成自愈：**系统自己发现卡在授权上，就去请求一次**。
好处不只是省掉一次人工触发——下一次授权过期（TTL 到期是必然的），
Owner 会自动收到请求，而不是整条链默默红着等人发现。

两条闸，都必须成立才请求：
  1. 确实卡住了——upstream-archive 最近一次是失败的；
  2. 上次请求已隔了 MIN_INTERVAL_HOURS——授权弹窗有骚扰性，
     不许因为技能一直红就每 10 分钟弹一次。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

#: 卡在数据授权上的技能。它红 = 这条链断了。
BLOCKED_SKILL = "upstream-archive"

#: 两次授权请求之间至少隔多久。
#:
#: 6 小时的来由：授权默认 TTL 是 24h 量级，6 小时足够覆盖「Owner 白天在线」
#: 的节奏，又不至于一天弹很多次。**这个值不能取消**——没有下界就等于
#: 「技能红着就一直弹」，那是骚扰。
MIN_INTERVAL_HOURS = 6.0


def last_run(ledger: Path, skill: str) -> dict | None:
    row = None
    try:
        text = ledger.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except (ValueError, TypeError):
            continue
        if parsed.get("skill") == skill:
            row = parsed
    return row


def decide(*, ledger: Path, state: Path, now: datetime) -> tuple[bool, str]:
    row = last_run(ledger, BLOCKED_SKILL)
    if row is None:
        return False, f"{BLOCKED_SKILL} 还没跑过——没有「卡住」的证据，不打扰 Owner"
    if row.get("rc") in (0, None):
        return False, f"{BLOCKED_SKILL} 最近一次是成功的——授权是通的，不用请求"

    if state.exists():
        try:
            previous = datetime.fromisoformat(state.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            previous = None
        if previous is not None:
            elapsed = now - previous
            if elapsed < timedelta(hours=MIN_INTERVAL_HOURS):
                left = timedelta(hours=MIN_INTERVAL_HOURS) - elapsed
                return False, (f"上次请求在 {previous:%m-%d %H:%M}，还差 "
                               f"{left.total_seconds() / 3600:.1f} 小时才到间隔"
                               f"（{MIN_INTERVAL_HOURS:g}h）——弹窗有骚扰性，不连发")
    return True, f"{BLOCKED_SKILL} 最近一次失败（rc={row.get('rc')}），且已过静默期"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default="/var/log/kmfa/ledger.jsonl")
    ap.add_argument("--state", default="/var/log/kmfa/dws-data-auth/.last_request")
    ap.add_argument("--now", default=None, help="ISO 时间，仅供测试注入")
    ap.add_argument("--mark", action="store_true",
                    help="判定为「该请求」时顺便写下时间戳（真要发起时才带）")
    args = ap.parse_args()

    now = datetime.fromisoformat(args.now) if args.now else datetime.now()
    state = Path(args.state)
    ok, why = decide(ledger=Path(args.ledger), state=state, now=now)

    # 理由一律写出来：「没请求」和「请求了但没反应」在日志里长得一样，
    # 而前者是设计、后者是故障。
    print(why, file=sys.stderr)
    if ok and args.mark:
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(now.isoformat(timespec="seconds"), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
