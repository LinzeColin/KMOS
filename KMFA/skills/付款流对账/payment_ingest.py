#!/usr/bin/env python3
"""把红圈「付款审批（日常费用）」全历史导出灌进 P2 approval 表，作为一个新快照。

为什么存在（根因，不是补丁）：
付款核对三项（dup_reimbursement / amount_changed / status_regressed）比对 approval
表里最新的两份快照。原来的入库步骤在 2026-09-10 主树清理时被删（未跟踪→蒸发），
表从此冻结在 09-09（数据只到 09-04）。于是每天真去核对时，三项都在拿两份两周前的
陈旧快照对比，看不到近几天的付款——这就是「哨兵不查付款、只刷欠款」的根因。

本模块每天把最新的全历史导出灌成一份新快照，让付款核对重新睁眼。

幂等：同一份文件（按内容 md5）只灌一次；内容没变（当天没有新付款）就不产生新快照，
所以「上一份快照」天然就是「上次数据发生变化时」，amount_changed / status_regressed
比的永远是真正的变化，而不是同一份数据自己跟自己比。
"""
import datetime as dt
import hashlib
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xlsx_raw import read_sheet                      # noqa: E402
from payment_checks import P2, latest_hongquan       # noqa: E402

OBJECT = "付款审批（日常费用）"

# 导出表头 → approval 列。红圈这张对象的表头稳定；逐个精确匹配，缺一个就拒绝入库，
# 绝不静默灌半张表。
HEADER_TO_COL = {
    "付款编号": "payment_id",
    "创建人": "creator",
    "支付状态(系统)": "payment_status",
    "申请日期": "application_date",
    "支付日期": "payment_date",
    "申请支付金额": "requested_amount",
    "实际支付金额": "paid_amount",
    "审批状态": "approval_status",
    "收款账户": "payee_account",
    "付款内容": "payment_content",
    "备注": "remarks",
    "负责人": "principal",
}

# 只留最新 N 份快照：付款核对只需最新两份，多留两份给排查用。
KEEP_SNAPSHOTS = 4

_SCHEMA = """
CREATE TABLE IF NOT EXISTS approval (
  source_md5 TEXT NOT NULL, source_row INTEGER NOT NULL, source_file TEXT NOT NULL,
  manifest_message_time TEXT, ingested_at TEXT NOT NULL, raw_headers_json TEXT NOT NULL,
  payment_id TEXT, creator TEXT, payment_status TEXT, application_date TEXT, payment_date TEXT,
  requested_amount TEXT, paid_amount TEXT, approval_status TEXT, payee_account TEXT,
  payment_content TEXT, remarks TEXT, principal TEXT,
  PRIMARY KEY (source_md5, source_row)
);
"""

_INSERT_COLS = [
    "source_md5", "source_row", "source_file", "manifest_message_time",
    "ingested_at", "raw_headers_json",
    "payment_id", "creator", "payment_status", "application_date", "payment_date",
    "requested_amount", "paid_amount", "approval_status", "payee_account",
    "payment_content", "remarks", "principal",
]


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest_approval(db_path=None, export_path=None, now=None):
    """把最新的付款审批导出灌成一份新快照。返回 dict，status 取值：
       ingested  真灌了新快照（rows=行数）
       already   这份文件已经灌过（幂等命中）
       no_export SMB 上找不到导出文件
       bad_headers 表头缺列，拒绝入库（missing=缺的列）
    绝不抛异常吞掉——调用方按 status 判断，失败要告警不要静默降级。
    """
    db_path = db_path or P2
    if export_path is None:
        export_path = latest_hongquan(OBJECT, "")
    if not export_path or not os.path.exists(export_path):
        return {"status": "no_export", "path": export_path}

    md5 = _md5(export_path)
    con = sqlite3.connect(db_path)
    try:
        con.executescript(_SCHEMA)
        if con.execute("SELECT 1 FROM approval WHERE source_md5=? LIMIT 1", (md5,)).fetchone():
            return {"status": "already", "md5": md5, "path": export_path}

        headers, rows = read_sheet(export_path)
        inv = {t.strip(): c for c, t in headers.items()}
        missing = [h for h in HEADER_TO_COL if h not in inv]
        if missing:
            return {"status": "bad_headers", "missing": missing, "path": export_path}

        raw_headers = json.dumps([headers[c] for c in sorted(headers)], ensure_ascii=False)
        ingested_at = (now or dt.datetime.now(dt.timezone.utc)).astimezone(
            dt.timezone.utc).isoformat(timespec="seconds")
        src_file = os.path.basename(export_path)
        ph = ",".join("?" * len(_INSERT_COLS))

        n = 0
        for i, r in enumerate(rows, start=1):
            rec = {
                "source_md5": md5, "source_row": i, "source_file": src_file,
                "manifest_message_time": None, "ingested_at": ingested_at,
                "raw_headers_json": raw_headers,
            }
            for header, col in HEADER_TO_COL.items():
                rec[col] = r.get(inv[header], "")
            con.execute(
                f"INSERT OR IGNORE INTO approval ({','.join(_INSERT_COLS)}) VALUES ({ph})",
                [rec[c] for c in _INSERT_COLS])
            n += 1

        # 只留最新 KEEP_SNAPSHOTS 份，跟 payment_checks._snapshots 同一个排序口径
        snaps = [row[0] for row in con.execute(
            "SELECT source_md5 FROM approval GROUP BY source_md5 "
            "ORDER BY MAX(ingested_at) DESC, MAX(source_file) DESC")]
        for old in snaps[KEEP_SNAPSHOTS:]:
            con.execute("DELETE FROM approval WHERE source_md5=?", (old,))
        con.commit()
        return {"status": "ingested", "md5": md5, "rows": n,
                "path": export_path, "snapshots": min(len(snaps), KEEP_SNAPSHOTS)}
    finally:
        con.close()


if __name__ == "__main__":
    r = ingest_approval()
    print(json.dumps(r, ensure_ascii=False))
