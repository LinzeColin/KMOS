#!/usr/bin/env python3
"""考勤异常简报 —— 唯一入口。

调度方只需要设 KMFA_RUN_SLOT 并执行这一条命令，不传业务参数、不做任何判断：

    KMFA_RUN_SLOT=evening python3 scripts/run_attendance_brief.py

Codex automation / 人手动执行，结果完全一致（幂等）：一天只发一次。
失败自己写日志、自己在下一轮重跑，调度方不需要看懂任何东西。
"""
from __future__ import annotations
import json, os, sys, argparse
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from attendance_brief import (archives, collect, extract, punctuality,
                              report, roster, runtime)
from attendance_brief.config import Config

BEIJING = ZoneInfo("Asia/Shanghai")

UNLISTED_ALERT = 8          # 「不在册」超过这个数就判为整片误判，不再逐个列名

def business_day(explicit: str | None) -> str:
    """业务日一律按北京时间算。

    这台机器的系统时区是 Australia/Sydney（比北京快 2 小时），而钉钉返回的
    createTime、打卡 workDate 全部是北京时间 —— 已用实测核对过：
    本机 18:04 发出的消息，钉钉记的是 16:04。
    用本机时间判业务日会在北京 22:00 之后整体错开一天，所以这里显式转北京时区。
    """
    if explicit:
        return explicit
    now = datetime.now(BEIJING)
    # 下午跑取当天；凌晨补跑算前一天
    return (now if now.hour >= 12 else now - timedelta(days=1)).strftime("%Y-%m-%d")

def build(cfg: Config, day: str, wd: Path, dl: runtime.Deadline) -> dict:
    dws = collect.Dws(cfg.dws)
    out: dict = {"业务日": day, "状态": "正常"}

    dl.check("找人员表")
    imgs = collect.find_table_images(dws, cfg.group_id, cfg.publishers, day, wd)
    ledger = cfg.runtime_root / "人员表按时台账.json"
    if not imgs:
        # 没有人员表时，先分清是「该发没发」还是「今天本来就不上班」，
        # 判错了就是在非工作日追着发布人要表 —— 实测踩过。
        # 周末直接判非工作日：台账 38 个工作日 38 天有表，周末一张都没有。
        # 注意不能只看「有没有人打卡」—— 周日实测仍有零星打卡记录（值班/外派），
        # 那条证据只够用来识别工作日里的法定节假日和调休。
        if datetime.strptime(day, "%Y-%m-%d").weekday() >= 5:
            out["状态"] = "非工作日"; out["理由"] = "这天是周末"
            return out
        # 法定节假日和调休算不出来，用硬证据：全公司当天一个人都没打卡就是放假。
        cache = cfg.runtime_root / "roster.json"
        people = roster.load(cache) or roster.fetch(cfg.dws, cache)
        if people:
            dl.check("判非工作日")
            worked = [r for r in dws.punches(list(people.values()), day, day)
                      if r.get("timeResult") in ("Normal", "Late", "Early")]
            if not worked:
                out["状态"] = "非工作日"; out["理由"] = "全公司当天无人打卡"
                return out
        punctuality.record(ledger, day, None)
        ok, tot = punctuality.recent(ledger, day, cfg.deadline)
        out.update({"状态": "无人员表", "截止": cfg.deadline,
                    "按时率": (ok, tot), "发布人": "、".join(cfg.publishers)})
        return out
    img = imgs[0]
    hhmm = img.stem.split("_")[1][:2] + ":" + img.stem.split("_")[1][2:]
    punctuality.record(ledger, day, hhmm)
    ok, tot = punctuality.recent(ledger, day, cfg.deadline)
    out["人员表时间"] = hhmm
    out["按时"] = hhmm < cfg.deadline          # "HH:MM" 补零后按字符串比就是按时间比
    out["截止"] = cfg.deadline
    out["按时率"] = (ok, tot)
    out["发布人"] = "、".join(cfg.publishers)

    dl.check("识别人员表")
    tab = extract.extract(str(img))
    if not tab["类别可信"]:
        out["状态"] = "读不准"; out["不可信"] = [(0, "类别列块序与锚点冲突")]
        return out

    dl.check("花名册仲裁")
    cache = cfg.runtime_root / "roster.json"
    people = roster.load(cache) or roster.fetch(cfg.dws, cache)
    if not people:
        out["状态"] = "读不准"; out["不可信"] = [(0, "花名册取不到")]
        return out

    untrusted, own, outs, unlisted = [], [], 0, []
    for row in tab["行"]:
        if extract.is_outsourced(row):
            outs += len(row["人员"]); continue
        for p in row["人员"]:
            verdict, name, why = roster.arbitrate(p["候选"], people)
            if verdict == "不可信":
                untrusted.append((row["行"], f"{p['ocr']} — {why}"))
            elif verdict == "不在册":
                unlisted.append(p["ocr"])
            else:
                own.append({"姓名": name, "uid": people[name], "行": row,
                            "应打卡": extract.must_punch(row)})
    if untrusted:
        out["状态"] = "读不准"; out["不可信"] = untrusted
        return out

    dl.check("拉打卡")
    need = [p for p in own if p["应打卡"]]
    punches = dws.punches([p["uid"] for p in need], day, day) if need else []
    by_uid: dict[str, dict] = {}
    for r in punches:
        by_uid.setdefault(r["userId"], {})[r.get("checkType")] = r.get("timeResult")

    todo_考勤: list[str] = []
    todo = todo_考勤          # 下面的追加都进考勤类
    for p in need:
        v = by_uid.get(p["uid"], {})
        on, off = v.get("OnDuty"), v.get("OffDuty")
        where = p["行"]["项目"] or p["行"]["类别"]
        if not v:
            todo.append(f"{p['姓名']}（{where}）应打卡，钉钉无任何记录 → 本人补卡 · 明日 18:00 前")
        elif on in ("NotSigned", "Absenteeism") and off in ("NotSigned", "Absenteeism"):
            todo.append(f"{p['姓名']}（{where}）应打卡，全天未打卡 → 本人补卡 · 明日 18:00 前")
        elif on in ("NotSigned", "Absenteeism"):
            todo.append(f"{p['姓名']}（{where}）缺上班卡，下班正常 → 本人补卡 · 明日 18:00 前")
        elif off in ("NotSigned", "Absenteeism"):
            todo.append(f"{p['姓名']}（{where}）缺下班卡，上班正常 → 本人补卡 · 明日 18:00 前")
        elif on == "Late":
            todo.append(f"{p['姓名']}（{where}）上班迟到 → 知悉即可，无需动作")

    todo_纪律: list[str] = []
    if not out.get("按时", True):
        # 只说事，不点名。发布人是谁群里都知道，把名字印在每日简报上等于天天公开点名，
        # 压力给到个人而事情并不会因此更快 —— 要的是习惯，不是难堪。
        todo_纪律.append(f"人员表 {out['人员表时间']} 才发布，超过 {cfg.deadline} 截止线 "
                         f"→ 请明日 {cfg.deadline} 前发出")
    todo_名单: list[str] = []
    if unlisted:
        # 防呆闸：正常情况「不在册」是 0~4 人（新入职未录入）。一旦冲到十几二十几，
        # 几乎一定是这张表的「外协」标注没被识别，把整片外协当成了自己人 ——
        # 实测 38 张里有 2 张是这样（08-12、08-14，各 26/27 人）。
        # 这种时候列一长串名字是噪音而且是错的，收敛成一条提示并要求人工看原图。
        if len(unlisted) > UNLISTED_ALERT:
            todo_名单.append(
                f"有 {len(unlisted)} 人对不上钉钉花名册，远超常态 —— "
                f"多半是这张人员表的「外协」列没标全，请核对原图 · 今日")
        else:
            todo_名单.append(
                f"{'、'.join(unlisted)} 不在钉钉花名册 → 综合部确认是否入职录入 · 本周内")
    dup = [n for n, c in Counter(p["姓名"] for p in own).items() if c > 1]
    if dup:
        todo_纪律.append(f"人员表重复登记：{'、'.join(dup)} → 请发布人核对后重发 · 明日 12:00 前")

    rest = sum(len(r["人员"]) for r in tab["行"] if r["类别"] == "休息人员")
    back = sum(len(r["人员"]) for r in tab["行"] if r["类别"] == "回程途中")
    out.update({
        "纪律": todo_纪律, "考勤": todo_考勤, "名单": todo_名单,
        "待办数": len(todo_纪律) + len(todo_考勤) + len(todo_名单),
        "自有员工": len(own), "应打卡": len(need),
        "异常人数": len(todo_考勤),
        "应打卡分布": Counter((p["行"]["项目"] or p["行"]["类别"]) for p in need).most_common(),
        "休息": rest, "回程": back, "外协": outs,
    })
    return out

def alarm_target() -> tuple[str, str]:
    """告警目标直接读环境，不经过 Config —— Config 自己就可能是炸掉的那一个。
    告警这条路必须比它要通报的任何东西都简单。"""
    return (os.path.expanduser(os.environ.get("KMFA_BRIEF_DWS", "~/.local/bin/dws")),
            os.environ.get("KMFA_BRIEF_NOTIFY_USER", "").strip())

def main() -> int:
    """最外层兜底网。

    _run 里在 cfg 建好之前就有三处可能炸：配置数值解析（int() 拿到非整数）、
    SMB 在 smb_ready 通过之后瞬断（already_sent 的 .exists() 抛 OSError）、
    归档子进程 SIGKILL 都收不走。以前这三条路径会让进程直接带 traceback 退出 ——
    stderr 里一个结论性标记都没有，调度侧只能判 ESCALATE 写进 Codex 桌面 app，
    而手机上什么都收不到。那正是「没发简报，也没人知道没发」。
    """
    a = _parse_args()
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
                      f"考勤简报跑挂了，今天这份没发出去。\n{type(e).__name__}: {e}\n"
                      f"堆栈在运行日志里；下一个工作日 17:15 会自己重跑。")
        return 1

def _parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="指定业务日，默认自动判定")
    ap.add_argument("--dry-run", action="store_true", help="只出报不发送")
    ap.add_argument("--send", action="store_true",
                    help="手工运行时也真的发出去（调度器不需要这个）")
    ap.add_argument("--force", action="store_true",
                    help="人按的：无视周末和截止线。注意「今天已发过」照样拦，幂等无条件")
    return ap.parse_args()

def _run(a) -> int:
    try:
        cfg = Config()
    except SystemExit as e:
        runtime.emit("CONFIG_MISSING", str(e))
        dws, user = alarm_target()
        runtime.alarm(dws, user, "CONFIG_MISSING",
                      f"考勤简报没跑成：配置缺项，今天这份没发出去。\n{e}")
        return 2

    # SMB 必须最先查。人员表图片、花名册、台账、归档、运行日志全在共享盘上，
    # 盘掉了不查就会在后面某个 python 调用里以随机方式炸，判读侧根本对不上。
    why = runtime.smb_ready(cfg.runtime_root, cfg.archive_root)
    if why:
        runtime.emit("SMB_UNAVAILABLE", why)
        runtime.alarm(cfg.dws, cfg.notify_user, "SMB_UNAVAILABLE",
                      f"考勤简报没跑成：共享盘不可用。\n{why}\n"
                      f"挂上 /Volumes/share 后下一个工作日 17:15 会自己重跑。")
        return 1
    runtime.runlog_init(cfg.runtime_root)

    day = business_day(a.date)
    now_bj = datetime.now(BEIJING)
    runtime.emit("RUN_START", f"业务日={day} 北京={now_bj:%Y-%m-%d %H:%M} "
                              f"force={int(a.force)} scheduled={int(cfg.scheduled)}")

    # 幂等无条件：一个业务日只发一份，谁触发的都一样。--force 也不放行。
    if not a.dry_run and runtime.already_sent(cfg.runtime_root, day):
        runtime.emit("SKIP_ALREADY_SENT", f"{day} 今天这份已经发过了")
        return 0
    # 周末和截止线只拦排程；人按 Run 是他自己要，放行。
    auto = not a.date and not a.dry_run and not a.force
    if auto and datetime.strptime(day, "%Y-%m-%d").weekday() >= 5:
        runtime.emit("SKIP_WEEKEND", f"{day} 是周末，人员表本来就不在周末发")
        return 0
    # 容 5 分钟：调度器落地有抖动，19:15 那一枪可能在 19:13 到。
    want = cfg.publish_hour * 60 + cfg.publish_minute
    if auto and (now_bj.hour * 60 + now_bj.minute) < want - 5:
        runtime.emit("SKIP_BEFORE_PUBLISH",
                     f"北京 {now_bj:%H:%M} 还没到出报时刻 "
                     f"{cfg.publish_hour:02d}:{cfg.publish_minute:02d}，等本工作日的下一个触发点")
        return 0

    # 闸全过了，今天确实要出报 —— 先把自己这个群的 KMFile / KMMedia 增量跑一遍，
    # 让下游读到的钉钉原件是完整的。只跑生产管理群，不碰别的群。
    # 放在闸之后是有意的：备位那条 automation 绝大多数日子命中
    # SKIP_ALREADY_SENT，放闸之前等于每天白跑一轮。归档失败只记标记，绝不阻断简报。
    if not a.dry_run:
        archives.run(cfg.group_title, cfg.archive_budget)

    dl = runtime.Deadline(cfg.wall_clock_limit)
    try:
        with runtime.single_instance(), runtime.workdir() as wd:
            data = build(cfg, day, wd, dl)
            if data["状态"] == "非工作日" and not a.force:
                runtime.emit("SKIP_NON_WORKDAY", f"{day} {data.get('理由','非工作日')}")
                return 0
            title, body = report.render(data)
            stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            base = cfg.month_dir(day) / f"brief_{day.replace('-','')}_{stamp}"
            runtime.smb_write(body, base.with_suffix(".md"))
            runtime.smb_write(json.dumps(data, ensure_ascii=False, indent=1),
                              base.with_suffix(".json"))
            print(f"# {title}\n\n{body}")
            if a.dry_run or not cfg.send_enabled:
                runtime.emit("NOT_SENT_DRY_RUN", "dry-run 或 KMFA_BRIEF_SEND != 1")
                return 0
            if not (cfg.scheduled or a.send):
                runtime.emit("NOT_SENT_MANUAL", "手工运行，要真发进群请加 --send")
                return 0
            if not cfg.notify_group:
                runtime.emit("NO_TARGET", "没配 KMFA_BRIEF_NOTIFY_GROUP")
                return 1
            import subprocess
            # 只发群。张霖泽人在群里，再单发一份个人消息是重复打扰。
            # 私聊只留给故障告警，不用来发简报。
            r = subprocess.run([cfg.dws, "chat", "message", "send",
                                "--group", cfg.notify_group,
                                "--title", title, "--text", body],
                               capture_output=True, timeout=120)
            if r.returncode != 0:
                err = r.stderr.decode()[:400]
                runtime.emit("SEND_FAILED", err)
                runtime.alarm(cfg.dws, cfg.notify_user, "SEND_FAILED",
                              f"考勤简报生成成功但发不进生产管理群。\n{err}\n"
                              f"报文已存 {base.with_suffix('.md')}")
                return 1
            runtime.mark_sent(cfg.runtime_root, day,
                              f"{day} 已发送 {datetime.now(BEIJING):%Y-%m-%d %H:%M:%S}"
                              f" 北京时间 · 目标：生产管理群\n")
            runtime.emit("SEND_COMPLETED", f"生产管理群 · {title}")
            return 0
    except runtime.AlreadyRunning as e:
        runtime.emit("LOCK_HELD", str(e)); return 75
    except TimeoutError as e:
        runtime.emit("ABORTED_TIMEOUT", f"{e}，本轮不补发")
        runtime.alarm(cfg.dws, cfg.notify_user, "ABORTED_TIMEOUT",
                      f"考勤简报超时中止（上限 {cfg.wall_clock_limit} 秒），今天这份没发出去。\n{e}")
        return 1
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        runtime.emit("RUN_FAILED", f"{type(e).__name__}: {e}")
        runtime.runlog(tb)
        runtime.alarm(cfg.dws, cfg.notify_user, "RUN_FAILED",
                      f"考勤简报跑挂了，今天这份没发出去。\n{type(e).__name__}: {e}\n"
                      f"详细堆栈见运行日志 {cfg.runtime_root}/logs/kmfa_brief_run.log")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
