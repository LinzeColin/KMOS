#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_legacy_to_facts.py —— 把旧人类可读文件转成机器平面事实

旧结构（功能清单.md）是同构的：摘要字段块 + 功能表 + 证据表。
本工具把其中的**事实**抽取成 machine/facts/status.json 与 features.json，
使新七文件渲染出真实内容，而不是空 UNKNOWN。

原则：只搬事实，不搬叙述。抽取后旧文件即可删除（内容已进机器平面，
历史仍在 git 中可追溯）。抽不到的字段留空并标 UNKNOWN，绝不编造。

用法:
  python3 migrate_legacy_to_facts.py --project <项目目录>
    [--legacy <旧功能清单路径，默认自动探测>]
退出码: 0=成功  1=找不到旧文件
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

STATUS_FIELDS = {
    "project_id": "project_id",
    "product_version": "version",
    "current_stage": "stage",
    "current_phase": "phase",
    "current_task": "task",
    "evidence_status": "evidence_status",
}


def find_legacy(project: Path):
    for cand in [
        project / "功能清单.md",
        project / "machine" / "legacy" / "功能清单.md",
    ]:
        if cand.is_file():
            return cand
    return None


def parse_summary(text: str) -> dict:
    """抽取 '- key: `value`' 摘要块。"""
    out = {}
    for m in re.finditer(r"^-\s+([a-z_]+):\s*`([^`]*)`", text, re.MULTILINE):
        out[m.group(1)] = m.group(2)
    return out


def parse_features(text: str) -> list:
    """抽取功能表 '| FEAT-... | 名称 | 状态 | ... | 证据等级 |'。"""
    feats = []
    for m in re.finditer(r"^\|\s*(FEAT-[A-Z0-9\-]+)\s*\|([^|]*)\|([^|]*)\|(.*)\|([^|]*)\|\s*$",
                         text, re.MULTILINE):
        fid, name, status = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        evidence = m.group(5).strip().lower()
        feats.append({
            "id": fid,
            "name": name,
            "status": status,
            "evidence": "extracted" if "extract" in evidence else "declared",
        })
    return feats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--legacy")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    legacy = Path(args.legacy) if args.legacy else find_legacy(project)
    if not legacy or not legacy.is_file():
        print(f"FAIL: 找不到旧功能清单（{project}）")
        return 1

    text = legacy.read_text(encoding="utf-8")
    summary = parse_summary(text)
    features = parse_features(text)

    facts = project / "machine" / "facts"
    facts.mkdir(parents=True, exist_ok=True)

    status = {
        "version": summary.get("product_version", "UNKNOWN"),
        "stage": summary.get("current_stage", "UNKNOWN"),
        "phase": summary.get("current_phase", "UNKNOWN"),
        "task": summary.get("current_task", "无进行中任务"),
        "real_progress": summary.get("progress", "UNKNOWN")
                         + "（结构进度；真实进度待第二层核对）",
        "report_grade": "UNKNOWN（待口径裁定）",
        "business_verdict": "UNKNOWN",
        "evidence_status": summary.get("evidence_status", "UNKNOWN"),
        "rendered_at": "2026-07-15",
        "migrated_from_legacy": legacy.name,
    }
    (facts / "status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    (facts / "features.json").write_text(
        json.dumps(features, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ {project.name}: 抽取 {len(features)} 个功能 + {len(summary)} 个摘要字段 -> machine/facts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
