"""数据落在 SMB，运行时只用内存——本机不留持久化状态。

**为什么不是把 SQLite 文件放 SMB**：实测直接连 SMB 上的 .sqlite3 会
`OperationalError: disk I/O error`——CIFS 的文件锁撑不住 SQLite 的要求。
所以权威数据用 JSONL 存在 SMB（和归档自己的 .manifest.jsonl 同一套路），
进程内读进 `:memory:` 的 SQLite 查询，写回时整份重写。

217 天约 45KB，整份重写比增量写安全得多，也不需要任何锁。

**SMB 写入必须走 rsync 并回读校验**：这台机器上 `cp` 到 SMB 会静默写出
全零文件（字节数对、无报错、内容空）。所以一律写本地临时文件 → rsync → 读回
确认非零且行数对，任何一步不对就抛错，绝不让「写成功了但其实是空的」发生。

金额一律整数分，按图内日期幂等 upsert。
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# 数据落在受限资料区的财务目录——那里已经放着账户清单、资金计划表、现金情况，
# 每日余额正属于这一类。**不放进 KMVideo/付款请示群/**：那是归档 skill 自己
# 管理并会做 audit 的项目群目录，README 明写「一级目录 = 项目群」，
# 往里塞派生数据迟早会被它的自检当成异常。
SMB_DATA_DIR_DEFAULT = ("/Volumes/share/03_资料库/MetaData/IDS_MetaData"
                        "/60_受限资料/财务/每日资金看板")
DATA_NAME = "daily_funds.jsonl"

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_balance (
  report_date      TEXT PRIMARY KEY,
  bank_fen         INTEGER NOT NULL,
  bill_fen         INTEGER NOT NULL,
  total_fen        INTEGER NOT NULL,
  layout           TEXT NOT NULL,
  source_imbalance INTEGER NOT NULL DEFAULT 0,
  chain_suspect    INTEGER NOT NULL DEFAULT 0,
  gate_reasons     TEXT NOT NULL DEFAULT '',
  image_sha256     TEXT NOT NULL DEFAULT '',
  message_date     TEXT NOT NULL DEFAULT '',
  extracted_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS seen_media (
  original   TEXT PRIMARY KEY,
  outcome    TEXT NOT NULL,
  seen_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bill_list (
  media        TEXT PRIMARY KEY,
  posted_at    TEXT NOT NULL,
  ref_date     TEXT NOT NULL,
  as_of        TEXT NOT NULL,
  total_fen    INTEGER NOT NULL,
  bills_json   TEXT NOT NULL,
  image_sha256 TEXT NOT NULL DEFAULT '',
  extracted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alert_sent (
  key      TEXT PRIMARY KEY,
  sent_at  TEXT NOT NULL,
  text     TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS skipped (
  message_date TEXT NOT NULL,
  original     TEXT NOT NULL,
  reason       TEXT NOT NULL,
  detail       TEXT NOT NULL DEFAULT '',
  seen_at      TEXT NOT NULL,
  PRIMARY KEY (message_date, original)
);
"""

TABLES = ("daily_balance", "seen_media", "skipped", "bill_list", "alert_sent")


class SmbWriteError(RuntimeError):
    pass


class StoreBusy(RuntimeError):
    pass


# 整份重写的存储必须串行：两个进程同时从同一份旧文件装载、各写各的，后写者会用旧快照
# 把前者整份盖掉（新余额或首报台账丢失）。锁在本机——SMB 上的文件锁不可靠（见模块头）。
# 用 flock：持有进程一退出（包括被 kill）内核就释放，不会留下「陈旧锁伪装成正常」。
LOCK_PATH_DEFAULT = "/private/tmp/kmfa-daily-funds-store.lock"
LOCK_WAIT_SEC = 900
_PROCESS_LOCK = None      # 进程级：同一进程里再开 Store 不能自己跟自己抢锁


def _acquire_process_lock() -> None:
    global _PROCESS_LOCK
    if _PROCESS_LOCK is not None:
        return
    path = os.environ.get("DAILY_FUNDS_LOCK") or LOCK_PATH_DEFAULT
    wait = float(os.environ.get("DAILY_FUNDS_LOCK_WAIT") or LOCK_WAIT_SEC)
    fh = open(path, "a+")
    deadline = time.monotonic() + wait
    while True:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except (BlockingIOError, OSError):
            if time.monotonic() >= deadline:
                fh.close()
                raise StoreBusy("资金数据文件被另一个进程占用超过 %d 秒" % wait)
            time.sleep(1)
    _PROCESS_LOCK = fh


@dataclass
class Row:
    report_date: str
    bank_fen: int
    bill_fen: int
    total_fen: int
    layout: str
    source_imbalance: bool
    chain_suspect: bool = False


def data_dir() -> Path:
    return Path(os.environ.get("DAILY_FUNDS_SMB_DIR") or SMB_DATA_DIR_DEFAULT)


def data_path() -> Path:
    return data_dir() / DATA_NAME


class Store:
    """打开即从 SMB 读入内存；每次写操作后整份刷回 SMB。"""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = Path(path or os.environ.get("DAILY_FUNDS_DATA") or data_path())
        _acquire_process_lock()      # 装载之前拿锁：读—改—写整段串行
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(SCHEMA)
        self._defer = 0        # >0 时暂不刷盘，退出批量时统一刷一次
        self._dirty = False
        # 认不出的表原样保留、原样写回。整份重写的存储最怕「旧代码不认识新表，
        # 读的时候跳过、写的时候就把它删了」——数据只能加，不能被版本差抹掉。
        self._foreign: List[str] = []
        self._load()

    def begin_batch(self) -> None:
        """进入批量：期间的写只记脏，不碰 SMB。必须配对 end_batch()。"""
        self._defer += 1

    def end_batch(self) -> None:
        """退出批量：有脏就统一落盘一次。"""
        self._defer = max(0, self._defer - 1)
        if self._defer == 0 and self._dirty:
            self._flush_now()
            self._dirty = False

    @contextmanager
    def batch(self):
        """批量写：期间不刷 SMB，退出时统一刷一次。

        回填一轮有 219 条写，每条都刷就是 219 次网络往返；
        而且中途每一次都是一个可能被打断的写窗口。
        """
        self.begin_batch()
        try:
            yield self
        finally:
            self.end_batch()

    # ---------- SMB 读写 ----------

    def _load(self) -> None:
        if not self.path.exists():
            self.conn.commit()
            return
        local = Path(tempfile.mkdtemp(prefix="kmfa-store-")) / DATA_NAME
        rc = subprocess.run(["rsync", "-a", "--inplace", str(self.path), str(local)],
                            capture_output=True, text=True)
        if rc.returncode != 0 or not local.exists():
            raise SmbWriteError("从 SMB 读数据失败: %s" % rc.stderr.strip()[:160])
        n = 0
        with local.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                tbl = rec.pop("_t", "daily_balance")
                if tbl not in TABLES:
                    self._foreign.append(line)
                    continue
                cols = ",".join(rec.keys())
                marks = ",".join("?" * len(rec))
                self.conn.execute("INSERT OR REPLACE INTO %s (%s) VALUES (%s)"
                                  % (tbl, cols, marks), tuple(rec.values()))
                n += 1
        self.conn.commit()
        shutil.rmtree(local.parent, ignore_errors=True)
        self._loaded = n

    def _flush(self) -> None:
        """写操作的统一出口。批量模式下只记脏，退出批量时才真正落盘。"""
        if self._defer:
            self._dirty = True
            return
        self._flush_now()

    def _flush_now(self) -> None:
        """整份重写回 SMB。写本地 → rsync → 回读校验行数，任一步不对就抛。"""
        lines: List[str] = []
        for tbl in TABLES:
            cur = self.conn.execute("SELECT * FROM %s" % tbl)
            names = [d[0] for d in cur.description]
            for row in cur.fetchall():
                rec = {"_t": tbl}
                rec.update(dict(zip(names, row)))
                lines.append(json.dumps(rec, ensure_ascii=False))
        lines.extend(self._foreign)
        payload = "\n".join(lines) + ("\n" if lines else "")

        tmpdir = Path(tempfile.mkdtemp(prefix="kmfa-flush-"))
        local = tmpdir / DATA_NAME
        local.write_text(payload, encoding="utf-8")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        rc = subprocess.run(["rsync", "-a", "--inplace", str(local), str(self.path)],
                            capture_output=True, text=True)
        if rc.returncode != 0:
            raise SmbWriteError("写 SMB 失败: %s" % rc.stderr.strip()[:160])

        # 回读校验：SMB 上「写成功但内容是全零」是这台机器上真实发生过的事。
        back = tmpdir / "verify.jsonl"
        rc = subprocess.run(["rsync", "-a", "--inplace", str(self.path), str(back)],
                            capture_output=True, text=True)
        if rc.returncode != 0 or not back.exists():
            raise SmbWriteError("写完读不回来: %s" % rc.stderr.strip()[:160])
        got = back.read_text(encoding="utf-8")
        # 比完整内容，不只比行数：行数对、内容是旧的或残缺的，同样是写失败
        if got != payload:
            raise SmbWriteError("回读内容与写入不一致：写 %d 行，读回 %d 行"
                                % (len(lines), got.count("\n")))
        shutil.rmtree(tmpdir, ignore_errors=True)

    # ---------- 写 ----------

    def upsert(self, *, report_date: str, bank_fen: int, bill_fen: int,
               total_fen: int, layout: str, source_imbalance: bool,
               chain_suspect: bool = False,
               gate_reasons: str = "", image_sha256: str = "",
               message_date: str = "", extracted_at: str = "") -> None:
        self.conn.execute(
            "INSERT INTO daily_balance (report_date,bank_fen,bill_fen,total_fen,layout,"
            "source_imbalance,chain_suspect,gate_reasons,image_sha256,message_date,"
            "extracted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(report_date) DO UPDATE SET "
            "bank_fen=excluded.bank_fen, bill_fen=excluded.bill_fen, "
            "total_fen=excluded.total_fen, layout=excluded.layout, "
            "source_imbalance=excluded.source_imbalance, "
            "chain_suspect=excluded.chain_suspect, "
            "gate_reasons=excluded.gate_reasons, image_sha256=excluded.image_sha256, "
            "message_date=excluded.message_date, extracted_at=excluded.extracted_at",
            (report_date, bank_fen, bill_fen, total_fen, layout,
             1 if source_imbalance else 0, 1 if chain_suspect else 0,
             gate_reasons, image_sha256, message_date, extracted_at),
        )
        self.conn.commit()
        self._flush()

    def mark_skipped(self, message_date: str, original: str, reason: str,
                     detail: str = "", seen_at: str = "") -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO skipped (message_date,original,reason,detail,seen_at) "
            "VALUES (?,?,?,?,?)", (message_date, original, reason, detail, seen_at))
        self.conn.commit()
        self._flush()

    def clear_skipped(self, original: str) -> None:
        """这张图后来读成功了，撤掉丢弃记录——否则 --retry-skipped 会一直重跑它。"""
        self.conn.execute("DELETE FROM skipped WHERE original = ?", (original,))
        self.conn.commit()
        self._flush()

    def mark_seen(self, original: str, outcome: str, seen_at: str = "") -> None:
        """记下这张图处理过了。成功也要记——否则 poll 每天重读全部历史。"""
        self.conn.execute(
            "INSERT OR REPLACE INTO seen_media (original,outcome,seen_at) VALUES (?,?,?)",
            (original, outcome, seen_at))
        self.conn.commit()
        self._flush()

    def upsert_bill_list(self, *, media: str, posted_at: str, ref_date: str, as_of: str,
                         total_fen: int, bills: list, image_sha256: str = "",
                         extracted_at: str = "") -> None:
        """只收过了全部闸门的票据表。bills = [[到期日, 金额分], ...]。"""
        self.conn.execute(
            "INSERT OR REPLACE INTO bill_list (media,posted_at,ref_date,as_of,total_fen,"
            "bills_json,image_sha256,extracted_at) VALUES (?,?,?,?,?,?,?,?)",
            (media, posted_at, ref_date, as_of, total_fen,
             json.dumps(bills, ensure_ascii=False), image_sha256, extracted_at))
        self.conn.commit()
        self._flush()

    def delete_bill_list(self, media: str) -> None:
        self.conn.execute("DELETE FROM bill_list WHERE media = ?", (media,))
        self.conn.commit()
        self._flush()

    def clear_alert(self, key: str) -> bool:
        """事件已恢复：撤掉首报记录，下次再出问题算新事件。返回是否真有记录被撤。"""
        cur = self.conn.execute("DELETE FROM alert_sent WHERE key = ?", (key,))
        self.conn.commit()
        if cur.rowcount:
            self._flush()
        return bool(cur.rowcount)

    def clear_alerts_with_prefix(self, prefix: str) -> int:
        esc = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        cur = self.conn.execute("DELETE FROM alert_sent WHERE key LIKE ? ESCAPE '\\'", (esc + "%",))
        self.conn.commit()
        if cur.rowcount:
            self._flush()
        return cur.rowcount

    def mark_alert(self, key: str, text: str = "", sent_at: str = "") -> None:
        """首报制台账：发过的告警按指纹记下，永不重发。"""
        self.conn.execute("INSERT OR REPLACE INTO alert_sent (key,sent_at,text) VALUES (?,?,?)",
                          (key, sent_at, text[:400]))
        self.conn.commit()
        self._flush()

    # ---------- 读 ----------

    def bill_lists(self) -> List[dict]:
        cur = self.conn.execute(
            "SELECT media,posted_at,ref_date,as_of,total_fen,bills_json FROM bill_list "
            "ORDER BY posted_at")
        return [{"media": r[0], "posted_at": r[1], "ref_date": r[2], "as_of": r[3],
                 "total_fen": r[4], "bills": [tuple(x) for x in json.loads(r[5])]}
                for r in cur]

    def has_bill_list(self, media: str) -> bool:
        return self.conn.execute("SELECT 1 FROM bill_list WHERE media = ?",
                                 (media,)).fetchone() is not None

    def balances_between(self, start: str, end: str) -> List[tuple]:
        """[start, end] 内每个报表日的 (日期, 汇票分)，给票据表做跨源核对。"""
        return [(r[0], r[1]) for r in self.conn.execute(
            "SELECT report_date, bill_fen FROM daily_balance "
            "WHERE report_date >= ? AND report_date <= ? ORDER BY report_date", (start, end))]

    def has_alert(self, key: str) -> bool:
        return self.conn.execute("SELECT 1 FROM alert_sent WHERE key = ?",
                                 (key,)).fetchone() is not None

    def have_dates(self) -> set:
        return {r[0] for r in self.conn.execute("SELECT report_date FROM daily_balance")}

    def seen_originals(self) -> set:
        """poll 用来跳过的集合：处理过的 ∪ 丢弃过的。

        只看 skipped 是不够的——那样成功入库的候选每天都会被重新读一遍图。
        """
        a = {r[0] for r in self.conn.execute("SELECT original FROM seen_media")}
        b = {r[0] for r in self.conn.execute("SELECT original FROM skipped")}
        return a | b

    def retryable_originals(self) -> set:
        """--retry-skipped 用：只有丢弃过的才值得重试。"""
        return {r[0] for r in self.conn.execute("SELECT original FROM skipped")}

    def series(self, limit: Optional[int] = None) -> List[Row]:
        sql = ("SELECT report_date,bank_fen,bill_fen,total_fen,layout,"
               "source_imbalance,chain_suspect FROM daily_balance ORDER BY report_date")
        rows = [Row(r[0], r[1], r[2], r[3], r[4], bool(r[5]), bool(r[6]))
                for r in self.conn.execute(sql)]
        return rows[-limit:] if limit else rows

    def prev_close(self, report_date: str):
        """返回 (上一有效日, 该日 银行+汇票)。口径与 gate.storable_total 一致，
        不含库存现金——版式 A 的表内「总计」含现金，混用会让链条误报。"""
        cur = self.conn.execute(
            "SELECT report_date, bank_fen + bill_fen FROM daily_balance "
            "WHERE report_date < ? ORDER BY report_date DESC LIMIT 1", (report_date,))
        row = cur.fetchone()
        return (row[0], row[1]) if row else (None, None)

    def counts(self) -> dict:
        c = self.conn.execute
        return {
            "days": c("SELECT COUNT(*) FROM daily_balance").fetchone()[0],
            "source_imbalance": c("SELECT COUNT(*) FROM daily_balance WHERE source_imbalance=1").fetchone()[0],
            "chain_suspect": c("SELECT COUNT(*) FROM daily_balance WHERE chain_suspect=1").fetchone()[0],
            "skipped": c("SELECT COUNT(*) FROM skipped").fetchone()[0],
            "bill_lists": c("SELECT COUNT(*) FROM bill_list").fetchone()[0],
            "by_layout": dict(c("SELECT layout,COUNT(*) FROM daily_balance GROUP BY layout").fetchall()),
            "by_skip_reason": dict(c("SELECT reason,COUNT(*) FROM skipped GROUP BY reason").fetchall()),
        }
