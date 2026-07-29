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


#: 只有**真发出过请求**的结局才买得到静默期。
#: 「按设计没请求」「只探测」都不算——没打扰过 Owner，就没有理由让下一次闭嘴。
REQUESTED_OUTCOMES = frozenset({"AUTH_REQUESTED", "AUTH_REQUESTED_AWAITING_CONFIRM"})


def read_stamp(state: Path) -> tuple[datetime | None, str | None]:
    """读戳记 → (时间, 结局)。

    新格式是 JSON：`{"at": "...", "outcome": "AUTH_REQUESTED"}`。
    旧格式是**裸时间戳**（上一版写的），没有结局——那种戳记一律不算静默期：
    它恰恰可能是「盖了戳但没请求成功」的那一种，认它就等于让系统自己锁死自己。
    """
    if not state.exists():
        return None, None
    try:
        text = state.read_text(encoding="utf-8").strip()
    except OSError:
        return None, None
    if not text:
        return None, None
    try:
        data = json.loads(text)
        return datetime.fromisoformat(str(data["at"])), str(data.get("outcome") or "")
    except (ValueError, TypeError, KeyError):
        pass
    try:
        return datetime.fromisoformat(text), None   # 旧的裸时间戳
    except ValueError:
        return None, None


def write_stamp(state: Path, *, now: datetime, outcome: str) -> None:
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"at": now.isoformat(timespec="seconds"),
                                 "outcome": outcome}, ensure_ascii=False),
                     encoding="utf-8")


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

    stamped_at, outcome = read_stamp(state)
    if stamped_at is not None:
        if outcome not in REQUESTED_OUTCOMES:
            # **静默期必须有凭据。**
            # 2026-07-29 线上卡死在这里：上一版的 --mark 是在「判定该请求」时就盖戳，
            # 而不是在**真请求之后**。于是盖了戳、请求却没发出去，接下来 6 小时
            # 全被自己盖的戳拦住，端点只报 NOT_REQUESTED_BY_DESIGN——
            # 看上去一切正常，Owner 却永远收不到弹窗。
            # 静默期存在的理由是「刚请求过、别再打扰」；**没请求成功就不该买到安静**。
            return True, (f"{BLOCKED_SKILL} 最近一次失败（rc={row.get('rc')}）；"
                          f"上次戳记 {stamped_at:%m-%d %H:%M} 没有成功请求的凭据"
                          f"（outcome={outcome or '无'}），不算静默期")
        elapsed = now - stamped_at
        if elapsed < timedelta(hours=MIN_INTERVAL_HOURS):
            left = timedelta(hours=MIN_INTERVAL_HOURS) - elapsed
            return False, (f"上次请求在 {stamped_at:%m-%d %H:%M}（{outcome}），还差 "
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
        # 这里盖的戳**不带成功凭据**——它只说明「判过该请求」。
        # 真正的凭据由发起方在请求成功后写（见 dws_data_auth_request.py）。
        # 这个区分正是 2026-07-29 卡死的根因：判过 ≠ 请求过。
        write_stamp(state, now=now, outcome="DECIDED_ONLY")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
