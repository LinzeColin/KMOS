#!/usr/bin/env python3
"""KMFA 每日资金 · 本机路线入口。

    backfill [--limit N] [--from D] [--to D]   历史回填
    poll                                        只补尚未入库的日期
    bills  [--days N] [--attempts N]            「现存票据」入库（14 天内到期承兑的源）
    render [--out PNG]                          出图（不发送）
    send   [--dry-run] [--to-group]             出图并发送
    stats                                       库里现状

与同级云端 daily_funds/ 完全独立：只读 SMB、本地出图、DWS 单聊发送。
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daily_funds_local import bills, card, gate, notify     # noqa: E402
from daily_funds_local.smb_source import SmbArchive, SmbUnavailable  # noqa: E402
from daily_funds_local.store import Store, data_dir         # noqa: E402
from daily_funds_local.vision import VisionError, read_bill_list, read_card  # noqa: E402


HARD_GATE_ATTEMPTS = 3   # 硬门失败即重读；实测单次误读率约 15%


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest(args) -> int:
    archive = SmbArchive()
    store = Store()
    have = store.have_dates()
    seen = store.seen_originals() if args.command == "poll" else set()

    cands = sorted(archive.candidates(), key=lambda c: c.message_time)
    if args.since:
        cands = [c for c in cands if c.message_date >= args.since]
    if args.until:
        cands = [c for c in cands if c.message_date <= args.until]
    if args.command == "poll":
        cands = [c for c in cands if c.original_name not in seen]
    if getattr(args, "retry_skipped", False):
        # 闸门/读图改进之后重试历史丢弃项。只跑这些，不重烧已经读对的天。
        retry = store.retryable_originals()
        cands = [c for c in cands if c.original_name in retry]
    if args.limit:
        cands = cands[-args.limit:]

    stats = {"candidates": len(cands), "stored": 0, "imbalance": 0,
             "file_missing": 0, "vision_failed": 0, "hard_gate_failed": 0,
             "chain_suspect": 0, "already": 0}
    tmpdir = tempfile.mkdtemp(prefix="kmfa-cards-")

    # 一轮回填有两百多条写。每条都刷 SMB 就是两百多次网络往返，
    # 而且每次都是一个可能被打断的写窗口。整轮结束统一落盘一次。
    store.begin_batch()

    for cand in cands:
        local = archive.fetch(cand, tmpdir)
        if not local:
            stats["file_missing"] += 1
            store.mark_skipped(cand.message_date, cand.original_name,
                               "file_missing", "", _now())
            store.mark_seen(cand.original_name, "file_missing", _now())
            continue
        # 硬门失败几乎总是单个数字读错（实测：十万位的 6 读成 0）。
        # 重读一次通常就对了，所以不要一次不过就丢弃整天数据。
        facts = None
        result = None
        last_err = ""
        for attempt in range(HARD_GATE_ATTEMPTS):
            try:
                facts = read_card(local, cand.layout)
            except VisionError as exc:
                last_err = str(exc)[:160]
                facts = None
                continue
            prev_date, prev_close = store.prev_close(facts.report_date)
            result = gate.check(facts, prev_close=prev_close, prev_date=prev_date)
            # 链条断裂**超过量级门槛**才值得重读。门槛内的小差额是源表人工微调
            # （实测最大一千多元，财务改了前一天的数没重述），不是读错。
            # gate.check 已经按门槛判过了，这里只看它给的 chain_ok。
            if result.passed_hard and result.chain_ok:
                break
            last_err = ";".join(result.reasons)[:200]

        if facts is None:
            stats["vision_failed"] += 1
            store.mark_skipped(cand.message_date, cand.original_name,
                               "vision_failed", last_err, _now())
            store.mark_seen(cand.original_name, "vision_failed", _now())
            continue

        if facts.report_date in have and args.command == "poll":
            stats["already"] += 1
            continue

        if not result.passed_hard:
            stats["hard_gate_failed"] += 1
            store.mark_skipped(cand.message_date, cand.original_name,
                               "hard_gate_failed", last_err, _now())
            store.mark_seen(cand.original_name, "hard_gate_failed", _now())
            continue

        store.upsert(
            report_date=facts.report_date,
            bank_fen=facts.bank_close,
            bill_fen=facts.bill_close,
            total_fen=gate.storable_total(facts),
            layout=facts.layout,
            source_imbalance=result.source_imbalance,
            chain_suspect=result.chain_suspect,
            gate_reasons=";".join(result.reasons)[:400],
            image_sha256=_sha(local),
            message_date=cand.message_date,
            extracted_at=_now(),
        )
        store.clear_skipped(cand.original_name)
        store.mark_seen(cand.original_name, "stored", _now())
        have.add(facts.report_date)
        stats["stored"] += 1
        if result.source_imbalance:
            stats["imbalance"] += 1
        if result.chain_suspect:
            stats["chain_suspect"] += 1

    store.end_batch()

    for k, v in stats.items():
        print("  %-18s %d" % (k, v))
    print("\n库内现状:", store.counts())
    # 「今天没有新表」对每日轮询是正常结果，不是失败——把它当失败会让
    # cron 日志天天记一条假告警，真出事那条就淹没了。只有真的取不到/读不出
    # 才算失败。
    broken = stats["file_missing"] + stats["vision_failed"]
    return 2 if broken and not stats["stored"] else 0


def _beijing_now() -> dt.datetime:
    return dt.datetime.utcnow() + dt.timedelta(hours=8)


def ingest_bills(args) -> int:
    """「现存票据」入库：找消息 → 取归档图 → 读 → 三道校验位 + 跨源 → 入库。

    每轮读图有次数和时间上限：周一 12:00 这轮排在出卡片之前，不能把卡片拖晚。
    读不过不记失败到底——表在有效期内，第二天会再试；卡片侧用上一张合格的表滚动。
    """
    archive = SmbArchive()
    store = Store()
    now = _beijing_now()
    since = (now - dt.timedelta(days=args.days)).strftime("%Y-%m-%d 00:00:00")
    msgs = bills.find_list_messages(notify.dws_json, notify.PAYMENT_GROUP, since,
                                    now.strftime("%Y-%m-%d %H:%M:%S"), max_pages=args.pages)
    stats = {"found": len(msgs), "stored": 0, "already": 0, "expired": 0,
             "not_archived": 0, "pending": 0, "failed": 0}
    tmpdir = tempfile.mkdtemp(prefix="kmfa-bills-")
    t0 = time.monotonic()
    for m in msgs:
        if store.has_bill_list(m["media"]):
            stats["already"] += 1
            continue
        posted = dt.date.fromisoformat(m["posted_at"][:10])
        if (now.date() - posted).days > bills.MAX_LIST_AGE_DAYS and not args.backfill:
            stats["expired"] += 1          # 过了有效期，读出来卡片也不会用
            continue
        path = archive.fetch_media(m["media"], tmpdir)
        if not path:
            stats["not_archived"] += 1
            print("  %s 还没归档到，下一轮再试" % m["posted_at"])
            continue
        outcome, detail = "failed", ""
        for attempt in range(args.attempts):
            if time.monotonic() - t0 > args.budget:
                detail = "BUDGET"
                break
            try:
                data = read_bill_list(path, scale=1 if attempt % 2 == 0 else 2)
            except VisionError as exc:
                detail = str(exc)[:160]
                continue
            rows, total, errors = bills.parse_read(data)
            chk = bills.check_rows(rows, total, posted, errors)
            if not chk.ok:
                detail = ";".join(chk.reasons)[:300]
                continue
            window = store.balances_between(*bills.cross_window(chk.ref_date))
            if not window:
                outcome, detail = "pending", "NO_BALANCE_YET"
                break
            as_of = bills.cross_match(total, window)
            if as_of is None:
                detail = "CROSS_MISMATCH:%d~%s" % (total, window[-1])
                continue
            store.upsert_bill_list(media=m["media"], posted_at=m["posted_at"],
                                   ref_date=chk.ref_date, as_of=as_of, total_fen=total,
                                   bills=[list(b) for b in chk.bills],
                                   image_sha256=_sha(path), extracted_at=_now())
            store.clear_skipped(m["media"])
            outcome, detail = "stored", "ref=%s as_of=%s 张数=%d" % (chk.ref_date, as_of, len(chk.bills))
            break
        stats[outcome] += 1
        if outcome == "failed":
            store.mark_skipped(m["posted_at"][:10], m["media"], "bill_list_failed", detail, _now())
        print("  %s %s %s" % (m["posted_at"], outcome, detail))
    for k, v in stats.items():
        print("  %-14s %d" % (k, v))
    return 2 if stats["failed"] and not stats["stored"] else 0


def _due14(store: Store, rows):
    return bills.card_fields(store.bill_lists(), rows[-1].report_date, rows[-1].bill_fen)


def _notice_once(store: Store, key: str, text: str) -> str:
    """首报制：同一件事只说一次。返回 sent / known / failed。发不出去不记台账，下一轮再说。"""
    if store.has_alert(key):
        return "known"
    try:
        notify.send_notice(text)
    except Exception as exc:
        print("提醒没发出去:", exc, file=sys.stderr)
        return "failed"
    store.mark_alert(key, text, _now())
    return "sent"


RECHECK_WINDOW_DAYS = 12   # 覆盖春节/国庆长假后的批量补发


def recheck(args) -> int:
    """重读被标记 chain_suspect 的天，用补齐后的序列重新判定。

    为什么必须重读而不是重算：链条校验比的是「今天表上印的**昨日余额**」对
    「昨天读到的**今日余额**」——按定义是同一个量。入库时只存了收盘值，
    开盘列没留，所以离线算不出来。而「今日收盘 vs 昨日收盘」不是一致性校验，
    那只是资金正常变动，拿它当校验会把每一天正常收付都标成可疑。

    入库时的标记还带一层顺序偏差：候选按消息时间处理，周一一次补发周五/六/日
    三张表时，先入库的那张会跟一个非相邻日比。序列补齐后重读才作数。
    """
    archive = SmbArchive()
    store = Store()
    flagged = [r.report_date for r in store.series() if r.chain_suspect]
    if not flagged:
        print("没有待复核的天")
        return 0

    by_date = {}
    tmpdir = tempfile.mkdtemp(prefix="kmfa-recheck-")
    for cand in sorted(archive.candidates(), key=lambda c: c.message_time):
        by_date.setdefault(cand.message_date, []).append(cand)

    cleared = kept = unresolved = 0
    for date in flagged:
        # 表报的是前一天，且长假后会一次性补发整段。实测 2026-05-01 那张是在
        # 05-06 补发的（劳动节），窗口开 4 天会找不到图，然后把一个纯粹的
        # 入库顺序假象当成真断链留在库里。按最长法定假期留足余量。
        d0 = dt.date.fromisoformat(date)
        pool = []
        for k in range(1, RECHECK_WINDOW_DAYS + 1):
            pool += by_date.get((d0 + dt.timedelta(days=k)).isoformat(), [])
        hit = None
        for cand in pool:
            local = archive.fetch(cand, tmpdir)
            if not local:
                continue
            try:
                facts = read_card(local, cand.layout)
            except VisionError:
                continue
            if facts.report_date == date:
                hit = (facts, local, cand)
                break
        if hit is None:
            unresolved += 1
            print("  %s  找不到对应图，保留标记" % date)
            continue
        facts, local, cand = hit
        prev_date, prev_close = store.prev_close(date)
        result = gate.check(facts, prev_close=prev_close, prev_date=prev_date)
        if not result.passed_hard:
            unresolved += 1
            print("  %s  重读仍不过硬门，保留标记" % date)
            continue
        store.upsert(
            report_date=facts.report_date, bank_fen=facts.bank_close,
            bill_fen=facts.bill_close, total_fen=gate.storable_total(facts),
            layout=facts.layout, source_imbalance=result.source_imbalance,
            chain_suspect=result.chain_suspect,
            gate_reasons=";".join(result.reasons)[:400], image_sha256=_sha(local),
            message_date=cand.message_date, extracted_at=_now())
        if result.chain_suspect:
            kept += 1
            print("  %s  重读后仍断链（%s）——大概率是源表本身跳了"
                  % (date, next((x for x in result.reasons
                                 if x.startswith("SOFT_CHAIN")), "")))
        else:
            cleared += 1
    print("\n复核 %d 天：澄清 %d，仍断链 %d，无法判定 %d"
          % (len(flagged), cleared, kept, unresolved))
    print("库内现状:", store.counts())
    return 0


def _series_and_staleness(store: Store):
    rows = store.series()
    if not rows:
        raise SystemExit("库里没有数据，先跑 backfill")
    today = dt.date.today()
    stale = (today - dt.date.fromisoformat(rows[-1].report_date)).days
    # 表发的是前一天的数，所以滞后 1 天是正常的
    return rows, max(0, stale - 1)


def render(args) -> int:
    store = Store()
    rows, stale = _series_and_staleness(store)
    out = args.out or os.path.join(tempfile.mkdtemp(prefix="kmfa-card-"),
                                   "资金账户日报_%s.png" % rows[-1].report_date.replace("-", ""))
    fields, status, _ = _due14(store, rows)
    payload = card.build_payload(rows, stale)
    payload.update(fields)
    card.render(payload, out)
    print(out)
    print("14 天内到期承兑：", status)
    print()
    print(card.summary_text(rows, stale, fields.get("bill_due14")))
    return 0


# 断供时管道会安静地发一张旧图，所以要有阈值：超过就告警，且不许进群。
#
# 阈值必须大于「正常周末 + 财务当天还没发」这个组合，否则每周一都会被自己挡住。
# 算一下：上周四的余额表在周五发出，到周一 stale = (周一 − 周四) − 1 = 3。
# 实测 2026-09-07 周一 12:03 那次就是这么被挡的——数据并没有断，只是周末没有表。
# 取 6 天：周一那 3 天照常放行，真正的断供（实测 2026-08-30 起断过 6 天）仍然拦得住。
STALE_ALERT_DAYS = 6


def send(args) -> int:
    store = Store()
    try:
        # 先过发送目标这道闸，再干别的。
        # 否则 --dry-run --to-group 在未授权时也会「通过」，给出假信心——
        # dry-run 的全部价值就是忠实预演真实路径，不校验闸门的预演是骗人的。
        notify.resolve_target(to_group=args.to_group)

        rows, stale = _series_and_staleness(store)
        if stale >= STALE_ALERT_DAYS:
            warn = ("上游归档已 %d 天没有新表（最新 %s）。\n"
                    "多半是上游归档没在跑，或者财务这几天没发表。"
                    % (stale, rows[-1].report_date))
            if args.to_group and not args.dry_run:
                # 不把陈旧数据推给管理层，改成私下告警
                notify.send_failure(warn + "\n本次未发群。")
                print("数据过旧，已改为私聊告警，未发群", file=sys.stderr)
                return 3
            print("警告:", warn.replace("\n", " "), file=sys.stderr)
        out = os.path.join(tempfile.mkdtemp(prefix="kmfa-card-"),
                           "资金账户日报_%s.png" % rows[-1].report_date.replace("-", ""))
        fields, due_status, due_list = _due14(store, rows)
        payload = card.build_payload(rows, stale)
        payload.update(fields)
        card.render(payload, out)
        text = card.summary_text(rows, stale, fields.get("bill_due14"))
        if args.dry_run:
            print("[dry-run] 不发送。图:", out)
            print(text)
            return 0
        notify.send_card(out, text, to_group=args.to_group)
        print("已发送（图 + 文字）:",
              "付款请示群" if args.to_group else "张霖泽（单聊）")
        # 授权只能人工 OAuth 续期，自动化补不了。唯一能做的是提前喊一声，
        # 别让它某天早上突然静默停摆。
        # 色块不画的两种情况要让人知道，但只说一次（按用到的那张表做指纹）。
        if due_status == "stale":
            _notice_once(store, "bills_stale:%s" % due_list["media"],
                         "每日资金：「现存票据」最近一张合格的是 %s 发的，已超过 %d 天，"
                         "卡片上的「14 天内到期承兑」先不显示。多半是周一的表没发、没归档，"
                         "或者读图没过校验。" % (due_list["posted_at"][:10], bills.MAX_LIST_AGE_DAYS))
        elif due_status == "none":
            _notice_once(store, "bills_none", "每日资金：库里还没有任何一张合格的「现存票据」，"
                                              "卡片上的「14 天内到期承兑」不显示。")
        warned = notify.warn_if_auth_expiring()
        if warned:
            print("提醒已发出:", warned.replace("\n", " "), file=sys.stderr)
        return 0
    except Exception as exc:
        detail = "%s: %s" % (type(exc).__name__, exc)
        print("发送失败:", detail, file=sys.stderr)
        traceback.print_exc()
        if not args.dry_run:
            try:
                notify.send_failure(detail)   # 只发个人，不进群
            except Exception:
                print("连失败通知都没发出去", file=sys.stderr)
        return 2


AUTOMATION_TOML = os.path.expanduser("~/.codex/automations/kmfa-daily-funds/automation.toml")
RUNTIME_SCRIPT = os.path.expanduser("~/.codex/skills/KMFA-Daily-Funds/scripts/daily_funds_run.sh")


def _previous_weekday(today: dt.date) -> dt.date:
    d = today - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def _smb_text(path) -> str:
    """SMB 只用 rsync 读。文件不存在返回空串。"""
    if not os.path.exists(str(path)):
        return ""
    local = os.path.join(tempfile.mkdtemp(prefix="kmfa-wd-"), "f.txt")
    rc = subprocess.run(["rsync", "-a", "--inplace", str(path), local], capture_output=True, text=True)
    if rc.returncode != 0:
        raise SmbUnavailable("读不到 %s: %s" % (path, rc.stderr.strip()[:120]))
    return open(local, encoding="utf-8", errors="replace").read()


def _ran_on(day: dt.date, state) -> bool:
    """那天有没有跑过：发送标记，或运行日志里有那天的带日期行（每条路径都会写）。"""
    if os.path.exists(os.path.join(str(state), ".sent-%s" % day.isoformat())):
        return True
    return ("\n[%s " % day.isoformat()) in ("\n" + _smb_text(os.path.join(str(state), "daily_funds_run.log")))


def watchdog(args) -> int:
    """资金线停摆检测，由另一条 automation 每个工作日上午调用。

    主任务被暂停、被删、或者某天根本没被叫起来，它自己报不了——它都没跑。
    所以只能由别的任务来看。只查两件事，发现就私聊张霖泽，同一件事只说一次：
      1. 配置还在、状态是 ACTIVE、调的还是运行位的脚本（Codex 应用改过手改的配置）；
      2. 上一个工作日（本机日历，rrule 按本机时区排）有跑过的痕迹。
    """
    store = Store()
    problems = []
    try:
        txt = open(args.toml, encoding="utf-8").read()
        m = re.search(r'^status\s*=\s*"([^"]*)"', txt, re.M)
        u = re.search(r"^updated_at\s*=\s*(\d+)", txt, re.M)
        status = m.group(1) if m else "UNKNOWN"
        if RUNTIME_SCRIPT not in txt:
            problems.append(("path:%s" % (u.group(1) if u else ""),
                             "每日资金 automation 调的已经不是运行位脚本 %s（多半被改回了主工作树的旧路径）。"
                             "主工作树会被定期恢复原状，那里的旧脚本没有崩溃保护。"
                             "请在 Codex 里把命令改回运行位路径。" % RUNTIME_SCRIPT))
        if status != "ACTIVE":
            problems.append(("status:%s:%s" % (status, u.group(1) if u else ""),
                             "每日资金 automation 现在是 %s，不会再自动发卡片。"
                             "要恢复请在 Codex 里把它改回 ACTIVE。" % status))
    except FileNotFoundError:
        problems.append(("toml_missing", "每日资金 automation 的配置不见了（%s），不会再自动发卡片。" % args.toml))
    day = _previous_weekday(dt.date.today())
    if not _ran_on(day, data_dir()):
        problems.append(("norun:%s" % day.isoformat(),
                         "%s（周%s）没有任何运行记录——没发卡片，也没有失败告警。"
                         "多半是 automation 没被触发：Codex 应用没开、机器睡了，或任务被暂停。"
                         % (day.isoformat(), "一二三四五六日"[day.weekday()])))
    # 输出给调度侧读：只有「本轮新发出」的告警才让 automation 上报。
    # 同一个问题持续多天时每天都 ESCALATE，就是在另一个渠道天天重报，违背首报制。
    result = {"sent": [], "known": [], "failed": []}
    for key, text in problems:
        result[_notice_once(store, "watchdog:" + key, "每日资金看门狗：" + text)].append(key)
    if not problems:
        print("WATCHDOG_OK 检查 %s：正常" % day.isoformat())
    elif result["sent"] or result["failed"]:
        print("WATCHDOG_ALERT 检查 %s：新告警 %s；发送失败 %s；已报过 %s"
              % (day.isoformat(), result["sent"], result["failed"], result["known"]))
    else:
        print("WATCHDOG_KNOWN 检查 %s：问题仍在但都已报过 %s" % (day.isoformat(), result["known"]))
    return 0


def stats(args) -> int:
    store = Store()
    counts = store.counts()
    for k, v in counts.items():
        print("  %-16s %s" % (k, v))
    rows = store.series()
    if rows:
        print("\n  区间  %s → %s" % (rows[0].report_date, rows[-1].report_date))
        print("  最新  %.2f 万" % ((rows[-1].bank_fen + rows[-1].bill_fen) / 1e6))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="KMFA 每日资金 · 本机路线")
    sub = p.add_subparsers(dest="command", required=True)

    for name in ("backfill", "poll"):
        s = sub.add_parser(name)
        s.add_argument("--limit", type=int, default=0)
        s.add_argument("--from", dest="since", default="")
        s.add_argument("--to", dest="until", default="")
        s.add_argument("--retry-skipped", action="store_true",
                       help="只重跑历史丢弃项（闸门或读图改进之后用）")
        s.set_defaults(func=ingest)

    s = sub.add_parser("bills")
    s.add_argument("--days", type=int, default=bills.MAX_LIST_AGE_DAYS + 2)
    s.add_argument("--pages", type=int, default=3)
    s.add_argument("--attempts", type=int, default=2)
    s.add_argument("--budget", type=int, default=300, help="本轮读图总秒数上限")
    s.add_argument("--backfill", action="store_true", help="过了有效期的表也读（回填用）")
    s.set_defaults(func=ingest_bills)

    s = sub.add_parser("render")
    s.add_argument("--out", default="")
    s.set_defaults(func=render)

    s = sub.add_parser("send")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--to-group", action="store_true",
                   help="发付款请示群（还需 DAILY_FUNDS_ALLOW_GROUP=1）")
    s.set_defaults(func=send)

    s = sub.add_parser("recheck")
    s.set_defaults(func=recheck)

    s = sub.add_parser("watchdog")
    s.add_argument("--toml", default=AUTOMATION_TOML)
    s.set_defaults(func=watchdog)

    s = sub.add_parser("stats")
    s.set_defaults(func=stats)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except SmbUnavailable as exc:
        print("SMB 不可用:", exc, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
