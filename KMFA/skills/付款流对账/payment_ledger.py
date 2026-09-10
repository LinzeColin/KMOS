#!/usr/bin/env python3
"""首报制台账。

一条发现只发一次。发过的永不重发；群里回应过的标 answered 并记原话。
老板 2026-09-10 定的：「你宁愿少报不报，都不要这样子搞。」

库必须放本地 —— SMB 上 sqlite 必报 disk I/O error（无文件锁）。
"""
import json, os, sqlite3, datetime as dt

DEFAULT_DB = os.path.expanduser("~/.local/share/kmfa-payment-alert/reported.sqlite3")

SCHEMA = """
CREATE TABLE IF NOT EXISTS finding (
  fingerprint     TEXT PRIMARY KEY,
  check_id        TEXT NOT NULL,
  rendered_line   TEXT NOT NULL,
  payload_json    TEXT NOT NULL,
  status          TEXT NOT NULL,          -- reported | answered
  first_reported  TEXT NOT NULL,
  answered_at     TEXT,
  answer_quote    TEXT,
  answer_msgid    TEXT
);
CREATE INDEX IF NOT EXISTS idx_status ON finding(status);
CREATE INDEX IF NOT EXISTS idx_check  ON finding(check_id);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


class Ledger:
    def __init__(self, path=None):
        self.path = path or DEFAULT_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    # ---- 读 ----
    def known(self, fp):
        return self.db.execute("SELECT 1 FROM finding WHERE fingerprint=?", (fp,)).fetchone() is not None

    def unreported(self, findings):
        """只留台账里没有的。这是首报制的唯一入口。"""
        return [f for f in findings if not self.known(f["fingerprint"])]

    def open_items(self, check_id=None):
        q = "SELECT * FROM finding WHERE status='reported'"
        a = ()
        if check_id:
            q += " AND check_id=?"; a = (check_id,)
        return [dict(r) for r in self.db.execute(q, a)]

    def counts(self):
        rows = self.db.execute("SELECT status, COUNT(*) n FROM finding GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}

    def get_meta(self, k, default=None):
        r = self.db.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        return r["v"] if r else default

    def set_meta(self, k, v):
        self.db.execute("INSERT INTO meta(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))
        self.db.commit()

    # ---- 写 ----
    def record_reported(self, findings, when=None):
        """发送成功之后才调。发送没确认落地就不写，下次还能重发。"""
        when = when or dt.datetime.now().isoformat(timespec="seconds")
        for f in findings:
            self.db.execute(
                "INSERT OR IGNORE INTO finding"
                "(fingerprint,check_id,rendered_line,payload_json,status,first_reported)"
                " VALUES(?,?,?,?,'reported',?)",
                (f["fingerprint"], f["check_id"], f.get("line", ""), json.dumps(f, ensure_ascii=False, default=str), when))
        self.db.commit()

    def mark_answered(self, fp, quote, msgid, when=None):
        when = when or dt.datetime.now().isoformat(timespec="seconds")
        cur = self.db.execute(
            "UPDATE finding SET status='answered', answered_at=?, answer_quote=?, answer_msgid=?"
            " WHERE fingerprint=? AND status='reported'", (when, quote[:500], msgid or "", fp))
        self.db.commit()
        return cur.rowcount > 0

    def seed(self, fp, check_id, line, payload, status, first_reported,
             answered_at=None, quote=None, msgid=None):
        """回填历史。上线第一次跑之前必须做，否则会把老账重发一遍。"""
        self.db.execute(
            "INSERT OR REPLACE INTO finding"
            "(fingerprint,check_id,rendered_line,payload_json,status,first_reported,"
            " answered_at,answer_quote,answer_msgid) VALUES(?,?,?,?,?,?,?,?,?)",
            (fp, check_id, line, json.dumps(payload, ensure_ascii=False, default=str), status,
             first_reported, answered_at, quote, msgid))
        self.db.commit()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stats", "list", "answered", "open"])
    ap.add_argument("--db")
    a = ap.parse_args()
    L = Ledger(a.db)
    if a.cmd == "stats":
        c = L.counts()
        print(f"台账 {L.path}")
        print(f"  已上报未结清 reported : {c.get('reported',0)}")
        print(f"  已回应结清   answered : {c.get('answered',0)}")
        return 0
    q = {"list": "SELECT * FROM finding ORDER BY first_reported",
         "answered": "SELECT * FROM finding WHERE status='answered' ORDER BY answered_at",
         "open": "SELECT * FROM finding WHERE status='reported' ORDER BY first_reported"}[a.cmd]
    for r in L.db.execute(q):
        mark = "✓" if r["status"] == "answered" else "·"
        print(f"{mark} [{r['check_id']}] {r['rendered_line'][:70]}")
        if r["answer_quote"]:
            print(f"      回应：{r['answer_quote'][:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
