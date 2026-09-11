"""审查修复回归：真跑 ingest（假归档、假读图、临时库），不再用固定退出码替代。"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_local_daily_funds as r  # noqa: E402
from daily_funds_local.gate import DayFacts  # noqa: E402
from daily_funds_local.smb_source import Candidate  # noqa: E402
from daily_funds_local.store import Store  # noqa: E402


def facts(report_date, bank_close=100000000, total_close=150000000):
    return DayFacts(report_date=report_date, layout="C",
                    bank_open=100000000, bank_in=0, bank_out=0, bank_close=bank_close,
                    bill_open=50000000, bill_in=0, bill_out=0, bill_close=50000000,
                    total_open=150000000, total_in=0, total_out=0, total_close=total_close)


class FakeArchive:
    def __init__(self, cands, path):
        self._c, self._p = cands, path

    def candidates(self):
        return iter(self._c)

    def fetch(self, cand, tmpdir):
        return self._p


class TestIngest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.img = self.dir / "img.png"
        self.img.write_bytes(b"\x89PNG-not-empty")
        os.environ["DAILY_FUNDS_DATA"] = str(self.dir / "d.jsonl")
        self._orig = (r.SmbArchive, r.read_card)

    def tearDown(self):
        r.SmbArchive, r.read_card = self._orig
        os.environ.pop("DAILY_FUNDS_DATA", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def _run(self, reads, message_time="2026-09-10 10:28:00", retry=False, name="a.png"):
        cand = Candidate(message_time=message_time, layout="C", width=1218, height=1396,
                         original_name=name, renamed=None, size_bytes=None)
        r.SmbArchive = lambda: FakeArchive([cand], str(self.img))
        queue = list(reads)
        r.read_card = lambda path, layout, message_date=None, **k: queue.pop(0)
        args = argparse.Namespace(command="poll", since="", until="", limit=0, retry_skipped=retry)
        return r.ingest(args), Store()

    def test_all_new_tables_rejected_is_reported_as_2(self):
        bad = facts("2026-09-09", bank_close=100000000, total_close=999)        # 组成对不上
        rc, store = self._run([bad, bad, bad])
        self.assertEqual(rc, 2)
        self.assertEqual(store.counts()["days"], 0)

    def test_flow_mismatch_is_reread_before_storing(self):
        misread = facts("2026-09-09", bank_close=110000000, total_close=160000000)   # 组成自洽、流水不平
        good = facts("2026-09-09")
        rc, store = self._run([misread, good])
        self.assertEqual(rc, 0)
        row = store.series()[-1]
        self.assertEqual((row.bank_fen, row.source_imbalance), (100000000, False))

    def test_future_report_date_never_becomes_latest(self):
        rc, store = self._run([facts("2026-10-01")] * 3)
        self.assertEqual(store.counts()["days"], 0)
        self.assertEqual(rc, 2)

    def test_retry_skipped_actually_retries(self):
        bad = facts("2026-09-09", total_close=999)
        self._run([bad, bad, bad], name="x.png")
        rc, store = self._run([facts("2026-09-09")], retry=True, name="x.png")
        self.assertEqual(store.counts()["days"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
