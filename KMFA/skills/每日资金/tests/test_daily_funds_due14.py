"""「14 天内到期承兑」回归测试。

票据是合成数据：KMOS 是公开仓，不放真实金额。结构照真表构造——同一基准日 2026-09-07 的
DAYS360 天数、同日多张到期、跨月跨年、一张 DAYS360 与自然日相差一天。真实表的回放验证不进公开仓。
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# 测试用自己的锁文件，不跟正在跑的生产/验证进程抢那把全局锁
os.environ.setdefault("DAILY_FUNDS_LOCK", os.path.join(tempfile.gettempdir(), "kmfa-daily-funds-test-%d.lock" % os.getpid()))

from daily_funds_local import bills, card  # noqa: E402
from daily_funds_local.store import Store  # noqa: E402

D = dt.date.fromisoformat

# (汇票到期日, 表上「距离到期日」（DAYS360，基准 2026-09-07）, 票据金额)
B0907 = [("2026-09-16", 9, "1000.00"), ("2026-09-20", 13, "2000.00"), ("2026-09-23", 16, "4000.00"),
         ("2026-09-24", 17, "8000.00"), ("2026-09-24", 17, "16000.00"), ("2026-10-15", 38, "32000.00"),
         ("2026-12-16", 99, "64000.00"), ("2027-01-14", 127, "128000.00"), ("2027-02-26", 169, "256000.00")]
TOTAL_0907 = 51100000


def fen(y):
    return int(Decimal(y) * 100)


def rows_0907():
    return [{"seq": i + 1, "due": D(d), "days": n, "amount_fen": fen(a)} for i, (d, n, a) in enumerate(B0907)]


def list_0907():
    return {"media": "lQLPfakeMediaA_x-1", "posted_at": "2026-09-07 11:35:50",
            "ref_date": "2026-09-07", "as_of": "2026-09-07", "total_fen": TOTAL_0907,
            "bills": [(d, fen(a)) for d, _, a in B0907]}


class TestListGates(unittest.TestCase):
    def test_real_table_passes_with_reference_day(self):
        chk = bills.check_rows(rows_0907(), TOTAL_0907, D("2026-09-07"))
        self.assertTrue(chk.ok, chk.reasons)
        self.assertEqual(chk.ref_date, "2026-09-07")

    def test_days_column_is_days360_not_calendar_days(self):
        self.assertEqual(bills.days360(D("2026-09-07"), D("2026-12-16")), 99)
        self.assertEqual((D("2026-12-16") - D("2026-09-07")).days, 100)
        self.assertEqual(bills.days360(D("2026-08-31"), D("2026-12-16")), 106)

    def test_one_misread_amount_fails_sum(self):
        rows = rows_0907()
        rows[3]["amount_fen"] -= 100000
        self.assertIn("SUM", ";".join(bills.check_rows(rows, TOTAL_0907, D("2026-09-07")).reasons))

    def test_one_misread_due_date_fails_days360(self):
        rows = rows_0907()
        rows[3]["due"] = D("2026-09-25")          # 表上印 9-24
        chk = bills.check_rows(rows, TOTAL_0907, D("2026-09-07"))
        self.assertFalse(chk.ok)
        self.assertIn("DAYS360_NO_COMMON_REF", chk.reasons)

    def test_dropped_row_fails_seq(self):
        rows = rows_0907()
        del rows[5]
        self.assertTrue(any(r.startswith("SEQ") for r in bills.check_rows(rows, TOTAL_0907, D("2026-09-07")).reasons))

    def test_missing_days_fails(self):
        rows = rows_0907()
        rows[0]["days"] = None
        self.assertIn("DAYS_MISSING", bills.check_rows(rows, TOTAL_0907, D("2026-09-07")).reasons)

    def test_parse_read_handles_yen_commas_and_bad_rows(self):
        rows, total, errors = bills.parse_read({"rows": [
            {"seq": 1, "due": "2026-9-24", "days": "17", "amount": "¥ 1,000.00"},
            {"seq": 2, "due": "看不清", "days": 17, "amount": "1.00"}], "total": "1,000.00"})
        self.assertEqual(rows[0]["due"], D("2026-09-24"))
        self.assertEqual(rows[0]["amount_fen"], 100000)
        self.assertEqual(total, 100000)
        self.assertEqual(len(errors), 1)
        self.assertFalse(bills.check_rows(rows, total, D("2026-09-07"), errors).ok)


class TestCrossSource(unittest.TestCase):
    """模型爱把各行加起来冒充合计，逐张求和就永远自洽——只有另一张独立的表抓得住。"""

    def test_window(self):
        self.assertEqual(bills.cross_window("2026-09-07"), ("2026-09-03", "2026-09-07"))

    def test_matches_latest_equal_day(self):
        bal = [("2026-09-03", 52000000), ("2026-09-04", TOTAL_0907), ("2026-09-05", TOTAL_0907),
               ("2026-09-06", TOTAL_0907), ("2026-09-07", TOTAL_0907)]
        self.assertEqual(bills.cross_match(TOTAL_0907, bal), "2026-09-07")

    def test_self_consistent_misread_is_rejected(self):
        # 形状取自实测：图上印的合计与资金表一致，模型输出的是自己加出来的数，错一个数字
        self.assertIsNone(bills.cross_match(51091000, [("2026-09-06", TOTAL_0907)]))

    def test_sub_yuan_residual_is_tolerated(self):
        self.assertEqual(bills.cross_match(TOTAL_0907 + 20, [("2026-09-06", TOTAL_0907)]), "2026-09-06")


class TestRollingWindow(unittest.TestCase):
    def test_moves_with_report_date(self):
        b = list_0907()["bills"]
        self.assertEqual(bills.due_within(b, "2026-09-07"), 300000)     # 9-16、9-20
        self.assertEqual(bills.due_within(b, "2026-09-09"), 700000)     # + 9-23（正好 14 天）
        self.assertEqual(bills.due_within(b, "2026-09-10"), 3100000)    # + 两张 9-24
        self.assertEqual(bills.due_within(b, "2026-09-17"), 3000000)    # 9-16 那张到期剔除

    def test_boundaries(self):
        b = [("2026-09-24", 100)]
        self.assertEqual(bills.due_within(b, "2026-09-10"), 100)   # 正好 14 天
        self.assertEqual(bills.due_within(b, "2026-09-09"), 0)     # 15 天
        self.assertEqual(bills.due_within(b, "2026-09-24"), 100)   # 当天到期
        self.assertEqual(bills.due_within(b, "2026-09-25"), 0)     # 已到期


class TestCardFields(unittest.TestCase):
    def test_fresh(self):
        f, status, _ = bills.card_fields([list_0907()], "2026-09-09", TOTAL_0907)
        self.assertEqual(status, "ok")
        self.assertEqual(f, {"bill_due14": 700000, "bill_due14_src": "2026-09-07"})

    def test_ten_days_still_shown_eleventh_hidden(self):
        self.assertEqual(bills.card_fields([list_0907()], "2026-09-17", 10 ** 10)[1], "ok")
        f, status, used = bills.card_fields([list_0907()], "2026-09-18", 10 ** 10)
        self.assertEqual((f, status), ({}, "stale"))
        self.assertEqual(used["media"], list_0907()["media"])

    def test_never_uses_a_table_from_the_future(self):
        self.assertEqual(bills.card_fields([list_0907()], "2026-09-05", 10 ** 10)[1], "none")

    def test_newest_eligible_table_wins(self):
        old = dict(list_0907(), media="old", posted_at="2026-08-31 14:07:18", as_of="2026-08-29",
                   bills=[("2026-09-10", 100)])
        f, _, used = bills.card_fields([old, list_0907()], "2026-09-09", 10 ** 10)
        self.assertEqual(used["media"], list_0907()["media"])

    def test_more_due_than_bills_on_hand_is_not_drawn(self):
        self.assertEqual(bills.card_fields([list_0907()], "2026-09-10", 100)[1], "inconsistent")


class TestFindMessages(unittest.TestCase):
    def test_labels_media_and_paging(self):
        pages = [
            {"result": {"messages": [
                {"openMessageId": "a", "createTime": "2026-09-07 11:35:50", "sender": "杨婷",
                 "content": "[图片消息](mediaId=@lQLPfakeMediaA_x-1)现存票据"},
                {"openMessageId": "b", "createTime": "2026-09-07 11:35:35",
                 "content": "[图片消息](mediaId=$iwEfakeOther) 注意"}]}},
            {"result": {"messages": [
                {"openMessageId": "c", "createTime": "2026-08-31 14:07:18", "sender": "杨婷",
                 "content": "[图片消息](mediaId=@lQLPfakeMediaB_y-2)现存票据"},
                {"openMessageId": "d", "createTime": "2026-08-20 09:00:00", "content": "票据到期，款已到账。"}]}},
        ]
        calls = []

        def run(args):
            calls.append(args)
            return pages[min(len(calls) - 1, len(pages) - 1)]

        got = bills.find_list_messages(run, "gid", "2026-08-25 00:00:00", "2026-09-11 12:00:00")
        self.assertEqual([g["posted_at"] for g in got], ["2026-08-31 14:07:18", "2026-09-07 11:35:50"])
        self.assertEqual(got[1]["media"], "lQLPfakeMediaA_x-1")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][calls[1].index("--time") + 1], "2026-09-07 11:35:35")


class TestStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "d.jsonl")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_unknown_tables_survive_a_rewrite(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"_t": "future_table", "x": 1}) + "\n")
        s = Store(self.path)
        s.mark_alert("k", "t", "2026-09-11T10:00:00")
        text = open(self.path, encoding="utf-8").read()
        self.assertIn('"future_table"', text)
        self.assertIn('"alert_sent"', text)

    def test_bill_list_round_trip_and_balance_window(self):
        s = Store(self.path)
        s.upsert(report_date="2026-09-06", bank_fen=1, bill_fen=TOTAL_0907, total_fen=TOTAL_0907 + 1,
                 layout="C", source_imbalance=False, extracted_at="x")
        L = list_0907()
        s.upsert_bill_list(media=L["media"], posted_at=L["posted_at"], ref_date=L["ref_date"], as_of="2026-09-06",
                           total_fen=TOTAL_0907, bills=[list(b) for b in L["bills"]], extracted_at="x")
        again = Store(self.path)
        self.assertTrue(again.has_bill_list(L["media"]))
        self.assertEqual(again.bill_lists()[0]["bills"][0], ("2026-09-16", 100000))
        self.assertEqual(again.balances_between("2026-09-03", "2026-09-07"), [("2026-09-06", TOTAL_0907)])
        self.assertFalse(again.has_alert("k"))


class Row:
    def __init__(self, d, bank, bill):
        self.report_date, self.bank_fen, self.bill_fen = d, bank, bill
        self.total_fen, self.source_imbalance, self.chain_suspect = bank + bill, False, False


class TestSummaryText(unittest.TestCase):
    rows = [Row("2026-09-08", 100000000, 52000000), Row("2026-09-09", 100000000, TOTAL_0907)]

    def test_order_matches_the_bar(self):
        lines = card.summary_text(self.rows, 0, 700000).split("\n")
        idx = [next(i for i, l in enumerate(lines) if l.strip().startswith(k))
               for k in ("银行存款", "14 天内到期承兑", "电子汇票")]
        self.assertEqual(idx, sorted(idx))
        self.assertIn("14 天内到期承兑 0.70 万（占汇票 1.4%）", "\n".join(lines))

    def test_without_data_no_line(self):
        self.assertNotIn("到期承兑", card.summary_text(self.rows, 0))

    def test_zero_is_stated_not_hidden(self):
        self.assertIn("14 天内到期承兑 0.00 万", card.summary_text(self.rows, 0, 0))


def _playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_playwright(), "没装 playwright")
class TestTemplateDom(unittest.TestCase):
    def _dom(self, extra):
        from playwright.sync_api import sync_playwright
        payload = {"series": [{"d": "2026-09-08", "b": 100000000, "e": 52000000, "imbalance": False},
                              {"d": "2026-09-09", "b": 100000000, "e": TOTAL_0907, "imbalance": False}],
                   "stale_days": 0}
        payload.update(extra)
        html = card.TEMPLATE.read_text(encoding="utf-8").replace("__PAYLOAD__", json.dumps(payload))
        tmp = Path(tempfile.mkdtemp()) / "c.html"
        tmp.write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page()
            page.goto(tmp.as_uri())
            page.wait_for_selector(".cell svg")
            out = page.evaluate("""() => ({
              segs: document.querySelectorAll('#splitbar i').length,
              dueShown: !document.getElementById('dueitem').hidden,
              legend: [...document.querySelectorAll('.legend > div')].filter(e => !e.hidden)
                        .map(e => e.querySelector('.k').textContent.trim()),
              note: document.querySelector('.note').innerText })""")
            b.close()
        return out

    def test_no_data_looks_exactly_like_before(self):
        o = self._dom({})
        self.assertEqual((o["segs"], o["dueShown"]), (2, False))
        self.assertEqual(o["legend"], ["银行存款", "电子汇票"])
        self.assertNotIn("到期承兑", o["note"])

    def test_with_data_three_segments_in_bar_order(self):
        o = self._dom({"bill_due14": 700000, "bill_due14_src": "2026-09-07"})
        self.assertEqual(o["segs"], 3)
        self.assertEqual(o["legend"], ["银行存款", "14 天内到期承兑", "电子汇票"])
        self.assertIn("现存票据（09-07）", o["note"])

    def test_zero_keeps_legend_without_segment(self):
        o = self._dom({"bill_due14": 0, "bill_due14_src": "2026-09-07"})
        self.assertEqual((o["segs"], o["dueShown"]), (2, True))


class TestRunScriptBranches(unittest.TestCase):
    """跑真脚本的控制流，只把归档、poll、send、bills、告警换成桩。

    2026-09-10 的「poll 崩溃仍发旧数据」修复，第二天就被一次 pull 冲回了旧版且无人察觉。
    所以这些分支必须由测试钉住，而不是靠记得。"""

    def _run(self, poll_rc=0, send_rc=0, bills_rc=0, marker_ok=True):
        src = (ROOT / "scripts" / "daily_funds_run.sh").read_text(encoding="utf-8")
        subs = [
            ('python3 scripts/run_local_daily_funds.py poll >> "${RUN_OUTPUT}" 2>&1 || POLL_RC=$?',
             'bash -c "exit ${STUB_POLL_RC}" || POLL_RC=$?'),
            ('python3 scripts/run_local_daily_funds.py send --to-group >> "${SEND_OUTPUT}" 2>&1 || SEND_RC=$?',
             'bash -c "exit ${STUB_SEND_RC}" || SEND_RC=$?'),
            ('python3 scripts/run_local_daily_funds.py bills >> "${BILLS_OUTPUT}" 2>&1 || BILLS_RC=$?',
             'touch "${STUB_BILLS_RAN}"; bash -c "exit ${STUB_BILLS_RC}" || BILLS_RC=$?'),
            ('alert_once() {\n', 'alert_once() {\n  echo "ALERT $*" >> "${STUB_ALERTS}"; return 0\n'),
            ('alert_clear_prefix() {\n', 'alert_clear_prefix() {\n  return 0\n'),
            ('archive_scan "KMFile', 'true archive_scan "KMFile'),
            ('archive_scan "KMMedia', 'true archive_scan "KMMedia'),
            ('case "${DECIDE}" in', 'DECIDE="GO now"\ncase "${DECIDE}" in'),
        ]
        if not marker_ok:
            subs.append(('if ! publish_smb_file "${MARKER}" "${STAMP}"; then', 'if ! false; then'))
        for old, new in subs:
            self.assertEqual(src.count(old), 1, "脚本结构变了，桩对不上：%s" % old[:50])
            src = src.replace(old, new)
        work = Path(tempfile.mkdtemp())
        (work / "scripts").mkdir()
        script = work / "scripts" / "daily_funds_run.sh"
        script.write_text(src, encoding="utf-8")
        state = work / "state"
        state.mkdir()
        alerts = work / "alerts.txt"
        alerts.write_text("")
        ran = work / "bills_ran"
        env = dict(os.environ, STUB_POLL_RC=str(poll_rc), STUB_SEND_RC=str(send_rc), STUB_BILLS_RC=str(bills_rc),
                   STUB_ALERTS=str(alerts), STUB_BILLS_RAN=str(ran),
                   DAILY_FUNDS_SMB_DIR=str(state), DAILY_FUNDS_TMP_DIR=str(work))
        rc = subprocess.run(["/bin/bash", str(script)], env=env, capture_output=True, text=True).returncode
        sent = any(state.glob(".sent-*"))
        n = len([l for l in alerts.read_text().splitlines() if l])
        log = (state / "daily_funds_run.log").read_text(encoding="utf-8") if (state / "daily_funds_run.log").exists() else ""
        out = (rc, sent, n, ran.exists(), log)
        shutil.rmtree(work, ignore_errors=True)
        return out

    def test_normal(self):
        rc, sent, n, bills_ran, log = self._run()
        self.assertEqual((rc, sent, n, bills_ran), (0, True, 0, True))
        self.assertIn("RUN_RESULT SENT", log)

    def test_poll_read_nothing_sends_and_alerts(self):
        self.assertEqual(self._run(poll_rc=2)[:4], (0, True, 1, True))

    def test_poll_crash_refuses_to_send(self):
        rc, sent, n, bills_ran, log = self._run(poll_rc=1)
        self.assertEqual((rc, sent, n, bills_ran), (2, False, 1, False))
        self.assertIn("RUN_RESULT REFUSED_POLL_CRASH", log)

    def test_bills_unreadable_is_quiet(self):
        self.assertEqual(self._run(bills_rc=2)[:4], (0, True, 0, True))

    def test_bills_crash_after_card_is_sent_alerts(self):
        self.assertEqual(self._run(bills_rc=1)[:4], (0, True, 1, True))

    def test_other_trigger_already_sent(self):
        rc, sent, n, bills_ran, log = self._run(send_rc=4)
        self.assertEqual((rc, sent, n, bills_ran), (0, False, 0, False))
        self.assertIn("RUN_RESULT ALREADY_SENT", log)

    def test_send_failure_already_alerted_by_python(self):
        rc, sent, n, bills_ran, log = self._run(send_rc=2)
        self.assertEqual((rc, sent, n, bills_ran), (2, False, 0, False))
        self.assertIn("RUN_RESULT NOT_SENT", log)

    def test_send_crash_is_reported_here(self):
        rc, sent, n, bills_ran, log = self._run(send_rc=1)
        self.assertEqual((rc, sent, n, bills_ran), (2, False, 1, False))
        self.assertIn("RUN_RESULT SEND_CRASHED", log)

    def test_marker_failure_after_sending_alerts(self):
        rc, sent, n, bills_ran, log = self._run(marker_ok=False)
        self.assertEqual((rc, sent, n, bills_ran), (2, False, 1, False))
        self.assertIn("RUN_RESULT SENT_MARKER_FAILED", log)


class TestWatchdog(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import run_local_daily_funds as r
        self.r = r
        self.dir = Path(tempfile.mkdtemp())
        self.sent = []
        self._orig = (r.notify.send_notice, os.environ.get("DAILY_FUNDS_SMB_DIR"), os.environ.get("DAILY_FUNDS_DATA"))
        r.notify.send_notice = self.sent.append
        os.environ["DAILY_FUNDS_SMB_DIR"] = str(self.dir)
        os.environ["DAILY_FUNDS_DATA"] = str(self.dir / "d.jsonl")

    def tearDown(self):
        self.r.notify.send_notice = self._orig[0]
        for k, v in (("DAILY_FUNDS_SMB_DIR", self._orig[1]), ("DAILY_FUNDS_DATA", self._orig[2])):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.dir, ignore_errors=True)

    def _toml(self, status, script=None):
        p = self.dir / "automation.toml"
        p.write_text('prompt = "执行 %s"\nstatus = "%s"\nupdated_at = 42\n'
                     % (script or self.r.RUNTIME_SCRIPT, status), encoding="utf-8")
        return str(p)

    def _args(self, toml):
        return type("A", (), {"toml": toml})()

    def test_previous_weekday_skips_weekend(self):
        pw = self.r._previous_weekday
        self.assertEqual(pw(D("2026-09-14")), D("2026-09-11"))   # 周一 → 周五
        self.assertEqual(pw(D("2026-09-15")), D("2026-09-14"))
        self.assertEqual(pw(D("2026-09-13")), D("2026-09-11"))   # 周日 → 周五

    def test_paused_is_reported_once(self):
        prev = self.r._previous_weekday(dt.date.today())
        (self.dir / (".sent-%s" % prev.isoformat())).write_text("")
        toml = self._toml("PAUSED")
        import contextlib
        import io
        outs = []
        for _ in range(2):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.r.watchdog(self._args(toml))
            outs.append(buf.getvalue())
        self.assertEqual(len(self.sent), 1)
        self.assertIn("PAUSED", self.sent[0])
        self.assertIn("WATCHDOG_ALERT", outs[0])
        self.assertIn("WATCHDOG_KNOWN", outs[1])     # 第二天不再让调度侧重报

    def test_missing_run_is_reported_and_log_line_counts_as_run(self):
        toml = self._toml("ACTIVE")
        self.r.watchdog(self._args(toml))
        self.assertEqual(len(self.sent), 1)
        self.assertIn("没有任何运行记录", self.sent[0])
        prev = self.r._previous_weekday(dt.date.today())
        self.sent.clear()
        log = self.dir / "daily_funds_run.log"
        log.write_text("[%s 14:00:01 AEST] 北京 11 点太早，今天还排了悉尼 15 点那次，本轮不发也不写标记\n" % prev.isoformat())
        self.assertFalse(self.r._ran_on(prev, self.dir))       # 只等了一次、后面那次没来 = 没跑
        log.write_text(log.read_text() + "[%s 15:00:02 AEST] RUN_RESULT SENT 已发送\n" % prev.isoformat())
        self.assertTrue(self.r._ran_on(prev, self.dir))

    def test_reverted_script_path_is_reported(self):
        prev = self.r._previous_weekday(dt.date.today())
        (self.dir / (".sent-%s" % prev.isoformat())).write_text("")
        old = "/Users/x/GithubProject/KMOS/KMFA/skills/每日资金/scripts/daily_funds_run.sh"
        self.r.watchdog(self._args(self._toml("ACTIVE", old)))
        self.assertEqual(len(self.sent), 1)
        self.assertIn("运行位", self.sent[0])

    def test_healthy_is_silent(self):
        prev = self.r._previous_weekday(dt.date.today())
        (self.dir / (".sent-%s" % prev.isoformat())).write_text("")
        self.r.watchdog(self._args(self._toml("ACTIVE")))
        self.assertEqual(self.sent, [])


class TestChunkedBillRead(unittest.TestCase):
    """长表分段读：每段带表头、段间重叠、按序号拼回；重叠行读得不一样就整次作废。"""

    def setUp(self):
        from daily_funds_local import vision
        self.v = vision
        self.dir = Path(tempfile.mkdtemp())
        self._orig = (vision._api_key, vision._ask, vision._bill_chunks)
        vision._api_key = lambda: "k"

    def tearDown(self):
        self.v._api_key, self.v._ask, self.v._bill_chunks = self._orig
        shutil.rmtree(self.dir, ignore_errors=True)

    def _img(self, h):
        from PIL import Image
        p = self.dir / ("img_%d.png" % h)
        im = Image.new("RGB", (400, h), "white")
        for y in range(0, 40):
            for x in range(0, 400, 7):
                im.putpixel((x, y), (0, 0, 0))     # 表头有字
        im.save(p)
        return str(p)

    def test_plan_depends_on_height(self):
        self.assertEqual(self.v.bill_read_plan(self._img(1300)), [(1, 1), (2, 1)])
        self.assertIn((2, 2), self.v.bill_read_plan(self._img(2000)))

    def test_chunks_carry_header_and_overlap(self):
        from PIL import Image
        self.v._bill_chunks = self._orig[2]
        paths = self.v._bill_chunks(self._img(2000), 2, scale=1)
        self.assertEqual(len(paths), 2)
        a, b = (Image.open(p) for p in paths)
        self.assertEqual(a.getpixel((0, 0)), (0, 0, 0))        # 两段顶上都是表头
        self.assertEqual(b.getpixel((0, 0)), (0, 0, 0))
        body = 2000 - 40
        self.assertGreater(a.size[1] + b.size[1] - 2 * (40 + 6), body)   # 有重叠，拼回来比原图正文高

    def _run(self, chunk_data):
        self.v._bill_chunks = lambda path, parts, scale=2: ["c%d" % i for i in range(parts)]
        it = iter(chunk_data)
        self.v._ask = lambda prompt, img, key, model, deadline=None: next(it)
        return self.v.read_bill_list("x.png", parts=len(chunk_data))

    def test_overlap_rows_dedupe_and_total_from_last_part(self):
        r1 = {"seq": 1, "due": "2026-09-16", "days": 9, "amount": "1000.00"}
        r2 = {"seq": 2, "due": "2026-09-20", "days": 13, "amount": "2000.00"}
        r3 = {"seq": 3, "due": "2026-09-23", "days": 16, "amount": "4000.00"}
        out = self._run([{"rows": [r1, r2], "total": ""}, {"rows": [r2, r3], "total": "7000.00"}])
        self.assertEqual([r["seq"] for r in out["rows"]], [1, 2, 3])
        self.assertEqual(out["total"], "7000.00")
        rows, total, errors = bills.parse_read(out)
        self.assertTrue(bills.check_rows(rows, total, D("2026-09-07"), errors).ok)

    def test_disagreeing_overlap_is_rejected(self):
        r2a = {"seq": 2, "due": "2026-09-20", "days": 13, "amount": "2000.00"}
        r2b = {"seq": 2, "due": "2026-09-20", "days": 13, "amount": "2600.00"}
        from daily_funds_local.vision import VisionError
        with self.assertRaises(VisionError):
            self._run([{"rows": [r2a], "total": ""}, {"rows": [r2b], "total": "2000.00"}])


class TestReviewFixesBills(unittest.TestCase):
    def test_days360_february_month_end_start(self):
        self.assertEqual(bills.days360(D("2011-02-28"), D("2011-03-31")), 30)
        self.assertEqual(bills.days360(D("2011-01-30"), D("2011-02-28")), 28)
        self.assertEqual(bills.days360(D("2026-02-28"), D("2026-03-30")), 30)
        self.assertEqual(bills.days360(D("2024-02-29"), D("2024-03-31")), 30)   # 闰年
        self.assertEqual(bills.days360(D("2024-02-28"), D("2024-03-30")), 32)   # 闰年的 28 日不是月末

    def test_never_uses_a_table_posted_after_the_report(self):
        future = dict(list_0907(), media="late", posted_at="2026-09-20 11:00:00", as_of="2026-09-07")
        self.assertIsNone(bills.pick([future], "2026-09-10"))
        monday = dict(list_0907(), posted_at="2026-09-08 11:35:50", as_of="2026-09-07")
        self.assertEqual(bills.pick([monday], "2026-09-07")["media"], monday["media"])   # 次日发的可以

    def test_same_reading_requires_row_by_row_agreement(self):
        a = bills.check_rows(rows_0907(), TOTAL_0907, D("2026-09-07"))
        rows = rows_0907()
        rows[0]["amount_fen"] += 10000
        rows[1]["amount_fen"] -= 10000                      # 两行串位互相抵消，合计不变
        b = bills.check_rows(rows, TOTAL_0907, D("2026-09-07"))
        self.assertTrue(b.ok)                                # 单次读的闸门拦不住
        self.assertFalse(bills.same_reading(a, b))           # 两次读一对就露馅
        self.assertTrue(bills.same_reading(a, bills.check_rows(rows_0907(), TOTAL_0907, D("2026-09-07"))))


class TestReviewFixesStore(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_second_process_waits_for_the_lock(self):
        lock = str(self.dir / "s.lock")
        holder = subprocess.Popen([sys.executable, "-c",
            "import sys,time; sys.path.insert(0, %r); import os; os.environ['DAILY_FUNDS_LOCK']=%r;"
            "from daily_funds_local.store import Store; Store(%r); print('held', flush=True); time.sleep(20)"
            % (str(ROOT), lock, str(self.dir / "d.jsonl"))], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), "held")
            rc = subprocess.run([sys.executable, "-c",
                "import sys; sys.path.insert(0, %r); import os; os.environ['DAILY_FUNDS_LOCK']=%r;"
                "os.environ['DAILY_FUNDS_LOCK_WAIT']='2';"
                "from daily_funds_local.store import Store, StoreBusy\n"
                "try:\n    Store(%r)\nexcept StoreBusy:\n    raise SystemExit(7)"
                % (str(ROOT), lock, str(self.dir / "d.jsonl"))], capture_output=True, text=True).returncode
            self.assertEqual(rc, 7)
        finally:
            holder.kill()
            holder.wait()

    def test_same_process_can_open_twice(self):
        a = Store(str(self.dir / "d.jsonl"))
        b = Store(str(self.dir / "d.jsonl"))
        self.assertEqual(a.counts()["days"], b.counts()["days"])

    def test_clear_alert_and_delete_bill_list(self):
        s = Store(str(self.dir / "d.jsonl"))
        s.mark_alert("k", "t", "x")
        self.assertTrue(s.clear_alert("k"))
        self.assertFalse(s.clear_alert("k"))
        L = list_0907()
        s.upsert_bill_list(media=L["media"], posted_at=L["posted_at"], ref_date=L["ref_date"], as_of=L["as_of"],
                           total_fen=TOTAL_0907, bills=[list(b) for b in L["bills"]], extracted_at="x")
        s.delete_bill_list(L["media"])
        self.assertFalse(Store(str(self.dir / "d.jsonl")).has_bill_list(L["media"]))


class TestReviewFixesNotify(unittest.TestCase):
    def _run_with_body(self, body):
        from daily_funds_local import notify
        orig = notify.subprocess.run
        notify.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, 0, json.dumps(body), "")
        try:
            return notify._run_once(["chat", "message", "send"])
        finally:
            notify.subprocess.run = orig

    def test_string_error_is_a_failure(self):
        from daily_funds_local import notify
        with self.assertRaises(notify.SendError):
            self._run_with_body({"error": "permission denied"})
        with self.assertRaises(notify.SendError):
            self._run_with_body({"error": {"message": "未登录"}})
        self.assertEqual(self._run_with_body({"success": True})["success"], True)

    def test_auth_notice_key_is_stable_across_days(self):
        from daily_funds_local import notify
        orig = notify.auth_expiry
        try:
            notify.auth_expiry = lambda: (5, "2026-10-01T08:00:00+08:00")
            k1, _ = notify.auth_expiry_notice()
            notify.auth_expiry = lambda: (4, "2026-10-01T08:00:00+08:00")
            k2, text = notify.auth_expiry_notice()
            self.assertEqual(k1, k2)
            self.assertIn("还有 4 天", text)
            notify.auth_expiry = lambda: (30, "2026-10-26T08:00:00+08:00")
            self.assertIsNone(notify.auth_expiry_notice())
        finally:
            notify.auth_expiry = orig

if __name__ == "__main__":
    unittest.main(verbosity=2)
