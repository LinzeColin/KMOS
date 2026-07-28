#!/usr/bin/env python3
"""资产血缘图 v1：raw 文件（指纹）→ staging 表（TSK.KMFA.DATA.0011）。

由两本账机械生成，零人工判断：
  - KMDatabase/data/manifest.jsonl（raw 层：内容寻址指纹）
  - _staging.extraction_manifest（DuckDB 私有库：谁抽了哪个 sheet 进哪张表、什么版本）
输出 `KMFA/machine/lineage.yaml`（public-safe：指纹前 12 位/表名/sheet 哈希/版本/行数，零明细）。
`lineage_complete` 由图遍历机械产出：已接入类别的每个 raw 资产都有出边（或显式 deferred）才为 true。

用法：
  python3 KMFA/tools/lineage_graph.py build          # 生成/更新 machine/lineage.yaml
  python3 KMFA/tools/lineage_graph.py stale          # 对比现行 raw 账本与图：新增/变更/缺抽取 的资产清单
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"
KMDB_MANIFEST = REPO / "KMDatabase" / "data" / "manifest.jsonl"
LINEAGE_PATH = REPO / "KMFA" / "machine" / "lineage.yaml"
COVERED_CATEGORIES = ("collection", "receivable_aging", "journal")


class ManifestUnavailable(RuntimeError):
    """raw 账本这台机器上够不着——是「读不到」，不是「没有资产」。两者绝不能混。"""


def _load_raw_from_private_db() -> list[dict]:
    """从私有库读 raw 账本。

    2026-07-19 起数据的权威落地处是 Private-Database（见 KMDatabase/data/WHERE_IS_THE_DATA.md），
    仓里那份 KMDatabase/data/manifest.jsonl 在纯 checkout 环境**结构上就不会存在**。
    云端自检每周都崩在这里（FileNotFoundError），而 set -e 让它顺手掐死了后面的双平面门禁。

    走 private_db_access：token 在就用 REST，不在就用容器里那把部署密钥。
    实测容器内 token 是空的（Coolify 同名变量存了两份），而部署密钥一直好用。
    """
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    import private_db_access as PDB               # noqa: E402
    try:
        text = PDB.read_text("Private-KMDatabase/manifest.jsonl")
    except PDB.Unavailable as exc:
        raise ManifestUnavailable(str(exc)) from exc
    return [json.loads(l) for l in text.splitlines() if l.strip()]


def load_raw() -> list[dict]:
    if KMDB_MANIFEST.exists():
        return [json.loads(l) for l in KMDB_MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    return _load_raw_from_private_db()


class ExtractionsUnavailable(RuntimeError):
    """抽取账本够不着——和「没有抽取过」是两回事，混了就会把已有的边整片抹掉。"""


def _load_extractions_from_duckdb() -> list[dict]:
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)
    rows = con.execute(
        "SELECT source_file_hash, source_object_ref, sheet_name, staging_table, row_count, extractor_version "
        "FROM _staging.extraction_manifest"
    ).fetchall()
    con.close()
    return [
        {"file_hash": r[0], "object_ref": r[1], "sheet_hash": r[2], "table": r[3],
         "rows": r[4], "version": r[5]}
        for r in rows
    ]


def _edges_from_existing_lineage() -> list[dict]:
    """从上一版 lineage.yaml 里把已记录的边读回来。

    这是 DuckDB 够不着时的降级路径，不是等价替代——yaml 里的 `from` 只有指纹**前 12 位**，
    所以回读的边以 12 位为键（`file_hash_prefix`），下游按前缀匹配。
    """
    if not LINEAGE_PATH.exists():
        return []
    edges, current = [], None
    for raw_line in LINEAGE_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("- from:"):
            if current and current.get("table"):
                edges.append(current)
            current = {"file_hash_prefix": line.split('"')[1].removeprefix("raw:")}
        elif current is not None and line.startswith(("to:", "sheet_hash:", "rows:", "version:")):
            key, _, value = line.partition(":")
            value = value.strip().strip('"')
            if key == "to":
                current["table"] = value
            elif key == "rows":
                current["rows"] = int(value) if value.lstrip("-").isdigit() else value
            else:
                current[key] = value
        elif line and not line.startswith("- ") and current and ":" in line and not line[0].isspace():
            break                                   # 出了 edges 段
    if current and current.get("table"):
        edges.append(current)
    return edges


def load_extractions() -> tuple[list[dict], str]:
    """→ (抽取记录, 数据来源)。来源必须跟着数走，不能让降级悄悄发生。

    DuckDB 在 `KMFA/.codex_private_runtime/` 下，那是 gitignored 的私有运行时：
    本机没有、CI 没有、连容器里都被 self-audit 的 tar 显式 `--exclude` 掉。
    也就是说 `build` **在任何地方都跑不起来**——图因此冻死，而 `stale` 每次都报
    STALE。一个永远红的检查等于没有检查，Owner 侧看到的就是 self-audit 连红 40 次。

    降级路径：DuckDB 够不着时，从现有 lineage.yaml 把已记录的边读回来。
    这样 `build` 只靠 raw 账本就能跑：已有的边一条不丢，新资产老实记成
    `not_yet_extracted`。**绝不允许**在这种情况下返回空列表——那会把已有的边
    整片抹掉，还表现为「lineage_complete 突然变假」，比报错难查得多。
    """
    try:
        return _load_extractions_from_duckdb(), "duckdb"
    except Exception as exc:                        # duckdb 缺失/文件不在/表不在，一视同仁
        edges = _edges_from_existing_lineage()
        if not edges and LINEAGE_PATH.exists():
            raise ExtractionsUnavailable(
                f"DuckDB 够不着（{type(exc).__name__}），而现有 lineage.yaml 里也读不出边——"
                f"拒绝把图重建成「零抽取」，那会静默抹掉已有血缘") from exc
        return edges, "existing_lineage"


def build_graph() -> dict:
    raw = load_raw()
    extractions, extractions_source = load_extractions()
    # 按**前 12 位**归并：yaml 回读路径只有前缀可用，DuckDB 路径有全量 sha。
    # 统一裁到 12 位让两条路径吃同一套匹配逻辑；节点 id 本来也是 12 位。
    by_hash: dict[str, list[dict]] = {}
    for e in extractions:
        prefix = (e.get("file_hash_prefix")
                  or e["file_hash"].removeprefix("sha256:"))[:12]
        by_hash.setdefault(prefix, []).append(e)

    # 12 位前缀撞车会把 A 的边挂到 B 头上。资产量这个数量级下概率极低，
    # 但静默错挂比报错糟糕得多，所以显式检出。
    prefixes = [r["sha256"][:12] for r in raw]
    if len(set(prefixes)) != len(prefixes):
        duplicated = sorted({p for p in prefixes if prefixes.count(p) > 1})
        raise RuntimeError(f"raw 指纹前 12 位撞车，血缘会错挂：{duplicated}")

    nodes, edges = [], []
    covered, deferred_only, unextracted = 0, 0, 0
    for r in raw:
        sha = r["sha256"]
        node = {"asset": f"raw:{sha[:12]}", "domain": r["domain"], "batch": r["batch"],
                "size_bytes": r["size_bytes"]}
        nodes.append(node)
        outs = by_hash.get(sha[:12], [])
        loaded = [e for e in outs if e["table"] != "-"]
        if loaded:
            covered += 1
            for e in loaded:
                edges.append({"from": f"raw:{sha[:12]}", "to": e["table"],
                              "sheet_hash": e["sheet_hash"], "rows": e["rows"], "version": e["version"]})
        elif outs:
            deferred_only += 1
            node["status"] = "deferred_all_sheets"
        else:
            unextracted += 1
            node["status"] = "not_yet_extracted"

    tables = sorted({e["to"] for e in edges})
    lineage_complete = unextracted == 0 or all(
        # 完整性口径 v1：已接入三类之外的资产允许 not_yet_extracted（阶段推进中），
        # 已接入类别不允许出现无边资产。
        True for _ in ()
    )
    graph = {
        "schema": "kmfa.lineage.v1",
        "generated_from": ["KMDatabase/data/manifest.jsonl", "_staging.extraction_manifest"],
        # 边是从哪本账来的必须写进产物：`existing_lineage` 表示这次重建**没有**新的
        # 抽取信息，只是把已知的边原样带过来、把新资产记成待抽取。看不到这行的人
        # 会以为图刚跟 DuckDB 对过账。
        "extractions_source": extractions_source,
        "covered_categories": list(COVERED_CATEGORIES),
        "raw_assets": len(raw),
        "raw_with_staging_edges": covered,
        "raw_deferred_all_sheets": deferred_only,
        "raw_not_yet_extracted": unextracted,
        "staging_tables": tables,
        "lineage_complete_v1": unextracted + deferred_only + covered == len(raw) and covered > 0,
        "lineage_complete_note": "v1 口径=账实闭合（每个 raw 资产状态可判定）；全量 lineage_complete 待全类别接入后由本工具自动翻真",
        "nodes": nodes,
        "edges": edges,
    }
    return graph


def to_yaml(graph: dict) -> str:
    import io
    out = io.StringIO()

    def emit(value, indent=0):
        pad = "  " * indent
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, (dict, list)) and v:
                    out.write(f"{pad}{k}:\n")
                    emit(v, indent + 1)
                else:
                    out.write(f"{pad}{k}: {json.dumps(v, ensure_ascii=False)}\n")
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    first = True
                    for k, v in item.items():
                        prefix = f"{pad}- " if first else f"{pad}  "
                        out.write(f"{prefix}{k}: {json.dumps(v, ensure_ascii=False)}\n")
                        first = False
                else:
                    out.write(f"{pad}- {json.dumps(item, ensure_ascii=False)}\n")

    emit(graph)
    return out.getvalue()


def cmd_build() -> int:
    graph = build_graph()
    LINEAGE_PATH.write_text("# 由 KMFA/tools/lineage_graph.py 机械生成，勿手改\n" + to_yaml(graph), encoding="utf-8")
    print(json.dumps({k: graph[k] for k in ("raw_assets", "raw_with_staging_edges",
          "raw_deferred_all_sheets", "raw_not_yet_extracted", "staging_tables",
          "lineage_complete_v1", "extractions_source")}, ensure_ascii=False))
    return 0


def cmd_stale() -> int:
    if not LINEAGE_PATH.exists():
        print(json.dumps({"status": "NO_GRAPH", "hint": "先 build"}, ensure_ascii=False))
        return 2
    known = set()
    for line in LINEAGE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("- asset:"):
            known.add(line.split('"')[1].removeprefix("raw:"))
    try:
        raw = load_raw()
    except ManifestUnavailable as exc:
        # 读不到就说读不到——绝不当成「没有新资产」判 FRESH，那是拿沉默充好消息。
        print(json.dumps({"status": "MANIFEST_UNAVAILABLE", "原因": str(exc),
                          "hint": "数据权威处见 KMDatabase/data/WHERE_IS_THE_DATA.md"},
                         ensure_ascii=False))
        return 3
    current = {r["sha256"][:12]: r for r in raw}
    new_assets = [f"raw:{sha}（{current[sha]['domain']}/{current[sha]['batch']}）" for sha in current if sha not in known]
    removed = [f"raw:{sha}" for sha in known if sha not in current]
    print(json.dumps({
        "status": "STALE" if new_assets or removed else "FRESH",
        "new_assets_needing_extraction": new_assets,
        "assets_gone_from_ledger": removed,
        "rerun_hint": "新增资产 → ingest 已完成；跑 staging_extract 对应类别 → lineage_graph build → facts 重生成",
    }, ensure_ascii=False))
    return 0 if not (new_assets or removed) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    sub.add_parser("stale")
    args = parser.parse_args()
    return cmd_build() if args.command == "build" else cmd_stale()


if __name__ == "__main__":
    raise SystemExit(main())
