#!/usr/bin/env python3
"""KMFA App 后端骨架（TSK.KMFA.PROD.0001，D2=A：KMIDS 同栈 FastAPI）。

只读吃机器面：machine/facts（状态/数据管线）+ metadata/quality/assertions.jsonl（对账断言）。
页眉三元组（质量等级/报告等级/GO 状态）由 /api/状态 直给——DoD 第 1 条的页眉数据源。
私有派生层（DuckDB）不经本服务暴露明细；App 只出 public-safe 聚合。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

REPO = Path(__file__).resolve().parents[4]
KMFA = REPO / "KMFA"
FACTS = KMFA / "machine" / "facts"
LINEAGE_PATH = KMFA / "machine" / "lineage.yaml"
STAGE_ARTIFACTS = KMFA / "stage_artifacts"
ASSERTIONS_PATH = KMFA / "metadata" / "quality" / "assertions.jsonl"
# PROD.0002 铁律：API 永不直读 raw inbox（KMDatabase/data）——只吃 machine/facts、
# machine/lineage.yaml、metadata/quality、stage_artifacts 这些已治理的派生/证据面。
FORBIDDEN_READ_ROOT = REPO / "KMDatabase" / "data"

app = FastAPI(title="KMFA App", version="0.2.0-prod0002")


def _paginate(rows: list[Any], page: int, size: int) -> tuple[list[Any], dict[str, int]]:
    size = max(1, min(int(size), 500))
    page = max(1, int(page))
    total = len(rows)
    pages = max(1, (total + size - 1) // size)
    start = (page - 1) * size
    return rows[start : start + size], {"page": page, "size": size, "total": total, "pages": pages}
STATIC = Path(__file__).resolve().parent / "static"


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/ui/")
def ui_index():
    if not (FRONTEND_DIST / "index.html").exists():
        raise HTTPException(status_code=503, detail="前端未构建（KMFA/app/frontend: npm run build）")
    return FileResponse(FRONTEND_DIST / "index.html")


@app.get("/ui/assets/{asset_path:path}")
def ui_assets(asset_path: str):
    target = (FRONTEND_DIST / "assets" / asset_path).resolve()
    if not str(target).startswith(str(FRONTEND_DIST.resolve())) or not target.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(target)


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


def _load_assertions() -> list[dict[str, Any]]:
    if not ASSERTIONS_PATH.exists():
        raise HTTPException(status_code=503, detail="断言表缺失")
    return [json.loads(l) for l in ASSERTIONS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


@app.get("/api/断言")
def assertions(status: str | None = None, domain: str | None = None, page: int = 1, size: int = 50):
    """断言表（支持按状态/域过滤 + 分页）。

    顶层 total/closed/analyzed_open/items 保持既有契约不变（前端概览页依赖），
    过滤与分页为 PROD.0002 新增能力。
    """
    rows = _load_assertions()
    closed = sum(1 for r in rows if str(r.get("status", "")).startswith("closed"))
    selected = rows
    if status:
        selected = [r for r in selected if str(r.get("status", "")) == status]
    if domain:
        selected = [r for r in selected if str(r.get("domain", "")) == domain]
    items, meta = _paginate(selected, page, size)
    return {
        "total": len(rows),
        "closed": closed,
        "analyzed_open": len(rows) - closed,
        "筛选": {"status": status, "domain": domain, "命中": len(selected)},
        "分页": meta,
        "状态清单": sorted({str(r.get("status")) for r in rows if r.get("status")}),
        "域清单": sorted({str(r.get("domain")) for r in rows if r.get("domain")}),
        "items": items,
    }


@app.get("/api/技能")
def skills():
    import re

    def clean(raw: str | None) -> str | None:
        if raw is None:
            return None
        text = re.sub(r"\s+#.*$", "", raw).strip()
        return text.strip('"') or None

    reg = (KMFA / "skills" / "registry.yaml").read_text(encoding="utf-8")
    skills_block = reg.split("\nschedules:")[0]
    items = []
    for chunk in re.split(r"^  - id: ", skills_block, flags=re.M)[1:]:
        def field(name: str) -> str | None:
            m = re.search(rf"^    {name}: (.+)$", chunk, re.M)
            return clean(m.group(1)) if m else None

        deps = field("external_deps") or "[]"
        scheds = field("schedules") or "[]"
        items.append({
            "id": chunk.split("\n", 1)[0].strip(),
            "名称": field("name_zh"),
            "用途": field("purpose_zh"),
            "登记状态": field("status"),
            "排程": [s.strip(' "') for s in scheds.strip("[]").split(",") if s.strip(' "')],
            "外部依赖": [s.strip(' "') for s in deps.strip("[]").split(",") if s.strip(' "')],
            "本地路径硬编码": int(field("hardcoded_local_paths") or 0),
        })
    return {"count": len(items), "skills": items}


# ── PROD.0002 新增：事实八件套 / 血缘图 / 报表清单 ──────────────────────────────

@app.get("/api/事实")
def facts_index():
    """机器面事实文件清单（machine/facts）——页面据此发现可用事实，不硬编码文件名。"""
    if not FACTS.is_dir():
        raise HTTPException(status_code=503, detail="事实目录缺失")
    items = [
        {"名": p.stem, "格式": p.suffix.lstrip("."), "字节": p.stat().st_size}
        for p in sorted(FACTS.iterdir())
        if p.is_file() and p.suffix in (".json", ".yaml", ".yml")
    ]
    return {"count": len(items), "items": items}


@app.get("/api/事实/{name}")
def facts_one(name: str):
    """按名取单个事实文件。白名单式解析 + 目录逃逸防护（永不越出 machine/facts）。

    路径参数名刻意用 ASCII `name`：非 ASCII 参数名会被 Starlette 编成非法的正则命名
    捕获组，导致该路由在真实 HTTP 下永远不匹配（TestClient 却能过——本单元实测踩到，
    正是「只跑单测不真起服务」会漏掉的那类缺陷）。
    """
    for suffix in (".json", ".yaml", ".yml"):
        candidate = (FACTS / f"{name}{suffix}").resolve()
        if candidate.is_file() and candidate.parent == FACTS.resolve():
            text = candidate.read_text(encoding="utf-8")
            return json.loads(text) if suffix == ".json" else yaml.safe_load(text)
    raise HTTPException(status_code=404, detail=f"无此事实文件: {name}")


@app.get("/api/血缘")
def lineage(include_graph: bool = False, page: int = 1, size: int = 100):
    """血缘图：覆盖统计 + 派生表 + 完备判定；include_graph=true 时附节点/边（分页）。"""
    if not LINEAGE_PATH.exists():
        raise HTTPException(status_code=503, detail="血缘图缺失（跑 KMFA/tools/lineage_graph.py build）")
    graph = yaml.safe_load(LINEAGE_PATH.read_text(encoding="utf-8")) or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    out: dict[str, Any] = {
        "schema": graph.get("schema"),
        "生成自": graph.get("generated_from", []),
        "覆盖类别": graph.get("covered_categories", []),
        "覆盖": {
            "原始资产": graph.get("raw_assets"),
            "有派生边": graph.get("raw_with_staging_edges"),
            "整表延后": graph.get("raw_deferred_all_sheets"),
            "未抽取": graph.get("raw_not_yet_extracted"),
        },
        "派生表": graph.get("staging_tables", []),
        "完备": {"v1": graph.get("lineage_complete_v1"), "说明": graph.get("lineage_complete_note")},
        "规模": {"节点": len(nodes), "边": len(edges)},
    }
    if include_graph:
        node_items, node_meta = _paginate(nodes, page, size)
        edge_items, edge_meta = _paginate(edges, page, size)
        out["图"] = {"节点": node_items, "节点分页": node_meta, "边": edge_items, "边分页": edge_meta}
    return out


def _report_title(report_dir: Path) -> str | None:
    human = report_dir / "human"
    if not human.is_dir():
        return None
    for md in sorted(human.glob("*.md")):
        for line in md.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("#"):
                return line.lstrip("#").strip()
    return None


@app.get("/api/报表")
def reports(q: str | None = None, page: int = 1, size: int = 50):
    """报表清单：《一致性证明与差异分析报告》各号，标题取自 human 正文首个标题。"""
    if not STAGE_ARTIFACTS.is_dir():
        raise HTTPException(status_code=503, detail="证据目录缺失")
    items = []
    for d in STAGE_ARTIFACTS.glob("DT5_DATA0019_report_no*"):
        if not d.is_dir():
            continue
        match = re.search(r"report_no(\d+)", d.name)
        files = sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file())
        items.append({
            "编号": int(match.group(1)) if match else 0,
            "目录": d.name,
            "标题": _report_title(d),
            "文件数": len(files),
            "文件": files[:20],
        })
    items.sort(key=lambda r: r["编号"])
    if q:
        items = [r for r in items if q in (r["标题"] or "") or q in r["目录"]]
    page_items, meta = _paginate(items, page, size)
    return {"count": len(items), "分页": meta, "items": page_items}
