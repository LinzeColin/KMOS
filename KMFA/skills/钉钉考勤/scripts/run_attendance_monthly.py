#!/usr/bin/env python3
"""考勤累计 —— 唯一入口。

    KMFA_RUN_SLOT=morning python3 scripts/run_attendance_monthly.py

跑在工作日上午（本机 10:50 = 北京 08:50），看的是**上一个自然日**：
那一天的打卡已经收全了，结论是定的。两种报文共用一次取数：

  越线通知  上一个自然日有人的本月出勤跨过门槛 → 发，只列当天新越线的人。
            没有人越线就什么都不发（事件驱动，照抄付款线「没付款就不说话」）。
  月  报    周一多发一条，报上一个自然日所属那个月的累计。

标记一律认 stderr 里的固定标记，不认中文措辞。
"""
from __future__ import annotations
import json, os, sys, argparse, subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from attendance_brief import collect, monthly, report, runtime
from attendance_brief.config import Config

BEIJING = ZoneInfo("Asia/Shanghai")

def alarm_target() -> tuple:
    """告警目标直接读环境，不经过 Config —— Config 自己就可能是炸掉的那一个。"""
    return (os.path.expanduser(os.environ.get("KMFA_BRIEF_DWS", "~/.local/bin/dws")),
            os.environ.get("KMFA_BRIEF_NOTIFY_USER", "").strip())

def _ledger_path(cfg) -> Path:
    return cfg.runtime_root / "考勤累计台账.json"

def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

def _save(p: Path, d: dict) -> None:
    runtime.smb_write(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True) + "\n", p)

def _print_only(title: str, body: str, why: str) -> int:
    """干跑落点。这个函数里没有 dws，也没有 subprocess —— 调不到投递。"""
    runtime.emit("NOT_SENT_DRY_RUN", why)
    print(f"# {title}\n\n{body}")
    return 0

def _deliver(cfg, title: str, body: str, token: str) -> int:
    """真投递。全脚本只有这一个函数会调 `dws chat message send`。"""
    if not cfg.notify_group:
        runtime.emit("NO_TARGET", "没配 KMFA_BRIEF_NOTIFY_GROUP")
        return 1
    r = subprocess.run([cfg.dws, "chat", "message", "send", "--group", cfg.notify_group,
                        "--title", title, "--text", report.dingtalk(body)],
                       capture_output=True, timeout=120)
    if r.returncode != 0:
        err = r.stderr.decode()[:400]
        runtime.emit("SEND_FAILED", err)
        runtime.alarm(cfg.dws, cfg.notify_user, "SEND_FAILED",
                      f"考勤累计（{token}）生成成功但发不进生产管理群。\n{err}")
        return 1
    runtime.emit(token, f"生产管理群 · {title}")
    return 0

def publisher(cfg, a):
    """本轮用哪个落点，在这里一次定死。

    2026-09-15 我在这栽过：`--dry-run` 只被拿去跳过台账，投递那段照跑，
    于是一次「干跑验证」把八月的两条报文真发进了生产管理群（已撤回）。
    老板早就定过规矩 —— **验证路径不许等于生产路径，干跑在代码层面就该调不到投递函数**。
    所以现在由这个函数选落点：干跑拿到的是 _print_only，它的调用图里根本没有 dws。
    """
    if a.dry_run:
        return lambda t, b, tok: _print_only(t, b, "--dry-run，不发送也不写台账")
    if not cfg.send_enabled:
        return lambda t, b, tok: _print_only(t, b, "KMFA_BRIEF_SEND != 1")
    return lambda t, b, tok: _deliver(cfg, t, b, tok)

def _publish(pub, cfg, title: str, body: str, token: str) -> int:
    """禁用词闸对两个落点一视同仁 —— 干跑也要能看出这份报文会被拒。"""
    bad = runtime.banned_words(f"{title}\n{body}")
    if bad:
        runtime.emit("BANNED_WORD", f"报文里出现禁用词 {bad}，拒发")
        runtime.alarm(cfg.dws, cfg.notify_user, "BANNED_WORD",
                      f"考勤累计报文里出现了禁用词 {bad}，已拒发。")
        return 1
    return pub(title, body, token)

def _run(a) -> int:
    try:
        cfg = Config()
    except SystemExit as e:
        runtime.emit("CONFIG_MISSING", str(e))
        dws, user = alarm_target()
        runtime.alarm(dws, user, "CONFIG_MISSING", f"考勤累计没跑成：配置缺项。\n{e}")
        return 2

    why = runtime.smb_ready(cfg.runtime_root)
    if why:
        runtime.emit("SMB_UNAVAILABLE", why)
        runtime.alarm(cfg.dws, cfg.notify_user, "SMB_UNAVAILABLE",
                      f"考勤累计没跑成：共享盘不可用。\n{why}\n挂上后下一个工作日会自己重跑。")
        return 1
    runtime.runlog_init(cfg.runtime_root)

    now_bj = datetime.now(BEIJING)
    day = a.date or (now_bj - timedelta(days=1)).strftime("%Y-%m-%d")
    month = day[:7]
    runtime.emit("MONTHLY_START", f"业务日={day} 北京={now_bj:%Y-%m-%d %H:%M} dry={int(a.dry_run)}")

    # 发送窗口。上沿下沿都有，谁触发的都一样 —— Codex 会补跑错过的计划，
    # 补到北京半夜也照样是「排程触发」。窗口外宁可今天不发。
    lo, hi = cfg.monthly_window
    nowm = now_bj.hour * 60 + now_bj.minute
    if not a.dry_run and not (lo <= nowm <= hi):
        runtime.emit("SKIP_OUT_OF_WINDOW",
                     f"北京 {now_bj:%H:%M} 不在发送窗口 "
                     f"{lo // 60:02d}:{lo % 60:02d}–{hi // 60:02d}:{hi % 60:02d}，本轮不发")
        return 0

    pub, live = publisher(cfg, a), (not a.dry_run and cfg.send_enabled)
    dws = collect.Dws(cfg.dws, tries=8)     # 上午有的是时间，网关阵发性抖动多试几次
    people = monthly.dept_members(dws, cfg.dept_root)
    if not people:
        runtime.emit("RUN_FAILED", f"{cfg.dept_root} 一个人都没取到")
        runtime.alarm(cfg.dws, cfg.notify_user, "RUN_FAILED",
                      f"考勤累计没跑成：{cfg.dept_root} 通讯录取不到人。")
        return 1
    uid2 = {u: (n, g) for n, (u, g) in people.items()}
    start = f"{month}-01"
    daily, agg = monthly.fetch(dws, list(uid2), start, day)

    ledger = _ledger_path(cfg)
    book = _load(ledger)
    reported = book.setdefault("越线已报", {}).setdefault(month, {})
    sent_days = book.setdefault("月报已发", {})

    # ① 越线通知：报「到今天为止已经跨过门槛、但还没报过」的人，首报制。
    #
    # 不是只看「昨天那一天跨的」—— 这条 automation 只在工作日跑，周六跨线的人
    # 没有哪一趟会正好看到周六；再加上节假日、漏触发，都会让人从缝里掉下去。
    # 按「还没报过」来判，谁都漏不掉，而且报过的永不重报。
    cross = monthly.crossings(daily, cfg.attend_threshold)
    pending = {u: d for u, d in cross.items() if u not in reported}
    # 按组归堆再按姓名 —— 排休是按班组排的，同组的人挨在一起才好安排。
    fresh = [(n, g) for g, n in sorted((uid2[u][1], uid2[u][0]) for u in pending)]
    rc = 0
    if fresh:
        title, body = monthly.render_cross(day, fresh, len(reported) + len(fresh),
                                           len(uid2), cfg.attend_threshold)
        rc = _publish(pub, cfg, title, body, "CROSS_SENT")
        if rc == 0 and live:
            reported.update(pending)
            _save(ledger, book)
    else:
        runtime.emit("SKIP_NO_CROSSING",
                     f"截至 {day} 没有人新跨过 {cfg.attend_threshold:g} 天"
                     f"（本月已报 {len(reported)} 人）")

    # ② 月报：周一一条，报 day 所属的那个月。
    want_month = a.force_month or now_bj.weekday() == 0          # 北京周一
    if want_month and sent_days.get(month) == day:
        runtime.emit("SKIP_MONTHLY_DONE", f"{month} 的月报今天已经发过了")
    elif want_month:
        rows = [(uid2[u][0], uid2[u][1], agg[u]) for u in uid2 if agg[u]["应出勤"] > 0]
        rows.sort()
        title, body = monthly.render_month(month, rows, cfg.attend_threshold)
        rc2 = _publish(pub, cfg, title, body, "MONTHLY_SENT")
        if rc2 == 0 and live:
            sent_days[month] = day
            _save(ledger, book)
        rc = rc or rc2
    else:
        runtime.emit("SKIP_NOT_MONDAY", f"北京今天是周{'一二三四五六日'[now_bj.weekday()]}，不发月报")
    return rc

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="指定业务日（上一个自然日），默认自动判定")
    ap.add_argument("--dry-run", action="store_true", help="只出报不发送，也不写台账")
    ap.add_argument("--force-month", action="store_true", help="不是周一也出月报（人工用）")
    a = ap.parse_args()
    try:
        return _run(a)
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        runtime.emit("RUN_FAILED", f"{type(e).__name__}: {e}")
        runtime.runlog(traceback.format_exc())
        dws, user = alarm_target()
        runtime.alarm(dws, user, "RUN_FAILED",
                      f"考勤累计跑挂了，今天这份没发出去。\n{type(e).__name__}: {e}\n"
                      f"堆栈在运行日志里；下一个工作日上午会自己重跑。")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
