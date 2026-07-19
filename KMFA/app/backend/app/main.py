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


def _quality_grade_short() -> str:
    """页眉质量等级取自 data_pipeline 事实，而非硬编码。

    PROD.0004 要求「数据来自 facts」——原实现把 "Q3" 写死在代码里，
    facts 一旦升级（如 Q3→Q4）页眉会静默说谎。
    """
    pipeline = json.loads((FACTS / "data_pipeline.json").read_text(encoding="utf-8"))
    full = str(pipeline.get("quality_grade_current") or "").strip()
    return full.split("（")[0].strip() or full or "未知"


@app.get("/api/状态")
def status():
    s = load_json(FACTS / "status.json")
    return {
        "版本": s.get("version"), "阶段": s.get("stage"), "当前任务": s.get("task"),
        "真实进度": s.get("real_progress"),
        "页眉": {
            "质量等级": _quality_grade_short(),
            "报告等级": s.get("report_grade"),
            "GO状态": s.get("business_verdict"),
        },
    }


@app.get("/api/我在哪")
def where_am_i():
    """首页「我在哪」（PROD.0004）——与 `文档/00_我在哪.md` 渲染件**同源**。

    同吃 machine/facts 的 status.json / blockers.json / roadmap.json（渲染件的事实源
    在其文件头已声明），确保页面与渲染件字字对得上；验收即以该渲染件为基准。
    """
    status_facts = load_json(FACTS / "status.json")
    blockers = load_json(FACTS / "blockers.json")
    roadmap = load_json(FACTS / "roadmap.json")
    pipeline = load_json(FACTS / "data_pipeline.json")
    stages = roadmap.get("stages", []) if isinstance(roadmap, dict) else []
    blocker_rows = blockers if isinstance(blockers, list) else []
    return {
        "更新于": status_facts.get("rendered_at"),
        "当前状态": {
            "版本": status_facts.get("version"),
            "阶段": status_facts.get("stage"),
            "分期": status_facts.get("phase"),
            "任务": status_facts.get("task"),
            "进度": status_facts.get("real_progress"),
            "报告可信度": status_facts.get("report_grade"),
            "业务结论": status_facts.get("business_verdict"),
            "证据状态": status_facts.get("evidence_status"),
            "卡住件数": len(blocker_rows),
        },
        "卡住的事": blocker_rows,
        "路线图": {"合计": len(stages), "阶段": stages},
        "数据面": {
            "质量等级": pipeline.get("quality_grade_current"),
            "截止批次": pipeline.get("data_as_of_batch"),
        },
        "同源": "machine/facts/{status,blockers,roadmap}.json —— 与 文档/00_我在哪.md 同源",
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


SOURCE_MATRIX_PATH = KMFA / "metadata" / "sources" / "source_check_matrix.jsonl"
AGING_MANIFEST_PATH = KMFA / "metadata" / "reports" / "collection_receivable_aging_manifest.json"
AGING_LANES_PATH = KMFA / "metadata" / "reports" / "collection_receivable_aging_source_lanes.jsonl"
AGING_ITEMS_PATH = KMFA / "metadata" / "reports" / "collection_receivable_aging_priority_items.jsonl"
AGING_STAGING_TABLES = ("receivable_aging", "collection", "v_collection_authoritative")


def _cents_to_yuan(cents: Any) -> str | None:
    """整数分 → 元字符串。**全程整数运算，禁用浮点**（金额纪律：恒整数分）。"""
    if cents is None:
        return None
    value = int(cents)
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    return f"{sign}{abs_value // 100:,}.{abs_value % 100:02d}"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


@app.get("/api/账龄回款")
def receivable_aging():
    """应收账龄与回款视图（PROD.0010）——`collection_receivable_aging` 真数据化。

    数据分两层，**如实区分**：
    · **对账层（真数字）**：断言表 collection 域逐月 delta_cents 与 receivable_aging 恒等式，
      皆为已核到分的真实结果，直接呈现。
    · **v014 账龄结构层（值被阻断）**：source_lanes 全部 `data_status=structure_available_values_blocked`，
      priority_items 只有 `public_aging_bucket_ref_00x` 匿名指针、`collection_action_allowed=false`
      ——**故本页不产出账龄分桶金额**，只报结构与阻断状态。
    """
    rows = _load_assertions()
    collection_rows = [r for r in rows if str(r.get("domain")) == "collection"]
    aging_rows = [r for r in rows if str(r.get("domain")) == "receivable_aging"]

    monthly = []
    for r in sorted(collection_rows, key=lambda x: str(x.get("period"))):
        delta = r.get("delta_cents")
        monthly.append({
            "断言": r.get("assertion_id"),
            "口径": r.get("metric"),
            "期间": r.get("period"),
            "差异分": delta,
            "差异元": _cents_to_yuan(delta),
            "状态": r.get("status"),
            "证据": r.get("evidence_ref"),
        })
    zero = [m for m in monthly if m["差异分"] == 0]
    open_rows = [m for m in monthly if str(m["状态"]) == "analyzed_open"]
    with_delta = [m for m in monthly if isinstance(m["差异分"], int) and m["差异分"] != 0]
    largest = max(with_delta, key=lambda m: abs(m["差异分"]), default=None)

    manifest = json.loads(AGING_MANIFEST_PATH.read_text(encoding="utf-8")) if AGING_MANIFEST_PATH.exists() else {}
    lanes = _read_jsonl(AGING_LANES_PATH)
    items = _read_jsonl(AGING_ITEMS_PATH)
    pipeline = load_json(FACTS / "data_pipeline.json")
    staging = pipeline.get("staging_tables") or {}

    return {
        "回款对账": {
            "月数": len(monthly),
            "零分差月数": len(zero),
            "未闭月数": len(open_rows),
            "最大差异": ({"期间": largest["期间"], "差异分": largest["差异分"], "差异元": largest["差异元"]}
                         if largest else None),
            "逐月": monthly,
        },
        "账龄恒等式": [
            {"断言": r.get("assertion_id"), "口径": r.get("metric"), "快照": r.get("period"),
             "差异分": r.get("delta_cents"), "状态": r.get("status"), "证据": r.get("evidence_ref")}
            for r in aging_rows
        ],
        "账龄结构层": {
            "公式版本": manifest.get("formula_version"),
            "报告版本": manifest.get("report_version"),
            "生成于": manifest.get("generated_at"),
            "源泳道数": len(lanes),
            "泳道数据状态": sorted({str(l.get("data_status")) for l in lanes}),
            "优先事项数": len(items),
            "允许作经营依据": bool((manifest.get("quality_gate") or {}).get("business_decision_basis_allowed")),
            "允许催收动作": all(not i.get("collection_action_allowed") for i in items) is False,
            "限制": manifest.get("limitations", []),
        },
        "派生层规模": [
            {"表": name, "行数": (staging.get(name) or {}).get("rows")}
            for name in AGING_STAGING_TABLES if name in staging
        ],
        "诚实边界": ("对账层为已核到分的真实结果；账龄分桶金额在 v014 结构层仍 values_blocked，"
                     "本页不产出分桶金额，亦不构成催收依据。"),
    }


COST_MANIFEST_PATH = KMFA / "metadata" / "reports" / "project_cost_fact_layer_manifest.json"
COST_RECORDS_PATH = KMFA / "metadata" / "lineage" / "project_cost_fact_records.jsonl"
# 成本归集会吃的派生层表（下钻用；行数取自 data_pipeline 事实）
COST_STAGING_TABLES = ("expense_lines", "kingdee_ledger", "kingdee_voucher", "goods_movement",
                       "invoice_lines", "collection", "receivable_aging")


@app.get("/api/项目成本")
def project_cost():
    """项目成本页（PROD.0006）——与 `project_cost_fact_layer` 输出一致。

    **诚实边界（务必保留）**：事实层当前
    `fact_layer_status = structural_fact_layer_blocked_for_formal_calculation`，
    全部记录 `amount_calculation_performed=false`、`calculation_status=blocked_pending_quality_resolution`
    ——**金额从未计算**，因其依赖 A0 权威基准，而 A0 被 BLK-001（Owner 约 273 行字段确认）阻塞。
    故本接口**不产出任何毛利/现金毛利数字**，只如实报结构、槽位与阻塞链。

    公开面只出 sha256 与 `private_ref://` 指针：明文值不在本仓
    （`metric_values_public_committed=false`），符合任务包「私面数据只在本机 App 显示、不入导出默认」。
    """
    if not COST_MANIFEST_PATH.exists() or not COST_RECORDS_PATH.exists():
        raise HTTPException(status_code=503, detail="项目成本事实层产物缺失")
    manifest = json.loads(COST_MANIFEST_PATH.read_text(encoding="utf-8"))
    records = [json.loads(l) for l in COST_RECORDS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    blockers = load_json(FACTS / "blockers.json")
    pipeline = load_json(FACTS / "data_pipeline.json")
    staging = pipeline.get("staging_tables") or {}

    rows = []
    for rec in records:
        cost_slots = rec.get("cost_category_slots") or []
        metric_slots = rec.get("metric_slots") or []
        rows.append({
            "记录号": rec.get("fact_record_id"),
            "项目实体": rec.get("project_entity_ref"),
            "计算状态": rec.get("calculation_status"),
            "金额已计算": bool(rec.get("amount_calculation_performed")),
            "允许正式计算": bool(rec.get("formal_calculation_allowed")),
            "成本槽位": len(cost_slots),
            "指标槽位": len(metric_slots),
            "已登记哈希": len(rec.get("cost_category_hash_refs") or {}) + len(rec.get("metric_hash_refs") or {}),
            "明文已公开": bool(rec.get("metric_values_public_committed")),
            "证据": rec.get("evidence_ref"),
        })

    calculated = sum(1 for r in rows if r["金额已计算"])
    return {
        "事实层": {
            "状态": manifest.get("fact_layer_status"),
            "公式版本": manifest.get("formula_version"),
            "映射版本": manifest.get("mapping_version"),
            "生成于": manifest.get("generated_at"),
            "记录数": len(rows),
            "已算金额记录数": calculated,
        },
        "必需结构": {
            "成本类别": manifest.get("required_cost_categories", []),
            "事实指标": manifest.get("required_fact_metrics", []),
        },
        "记录": rows,
        "阻塞链": {
            "直接原因": "A0 权威基准未从真实来源生成 → 事实层不允许正式计算",
            "基准引用": (records[0].get("authority_baseline_ref") if records else None),
            "根阻塞": [
                {"编号": b.get("id"), "内容": b.get("内容"), "只有Owner可解": b.get("owner_only"),
                 "已卡": b.get("首次登记")}
                for b in (blockers if isinstance(blockers, list) else [])
            ],
        },
        "可下钻派生层": [
            {"表": name, "行数": (staging.get(name) or {}).get("rows")}
            for name in COST_STAGING_TABLES if name in staging
        ],
        "诚实边界": ("毛利/现金毛利在 A0 就位前无法计算，本页不产出任何金额数字；"
                     "明文值仅存私有面（private_ref），公开面只有 sha256 指纹。"),
    }


@app.get("/api/源检查")
def source_check():
    """源检查板（PROD.0005）：矩阵协议状态 + 真实源覆盖矩阵 + 新鲜度 stale 提示。

    诚实边界：正式源检查矩阵 `metadata/sources/source_check_matrix.jsonl` 目前只有
    protocol_header、**零已提交源行**（S03-P2 协议定义态，源行由 file_import_register 产出）。
    本接口如实报出该状态，**不编造 entity_ref / account_ref 等取不到的维度值充数**。
    覆盖矩阵取自血缘图 + data_pipeline 事实（皆为机械生成面）；新鲜度由
    `data_as_of_batch` 与血缘节点批次比对得出——全程不读 raw inbox。
    """
    if not LINEAGE_PATH.exists():
        raise HTTPException(status_code=503, detail="血缘图缺失")
    graph = yaml.safe_load(LINEAGE_PATH.read_text(encoding="utf-8")) or {}
    pipeline = json.loads((FACTS / "data_pipeline.json").read_text(encoding="utf-8"))

    header: dict[str, Any] = {}
    committed_rows = 0
    if SOURCE_MATRIX_PATH.exists():
        for line in SOURCE_MATRIX_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("record_type") == "protocol_header":
                header = row
            else:
                committed_rows += 1

    nodes = graph.get("nodes") or []
    matrix: dict[str, dict[str, int]] = {}
    batches: set[str] = set()
    for node in nodes:
        source = str(node.get("domain") or "未标注")
        state = str(node.get("status") or "已抽取")
        matrix.setdefault(source, {})
        matrix[source][state] = matrix[source].get(state, 0) + 1
        if node.get("batch"):
            batches.add(str(node["batch"]))

    states = sorted({s for row in matrix.values() for s in row})
    as_of = str(pipeline.get("data_as_of_batch") or "")
    newer = sorted(b for b in batches if as_of and b > as_of)

    return {
        "矩阵协议": {
            "schema": header.get("schema_version"),
            "阶段": header.get("stage_phase"),
            "状态": header.get("status"),
            "必需维度": header.get("required_dimensions", []),
            "允许状态": header.get("allowed_statuses", []),
            "已提交源行": committed_rows,
            "说明": "协议已定义；源行待 file_import_register 产出后提交（当前为零行，如实报出）",
        },
        "覆盖矩阵": {
            "源": sorted(matrix),
            "状态列": states,
            "行": [
                {"源": src, "合计": sum(matrix[src].values()), **{st: matrix[src].get(st, 0) for st in states}}
                for src in sorted(matrix)
            ],
            "资产合计": len(nodes),
        },
        "新鲜度": {
            "数据批次": as_of,
            "血缘批次": sorted(batches),
            "stale": bool(newer),
            "更新的批次": newer,
            "提示": ("发现比 data_as_of_batch 更新的批次，需重跑抽取→血缘→facts"
                     if newer else "无更新批次，覆盖面与事实批次一致"),
        },
        "派生层": {
            "表数": len(pipeline.get("staging_tables") or {}),
            "行合计": pipeline.get("staging_rows_total"),
            "质量等级": pipeline.get("quality_grade_current"),
        },
    }


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
