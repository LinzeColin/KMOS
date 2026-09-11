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
from daily_funds_local.store import Store, StoreBusy, data_dir  # noqa: E402
from daily_funds_local.vision import VisionError, bill_read_plan, read_bill_list, read_card  # noqa: E402


HARD_GATE_ATTEMPTS = 3   # 硬门失败即重读；实测单次误读率约 15%

# 表报的是前一天或更早的数；长假后会一次补发整段（实测劳动节隔 5 天）。
# 读出来的日期晚于消息日期、或早于消息日期太多，就是把日期读错了——入库它会霸占「最新」，
# 让卡片一直停在一个错日期上。
REPORT_DATE_MAX_LAG_DAYS = 14


def _date_window_error(report_date: str, message_date: str) -> str:
    try:
        r = dt.date.fromisoformat(report_date)
        m = dt.date.fromisoformat(message_date)
    except ValueError:
        return "HARD_BAD_DATE:%s" % report_date
    if r > m:
        return "HARD_FUTURE_DATE:%s>%s" % (report_date, message_date)
    if (m - r).days > REPORT_DATE_MAX_LAG_DAYS:
        return "HARD_DATE_TOO_OLD:%s<%s" % (report_date, message_date)
    return ""


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
    if args.command == "poll" and not getattr(args, "retry_skipped", False):
        # --retry-skipped 要重试的正是「处理过」的那些，先按 seen 排除就一个都剩不下
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
                facts = read_card(local, cand.layout, message_date=cand.message_date)
            except VisionError as exc:
                last_err = str(exc)[:160]
                facts = None
                continue
            prev_date, prev_close = store.prev_close(facts.report_date)
            result = gate.check(facts, prev_close=prev_close, prev_date=prev_date)
            date_err = _date_window_error(facts.report_date, cand.message_date)
            if date_err:
                result.passed_hard = False
                result.reasons.append(date_err)
            # 链条断裂**超过量级门槛**才值得重读。门槛内的小差额是源表人工微调
            # （实测最大一千多元，财务改了前一天的数没重述），不是读错。
            # 收支不闭合也要重读：收盘列里分项和合计一起读错时组成关系仍然自洽，
            # 只有流水对不上——重读能分清是读错还是源表真的没平（04-27 那种）。
            # 重读后仍不闭合才按源表问题入库并打标记。
            if result.passed_hard and result.chain_ok and result.flow_ok:
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
    # cron 日志天天记一条假告警，真出事那条就淹没了。只有真的取不到/读不出/读错被拦
    # 才算失败：闸门把新表全拦下时卡片只能用旧数，这件事必须有人知道。
    broken = stats["file_missing"] + stats["vision_failed"] + stats["hard_gate_failed"]
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
    deadline = time.monotonic() + args.budget      # 总预算从翻群消息之前算起
    now = _beijing_now()
    since = (now - dt.timedelta(days=args.days)).strftime("%Y-%m-%d 00:00:00")
    msgs = bills.find_list_messages(notify.dws_json, notify.PAYMENT_GROUP, since,
                                    now.strftime("%Y-%m-%d %H:%M:%S"), max_pages=args.pages)
    stats = {"found": len(msgs), "stored": 0, "already": 0, "expired": 0,
             "not_archived": 0, "pending": 0, "failed": 0}
    tmpdir = tempfile.mkdtemp(prefix="kmfa-bills-")
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
        plan = bill_read_plan(path)
        # 过了四道闸门的读法先攒着，两次（不同读法）逐行一致才入库：
        # 只核总额挡不住两行金额读串位、互相抵消。
        good = []
        for attempt in range(args.attempts):
            if deadline - time.monotonic() < 15:
                detail = "BUDGET"
                break
            scale, parts = plan[attempt % len(plan)]
            try:
                data = read_bill_list(path, scale=scale, parts=parts, deadline=deadline)
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
            if not any(bills.same_reading(prev, chk) for prev in good):
                good.append(chk)
                detail = "WAIT_SECOND_READING（%d 次合格读法互不一致）" % len(good)
                continue
            store.upsert_bill_list(media=m["media"], posted_at=m["posted_at"],
                                   ref_date=chk.ref_date, as_of=as_of, total_fen=total,
                                   bills=[list(b) for b in chk.bills],
                                   image_sha256=_sha(path), extracted_at=_now())
            store.clear_skipped(m["media"])
            outcome, detail = "stored", "ref=%s as_of=%s 张数=%d 两次读法逐行一致" % (
                chk.ref_date, as_of, len(chk.bills))
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


def _notice_direct(text: str) -> None:
    try:
        notify.send_notice(text)
    except Exception as exc:
        print("提醒没发出去:", exc, file=sys.stderr)


def alert(args) -> int:
    """运行脚本用的首报入口：同一件事（key）只私聊一次；恢复后 --clear-prefix 撤掉，再出事算新事件。"""
    store = Store()
    if args.clear_prefix:
        n = store.clear_alerts_with_prefix(args.clear_prefix)
        print("ALERT_CLEARED %d" % n)
        return 0
    if not args.key:
        print("ALERT_BAD_ARGS 需要 --key 或 --clear-prefix", file=sys.stderr)
        return 1
    print("ALERT_" + _notice_once(store, args.key, args.text).upper())
    return 0


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
                facts = read_card(local, cand.layout, message_date=cand.message_date)
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
    """退出码：0 已发送；4 持锁检查发现今天已发过群；3 数据过旧未发群（已首报）；2 发送失败（已告警）。"""
    try:
        # 先过发送目标这道闸，再干别的。
        # 否则 --dry-run --to-group 在未授权时也会「通过」，给出假信心——
        # dry-run 的全部价值就是忠实预演真实路径，不校验闸门的预演是骗人的。
        notify.resolve_target(to_group=args.to_group)
        store = Store()      # 放进异常边界：数据文件读不出来也必须私聊，不能静默退出

        # 一个北京日只进群一次。检查与记录都在持锁的这个进程里完成：
        # 两个触发前后脚跟进来时，后一个一定看得见前一个留下的记录。
        sent_key = "group_sent:%s" % _beijing_now().date().isoformat()
        if args.to_group and not args.dry_run and store.has_alert(sent_key):
            print("今天已经发过群（%s），不重复发" % sent_key)
            return 4

        rows, stale = _series_and_staleness(store)
        stale_key = "stale_balance:%s" % rows[-1].report_date
        if stale >= STALE_ALERT_DAYS:
            warn = ("上游归档已 %d 天没有新表（最新 %s）。\n"
                    "多半是上游归档没在跑，或者财务这几天没发表。"
                    % (stale, rows[-1].report_date))
            if args.to_group and not args.dry_run:
                # 不把陈旧数据推给管理层，改成私聊。同一份陈旧数据只报一次。
                _notice_once(store, stale_key, "资金日报未发群：" + warn)
                print("数据过旧，未发群（首报私聊）", file=sys.stderr)
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
        print("已发送（图 + 文字）:", "付款请示群" if args.to_group else "张霖泽（单聊）")
        if args.to_group:
            try:
                store.mark_alert(sent_key, "已发群", _now())
            except Exception as exc:
                # 群已经发出去了，只是记录没写上——必须让人知道后面的触发可能重发
                print("已发群，但当日发送记录写入失败:", exc, file=sys.stderr)
                _notice_direct("资金日报已发群，但当日发送记录没写进 SMB（%s）。"
                               "今天后面的触发可能会重发，请留意。" % exc)
        store.clear_alert(stale_key)
        store.clear_alerts_with_prefix("send_failed:")
        # 色块不画的两种情况要让人知道，但只说一次（按用到的那张表做指纹）；恢复后撤掉。
        if due_status == "stale":
            _notice_once(store, "bills_stale:%s" % due_list["media"],
                         "每日资金：「现存票据」最近一张合格的是 %s 发的，已超过 %d 天，"
                         "卡片上的「14 天内到期承兑」先不显示。多半是周一的表没发、没归档，"
                         "或者读图没过校验。" % (due_list["posted_at"][:10], bills.MAX_LIST_AGE_DAYS))
        elif due_status == "none":
            _notice_once(store, "bills_none", "每日资金：库里还没有任何一张合格的「现存票据」，"
                                              "卡片上的「14 天内到期承兑」不显示。")
        else:
            store.clear_alerts_with_prefix("bills_stale:")
            store.clear_alert("bills_none")
        # 授权只能人工 OAuth 续期，自动化补不了。提前喊一声，同一个到期时刻只喊一次。
        notice = notify.auth_expiry_notice()
        if notice:
            _notice_once(store, notice[0], notice[1])
            print("提醒:", notice[1].replace("\n", " "), file=sys.stderr)
        return 0
    except Exception as exc:
        detail = "%s: %s" % (type(exc).__name__, exc)
        print("发送失败:", detail, file=sys.stderr)
        traceback.print_exc()
        if not args.dry_run:
            text = "资金日报未能发出：\n%s" % detail
            try:
                _notice_once(Store(), "send_failed:%s" % type(exc).__name__, text)
            except Exception:
                _notice_direct(text)      # 数据文件本身就是失败原因时没法去重，照发
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
    """那天是否真跑到了结局：有发送标记，或运行日志里有那天的 RUN_RESULT 收据。

    「北京时间太早、等更晚那次」「dry run」都会写带日期的日志行，但不写收据——
    后面那次要是没来，就等于没跑，必须报出来。
    """
    if os.path.exists(os.path.join(str(state), ".sent-%s" % day.isoformat())):
        return True
    text = "\n" + _smb_text(os.path.join(str(state), "daily_funds_run.log"))
    return re.search(r"\n\[%s [^\]]*\] RUN_RESULT " % re.escape(day.isoformat()), text) is not None


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
    s.add_argument("--attempts", type=int, default=4, help="最多读几次；两次逐行一致才入库")
    s.add_argument("--budget", type=int, default=600, help="本轮总秒数上限（含翻消息、取图、读图）")
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

    s = sub.add_parser("alert")
    s.add_argument("--key", default="")
    s.add_argument("--text", default="")
    s.add_argument("--clear-prefix", dest="clear_prefix", default="")
    s.set_defaults(func=alert)

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
    except StoreBusy as exc:
        print("数据文件被占用:", exc, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
