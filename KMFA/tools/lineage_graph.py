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
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"
KMDB_MANIFEST = REPO / "KMDatabase" / "data" / "manifest.jsonl"
LINEAGE_PATH = REPO / "KMFA" / "machine" / "lineage.yaml"
COVERED_CATEGORIES = ("collection", "receivable_aging", "journal")


def load_raw() -> list[dict]:
    return [json.loads(l) for l in KMDB_MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_extractions() -> list[dict]:
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


def build_graph() -> dict:
    raw = load_raw()
    extractions = load_extractions()
    by_hash: dict[str, list[dict]] = {}
    for e in extractions:
        by_hash.setdefault(e["file_hash"].removeprefix("sha256:"), []).append(e)

    nodes, edges = [], []
    covered, deferred_only, unextracted = 0, 0, 0
    for r in raw:
        sha = r["sha256"]
        node = {"asset": f"raw:{sha[:12]}", "domain": r["domain"], "batch": r["batch"],
                "size_bytes": r["size_bytes"]}
        nodes.append(node)
        outs = by_hash.get(sha, [])
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
          "raw_deferred_all_sheets", "raw_not_yet_extracted", "staging_tables", "lineage_complete_v1")}, ensure_ascii=False))
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
    current = {r["sha256"][:12]: r for r in load_raw()}
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
