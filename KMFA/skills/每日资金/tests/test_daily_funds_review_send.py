"""审查修复回归：同日只发一次群、首报去重、alert 子命令、票据表两次读一致才入库。"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("DAILY_FUNDS_LOCK", os.path.join(tempfile.gettempdir(), "kmfa-daily-funds-test-%d.lock" % os.getpid()))

import run_local_daily_funds as r  # noqa: E402
from daily_funds_local import bills, card, notify  # noqa: E402
from daily_funds_local.store import Store  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        os.environ["DAILY_FUNDS_DATA"] = str(self.dir / "d.jsonl")
        os.environ["DAILY_FUNDS_ALLOW_GROUP"] = "1"
        self.notices, self.cards = [], []
        self._orig = (notify.send_notice, notify.send_card, notify.auth_expiry_notice, card.render)
        notify.send_notice = self.notices.append
        notify.send_card = lambda png, text, to_group=False: self.cards.append(to_group)
        notify.auth_expiry_notice = lambda: None
        card.render = lambda payload, out, scale=1: out

    def tearDown(self):
        notify.send_notice, notify.send_card, notify.auth_expiry_notice, card.render = self._orig
        for k in ("DAILY_FUNDS_DATA", "DAILY_FUNDS_ALLOW_GROUP"):
            os.environ.pop(k, None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def seed(self, days_ago, bill_fen=50000000):
        s = Store()
        d = (dt.date.today() - dt.timedelta(days=days_ago)).isoformat()
        s.upsert(report_date=d, bank_fen=100000000, bill_fen=bill_fen, total_fen=100000000 + bill_fen,
                 layout="C", source_imbalance=False, extracted_at="x")

    def send(self):
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return r.send(argparse.Namespace(to_group=True, dry_run=False))


class TestSend(Base):
    def test_second_send_on_the_same_beijing_day_is_refused(self):
        self.seed(1)
        self.assertEqual(self.send(), 0)
        self.assertEqual(self.send(), 4)
        self.assertEqual(self.cards, [True])

    def test_stale_data_is_reported_once(self):
        self.seed(20)
        self.assertEqual((self.send(), self.send()), (3, 3))
        self.assertEqual(self.cards, [])
        self.assertEqual(len([n for n in self.notices if "未发群" in n]), 1)

    def test_send_failure_is_reported_once_per_cause(self):
        self.seed(1)
        card.render = lambda payload, out, scale=1: (_ for _ in ()).throw(RuntimeError("渲染坏了"))
        self.assertEqual((self.send(), self.send()), (2, 2))
        self.assertEqual(len([n for n in self.notices if "未能发出" in n]), 1)


class TestAlertCommand(Base):
    def alert(self, **kw):
        ns = argparse.Namespace(key=kw.get("key", ""), text=kw.get("text", ""), clear_prefix=kw.get("clear_prefix", ""))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r.alert(ns)
        return buf.getvalue()

    def test_once_then_known_then_new_after_clear(self):
        self.assertIn("ALERT_SENT", self.alert(key="archive:KMFile 付款请示群:locked", text="t"))
        self.assertIn("ALERT_KNOWN", self.alert(key="archive:KMFile 付款请示群:locked", text="t"))
        self.alert(clear_prefix="archive:KMFile 付款请示群:")
        self.assertIn("ALERT_SENT", self.alert(key="archive:KMFile 付款请示群:locked", text="t"))
        self.assertEqual(len(self.notices), 2)

    def test_prefix_underscore_is_literal(self):
        s = Store()
        s.mark_alert("send_step:crash", "", "x")
        s.mark_alert("sendXstep:crash", "", "x")
        self.assertEqual(s.clear_alerts_with_prefix("send_step:"), 1)
        self.assertTrue(s.has_alert("sendXstep:crash"))


ROWS = [(1, "2026-09-16", 9, "1000.00"), (2, "2026-09-20", 13, "2000.00"), (3, "2026-09-23", 16, "4000.00")]


def reading(amounts=None):
    amounts = amounts or [a for *_, a in ROWS]
    return {"rows": [{"seq": s, "due": d, "days": n, "amount": a} for (s, d, n, _), a in zip(ROWS, amounts)],
            "total": "7000.00"}


class FakeArchive:
    def __init__(self, path):
        self.path = path

    def fetch_media(self, media, tmpdir):
        return self.path


class TestBillsAgreement(Base):
    def setUp(self):
        super().setUp()
        s = Store()
        for d in ("2026-09-03", "2026-09-04", "2026-09-05", "2026-09-06", "2026-09-07"):
            s.upsert(report_date=d, bank_fen=1, bill_fen=700000, total_fen=700001, layout="C",
                     source_imbalance=False, extracted_at="x")
        img = self.dir / "b.png"
        img.write_bytes(b"\x89PNG-not-empty")
        self._o2 = (bills.find_list_messages, r.SmbArchive, r.bill_read_plan, r.read_bill_list)
        bills.find_list_messages = lambda *a, **k: [{"media": "m1", "posted_at": "2026-09-07 11:35:50", "sender": "x"}]
        r.SmbArchive = lambda: FakeArchive(str(img))
        r.bill_read_plan = lambda path: [(1, 1), (2, 1)]

    def tearDown(self):
        bills.find_list_messages, r.SmbArchive, r.bill_read_plan, r.read_bill_list = self._o2
        super().tearDown()

    def run_bills(self, readings, attempts):
        queue = list(readings)
        r.read_bill_list = lambda path, scale=1, parts=1, deadline=None: queue.pop(0)
        with contextlib.redirect_stdout(io.StringIO()):
            r.ingest_bills(argparse.Namespace(days=12, pages=1, attempts=attempts, budget=600, backfill=True))
        return Store().has_bill_list("m1")

    def test_two_passing_but_different_readings_are_not_stored(self):
        swapped = reading(["2000.00", "1000.00", "4000.00"])          # 两行串位：合计、资金表都对得上
        self.assertTrue(bills.check_rows(*bills.parse_read(swapped)[:2], dt.date(2026, 9, 7)).ok)
        self.assertFalse(self.run_bills([reading(), swapped], attempts=2))

    def test_stored_once_two_readings_agree(self):
        swapped = reading(["2000.00", "1000.00", "4000.00"])
        self.assertTrue(self.run_bills([reading(), swapped, reading()], attempts=3))


if __name__ == "__main__":
    unittest.main(verbosity=2)
