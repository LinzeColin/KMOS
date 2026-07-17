#!/usr/bin/env python3
"""KMFA App 后端骨架（TSK.KMFA.PROD.0001，D2=A：KMIDS 同栈 FastAPI）。

只读吃机器面：machine/facts（状态/数据管线）+ metadata/quality/assertions.jsonl（对账断言）。
页眉三元组（质量等级/报告等级/GO 状态）由 /api/状态 直给——DoD 第 1 条的页眉数据源。
私有派生层（DuckDB）不经本服务暴露明细；App 只出 public-safe 聚合。
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

REPO = Path(__file__).resolve().parents[4]
KMFA = REPO / "KMFA"
FACTS = KMFA / "machine" / "facts"

app = FastAPI(title="KMFA App", version="0.1.0-prod0001")


def load_json(path: Path):
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"事实文件缺失: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/healthz")
def healthz():
    return {"status": "ok", "facts_dir_present": FACTS.is_dir()}


@app.get("/api/状态")
def status():
    s = load_json(FACTS / "status.json")
    return {
        "版本": s.get("version"), "阶段": s.get("stage"), "当前任务": s.get("task"),
        "真实进度": s.get("real_progress"),
        "页眉": {"质量等级": "Q3", "报告等级": s.get("report_grade"), "GO状态": s.get("business_verdict")},
    }


@app.get("/api/数据管线")
def data_pipeline():
    return load_json(FACTS / "data_pipeline.json")


@app.get("/api/断言")
def assertions():
    path = KMFA / "metadata" / "quality" / "assertions.jsonl"
    if not path.exists():
        raise HTTPException(status_code=503, detail="断言表缺失")
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    closed = sum(1 for r in rows if str(r.get("status", "")).startswith("closed"))
    return {"total": len(rows), "closed": closed, "analyzed_open": len(rows) - closed, "items": rows}


@app.get("/api/技能")
def skills():
    import re
    reg = (KMFA / "skills" / "registry.yaml").read_text(encoding="utf-8")
    skills_block = reg.split("\nschedules:")[0]
    ids = re.findall(r"^  - id: (\S+)", skills_block, re.M)
    names = re.findall(r"^    name_zh: (.+)$", skills_block, re.M)
    return {"count": len(ids), "skills": [{"id": i, "名称": n} for i, n in zip(ids, names)]}
