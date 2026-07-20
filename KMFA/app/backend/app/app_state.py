#!/usr/bin/env python3
"""应用状态面（TSK.KMFA.PROD.0001，D2=A：SQLite）。

**数据面与应用状态面分离**是这一层存在的理由：
· 数据面 = `machine/facts`、`metadata/quality`、`machine/lineage.yaml` —— App **只读**，永不写；
· 应用状态面 = 本模块 —— App 自己写的东西（决策事件、重跑步骤、导出登记、审计事件）。

从 JSONL 换成 SQLite 的**实质收益**：append-only 由「我们只用 'a' 模式打开」这种
君子协定，升级成**数据库层强制**——每张表挂 UPDATE/DELETE 触发器直接 RAISE(ABORT)。
即便将来有人手滑写了 UPDATE，也会被库本身拒绝，而不是悄悄改掉一条已发生的事实。
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable

# 五张表 = 原来的五个 JSONL，语义一一对应，契约不变
TABLES = (
    "resolution_events",      # 差异工作台决策与冲正（PROD.0007）
    "rerun_steps",            # 影响重跑四层链步骤（PROD.0008）
    "rerun_consistency",      # 重跑一致性检查（PROD.0008）
    "export_records",         # 报告导出 hash 登记（PROD.0009）
    "audit_events",           # 审计事件（PROD.0003）
)


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path), isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")   # 崩溃安全
    con.execute("PRAGMA synchronous=FULL")   # 写完真落盘——审计与决策不容许丢
    return con


def init(db_path: Path) -> None:
    """建表 + 挂 append-only 触发器。幂等。"""
    con = _connect(db_path)
    try:
        for t in TABLES:
            con.execute(
                f"CREATE TABLE IF NOT EXISTS {t} ("
                " seq INTEGER PRIMARY KEY AUTOINCREMENT,"
                " payload TEXT NOT NULL)"
            )
            # **append-only 的数据库层强制**：改与删一律 ABORT。
            # JSONL 时代靠"只用 'a' 打开"，那是约定；这里是库本身拒绝。
            con.execute(
                f"CREATE TRIGGER IF NOT EXISTS {t}_no_update"
                f" BEFORE UPDATE ON {t} BEGIN"
                f"  SELECT RAISE(ABORT, '{t} 是 append-only，不得 UPDATE');"
                f" END"
            )
            con.execute(
                f"CREATE TRIGGER IF NOT EXISTS {t}_no_delete"
                f" BEFORE DELETE ON {t} BEGIN"
                f"  SELECT RAISE(ABORT, '{t} 是 append-only，不得 DELETE');"
                f" END"
            )
    finally:
        con.close()


def append(db_path: Path, table: str, record: dict[str, Any]) -> dict[str, Any]:
    """追加一条。表名走白名单——不做字符串拼接注入面。"""
    if table not in TABLES:
        raise ValueError(f"未知状态表：{table}")
    init(db_path)
    con = _connect(db_path)
    try:
        con.execute(
            f"INSERT INTO {table}(payload) VALUES (?)",
            (json.dumps(record, ensure_ascii=False, sort_keys=True),),
        )
        # 审计与决策不容许因为进程崩溃而丢
        os.sync() if hasattr(os, "sync") else None
    finally:
        con.close()
    return record


def read(db_path: Path, table: str) -> list[dict[str, Any]]:
    """按写入顺序读全表。表不存在或库不存在时返回空——读路径不该因为还没写过就报错。"""
    if table not in TABLES:
        raise ValueError(f"未知状态表：{table}")
    if not db_path.exists():
        return []
    con = _connect(db_path)
    try:
        rows = con.execute(f"SELECT payload FROM {table} ORDER BY seq").fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()
    return [json.loads(r[0]) for r in rows]


def migrate_jsonl(db_path: Path, table: str, jsonl_path: Path) -> int:
    """把既有 JSONL 搬进来。已迁过就跳过，避免重复导入。"""
    if not jsonl_path.exists() or read(db_path, table):
        return 0
    n = 0
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            append(db_path, table, json.loads(line))
            n += 1
    return n


def stats(db_path: Path) -> dict[str, Any]:
    counts = {t: len(read(db_path, t)) for t in TABLES}
    return {
        "库": str(db_path),
        "存在": db_path.exists(),
        "字节": db_path.stat().st_size if db_path.exists() else 0,
        "表": counts,
        "合计": sum(counts.values()),
        "append_only": "数据库层强制（UPDATE/DELETE 触发器 RAISE ABORT）",
    }
