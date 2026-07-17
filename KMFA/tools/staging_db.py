#!/usr/bin/env python3
"""KMFA 私有派生层 DuckDB 基座（TSK.KMFA.DATA.0006，D5=C：DuckDB 做分析派生层）。

数据边界（任务包 06 边界②）：库文件永不 tracked——固定落在 `KMFA/.codex_private_runtime/duckdb/`
（.gitignore 第 8 行整目录忽略），目录权限 700；备份走私有链路，不进 git bundle。

用法：
  python3 KMFA/tools/staging_db.py init          # 建库 + _staging schema + 抽取 manifest 表
  python3 KMFA/tools/staging_db.py check         # 可建可查 + 权限核验 + 写入基准（DATA.0006 验收三项）
  python3 KMFA/tools/staging_db.py sql "SELECT ..."   # 只读查询入口
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRIVATE_DIR = REPO / "KMFA" / ".codex_private_runtime" / "duckdb"
DB_PATH = PRIVATE_DIR / "kmfa_staging.duckdb"


def _duckdb():
    try:
        import duckdb
    except ImportError:
        print(json.dumps({"status": "DUCKDB_MISSING", "hint": "pip install duckdb（本地 venv 或容器均可）"}, ensure_ascii=False))
        raise SystemExit(2)
    return duckdb


def ensure_private_dir() -> None:
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(PRIVATE_DIR, 0o700)


def cmd_init() -> int:
    duckdb = _duckdb()
    ensure_private_dir()
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS _staging")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS _staging.extraction_manifest (
            source_file_hash VARCHAR NOT NULL,      -- sha256:<64hex>，对 KMDatabase 对象
            source_object_ref VARCHAR NOT NULL,     -- KMDatabase/data/objects/...
            sheet_name VARCHAR NOT NULL,
            staging_table VARCHAR NOT NULL,
            row_count BIGINT NOT NULL,
            mapped_columns INTEGER NOT NULL,
            deferred_columns INTEGER NOT NULL,
            extracted_at TIMESTAMP NOT NULL,
            extractor_version VARCHAR NOT NULL,
            idempotency_key VARCHAR NOT NULL UNIQUE -- hash(source_file_hash+sheet+version)：同指纹重跑零 diff
        )
        """
    )
    con.close()
    print(json.dumps({"status": "INITIALIZED", "db": str(DB_PATH.relative_to(REPO)), "schema": "_staging"}, ensure_ascii=False))
    return 0


def cmd_check() -> int:
    duckdb = _duckdb()
    ensure_private_dir()
    result: dict[str, object] = {"status": "PASS"}

    mode = stat.S_IMODE(PRIVATE_DIR.stat().st_mode)
    result["private_dir_mode"] = oct(mode)
    if mode & 0o077:
        result["status"] = "FAIL"
        result["private_dir_mode_error"] = "目录对组/他人可见，要求 700"

    tracked_probe = os.popen(f"cd {REPO} && git check-ignore -q KMFA/.codex_private_runtime/duckdb/x && echo ignored").read().strip()
    result["gitignored"] = tracked_probe == "ignored"
    if not result["gitignored"]:
        result["status"] = "FAIL"

    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS _staging")
    con.execute("CREATE OR REPLACE TABLE _staging._bench (id BIGINT, amount_cents BIGINT, label VARCHAR)")
    start = time.perf_counter()
    con.execute("INSERT INTO _staging._bench SELECT range, range * 137 % 1000000, 'r' || range FROM range(1000000)")
    write_s = time.perf_counter() - start
    start = time.perf_counter()
    total = con.execute("SELECT count(*), sum(amount_cents) FROM _staging._bench").fetchone()
    read_s = time.perf_counter() - start
    con.execute("DROP TABLE _staging._bench")
    con.close()
    result["write_1m_rows_seconds"] = round(write_s, 3)
    result["aggregate_1m_rows_seconds"] = round(read_s, 4)
    result["bench_row_count"] = total[0]
    result["amounts_are_integer_cents"] = True

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


def cmd_sql(query: str) -> int:
    duckdb = _duckdb()
    if not DB_PATH.exists():
        print(json.dumps({"status": "DB_MISSING", "hint": "先跑 init"}, ensure_ascii=False))
        return 2
    con = duckdb.connect(str(DB_PATH), read_only=True)
    for row in con.execute(query).fetchall():
        print(row)
    con.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("check")
    sql_p = sub.add_parser("sql")
    sql_p.add_argument("query")
    args = parser.parse_args()
    if args.command == "init":
        return cmd_init()
    if args.command == "check":
        return cmd_check()
    return cmd_sql(args.query)


if __name__ == "__main__":
    raise SystemExit(main())
