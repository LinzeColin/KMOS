#!/usr/bin/env python3
"""生产部周报 —— 唯一入口。

    KMFA_RUN_SLOT=morning python3 scripts/run_attendance_weekly.py

跑在工作日上午（本机 10:50 = 北京 08:50），看的是**上一个自然日**：
那一天的打卡已经收全了，结论是定的。

一周一条，周一出。周一那趟没跑成（机器睡着 / 网关阵发 / Codex 没触发），
周二到周五的同一个槽位会接着出同一周的那条 —— 台账按 ISO 周去重，
发成功才记账，所以补得上，也不会重发。

标记一律认 stderr 里的固定标记，不认中文措辞；最后一行是 `ACTION: X`。
"""
from __future__ import annotations
import json, os, sys, argparse, subprocess, tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from attendance_brief import collect, report, roster, runtime, weekly
from attendance_brief.config import Config

BEIJING = ZoneInfo("Asia/Shanghai")

def alarm_target() -> tuple:
    """告警目标直接读环境，不经过 Config —— Config 自己就可能是炸掉的那一个。"""
    return (os.path.expanduser(os.environ.get("KMFA_BRIEF_DWS", "~/.local/bin/dws")),
            os.environ.get("KMFA_BRIEF_NOTIFY_USER", "").strip())

def _iso_week(day: str) -> str:
    y, w, _ = datetime.strptime(day, "%Y-%m-%d").date().isocalendar()
    return f"{y}-W{w:02d}"

def _ledger_path(cfg) -> Path:
    return cfg.runtime_root / "考勤周报台账.json"

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
                      f"生产部周报生成成功但发不进生产管理群。\n{err}")
        return 1
    runtime.emit(token, f"生产管理群 · {title}")
    return 0

def publisher(cfg, a):
    """本轮用哪个落点，在这里一次定死。

    2026-09-15 在这栽过：`--dry-run` 只被拿去跳过台账，投递那段照跑，
    于是一次「干跑验证」把两条报文真发进了生产管理群（已撤回）。
    老板早就定过规矩 —— **验证路径不许等于生产路径，干跑在代码层面就该调不到投递函数**。
    所以由这个函数选落点：干跑拿到的是 _print_only，它的调用图里根本没有 dws。
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
                      f"生产部周报里出现了禁用词 {bad}，已拒发。")
        return 1
    return pub(title, body, token)

def _run(a) -> int:
    try:
        cfg = Config()
    except SystemExit as e:
        runtime.emit("CONFIG_MISSING", str(e))
        dws, user = alarm_target()
        runtime.alarm(dws, user, "CONFIG_MISSING", f"生产部周报没跑成：配置缺项。\n{e}")
        return 2

    why = runtime.smb_ready(cfg.runtime_root)
    if why:
        runtime.emit("SMB_UNAVAILABLE", why)
        runtime.alarm(cfg.dws, cfg.notify_user, "SMB_UNAVAILABLE",
                      f"生产部周报没跑成：共享盘不可用。\n{why}\n挂上后下一个工作日会自己重跑。")
        return 1
    runtime.runlog_init(cfg.runtime_root)

    now_bj = datetime.now(BEIJING)
    bizday = a.date or (now_bj - timedelta(days=1)).strftime("%Y-%m-%d")
    week = _iso_week(bizday)
    runtime.emit("WEEKLY_START", f"业务日={bizday} {week} 北京={now_bj:%Y-%m-%d %H:%M} "
                                 f"dry={int(a.dry_run)}")

    # 发送窗口。上沿下沿都有，谁触发的都一样 —— Codex 会补跑错过的计划，
    # 补到北京半夜也照样是「排程触发」。窗口外宁可今天不发。
    lo, hi = cfg.weekly_window
    nowm = now_bj.hour * 60 + now_bj.minute
    if not a.dry_run and not (lo <= nowm <= hi):
        runtime.emit("SKIP_OUT_OF_WINDOW",
                     f"北京 {now_bj:%H:%M} 不在发送窗口 "
                     f"{lo // 60:02d}:{lo % 60:02d}–{hi // 60:02d}:{hi % 60:02d}，本轮不发")
        return 0

    ledger = _ledger_path(cfg)
    book = _load(ledger)
    sent = book.setdefault("周报已发", {})
    if not a.dry_run and week in sent:
        runtime.emit("SKIP_WEEKLY_DONE", f"{week} 这一周的周报 {sent[week]} 已经发过了")
        return 0

    pub, live = publisher(cfg, a), (not a.dry_run and cfg.send_enabled)
    dws = collect.Dws(cfg.dws, tries=8)     # 上午有的是时间，网关阵发性抖动多试几次
    people = weekly.dept_members(dws, cfg.dept_root)
    if not people:
        runtime.emit("RUN_FAILED", f"{cfg.dept_root} 一个人都没取到")
        runtime.alarm(cfg.dws, cfg.notify_user, "RUN_FAILED",
                      f"生产部周报没跑成：{cfg.dept_root} 通讯录取不到人。")
        return 1
    uid2 = {u: n for n, (u, _) in people.items()}
    start = (datetime.strptime(bizday, "%Y-%m-%d")
             - timedelta(days=cfg.weekly_window_days - 1)).strftime("%Y-%m-%d")
    rec = weekly.fetch(dws, list(uid2), start, bizday)

    # ① 轮休名单：连续到岗够门槛的人。休一天即归零，自己就会从名单上消失。
    roll_uid = [u for u in rec if weekly.streak(rec[u], bizday) >= cfg.rest_threshold]
    roll_uid.sort(key=lambda u: -weekly.streak(rec[u], bizday))
    # ② 在岗待核实：在册却一次卡没打，且没走过请假流程的。
    pend_uid = []
    for u in rec:
        z = weekly.zero_run(rec[u], bizday)
        if z >= cfg.zero_punch_days and not weekly.leave_filed(rec[u], bizday, z):
            pend_uid.append(u)

    # 项目归属：唯一口径是人员表的「项目名称」列。名单里的人全有项目就停，
    # 常态只解析一张表。一张都取不到就降级 —— 名单照发，只是归不了类。
    need = {uid2[u] for u in roll_uid + pend_uid}
    cache = cfg.runtime_root / "roster.json"
    names = roster.load(cache) or roster.fetch(cfg.dws, cache)
    with tempfile.TemporaryDirectory() as td:
        pm, got = weekly.project_map(dws, cfg, bizday, Path(td), names, need,
                                     back=cfg.roster_lookback)
    degraded = "" if pm else "本周人员表未取到，暂未按项目归类。"
    if not pm:
        runtime.emit("ROSTER_DEGRADED", f"往回 {cfg.roster_lookback} 天一张人员表都没读到")

    roll = [(uid2[u], pm.get(uid2[u], "未登记")) for u in roll_uid]
    pend = [(uid2[u], pm.get(uid2[u], "未登记")) for u in pend_uid]

    # ③ 打卡规范：本月 1 日到业务日的累计。
    disc = []
    for lab, fs in (("迟到", ("迟到",)), ("缺卡", ("上缺", "下缺")), ("补卡", ("补卡",))):
        arr = []
        for u in rec:
            n = 0
            for d, cell in rec[u].items():
                if d[:7] != bizday[:7] or d > bizday:
                    continue
                for f in fs:
                    try:
                        n += float(cell.get(f) or 0)
                    except (TypeError, ValueError):
                        pass
            if n >= cfg.discipline_threshold:
                arr.append((uid2[u], int(n)))
        if arr:
            disc.append((lab, sorted(arr, key=lambda z: -z[1])))

    prev = set(book.get("上周名单") or []) if book.get("上周名单") is not None else None
    weeks = {uid2[u]: v for u, v in (book.get("在列周数") or {}).items() if u in uid2}
    prev_names = {uid2[u] for u in prev if u in uid2} if prev is not None else None
    monday = (datetime.strptime(bizday, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    title, body = weekly.render(monday, bizday, roll, pend, disc,
                                cfg.rest_threshold, prev_names, weeks, degraded)
    rc = _publish(pub, cfg, title, body, "WEEKLY_SENT")
    if rc == 0 and live:
        cur = [u for u in roll_uid]
        book["在列周数"] = {u: ((book.get("在列周数") or {}).get(u, 0) + 1
                               if prev and u in prev else 1) for u in cur}
        book["上周名单"] = cur
        sent[week] = bizday
        # 台账只留最近 12 周，不让它无限长。
        for k in sorted(sent)[:-12]:
            sent.pop(k)
        _save(ledger, book)
    return rc

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="指定业务日（上一个自然日），默认自动判定")
    ap.add_argument("--dry-run", action="store_true", help="只出报不发送，也不写台账")
    a = ap.parse_args()
    if a.dry_run:
        runtime.quiet_alarms()
    try:
        with runtime.single_instance("weekly"):
            return _run(a)
    except SystemExit:
        raise
    except runtime.AlreadyRunning as e:
        runtime.emit("LOCK_HELD", str(e))     # 上一轮还在跑，不是故障
        return 0
    except Exception as e:
        import traceback
        runtime.emit("RUN_FAILED", f"{type(e).__name__}: {e}")
        runtime.runlog(traceback.format_exc())
        dws, user = alarm_target()
        runtime.alarm(dws, user, "RUN_FAILED",
                      f"生产部周报跑挂了，这一周的还没发出去。\n{type(e).__name__}: {e}\n"
                      f"堆栈在运行日志里；下一个工作日上午会自己重跑。")
        return 1
    finally:
        runtime.emit_action()

if __name__ == "__main__":
    raise SystemExit(main())
