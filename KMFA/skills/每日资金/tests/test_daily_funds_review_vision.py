"""审查修复回归：读图的日期年份与时间预算。"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from daily_funds_local import vision  # noqa: E402


class TestYearFromMessageDate(unittest.TestCase):
    def test_year_follows_the_message(self):
        n = vision._normalize_date
        self.assertEqual(n("09月09日", "2026-09-10"), "2026-09-09")
        self.assertEqual(n("12月31日", "2027-01-02"), "2026-12-31")     # 年初补发去年的表
        self.assertEqual(n("01月02日", "2027-01-03"), "2027-01-02")
        self.assertEqual(n("2026年9月9日", "2027-01-03"), "2026-09-09")  # 写了年份就照抄


class TestBudget(unittest.TestCase):
    def test_timeout_never_exceeds_what_is_left(self):
        self.assertEqual(vision._timeout_left(None), vision.VISION_CALL_TIMEOUT)
        self.assertLessEqual(vision._timeout_left(time.monotonic() + 100), 100)
        with self.assertRaises(vision.VisionError):
            vision._timeout_left(time.monotonic() + 5)

    def test_deadline_reaches_every_call(self):
        seen = []
        orig = (vision._api_key, vision._ask, vision._bill_chunks)
        vision._api_key = lambda: "k"
        vision._bill_chunks = lambda path, parts, scale=2: ["a", "b"]
        vision._ask = lambda prompt, img, key, model, deadline=None: seen.append(deadline) or {"rows": [], "total": ""}
        try:
            vision.read_bill_list("x.png", parts=2, deadline=123.0)
        finally:
            vision._api_key, vision._ask, vision._bill_chunks = orig
        self.assertEqual(seen, [123.0, 123.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
