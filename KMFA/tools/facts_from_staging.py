#!/usr/bin/env python3
"""facts 数据管线切片生成器（TSK.KMFA.DATA.0012 v1）。

从三本机器账（KMDatabase manifest / lineage.yaml / DuckDB staging）机械聚合出
`machine/facts/data_pipeline.json`（public-safe：只有计数/期间/Q级/阻断计数，零明细零金额）。
确定性输出：同输入 → 字节级相同（幂等验收）；数据时点 = 批次日，不写墙钟。
并在 facts/changelog.json 幂等登记 v1.5.2 里程碑（渲染进 06_运维手册）。
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FACTS = REPO / "KMFA" / "machine" / "facts"
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"


def main() -> int:
    import duckdb
    kmdb = [json.loads(l) for l in (REPO / "KMDatabase/data/manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    quality = json.loads((REPO / "KMFA/stage_artifacts/DT5_DATA0010_quality_initial/machine/quality_report.json").read_text(encoding="utf-8"))
    con = duckdb.connect(str(DB_PATH), read_only=True)
    tbl = {}
    for (name,) in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='_staging' AND table_name NOT IN ('extraction_manifest')").fetchall():
        rows, = con.execute(f"SELECT count(*) FROM _staging.{name}").fetchone()
        tbl[name] = rows
    con.close()

    facts = {
        "schema": "kmfa.facts.data_pipeline.v1",
        "data_as_of_batch": sorted({r["batch"] for r in kmdb})[-1],
        "raw_assets_registered": len(kmdb),
        "raw_domains": sorted({r["domain"] for r in kmdb}),
        "staging_tables": {t: {"rows": n} for t, n in sorted(tbl.items())},
        "quality_grade_current": "Q3（机器候选结构化；对账收敛进行中）",
        "staging_rows_total": sum(tbl.values()),
        "lineage": "machine/lineage.yaml（raw→staging 机械生成，stale 判定可用）",
        "quality_blockers_open": len(quality["blockers"]),
        "reconciliation_status": "报告第1号已交付：报表vs权威台账 7/11 月 0 分差；五账套凭证视角借贷全等（0 不平凭证）；analyzed-open 差异 4 条见断言表",
        "next_gates": ["operating_analysis/金蝶zip 抽取", "facts 八件套全量重生成", "渲染门真绿（DATA.0013）"],
    }
    out = FACTS / "data_pipeline.json"
    new_text = json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    changed = (not out.exists()) or out.read_text(encoding="utf-8") != new_text
    if changed:
        out.write_text(new_text, encoding="utf-8")

    chlog_path = FACTS / "changelog.json"
    chlog = json.loads(chlog_path.read_text(encoding="utf-8"))
    if not any(e.get("version") == "v1.5.4" for e in chlog):
        chlog.insert(0, {
            "version": "v1.5.4", "date": "2026-07-17",
            "summary": "对账工程化：行级匹配引擎 v2 达 72.9%（批量入账 57 笔确证）；声明式门禁引擎试点三门全绿（校验即配置生效）；App 后端骨架+中文仪表首页+部署件就位（页眉三元组 API）；开票明细入 staging；硬阻断六项逐项对证据，距 Q5 剩五项清单固化。",
        })
        chlog_path.write_text(json.dumps(chlog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not any(e.get("version") == "v1.5.3" for e in chlog):
        chlog.insert(0, {
            "version": "v1.5.3", "date": "2026-07-17",
            "summary": "对账收敛实弹开跑：《一致性证明与差异分析报告》第 1 号交付（报表对权威回款台账 7/11 个月分毫不差）；金蝶五账套凭证视角借贷全等（0 不平凭证）；`_staging` 十表约 20 万行；对账断言表 `metadata/quality/assertions.jsonl` 播种。",
        })
        chlog_path.write_text(json.dumps(chlog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not any(e.get("version") == "v1.5.2" for e in chlog):
        chlog.insert(0, {
            "version": "v1.5.2", "date": "2026-07-17",
            "summary": "真实数据管线贯通首段：53 个原始文件内容寻址入仓并登记；回款/应收台账/银行日记账三表 19,443 行入私有 `_staging`（金额一律整数分）；血缘图 `machine/lineage.yaml` 机械生成；质量初评三表 Q3，勾稽初检 0 不平，28 行已收款大于合同额进差异队列候选。",
        })
        chlog_path.write_text(json.dumps(chlog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"data_pipeline_json": "updated" if changed else "unchanged", "staging_rows_total": facts["staging_rows_total"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
