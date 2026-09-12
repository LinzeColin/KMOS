#!/usr/bin/env python3
"""付款异常哨兵主流程。

用 Python 写而不是 bash：考勤那条线 2026-09-07 就是死在 macOS 自带 bash 3.2
的 `set -u` 下展开空数组（`ARGS[@]: unbound variable`），而且只在走到那条
分支时才炸 —— 定时任务里这种错要等到出事那天才发现。

固定标记（automation 只认这些，不解释中文措辞）：
  ALERT_SENT / ALERT_NONE / ALERT_NO_EVENT / ALERT_HELD / ALERT_ALREADY_DONE
  ALERT_OUT_OF_WINDOW / EVENT_SCAN_FAILED
  ALERT_LOCKED / ALERT_LOCK_INDETERMINATE / SMB_UNAVAILABLE
  CHECKS_FAILED / SEND_FAILED / SEND_UNVERIFIED
"""
import datetime as dt, json, os, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

EVENT_WINDOW_DAYS = 7       # 回看窗口。4 天够看「周五提、周一才付」，但不够看出习惯：
                            # 「请示正文不写金额」这类要攒够样本才算数（≥3 笔才报），
                            # 4 天窗口下它几乎永远看不见。7 天既够看习惯，也不至于翻旧账。

STATE = os.environ.get("PAYMENT_ALERT_STATE_DIR",
                       os.path.expanduser("~/.local/share/kmfa-payment-alert/state"))
SMB_ROOT = "/Volumes/share"
LOCK = os.path.join(STATE, "payment_alert.lock")
BJ = dt.timezone(dt.timedelta(hours=8))


def out(token, msg=""):
    print(f"{token} {msg}".rstrip())
    return token


# ------------------------------------------------------------------ 进程锁
def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True            # 存在但不属于我们
    except Exception:
        return None            # 查不清


def acquire_lock():
    """三态：活着→占用；确证已死→接管；查不清→不确定，**绝不删锁**。"""
    os.makedirs(STATE, exist_ok=True)
    if os.path.exists(LOCK):
        try:
            raw = open(LOCK, encoding="utf-8").read().strip()
            pid = int(raw.split()[0])
        except Exception:
            return "indeterminate", f"锁文件读不出 pid：{LOCK}"
        alive = _pid_alive(pid)
        if alive is True:
            return "locked", f"pid {pid} 仍在跑"
        if alive is None:
            return "indeterminate", f"pid {pid} 状态查不清"
        os.unlink(LOCK)        # 确证已死才接管
    with open(LOCK, "w", encoding="utf-8") as f:
        f.write(f"{os.getpid()} {dt.datetime.now().isoformat(timespec='seconds')}\n")
    return "acquired", ""


def release_lock():
    try:
        if os.path.exists(LOCK):
            with open(LOCK, encoding="utf-8") as f:
                if int(f.read().split()[0]) == os.getpid():
                    os.unlink(LOCK)
    except Exception:
        pass


# ------------------------------------------------------------------ 主流程
def main():
    import payment_send as S
    from payment_ledger import Ledger

    dry = os.environ.get("PAYMENT_ALERT_DRY_RUN") == "1"
    now_bj = S.bj_now()
    today_cn = now_bj.date().isoformat()
    stamp = os.path.join(STATE, f".done-{today_cn}")

    if not os.path.isdir(SMB_ROOT):
        return out("SMB_UNAVAILABLE", SMB_ROOT), 1

    os.makedirs(STATE, exist_ok=True)
    if os.path.exists(stamp) and not dry:
        return out("ALERT_ALREADY_DONE", today_cn), 0

    st, why = acquire_lock()
    if st == "locked":
        return out("ALERT_LOCKED", why), 75
    if st == "indeterminate":
        S.alert_owner(f"付款异常哨兵：锁状态查不清（{why}）。不要删锁文件 {LOCK}，请人工确认。")
        return out("ALERT_LOCK_INDETERMINATE", why), 76

    try:
        # ---- 时窗：不在窗口内直接让路，不跑检查也不留标记 ----
        if not S.in_send_window(now_bj) and not dry:
            return out("ALERT_OUT_OF_WINDOW",
                       f"北京 {now_bj:%H:%M}，发布窗口 08:00–12:00"), 0

        # ---- 回应闭环：先把群里的答复吃进台账，再决定发什么 ----
        L = Ledger(os.environ.get("PAYMENT_LEDGER_DB"))
        try:
            import payment_feedback as FB
            fb = FB.scan(L)
            print(f"FEEDBACK_SCAN msgs={fb['msgs']} imgs={fb['imgs']} "
                  f"ocr_new={fb['ocr_new']} matched={fb['matched']} "
                  f"unmatched_notes={fb['unmatched']}")
        except Exception as exc:                     # 降级，绝不拖垮主流程
            print(f"FEEDBACK_DEGRADED {type(exc).__name__}: {exc}")

        # ---- 审批数据刷新：把最新的红圈付款审批导出灌成新快照，让付款核对
        # （dup/amount/status）看得到近几天的付款，而不是拿两周前的旧快照瞎比。
        # 入库失败绝不静默降级：私聊告警老板，让人知道核对可能在用旧数据。
        try:
            import payment_ingest as ING
            ir = ING.ingest_approval()
            print(f"APPROVAL_INGEST {ir.get('status')} rows={ir.get('rows','-')} "
                  f"md5={str(ir.get('md5', ''))[:8]}")
            if ir.get("status") not in ("ingested", "already"):
                S.alert_owner("付款异常哨兵：审批数据本轮没刷新成"
                              f"（{ir.get('status')}：{ir.get('missing') or ir.get('path')}）。"
                              "付款核对可能在拿旧快照，请人工看一眼。")
        except Exception as exc:
            print(f"APPROVAL_INGEST_CRASH {type(exc).__name__}: {exc}")
            S.alert_owner("付款异常哨兵：审批入库崩了，付款核对可能在拿旧快照。\n"
                          f"{type(exc).__name__}: {exc}")

        # ---- 周一欠款通知：独立于付款事件，每周一单发一次（老板 2026-09-11）----
        # 欠款=应收账款，跟付款异常不是一回事，绝不进事件日报文；只有周一提醒一次。
        # 自带 .recv-<日期> 幂等，走 render_receivables + 各自的合法前缀。
        if now_bj.weekday() == 0:
            recv_stamp = os.path.join(STATE, f".recv-{today_cn}")
            if dry or not os.path.exists(recv_stamp):
                try:
                    from payment_checks import receivable_major
                    rst, ritems, rnote = receivable_major()
                    if rst == "hit" and ritems:
                        rtok, rdetail = S.send(
                            S.render_receivables(ritems, rnote, now_bj.date()),
                            dry_run=dry, now=now_bj)
                        print(f"RECEIVABLE_WEEKLY {rtok} n={len(ritems)}")
                        if rtok in ("SENT", "DRY_RUN"):
                            if not dry:
                                open(recv_stamp, "w").close()
                        elif rtok not in ("OUT_OF_WINDOW", "HELD"):
                            S.alert_owner(f"周一欠款通知没发出去：{rtok} {rdetail[:200]}")
                    else:
                        print(f"RECEIVABLE_WEEKLY skip status={rst} n={len(ritems)}")
                except Exception as exc:
                    print(f"RECEIVABLE_WEEKLY_CRASH {type(exc).__name__}: {exc}")
                    S.alert_owner(f"周一欠款通知崩了：{type(exc).__name__}: {exc}")

        # ---- 事件闸门：没有付款事件，一个字都不发 ----
        #
        # 老板 2026-09-11：「他不是每天都有付款，有付款才发送消息，你才需要去核对……
        # 而不是他没有付款的时候你也发。」
        # 实测 08-25~09-10 这 16 天，生产付款群只有 9 天有回执，旧机制那 7 个空天
        # 照发不误，发的还是老板已经听过无数遍的存量欠款。
        #
        # 读群失败必须炸出来告警，绝不能当成「今天没事件」而静默——那是装死。
        import payment_event as EV
        try:
            ev = EV.scan(days=EVENT_WINDOW_DAYS, now=now_bj)
        except Exception as exc:
            S.alert_owner(f"付款异常哨兵：读不到群消息，今天无法判断有没有付款事件，本轮不发。\n"
                          f"{type(exc).__name__}: {exc}")
            return out("EVENT_SCAN_FAILED", f"{type(exc).__name__}: {exc}"[:200]), 2

        if not ev["has_event"]:
            open(stamp, "w").close()
            return out("ALERT_NO_EVENT",
                       f"窗口 {ev['window'][0]} 起：请示群没有申请、生产付款群没有回执，按设计不发"), 0

        event_items = EV.findings(ev, now=now_bj)
        try:
            # 申请单里的金额和收款方要 OCR 才拿得到。补不上就原样报，
            # 绝不因为读不出图就把一条真异常吞掉。
            EV.enrich(event_items, ev)
        except Exception as exc:
            print(f"EVENT_ENRICH_DEGRADED {type(exc).__name__}: {exc}")
        print(f"EVENT_SCAN 申请={len(ev['申请'])} 催办={len(ev['催办'])} "
              f"批示={len(ev['批示'])} 回执={len(ev['回执'])} 异常={len(event_items)}")

        # ---- 六项检查 ----
        from payment_checks import run_all, CHECKS
        results = run_all(today=now_bj.date())
        healthy = [c for c in results.values() if c["status"] in ("hit", "clear")]
        if not healthy:
            detail = "；".join(f"{k}:{v['note'] or v['status']}" for k, v in results.items())
            S.alert_owner(f"付款异常哨兵今天没跑成：六项检查全部不可用。\n{detail[:500]}")
            return out("CHECKS_FAILED", detail[:200]), 2

        all_items = event_items + [
            it for cid in S.ORDER for it in results.get(cid, {}).get("items", [])
            if cid not in S.DAILY_EXCLUDED]
        new_items = L.unreported(all_items)

        if not new_items:
            open(stamp, "w").close()
            return out("ALERT_NONE",
                       f"有付款事件，但 {len(all_items)} 条命中全部已上报或已结清，按设计不发"), 0

        sources = _source_dates()
        text = S.render(new_items, results, L.counts(), sources, today=now_bj.date())

        tok, detail = S.send(text, dry_run=dry, now=now_bj)
        if tok == "DRY_RUN":
            print("---- 干跑，以下内容不会发出 ----")
            print(text)
            return out("ALERT_DRY_RUN", f"chars={len(text)} new={len(new_items)}"), 0
        if tok == "HELD":
            return out("ALERT_HELD", detail), 0
        if tok == "OUT_OF_WINDOW":
            return out("ALERT_OUT_OF_WINDOW", detail), 0
        if tok == "SEND_FAILED":
            S.alert_owner(f"付款异常哨兵：消息没发出去。\n{detail}")
            return out("SEND_FAILED", detail), 3
        if tok == "SEND_UNVERIFIED":
            S.alert_owner(f"付款异常哨兵：发送命令成功但回读不到，无法确认是否落地。台账未写，明天会重发。\n{detail}")
            return out("SEND_UNVERIFIED", detail), 3

        # 回读确认到了，才写台账、才盖当日戳
        L.record_reported(new_items)
        L.set_meta("last_report_scan", dt.datetime.now(BJ).isoformat(timespec="seconds"))
        open(stamp, "w").close()
        return out("ALERT_SENT", f"new={len(new_items)} chars={len(text)}"), 0

    except Exception:
        tb = traceback.format_exc()
        try:
            S.alert_owner(f"付款异常哨兵异常中止：\n{tb[-600:]}")
        except Exception:
            pass
        print(tb, file=sys.stderr)
        return out("CHECKS_FAILED", "未捕获异常，详见 stderr"), 2
    finally:
        release_lock()


def _source_dates(root=None):
    """各上游最后一次更新到哪天 —— 页脚要写清楚，别让人以为看的是全量。"""
    import sqlite3
    from payment_checks import P2, P3, latest_hongquan, name_date
    src = {}
    try:
        c = sqlite3.connect(f"file:{P2}?mode=ro", uri=True)
        r = c.execute("SELECT MAX(application_date) FROM approval WHERE source_md5="
                      "(SELECT source_md5 FROM approval GROUP BY source_md5 "
                      " ORDER BY MAX(ingested_at) DESC LIMIT 1)").fetchone()
        src["红圈付款审批"] = (r[0] or "")[:10]
        # 文件名形如「项目资金计划2026.7.9.xlsx」：点分隔、月日不补零，
        # 所以既不能用 (\d{4})(\d{2})(\d{2}) 去抓，也不能按字典序取最大
        # （字典序会把 7.9 排在 7.24 后面）。必须解成真日期再比。
        import re as _re, datetime as _dt
        best = None
        for (fn,) in c.execute("SELECT DISTINCT source_file FROM plan"):
            m = _re.search(r"(\d{4})[.\-年](\d{1,2})[.\-月](\d{1,2})", fn or "")
            if not m:
                continue
            try:
                d = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
            if best is None or d > best:
                best = d
        src["周付款计划"] = best.isoformat() if best else ""
    except Exception:
        pass
    try:
        c = sqlite3.connect(f"file:{P3}?mode=ro", uri=True)
        r = c.execute("SELECT MAX(transaction_time) FROM transfer").fetchone()
        src["下游转账凭证"] = (r[0] or "")[:10]
    except Exception:
        pass
    try:
        f = latest_hongquan("收款登记", "全历史导出", root=root)
        d = name_date(os.path.basename(f)) if f else None
        src["红圈收款登记"] = d.isoformat() if d else ""
    except Exception:
        pass
    return src


if __name__ == "__main__":
    token, rc = main()
    raise SystemExit(rc)
