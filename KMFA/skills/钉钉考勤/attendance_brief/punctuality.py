"""人员表按时率台账。

存在的理由：截止线是给发布人的规矩，不是技术容差。
光说「今天迟了」没有约束力，累计按时率才有 —— 所以每天记一笔，简报里印出来。
台账落 SMB，跟其他产出同一个落点。
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path

def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def record(ledger: Path, day: str, posted: str | None) -> None:
    """posted 为 'HH:MM' 或 None（未发）。同一天重复运行只保留最早的发布时间。

    周末不记账：实测 39 天台账里周一到周五 38/38 天都有人员表，周末一张都没有 ——
    人员表本来就只在工作日发，把周末记成「未发」是给发布人扣一笔不存在的账。"""
    if datetime.strptime(day, "%Y-%m-%d").weekday() >= 5:
        return
    d = _load(ledger)
    prev = d.get(day, {}).get("发布时间")
    if prev and posted and prev <= posted:
        return
    # 只存事实（几点发的），不存判断（算不算按时）。
    # 判断依赖截止线，而截止线是会改的 —— 2026-09-09 就从 16:00 改成了 17:15。
    # 把判断存死，改一次截止线全部历史记录就错了，而且错得看不出来。
    d[day] = {"发布时间": posted}
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True),
                      encoding="utf-8")

def recent(ledger: Path, day: str, deadline: str, n: int = 10) -> tuple[int, int]:
    """返回 (按时天数, 统计天数)，只数有记录的工作日，最近 n 天。
    按时与否用当前截止线现算，deadline 形如 "17:15"。"""
    d = _load(ledger)
    days, cur, guard = [], datetime.strptime(day, "%Y-%m-%d").date(), 0
    while len(days) < n and guard < 400:
        guard += 1
        k = cur.isoformat()
        if cur.weekday() < 5 and k in d:
            days.append(d[k])
        cur -= timedelta(days=1)
    # "HH:MM" 补零后按字符串比就是按时间比。
    return sum(1 for x in days
               if (x.get("发布时间") or "") and x["发布时间"] < deadline), len(days)
