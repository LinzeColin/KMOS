#!/usr/bin/env python3
"""考勤异常简报 —— 唯一入口。

调度方只需要设 KMFA_RUN_SLOT 并执行这一条命令，不传业务参数、不做任何判断：

    KMFA_RUN_SLOT=evening python3 scripts/run_attendance_brief.py

Codex automation / 人手动执行，结果完全一致（幂等）：一天只发一次。
失败自己写日志、自己在下一轮重跑，调度方不需要看懂任何东西。
"""
from __future__ import annotations
import json, os, re, sys, argparse
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

def _title_date(title: str) -> str | None:
    """从「2026.09.16人员表」这类标题里抠出日期。抠不出返回 None。"""
    m = re.search(r"(20\d{2})[.\-/年](\d{1,2})[.\-/月](\d{1,2})", title or "")
    return f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}" if m else None

def _wide(p: Path) -> bool:
    """便宜的预筛：人员表是 23 列的宽表，聊天截图和现场照片基本都是竖的。
    只用来省掉无谓的 OCR（一张 18 秒），**不当判据** —— 真判据是能不能解出表格结构。
    看不出来就别拦，交给 extract 去判。"""
    try:
        from PIL import Image
        w, h = Image.open(p).size
        return w >= h
    except Exception:
        return True

def pick_table(imgs: list, dl, day: str) -> tuple:
    """从当天所有图里挑出人员表那一张。返回 (图, 解析结果, 标题日期) 或 (None, None, None)。

    不能按「最新那张就是人员表」办 —— 当天群里还会有聊天截图、现场照片，
    也可能一天发两版表、或者提前发次日的表。
    2026-09-15 实测：16:29 发人员表、16:56 发了一张聊天截图，
    而调用方只取 imgs[0]，于是整份报告降级成「读不准」，
    而 find_table_images 的注释里本来就写着「最新的先试」—— 只是从来没试过第二张。

    挑法：能解出表格结构的才算候选；多个候选里优先标题日期正好是业务日的那张，
    没有就用最新的那张（并把实际用的是哪天的表往上报，不闷着）。
    """
    cands = []
    for cand in imgs:
        if not _wide(cand):
            continue
        dl.check("识别人员表")
        t = extract.extract(str(cand))
        if t["类别可信"]:
            cands.append((cand, t, _title_date(t["标题"])))
    if not cands:
        return None, None, None
    return next((c for c in cands if c[2] == day), cands[0])


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
    img, tab, tdate = pick_table(imgs, dl, day)
    if tab is None:
        out["状态"] = "读不准"
        out["不可信"] = [(0, f"当天 {len(imgs)} 张图里没有一张能解出人员表结构")]
        return out
    # 按时率按**人员表那张**的时间算，不按当天最后一张图的时间 ——
    # 今天 16:29 就发了表、16:56 发的是别的东西，按 16:56 算等于冤枉发布人。
    hhmm = img.stem.split("_")[1][:2] + ":" + img.stem.split("_")[1][2:]
    punctuality.record(ledger, day, hhmm)
    ok, tot = punctuality.recent(ledger, day, cfg.deadline)
    out["人员表时间"] = hhmm
    out["按时"] = hhmm < cfg.deadline          # "HH:MM" 补零后按字符串比就是按时间比
    out["截止"] = cfg.deadline
    out["按时率"] = (ok, tot)
    out["发布人"] = "、".join(cfg.publishers)
    if tdate and tdate != day:
        # 用的不是业务日那天的表（常见于提前发次日计划）。照常出报，但要说清楚，
        # 不能让人以为这份考勤是照着今天的在场表判的。
        out["表日期"] = tdate

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

    def 没打 (r) -> bool:
        """None = 钉钉这一趟压根没返回这个打卡点的记录。

        以前把 None 当成「不是 NotSigned，所以正常」，于是只返回上班卡那一条的日子，
        简报会写「缺上班卡，**下班正常**」—— 而那天他下班也没打。
        2026-09-15 实测有人连着六周每天两条 NotSigned，最近一天只返回一条，
        简报当天就说他下班正常。**没有记录不是正常，是不知道。**
        """
        return r is None or r in ("NotSigned", "Absenteeism")

    # 「缺下班卡」只在这个打卡点**已经到点**之后才算数。
    #
    # 出报时刻是北京 17:15，而班次下班是 17:30 —— 当天出报时下班卡本来就还没到时间。
    # #417 修掉了「钉钉没返回这个打卡点就当他正常」，但没带上「到点了没有」这一半，
    # 于是同一批人在当天出报时会被整片判成缺下班卡。
    # 2026-09-15 实测：同一天同一批人，北京 17:17 跑报 3 条、17:35 跑报 28 条，
    # 差的 25 条全是「缺下班卡」—— 那 25 条一条都不成立，他们只是还没到下班时间。
    # 报的是过去某一天（补跑 / --date 指定）时数据已经收全，照常判。
    # 当天的下班卡不是不管：周报的「打卡规范」按月累计缺卡次数，出口在那里。
    判下班 = day < datetime.now(BEIJING).strftime("%Y-%m-%d")
    todo_考勤: list[str] = []
    todo = todo_考勤          # 下面的追加都进考勤类
    for p in need:
        v = by_uid.get(p["uid"], {})
        on, off = v.get("OnDuty"), v.get("OffDuty")
        where = p["行"]["项目"] or p["行"]["类别"]
        if not v and 判下班:
            todo.append(f"{p['姓名']}（{where}）应打卡，钉钉无任何记录 → 本人补卡 · 明日 18:00 前")
        elif 没打(on) and 没打(off) and 判下班:
            todo.append(f"{p['姓名']}（{where}）应打卡，全天未打卡 → 本人补卡 · 明日 18:00 前")
        elif 没打(on):
            todo.append(f"{p['姓名']}（{where}）缺上班卡 → 本人补卡 · 明日 18:00 前")
        elif 判下班 and 没打(off):
            todo.append(f"{p['姓名']}（{where}）缺下班卡 → 本人补卡 · 明日 18:00 前")
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
        "休息": rest, "回程": back, "外协": outs, "判下班": 判下班,
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
    if a.dry_run:
        runtime.quiet_alarms()
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
    finally:
        runtime.emit_action()

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

    # 幂等：一个业务日最多一条完整版，谁触发的都一样，--force 也不放行。
    # 只有「已经发过的是降级版」这一种情况放行 —— 那条是临时的，等的就是完整版。
    kind = None if a.dry_run else runtime.sent_kind(cfg.runtime_root, day)
    if kind == runtime.FINAL:
        runtime.emit("SKIP_ALREADY_SENT", f"{day} 完整版已经发过了")
        return 0
    # 周末 / 非工作日只拦排程；人按 Run 是他自己要，放行。
    auto = not a.date and not a.dry_run and not a.force
    if auto and datetime.strptime(day, "%Y-%m-%d").weekday() >= 5:
        runtime.emit("SKIP_WEEKEND", f"{day} 是周末，人员表本来就不在周末发")
        return 0

    # 发送窗口（北京 17:15 起 window_hours 小时）**对所有触发一视同仁，--force 也不放行**。
    #
    # 老板 2026-09-10 定的规矩原话：闸门要上下沿都有，落在真正投递的那一层，
    # 不留任何口子能绕过它 —— 在非指定时间冒出消息，等于自动化失控。
    #
    # 为什么 --force 也必须挡：包装脚本靠「离计划钟点多远」区分「排程」和「人点的 Run」，
    # 远就给 --force。而 Codex 的 automation-run-mode 明写「不得因错过计划而拒绝执行」，
    # 也就是说**桌面端重新打开时会把错过的那一枪补上**，补跑离钟点同样很远，
    # 按那个推断会拿到 --force。运行日志里就有实例：
    #   2026-09-10 11:20 RUN_START 北京 09:20 force=1 scheduled=1
    # 那次只是恰好撞上「今天已发过」才没有在北京早上九点把简报发进生产管理群。
    #
    # 窗口外没有补发路径，这是有意的：--force / --date / --send 一个都不放行，
    # 只有 --dry-run 能跑（它在代码层面就调不到投递函数，只把报文打到屏幕上）。
    # 昨天的考勤在今晚十点补进生产管理群，对谁都没有用；想看内容就干跑。
    want = cfg.publish_hour * 60 + cfg.publish_minute
    stop = want + cfg.window_hours * 60
    nowm = now_bj.hour * 60 + now_bj.minute
    win = f"{want // 60:02d}:{want % 60:02d}–{stop // 60:02d}:{stop % 60:02d}"
    if not a.dry_run and nowm < want - 5:      # 容 5 分钟：调度器落地有抖动
        runtime.emit("SKIP_BEFORE_PUBLISH",
                     f"北京 {now_bj:%H:%M} 还没到出报时刻 "
                     f"{cfg.publish_hour:02d}:{cfg.publish_minute:02d}，等本工作日的下一个触发点")
        return 0
    if not a.dry_run and nowm > stop:
        runtime.emit("SKIP_AFTER_WINDOW",
                     f"北京 {now_bj:%H:%M} 已过发送窗口 {win}，今天不补发，等下一个工作日")
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
            # 本轮出的是完整版还是降级版。降级 = 没拿到人员表 / 读不准，判不了考勤。
            this_kind = runtime.FINAL if data["状态"] == "正常" else runtime.DEGRADED
            if kind == runtime.DEGRADED and this_kind == runtime.DEGRADED:
                # 催办已经发过一条了，同一天不再催第二遍。
                runtime.emit("SKIP_ALREADY_SENT", f"{day} 降级版已发过，人员表还是没到，本轮不重复催")
                return 0
            stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            base = cfg.month_dir(day) / f"brief_{day.replace('-','')}_{stamp}"
            runtime.smb_write(body, base.with_suffix(".md"))
            runtime.smb_write(json.dumps(data, ensure_ascii=False, indent=1),
                              base.with_suffix(".json"))
            print(f"# {title}\n\n{body}")
            # 禁用词闸对干跑和真发一视同仁。以前它写在下面那三个 return 之后 ——
            # 于是干跑永远看不出这份报文会被拒，等排程那一轮才炸，而那时已经来不及。
            # 验证路径必须和生产路径判一样的闸，否则验证不出问题。
            bad = runtime.banned_words(f"{title}\n{body}")
            if bad:
                runtime.emit("BANNED_WORD", f"报文里出现禁用词 {bad}，拒发")
                runtime.alarm(cfg.dws, cfg.notify_user, "BANNED_WORD",
                              f"考勤简报里出现了禁用词 {bad}，已拒发，今天这份没发出去。\n"
                              f"报文已存 {base.with_suffix('.md')}")
                return 1
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
                              f" 北京时间 · 目标：生产管理群",
                              this_kind)
            runtime.emit("SEND_COMPLETED",
                         f"生产管理群 · {title}"
                         + (f" · 顶替了本日的降级版" if kind == runtime.DEGRADED else ""))
            return 0
    except runtime.AlreadyRunning as e:
        runtime.emit("LOCK_HELD", str(e)); return 75
    except collect.DwsUnavailable as e:
        # 「够不着钉钉」跟「查到的是空」必须分开。降级成空集会让简报去公开点
        # 发布人的名（他其实发了），或者整片点名补卡（他们其实打了卡）。
        # 给管理层看错名字，比今天不发严重得多 —— 一律拒发。
        runtime.emit("DINGTALK_UNAVAILABLE", str(e))
        runtime.alarm(cfg.dws, cfg.notify_user, "DINGTALK_UNAVAILABLE",
                      f"考勤简报没跑成：连不上钉钉网关，今天这份没发出去。\n{e}\n"
                      f"这是阵发性的，本工作日剩下的触发点还会再试。")
        return 1
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
