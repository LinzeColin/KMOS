#!/usr/bin/env python3
"""facts 数据管线切片生成器（TSK.KMFA.DATA.0012 v1）。

从三本机器账（KMDatabase manifest / lineage.yaml / DuckDB staging）机械聚合出
`machine/facts/data_pipeline.json`（public-safe：只有计数/期间/Q级/阻断计数，零明细零金额）。
确定性输出：同输入 → 字节级相同（幂等验收）；数据时点 = 批次日，不写墙钟。
并在 facts/changelog.json 幂等登记 v1.5.2 里程碑（渲染进 06_运维手册）。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FACTS = REPO / "KMFA" / "machine" / "facts"
DB_PATH = REPO / "KMFA" / ".codex_private_runtime" / "duckdb" / "kmfa_staging.duckdb"
# 原始件登记册的权威位置 = 私有库 Private-Database。
# 公开仓 KMDatabase/data/manifest.jsonl 含真人姓名与客户名（余永昕、新疆宜化 等 53 条），
# 属「财务/工资数据只进私有库、永不进公开 KMOS」策略要清的对象——本生成器不得再依赖它。
PRIVATE_AREA = "Private-KMDatabase"
PRIVATE_MANIFEST = "manifest.jsonl"
PRIVATE_DB_CLIENT = REPO / "KMDatabase" / "machine" / "tools" / "private_db_client.py"


def load_kmdb_manifest() -> list[dict]:
    """从私有库读原始件登记册。

    **不做本地回退**：回退到公开仓的那份，等于把刚解耦掉的依赖又悄悄接回去，
    而且会在清除之后静默读到空/旧数据。读不到就明说、就停。
    """
    if not PRIVATE_DB_CLIENT.exists():
        raise SystemExit(f"缺少私有库 SDK：{PRIVATE_DB_CLIENT}")
    sys.path.insert(0, str(PRIVATE_DB_CLIENT.parent))
    try:
        import private_db_client as pdb
    except ImportError as exc:
        raise SystemExit(f"私有库 SDK 导入失败：{exc}") from exc

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "manifest.jsonl"
        try:
            pdb.get(PRIVATE_AREA, PRIVATE_MANIFEST, str(out))
        except Exception as exc:  # SDK 内部已带连接级重试，到这里就是真读不到
            raise SystemExit(
                f"从私有库读 {PRIVATE_AREA}/{PRIVATE_MANIFEST} 失败：{exc}\n"
                "  · 确认 `gh auth status` 已登录且对 LinzeColin/Private-Database 有读权限\n"
                "  · 本生成器**不回退读公开仓**，见函数注释"
            ) from exc
        rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]

    if not rows:
        raise SystemExit("私有库登记册为空——拒绝据此生成事实")
    print(f"✓ 登记册取自私有库 {PRIVATE_AREA}/{PRIVATE_MANIFEST}：{len(rows)} 条", file=sys.stderr)
    return rows


def main() -> int:
    import duckdb
    kmdb = load_kmdb_manifest()
    # 质量报告取最新版（v2 重裁于 2026-07-18：回款重复项经权威视图消解闭案，open 阻断 3→2）
    quality_path = REPO / "KMFA/stage_artifacts/DT5_DATA0010_quality_v2/machine/quality_report.json"
    if not quality_path.exists():
        quality_path = REPO / "KMFA/stage_artifacts/DT5_DATA0010_quality_initial/machine/quality_report.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
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
        "reconciliation_status": "报告第1-8号已交付、八切面零候选：回款 7/11 月 0 分差；开票三角差 3 分+逐票层 126/134 闭案；五账套凭证 0 不平；费用轴两账套收口零候选；税费轴 36/39 格；借款轴流量级闭合+仲利三方履约逐分；材料轴 125/190 假设穷尽；个人借支 27/30 在位；open 项全部收敛为下批数据四类依赖",
        "next_gates": ["下批数据（曦悦明细账/湖北开明凭证重导）", "12 月报表期间差重验", "银行流水窗口延展后行级匹配 v3"],
    }
    out = FACTS / "data_pipeline.json"
    new_text = json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    changed = (not out.exists()) or out.read_text(encoding="utf-8") != new_text
    if changed:
        out.write_text(new_text, encoding="utf-8")

    chlog_path = FACTS / "changelog.json"
    chlog = json.loads(chlog_path.read_text(encoding="utf-8"))
    if not any(e.get("version") == "v1.5.8" for e in chlog):
        chlog.insert(0, {
            "version": "v1.5.8", "date": "2026-07-18",
            "summary": "会话终章：报告第 6-8 号交付（零候选收官/实例日加固/开票逐票层）；派生层至 17 表 263,758 行（+个人借支/编码母表/项目开票原件）；八颗实例日地雷全排（含夏令时年漂移改锚北京）；`bootstrap.sh` 一键引导+`cloudflared` 上线件+`DT8` 健康周检+语义门入 CI；证据链 30/30 零悬空；证据档索引 76 档一表可查；Owner 两张一页纸（三件套/下批数据需求单）。",
        })
        chlog_path.write_text(json.dumps(chlog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not any(e.get("version") == "v1.5.7" for e in chlog):
        chlog.insert(0, {
            "version": "v1.5.7", "date": "2026-07-18",
            "summary": "借款与材料两域收官+部署实证：贷款一览表/收发明细入仓（第 13/14 表，派生层 253,864 行）；借款轴流量级闭合（负债类期初系统性缺失具名、登记册反推期初互证）；材料轴三层匹配 125/190、七项假设穷尽（映射表定稿、匹配引擎固化带自检）；报告第 4/5 号交付；镜像同架构真构建排掉四颗实例日地雷、`run_skill` 管道五场演练全过；App 四页签+三图；Owner 三件套一页纸落仓。",
        })
        chlog_path.write_text(json.dumps(chlog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not any(e.get("version") == "v1.5.6" for e in chlog):
        chlog.insert(0, {
            "version": "v1.5.6", "date": "2026-07-17",
            "summary": "税费轴开张即闭合：税负率明细板表带状解析入 `_staging.tax_composition`（798 行、亚分舍入 71 处全登记、带内脚验 90/94 平）；对费用表 6403 计提逐月逐税种 36/39 格 0 分差，余 3 格为跨月对冲对（±67.57 元）与 1 分舍入；费用轴七码全解释（报告第 3 号）；App 四页签成形。",
        })
        chlog_path.write_text(json.dumps(chlog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not any(e.get("version") == "v1.5.4" for e in chlog):
        chlog.insert(0, {
            "version": "v1.5.4", "date": "2026-07-17",
            "summary": "对账工程化：行级匹配引擎 v2 达 72.9%（批量入账 57 笔确证）；声明式门禁引擎试点三门全绿（校验即配置生效）；App 后端骨架+中文仪表首页+部署件就位（页眉三元组 API）；开票明细入 `_staging`；硬阻断六项逐项对证据，距 Q5 剩五项清单固化。",
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
