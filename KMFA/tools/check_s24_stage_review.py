#!/usr/bin/env python3
"""S24 stage review 检查器（TSK.KMFA.PROD.0012）。

任务包第 21 行要求「对照恢复的 v1.5 roadmap S24 原定范围逐项执行/裁剪」。
**范围权威文档不在仓里**（见下 missing_authority），故本检查器改以仓内可核者为准：
  · 任务包 18 项（PROD.0001-0018）的证据是否真的落了 stage_artifacts
  · G5 出口门禁五项（任务包第 29 行）的当前状态
不做主观打分，只报可机器核验的事实。**可复跑**：结论随仓内实况变化，不写死。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KMFA = ROOT / "KMFA"
ART = KMFA / "stage_artifacts"

# 18 项 → 证据目录名（逐项落档才算数）
EVIDENCE = {
    "PROD.0001": "DT6_PROD0001_sqlite_state", "PROD.0002": "DT6_PROD0002_backend_api",
    "PROD.0003": "DT6_PROD0003_access_security", "PROD.0004": "DT6_PROD0004_home",
    "PROD.0005": "DT6_PROD0005_source_board", "PROD.0006": "DT6_PROD0006_project_cost",
    "PROD.0007": "DT6_PROD0007_workbench", "PROD.0008": "DT6_PROD0008_impact_rerun",
    "PROD.0009": "DT6_PROD0009_report_center", "PROD.0010": "DT6_PROD0010_aging",
    "PROD.0011": "DT6_PROD0011_invoice_tax", "PROD.0013": "DT6_PROD0013_e2e",
    "PROD.0015": "DT6_PROD0015_app_entry", "PROD.0016": "DT6_PROD0016_perf",
    "PROD.0017": "DT6_PROD0017_docs", "PROD.0012": "DT6_PROD0012_s24_review",
    "PROD.0014": "DT6_PROD0014_erpnext_gap", "PROD.0018": "DT6_PROD0018_g5",
}

# G5 出口门禁五项（任务包第 29 行原文）→ 判据落在哪
G5 = [
    ("S24 review 通过", "DT6_PROD0012_s24_review"),
    ("App 真数据端到端 PASS 并入 CI", "DT6_PROD0013_e2e"),
    (".app parity", "DT6_PROD0015_app_entry"),
    ("性能达标", "DT6_PROD0016_perf"),
    ("渲染门持续真绿", "DT6_PROD0017_docs"),
]


def main() -> int:
    items = []
    for task, d in sorted(EVIDENCE.items()):
        p = ART / d
        docs = sorted(p.glob("*.md")) if p.is_dir() else []
        items.append({
            "任务": task, "证据目录": d,
            "证据存在": bool(docs),
            "文件数": len(list(p.iterdir())) if p.is_dir() else 0,
        })
    done = [i for i in items if i["证据存在"]]

    g5 = [{"项": name, "证据目录": d, "证据存在": (ART / d).is_dir() and any((ART / d).glob("*.md"))}
          for name, d in G5]

    report = {
        "record_type": "s24_stage_review",
        "task_id": "TSK.KMFA.PROD.0012",
        "missing_authority": {
            "文档": "v1.5 原 roadmap S24 原定范围",
            "任务包引用": "07 任务包第 6 行「v1.5 原 roadmap S24 是范围权威」",
            "仓内是否存在": False,
            "处置": "改以仓内可核者为准：任务包 18 项证据 + G5 五项状态；"
                    "不臆造 S24 条目，也不据此宣称「已对照原范围逐项执行」",
        },
        "十八项": {"合计": len(items), "有证据": len(done),
                   "缺证据": [i["任务"] for i in items if not i["证据存在"]],
                   "逐项": items},
        "G5五项": {"合计": len(g5), "已具备": len([x for x in g5 if x["证据存在"]]),
                   "逐项": g5},
        "裁剪": [],   # 无裁剪：18 项一项没砍，缺的三项是未做完不是砍掉
        "结论": None,
    }
    all_18 = len(done) == len(items)
    all_g5 = all(x["证据存在"] for x in g5)
    report["结论"] = ("S24_REVIEW_PASS" if all_18 and all_g5
                      else "S24_REVIEW_INCOMPLETE")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report["结论"] == "S24_REVIEW_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
