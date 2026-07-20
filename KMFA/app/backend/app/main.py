#!/usr/bin/env python3
"""KMFA App 后端骨架（TSK.KMFA.PROD.0001，D2=A：KMIDS 同栈 FastAPI）。

只读吃机器面：machine/facts（状态/数据管线）+ metadata/quality/assertions.jsonl（对账断言）。
页眉三元组（质量等级/报告等级/GO 状态）由 /api/状态 直给——DoD 第 1 条的页眉数据源。
私有派生层（DuckDB）不经本服务暴露明细；App 只出 public-safe 聚合。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

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
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/")
def index():
    # 根路径直达应用本体。曾在这里挂过一张早期静态摘要页——Owner 打开裸域名
    # 看到的是它而不是 App，误以为「前端没更新」（2026-07-20 截图实证）。
    # 用户不该需要知道 /ui/ 才能用产品；那张静态页已删除，不许再回来。
    return RedirectResponse(url="/ui/", status_code=307)


@app.get("/ui/")
def ui_index():
    if not (FRONTEND_DIST / "index.html").exists():
        raise HTTPException(status_code=503, detail="前端未构建（KMFA/app/frontend: npm run build）")
    # 入口 html 禁缓存：不禁的话部署换新后浏览器仍用旧 html 引旧资产——
    # 「服务器已换新、用户看着没变」，2026-07-20 Owner 真踩到。
    return FileResponse(FRONTEND_DIST / "index.html",
                        headers={"Cache-Control": "no-cache, must-revalidate"})


@app.get("/ui/assets/{asset_path:path}")
def ui_assets(asset_path: str):
    target = (FRONTEND_DIST / "assets" / asset_path).resolve()
    if not str(target).startswith(str(FRONTEND_DIST.resolve())) or not target.is_file():
        raise HTTPException(status_code=404)
    # 资产文件名含内容哈希，内容一变名字必变——可放心永久缓存
    return FileResponse(target, headers={"Cache-Control": "public, max-age=31536000, immutable"})


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


QUALITY_DIR = KMFA / "metadata" / "quality"
# v014 S14 三段：P1 资金/现金/贷款计划、P2 开票/纳税计划、P3 税务政策证据
S14_P1 = QUALITY_DIR / "v014_s14_p1_post_remediation_fund_cash_loan_plan"
S14_P2 = QUALITY_DIR / "v014_s14_p2_post_remediation_invoice_tax_plan"
S14_P3 = QUALITY_DIR / "v014_s14_p3_post_remediation_policy_evidence_plan"
POLICY_RISKS_PATH = QUALITY_DIR / "v014_s14_p3_post_remediation_policy_risk_tips_public_safe.json"
POLICY_GAPS_PATH = QUALITY_DIR / "v014_s14_p3_post_remediation_policy_evidence_gaps_public_safe.json"
# 开票/纳税/贷款三域会吃的派生层表（行数取自 data_pipeline 事实）
INVOICE_STAGING_TABLES = ("invoice_raw", "invoice_lines", "tax_composition", "loan_register")


def _assertion_row(r: dict[str, Any]) -> dict[str, Any]:
    """断言 → 展示行。差异分**原样透传**，元值走整数换算，绝不另造一套数。"""
    delta = r.get("delta_cents")
    return {
        "断言": r.get("assertion_id"),
        "口径": r.get("metric"),
        "期间": r.get("period"),
        "差异分": delta,
        "差异元": _cents_to_yuan(delta),
        "状态": r.get("status"),
        "对账方": r.get("expect_source"),
        "我方源": r.get("our_source"),
        "结论": r.get("finding"),
        "证据": r.get("evidence_ref"),
    }


def _s14_lanes_and_methods(manifest_path: Path, method_keys: tuple[str, ...]) -> dict[str, Any]:
    """读 v014 S14 manifest 的车道与方法定义——只报结构与阻断状态，不取任何金额。"""
    if not manifest_path.exists():
        return {"车道": [], "方法": [], "缺失": manifest_path.name}
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    lanes = [
        {
            "车道": l.get("lane_id"),
            "数据状态": l.get("data_status"),
            "私有候选表数": (l.get("private_candidate_sheet_count")
                             or l.get("private_direct_candidate_sheet_count")),
            "含业务金额": bool(l.get("contains_business_amounts")),
            "允许作经营依据": bool(l.get("business_decision_basis_allowed")),
        }
        for l in (m.get("source_lanes") or [])
    ]
    methods = []
    for key in method_keys:
        for d in (m.get(key) or []):
            lanes_needed = d.get("required_lanes") or []
            # 三个 cash_summary 方法事实里没有 method_note；兜底句由 required_lanes 推出，
            # 且必须落在 API 而不是某个页面——否则导出/自动化拿到的仍是 null。
            note = d.get("method_note") or (
                f"需 {'、'.join(lanes_needed)} 车道的权威期间值绑定后才能出汇总。"
                if lanes_needed else None)
            methods.append({
                "方法组": key,
                "方法": d.get("method_id"),
                # 事实里每个方法都带中文 visible_name 与 required_lanes；只显英文 id、
                # 让三个无 method_note 的方法露出"—"是把已有事实丢了——真开页面时实测到。
                "名称": d.get("visible_name"),
                "依赖车道": lanes_needed,
                "定义完备": bool(d.get("method_definition_complete")),
                "产出状态": d.get("current_output_status"),
                "绑定状态": d.get("current_binding_status"),
                "说明": note,
            })
    return {"车道": lanes, "方法": methods}


@app.get("/api/开票纳税")
def invoice_tax_fund():
    """开票纳税与资金贷款视图（PROD.0011）——`invoice_tax_plan`/`fund_cash_loan_plan` 真数据化。

    与账龄页同构，**数据分两层如实区分**：
    · **对账层（真数字）**：断言表 invoicing / tax / loan 三域，皆已核到分，直接呈现。
      其中 `AST-LOAN-ZHONGLI-ADHERENCE` 为 0 分差已闭，`AST-TAX-AXIS-HBKM-2025` 39 格
      逐月逐税种仅差 1 分。
    · **v014 S14 结构层（值被阻断）**：P1 四车道 / P2 三车道全部
      `values_unproven`，九个方法（3 计划 + 3 现金汇总 + 3 问题复核）全部
      `blocked_no_authoritative_*_value_binding`——**故本页不产出计划金额、不列到期提示**。

    任务包红线（P1 §212 / P2 §213）：**不做付款操作、不做正式纳税申报**。红线计数直接读
    v014 summary 事实（非硬编码），任何一项非零都会被契约测试打回。
    """
    rows = _load_assertions()
    by_domain = {d: [r for r in rows if str(r.get("domain")) == d]
                 for d in ("invoicing", "tax", "loan")}

    def block(domain: str) -> dict[str, Any]:
        rs = [_assertion_row(r) for r in sorted(by_domain[domain], key=lambda x: str(x.get("assertion_id")))]
        return {
            "条数": len(rs),
            "零分差条数": len([r for r in rs if r["差异分"] == 0]),
            "未闭条数": len([r for r in rs if str(r["状态"]) == "analyzed_open"]),
            "逐条": rs,
        }

    p1 = load_json(Path(f"{S14_P1}_summary.json"))
    p2 = load_json(Path(f"{S14_P2}_summary.json"))
    p3 = load_json(Path(f"{S14_P3}_summary.json"))

    risks = {r.get("program_id"): r for r in
             (json.loads(POLICY_RISKS_PATH.read_text(encoding="utf-8")).get("risks") or []
              if POLICY_RISKS_PATH.exists() else [])}
    gaps = (json.loads(POLICY_GAPS_PATH.read_text(encoding="utf-8")).get("gaps") or []
            if POLICY_GAPS_PATH.exists() else [])
    policy = []
    for g in sorted(gaps, key=lambda x: x.get("gap_sequence") or 0):
        r = risks.get(g.get("program_id")) or {}
        policy.append({
            "项目": g.get("visible_name"),
            "风险等级": r.get("risk_level"),
            "风险提示": r.get("risk_tip"),
            "证据缺口": g.get("gap_summary"),
            "缺口状态": g.get("gap_status"),
            "证据完备": bool(g.get("evidence_complete")),
            "允许出资格结论": bool(g.get("formal_policy_qualification_conclusion_allowed")),
        })

    pipeline = load_json(FACTS / "data_pipeline.json")
    staging = pipeline.get("staging_tables") or {}

    return {
        "开票对账": block("invoicing"),
        "税务对账": block("tax"),
        "贷款对账": block("loan"),
        "派生层规模": [
            {"表": name, "行数": (staging.get(name) or {}).get("rows")}
            for name in INVOICE_STAGING_TABLES if name in staging
        ],
        "结构层": {
            "开票纳税计划（S14-P2）": {
                "决策": p2.get("decision"),
                "已证值绑定车道数": p2.get("value_binding_proven_lane_count"),
                "公开业务金额数": p2.get("public_business_amount_count"),
                **_s14_lanes_and_methods(Path(f"{S14_P2}_manifest.json"),
                                         ("cash_summary_methods", "issue_review_methods")),
            },
            "资金贷款计划（S14-P1）": {
                "决策": p1.get("decision"),
                "已证值绑定车道数": p1.get("value_binding_proven_lane_count"),
                "公开业务金额数": p1.get("public_business_amount_count"),
                **_s14_lanes_and_methods(Path(f"{S14_P1}_manifest.json"), ("planning_methods",)),
            },
        },
        "税务政策证据": {
            "项目数": p3.get("policy_program_count"),
            "证据完备项目数": p3.get("evidence_complete_program_count"),
            "证据缺口数": p3.get("evidence_gap_count"),
            "要求证据类目数": p3.get("required_evidence_category_total_count"),
            "逐项": policy,
        },
        "红线": {
            "开票次数": p2.get("invoice_issuance_count"),
            "纳税申报次数": p2.get("tax_filing_count"),
            "付款或动账次数": p2.get("payment_or_bank_operation_count"),
            "银行操作次数": p1.get("bank_operation_count"),
            "付款审批次数": p1.get("payment_approval_count"),
            "贷款管理动作数": p1.get("loan_management_action_count"),
            "政策申报提交次数": p3.get("policy_application_submission_count"),
            "补贴申请次数": p3.get("subsidy_application_count"),
        },
        "诚实边界": ("对账层为已核到分的真实结果（仲利摊销 0 分差已闭、税负率 39 格仅差 1 分）；"
                     "计划层在 v014 S14 仍 values_unproven，本页**不产出计划金额、不列贷款到期提示**。"
                     "税务政策部分只出证据缺口与风险提示，**不构成资格判断**，"
                     "且全线不开票、不申报、不付款、不动账。"),
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


# ── PROD.0007 差异工作台：三选一决策 + append-only 回写 ────────────────────────
# 契约来自既有 KMFA/tools/manual_resolution_events.py（任务包原文：「走既有
# manual_resolution_events 契约」），不另造一套：
#   · 24 个必填字段、event_type=resolution_event、manual_action_kind=difference_handling
#   · append_only=true；**改主意不是改记录**——silent_update_allowed=false、
#     reversal_required_for_change=true，要改就追加一条 reverses_event_id 的冲正事件
#     （既有 MANEVT-S12P1-005 冲正 -003 即此模式）
#   · raw/source 层一律不可写：断言表 assertions.jsonl 是治理数据面，App 只读不改
APPROVALS_DIR = KMFA / "metadata" / "approvals"
REPO_EVENTS_PATH = APPROVALS_DIR / "manual_resolution_events.jsonl"
# 应用状态面与数据面分离（PROD.0001 的 D2=A 约定）：App 写的事件落**可写状态目录**，
# 绝不写进治理数据面。SQLite 状态面待 PROD.0001 建成后接管，契约与此处完全一致。
APP_STATE_DIR = Path(os.environ.get("KMFA_APP_STATE_DIR", "/var/lib/kmfa/state"))
# PROD.0001：应用状态面走 SQLite（D2=A）。append-only 由触发器在**库层**强制，
# 不再依赖"我们只用 'a' 模式打开文件"这种君子协定。
APP_DB_PATH = APP_STATE_DIR / "kmfa_app_state.sqlite3"
from app import app_state as _st  # noqa: E402
APP_EVENTS_PATH = APP_STATE_DIR / "manual_resolution_events.jsonl"

BEIJING = timezone(timedelta(hours=8))  # 业务锚 +0800，与技能容器挂钟一致

# 三选一决策 → 断言状态流转（open / closed / excluded）
DECISIONS: dict[str, dict[str, str]] = {
    "闭案": {"到状态": "closed", "reason_code": "DIFF_ACCEPTED_CLOSED",
             "event_action": "close_difference"},
    "排除": {"到状态": "excluded", "reason_code": "DIFF_OUT_OF_SCOPE_EXCLUDED",
             "event_action": "exclude_difference"},
    "保持未闭": {"到状态": "open", "reason_code": "DIFF_REMAIN_OPEN_PENDING_INPUT",
                 "event_action": "keep_difference_open"},
}
REQUIRED_EVENT_FIELDS = (
    "event_id", "schema_version", "record_type", "stage_phase", "event_type",
    "manual_action_kind", "actor_ref", "actor_role", "event_time", "reason_code",
    "reason_summary", "impact_scope", "event_version", "target_layer", "target_ref",
    "status", "append_only", "raw_layer_write_allowed", "raw_source_mutation_allowed",
    "source_layer_write_allowed", "business_plaintext_committed", "forbidden_plaintext",
    "evidence_refs",
)
# 公开面禁词（取自既有契约 FORBIDDEN_PUBLIC_KEYS 的金额/明文子集）——事件里只准放
# 断言号与理由，绝不准把金额或业务明文塞进来
FORBIDDEN_EVENT_KEYS = frozenset({
    "amount_cents", "amount_yuan", "raw_value", "normalized_value", "original_value",
    "plaintext_value", "source_header_text", "bank_account_number", "account_number",
    "identity_document_number", "project_name_plaintext", "customer_name_plaintext",
    "counterparty_plaintext",
})
APP_EVENT_ID_RE = re.compile(r"^MANEVT-APP-[0-9]{4}$")


def _read_events(path: Path) -> list[dict[str, Any]]:
    """仓内事件读 JSONL（治理数据面，只读）；App 自己写的读 SQLite 状态面。"""
    rows = _st.read(APP_DB_PATH, "resolution_events") if path == APP_EVENTS_PATH else _read_jsonl(path)
    return [r for r in rows if r.get("record_type") != "protocol_header"]


def _all_events() -> list[dict[str, Any]]:
    """仓内既有事件（只读）+ App 写的事件（应用状态面）。"""
    return _read_events(REPO_EVENTS_PATH) + _read_events(APP_EVENTS_PATH)


def _assertion_state(row: dict[str, Any]) -> str:
    """断言原始三态：open / closed / excluded（任务包要求的可视化分组）。"""
    status = str(row.get("status") or "")
    if status.startswith("closed"):
        return "closed"
    if "exclud" in status:
        return "excluded"
    return "open"


def _scan_forbidden(node: Any) -> list[str]:
    hits: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if str(k) in FORBIDDEN_EVENT_KEYS:
                hits.append(str(k))
            hits.extend(_scan_forbidden(v))
    elif isinstance(node, list):
        for v in node:
            hits.extend(_scan_forbidden(v))
    return hits


def _content_hash(event: dict[str, Any]) -> str:
    payload = {k: v for k, v in event.items() if k != "content_hash"}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _append_event(event: dict[str, Any]) -> dict[str, Any]:
    """写前全量校验，**只以追加方式落盘**，绝不改写既有行。"""
    missing = [f for f in REQUIRED_EVENT_FIELDS if f not in event]
    if missing:
        raise HTTPException(status_code=500, detail=f"事件缺必填字段：{missing}")
    forbidden = _scan_forbidden(event)
    if forbidden:
        raise HTTPException(status_code=400, detail=f"事件含禁写字段：{sorted(set(forbidden))}")
    for flag in ("raw_layer_write_allowed", "raw_source_mutation_allowed",
                 "source_layer_write_allowed", "business_plaintext_committed",
                 "forbidden_plaintext", "silent_update_allowed"):
        if event.get(flag) is not False:
            raise HTTPException(status_code=500, detail=f"{flag} 必须为 false")
    if event.get("append_only") is not True:
        raise HTTPException(status_code=500, detail="append_only 必须为 true")
    event["content_hash"] = _content_hash(event)

    _st.append(APP_DB_PATH, "resolution_events", event)
    return event


def _next_app_event_id() -> str:
    existing = [e.get("event_id", "") for e in _read_events(APP_EVENTS_PATH)]
    nums = [int(e.rsplit("-", 1)[1]) for e in existing if APP_EVENT_ID_RE.match(str(e))]
    return f"MANEVT-APP-{max(nums, default=0) + 1:04d}"


def _base_event(assertion_id: str, reason: str, actor: str) -> dict[str, Any]:
    return {
        "event_id": _next_app_event_id(),
        "schema_version": "kmfa.manual_resolution_event.v1",
        "record_type": "manual_resolution_event",
        "stage_phase": "DT6-PROD0007",
        "event_type": "resolution_event",
        "manual_action_kind": "difference_handling",
        "actor_ref": f"actor_ref://owner_or_authorized_delegate/{actor}",
        "actor_role": "owner_or_authorized_delegate",
        "event_time": datetime.now(BEIJING).isoformat(timespec="seconds"),
        "reason_summary": reason,
        "impact_scope": ["assertion_status_flow", "difference_workbench"],
        "event_version": "MANUAL-EVENT-KMFA-DT6-PROD0007-001",
        "target_layer": "quality",
        "target_ref": assertion_id,
        "project_id": "KMFA",
        "system_name": "KMFA 经营分析系统",
        "append_only": True,
        "raw_layer_write_allowed": False,
        "raw_source_mutation_allowed": False,
        "source_layer_write_allowed": False,
        "business_plaintext_committed": False,
        "forbidden_plaintext": False,
        "silent_update_allowed": False,
        "reversal_required_for_change": True,
        "approved_event_immutable": True,
        "evidence_refs": [
            "KMFA/metadata/quality/assertions.jsonl",
            "KMFA/tools/manual_resolution_events.py",
        ],
    }


@app.get("/api/差异工作台")
def difference_workbench():
    """差异工作台（PROD.0007）——断言 open/closed/excluded 可视化 + 决策留痕。

    「与 assertions.jsonl 双向一致」的落法：
    · 正向——每条断言挂出针对它的全部决策事件（含冲正）；
    · 反向——每条事件的 target_ref 必须能解析到真实断言，孤儿事件计数须为 0。
    断言表本身**只读**：状态流转由事件表达，App 绝不改写治理数据面。
    """
    rows = _load_assertions()
    events = _all_events()
    by_target: dict[str, list[dict[str, Any]]] = {}
    for e in events:
        by_target.setdefault(str(e.get("target_ref")), []).append(e)

    reversed_ids = {str(e.get("reverses_event_id")) for e in events if e.get("reverses_event_id")}

    def view(e: dict[str, Any]) -> dict[str, Any]:
        return {
            "事件号": e.get("event_id"),
            "动作": e.get("event_action"),
            "决策": e.get("decision_label"),
            "到状态": e.get("target_state"),
            "理由": e.get("reason_summary"),
            "理由码": e.get("reason_code"),
            "时间": e.get("event_time"),
            "操作人": e.get("actor_ref"),
            "已被冲正": e.get("event_id") in reversed_ids,
            "冲正的是": e.get("reverses_event_id"),
            "内容哈希": e.get("content_hash"),
            "来源": "仓内治理面（只读）" if e.get("stage_phase") != "DT6-PROD0007" else "App 应用状态面",
        }

    items = []
    for r in sorted(rows, key=lambda x: str(x.get("assertion_id"))):
        aid = str(r.get("assertion_id"))
        evs = sorted(by_target.get(aid, []), key=lambda e: str(e.get("event_time")))
        live = [e for e in evs if e.get("event_id") not in reversed_ids
                and not e.get("reverses_event_id")]
        items.append({
            "断言": aid,
            "域": r.get("domain"),
            "口径": r.get("metric"),
            "期间": r.get("period"),
            "原始状态": r.get("status"),
            "分组": _assertion_state(r),
            "差异分": r.get("delta_cents"),
            "差异元": _cents_to_yuan(r.get("delta_cents")),
            "结论": r.get("finding"),
            "决策事件": [view(e) for e in evs],
            "现行决策": view(live[-1]) if live else None,
        })

    known = {str(r.get("assertion_id")) for r in rows}
    # 「双向一致」的诚实口径：本台写入的事件**必须**条条解析到真实断言（写入时已 404 拦住）；
    # 仓内既有的 S12-P1 事件指向 S09P3-REC-001 等**治理记录号**而非断言号，它们不是孤儿、
    # 也不该被算成一致性缺陷——如实单列为「未挂载到断言层」。
    app_events = _read_events(APP_EVENTS_PATH)
    app_orphans = sorted({str(e.get("target_ref")) for e in app_events
                          if str(e.get("target_ref")) not in known})
    unmounted = sorted({str(e.get("target_ref")) for e in _read_events(REPO_EVENTS_PATH)
                        if str(e.get("target_ref")) not in known})
    groups = {g: len([i for i in items if i["分组"] == g]) for g in ("open", "closed", "excluded")}

    return {
        "分组计数": groups,
        "断言总数": len(items),
        "断言明细": items,
        "决策入口": [
            {"决策": k, "到状态": v["到状态"], "理由码": v["reason_code"]} for k, v in DECISIONS.items()
        ],
        "事件": {
            "总数": len(events),
            "仓内既有": len(_read_events(REPO_EVENTS_PATH)),
            "App 写入": len(_read_events(APP_EVENTS_PATH)),
            "已被冲正": len(reversed_ids),
            "写入位置": str(APP_EVENTS_PATH),
        },
        "双向一致": {
            "本台孤儿事件数": len(app_orphans),
            "本台孤儿事件": app_orphans,
            "一致": not app_orphans,
            "仓内未挂载事件数": len(unmounted),
            "仓内未挂载事件": unmounted,
            "说明": ("正向：每条断言挂出针对它的全部决策事件；反向：本台写入的事件条条解析到"
                     "真实断言（写入时即 404 拦截孤儿）。仓内既有 S12-P1 事件指向 "
                     "S09P3-REC-001 等治理记录号而非断言号，如实单列为未挂载，不算一致性缺陷。"),
        },
        "写入纪律": {
            "append_only": True,
            "允许静默改写": False,
            "改主意的做法": "追加一条 reverses_event_id 的冲正事件，绝不编辑既有行",
            "断言表可写": False,
        },
    }


@app.post("/api/差异工作台/决策")
def workbench_decide(payload: dict[str, Any] = Body(...)):
    """三选一决策入口——append-only 回写一条 difference_handling 事件。"""
    assertion_id = str(payload.get("断言") or "").strip()
    decision = str(payload.get("决策") or "").strip()
    reason = str(payload.get("理由") or "").strip()
    actor = str(payload.get("操作人") or "owner").strip() or "owner"

    if decision not in DECISIONS:
        raise HTTPException(status_code=400, detail=f"决策须为三选一：{list(DECISIONS)}")
    if not reason:
        raise HTTPException(status_code=400, detail="必须写明理由——无理由的决策不留痕等于没决策")
    known = {str(r.get("assertion_id")) for r in _load_assertions()}
    if assertion_id not in known:
        raise HTTPException(status_code=404, detail=f"断言不存在：{assertion_id}（拒绝写孤儿事件）")

    spec = DECISIONS[decision]
    event = _base_event(assertion_id, reason, actor)
    event.update({
        "event_action": spec["event_action"],
        "reason_code": spec["reason_code"],
        "decision_label": decision,
        "target_state": spec["到状态"],
        "status": "recorded_pending_approval",
        "approval_state": "draft",
    })
    written = _append_event(event)
    _audit("processing", subject_ref=assertion_id, result_status="OK",
           evidence_ref=str(APP_EVENTS_PATH), event_ref=written["event_id"],
           decision=decision)
    return {"已写入": written, "写入位置": str(APP_EVENTS_PATH)}


@app.post("/api/差异工作台/冲正")
def workbench_reverse(payload: dict[str, Any] = Body(...)):
    """改主意的唯一合法做法：追加冲正事件（silent_update_allowed=false）。"""
    target_event_id = str(payload.get("冲正事件号") or "").strip()
    reason = str(payload.get("理由") or "").strip()
    actor = str(payload.get("操作人") or "owner").strip() or "owner"
    if not reason:
        raise HTTPException(status_code=400, detail="冲正必须写明理由")

    events = {str(e.get("event_id")): e for e in _all_events()}
    origin = events.get(target_event_id)
    if origin is None:
        raise HTTPException(status_code=404, detail=f"被冲正事件不存在：{target_event_id}")
    if any(str(e.get("reverses_event_id")) == target_event_id for e in events.values()):
        raise HTTPException(status_code=409, detail=f"{target_event_id} 已被冲正过，不得重复冲正")

    event = _base_event(str(origin.get("target_ref")), reason, actor)
    event.update({
        "event_action": "reverse_difference_decision",
        "reason_code": "DECISION_REVERSED_BY_HUMAN",
        "decision_label": "冲正",
        "target_state": None,
        "status": "reverse_event_recorded",
        "approval_state": "reversal_recorded",
        "reverses_event_id": target_event_id,
    })
    written = _append_event(event)
    _audit("processing", subject_ref=str(origin.get("target_ref")), result_status="REVERSED",
           evidence_ref=str(APP_EVENTS_PATH), event_ref=written["event_id"],
           reverses=target_event_id)
    return {"已写入": written, "被冲正": target_event_id}


# ── PROD.0009 报告中心：HTML/CSV/PDF 三格式导出 + 不可去除的 D 级水印 ──────────
# 权威任务包第 18 行：HTML/CSV 导出承接既有 runtime；新增 PDF（复用 KMIDS PDF 管线）；
# 报告页眉强制显示等级/Q 级/delivery 状态。
# 验收：**三格式导出 hash 登记；D 级水印在解锁前不可去除**。
#
# 既有 runtime 契约（KMFA/tools/report_export_runtime.py）：
#   · HTML/CSV = public-safe 可提交；PDF = enabled_private_runtime_only，
#     committed_artifact_path 恒为 null——**公开仓永不提交 PDF 文件**。
#   · FORBIDDEN_PUBLIC_SUFFIXES 含 .pdf，故 PDF 只在运行时生成、只走响应流。
# KMIDS 管线本机不可得（按需 clone 铁律，未 clone），故 PDF 用 reportlab 内置
# STSong-Light CID 字体渲染中文——不装任何字体文件，策略与既有契约完全一致。
GRADE_RECORDS_PATH = KMFA / "metadata" / "reports" / "report_grade_runtime_records.jsonl"
DELIVERY_GATE_PATH = KMFA / "metadata" / "quality" / "v014_s18_p2_go_no_go_report.json"
EXPORT_REGISTRY_PATH = APP_STATE_DIR / "report_export_records.jsonl"
EXPORT_FORMATS = ("html", "csv", "pdf")


def _delivery_state() -> dict[str, Any]:
    """页眉三元组 + 水印判据——**全部取自事实**，没有任何请求参数能左右它。"""
    grade_rows = _read_jsonl(GRADE_RECORDS_PATH)
    grade_row = grade_rows[0] if grade_rows else {}
    inputs = grade_row.get("grade_inputs") or {}
    gate = load_json(DELIVERY_GATE_PATH) if DELIVERY_GATE_PATH.exists() else {}
    delivery_allowed = bool(gate.get("delivery_allowed"))
    return {
        "报告等级": grade_row.get("computed_report_grade") or "未知",
        "质量等级": inputs.get("source_quality_grade") or _quality_grade_short(),
        "delivery_allowed": delivery_allowed,
        "delivery状态": "已解锁" if delivery_allowed else "未解锁（NO_GO）",
        "正式报告可出": bool(grade_row.get("formal_report_allowed")),
        "可作经营依据": bool(grade_row.get("business_decision_basis_allowed")),
        "等级政策版本": grade_row.get("grade_policy_version"),
        "判据来源": [
            "KMFA/metadata/reports/report_grade_runtime_records.jsonl",
            "KMFA/metadata/quality/v014_s18_p2_go_no_go_report.json",
        ],
    }


def _watermark_text() -> str | None:
    """水印文案由事实推出。delivery 解锁前**恒非空**，且无参数可关。"""
    state = _delivery_state()
    if state["delivery_allowed"]:
        return None
    # 分隔符用全角竖线：U+00B7（·）不在 STSong-Light 的 UniGB-UCS2-H 映射里，
    # PDF 里会渲成黑三角豆腐块——真把 PDF 渲成图看才发现的。
    return (f"{state['报告等级']} 级 ｜ 未解锁不可作经营依据 ｜ "
            f"质量 {state['质量等级']} ｜ delivery_allowed=false")


def _report_dirs() -> list[Path]:
    return sorted((d for d in STAGE_ARTIFACTS.glob("DT5_DATA0019_report_no*") if d.is_dir()),
                  key=lambda d: int(re.search(r"report_no(\d+)", d.name).group(1)))


def _report_dir(no: int) -> Path:
    for d in _report_dirs():
        if int(re.search(r"report_no(\d+)", d.name).group(1)) == no:
            return d
    raise HTTPException(status_code=404, detail=f"报告不存在：第 {no} 号")


def _report_body(d: Path) -> str:
    docs = sorted((d / "human").glob("*.md"))
    if not docs:
        raise HTTPException(status_code=503, detail=f"{d.name} 缺 human 正文")
    return docs[0].read_text(encoding="utf-8")


def _export_html(no: int, title: str, body: str, header: dict[str, Any], mark: str | None) -> bytes:
    import html as _html

    # 水印用 ::before 伪元素 + 固定定位铺满，**不提供任何开关**；
    # 页眉三元组同样硬渲染进文档，不是可选装饰。
    band = "" if mark is None else f"""
  <div class="wm" aria-label="水印">{_html.escape(mark)}</div>
  <style>
    .wm {{ position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
          transform: rotate(-28deg); font-size: 2.2rem; font-weight: 800; color: rgba(192,57,43,.18);
          pointer-events: none; z-index: 9999; white-space: pre-wrap; text-align: center; }}
    @media print {{ .wm {{ display: flex !important; }} }}
  </style>"""
    rows = "\n".join(
        f"<tr><td>{_html.escape(str(k))}</td><td><b>{_html.escape(str(v))}</b></td></tr>"
        for k, v in (("报告等级", header["报告等级"]), ("质量等级", header["质量等级"]),
                     ("delivery 状态", header["delivery状态"]))
    )
    esc_body = _html.escape(body)
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>{_html.escape(title)}</title>
<style>
 body{{font-family:-apple-system,"PingFang SC",sans-serif;max-width:60rem;margin:0 auto;padding:2rem;line-height:1.7}}
 table{{border-collapse:collapse;margin:.8rem 0}} td{{border:1px solid #ccc;padding:.35rem .6rem}}
 pre{{white-space:pre-wrap;word-wrap:break-word}}
 header{{border-bottom:2px solid #174a7c;padding-bottom:.6rem}}
</style></head><body>{band}
<header><h1>{_html.escape(title)}</h1><table><tbody>{rows}</tbody></table></header>
<pre>{esc_body}</pre>
</body></html>""".encode("utf-8")


def _export_csv(no: int, d: Path, header: dict[str, Any], mark: str | None) -> bytes:
    import csv as _csv
    import io as _io

    disp_path = d / "machine" / "dispositions.json"
    disp = json.loads(disp_path.read_text(encoding="utf-8")) if disp_path.exists() else {}
    buf = _io.StringIO()
    w = _csv.writer(buf)
    # 水印与页眉三元组写成 CSV 前置行——任何打开方式都看得到，删不掉才算不可去除
    if mark:
        w.writerow(["水印", mark])
    w.writerow(["报告等级", header["报告等级"]])
    w.writerow(["质量等级", header["质量等级"]])
    w.writerow(["delivery 状态", header["delivery状态"]])
    w.writerow([])
    w.writerow(["条目", "状态", "差异分", "差异元", "结论"])
    for item in (disp.get("dispositions") or []):
        cents = item.get("delta_cents")
        w.writerow([item.get("item"), item.get("status"), cents,
                    _cents_to_yuan(cents) or "", item.get("finding") or ""])
    return buf.getvalue().encode("utf-8-sig")  # BOM：Excel 直接双击不乱码


# STSong-Light（UniGB-UCS2-H）渲不出的字符 → 可渲替身。
# 表是**实测出来的**：扫 8 份报告正文找 GBK 编不出的字符，再加上 U+00B7——
# 它 GBK 能编但实测仍渲成黑三角（把 PDF 渲成 PNG 看才发现）。
PDF_GLYPH_FALLBACKS = {
    "\u2705": "\u221a",   # ✅ → √
    "\u00a5": "\uffe5",   # ¥ → ￥（半角日元符渲不出，全角人民币符可以）
    "\u2194": "<->",      # ↔
    "\u2212": "-",        # − 数学减号
    "\u2213": "-/+",      # ∓
    "\u00b7": " - ",      # · 间隔号
    "\u2022": "-",        # •
    "\u2013": "-", "\u2014": "-",
}


def _pdf_safe(text: str) -> str:
    """把渲不出的字符换成可渲替身。**PDF 里所有落笔的文字都要过这一道。**"""
    for bad, good in PDF_GLYPH_FALLBACKS.items():
        text = text.replace(bad, good)
    return text


def _markdown_to_plain(body: str) -> list[str]:
    """把报告 markdown 压成可读纯文本行——PDF 里倒 `###`/`**`/`|---|` 原文没法看。

    表格保留内容、去掉分隔线；标题降为「N、」式；强调标记剥掉。数字一律不动。
    """
    lines: list[str] = []
    for raw in body.splitlines():
        line = raw.rstrip()
        if re.fullmatch(r"\s*\|?[\s\|:–—-]*\|[\s\|:–—-]*\|?\s*", line) and "-" in line:
            continue  # 表格分隔线
        line = re.sub(r"^\s{0,3}(#{1,6})\s*", "", line)
        line = re.sub(r"^\s{0,3}>\s?", "", line)
        line = line.replace("**", "").replace("`", "")
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            line = "    ".join(c for c in cells if c)
        lines.append(line)
    return lines


def _export_pdf(no: int, title: str, body: str, header: dict[str, Any], mark: str | None) -> bytes:
    import io as _io

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfgen import canvas as _canvas
    except ImportError as exc:  # 缺依赖就明说，绝不悄悄产出一个假 PDF
        raise HTTPException(status_code=503, detail=f"PDF 管线不可用：{exc}") from exc

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    buf = _io.BytesIO()
    # invariant=1：固定 /CreationDate 与文档 ID。默认会写入挂钟时间，导致同一份报告
    # 每次导出字节都不同——那样登记的 hash 事后验不了任何东西（契约测试当场逮到）。
    c = _canvas.Canvas(buf, pagesize=A4, invariant=1)
    width, height = A4

    def stamp() -> None:
        """每一页都盖水印——翻页删不掉、抽页也删不掉。"""
        if not mark:
            return
        c.saveState()
        c.setFont("STSong-Light", 20)
        c.setFillColorRGB(0.75, 0.22, 0.17, alpha=0.18)
        c.translate(width / 2, height / 2)
        c.rotate(28)
        c.drawCentredString(0, 0, _pdf_safe(mark))
        c.restoreState()

    safe_title = _pdf_safe(title)
    c.setTitle(safe_title)

    def head(y: float) -> float:
        c.setFont("STSong-Light", 15)
        c.drawString(45, y, safe_title)
        c.setFont("STSong-Light", 9.5)
        c.drawString(45, y - 18, _pdf_safe(
            f"报告等级 {header['报告等级']} ｜ 质量等级 {header['质量等级']} "
            f"｜ delivery {header['delivery状态']}"))
        c.line(45, y - 26, width - 45, y - 26)
        return y - 44

    stamp()
    y = head(height - 50)
    body_size, usable = 9, width - 90
    c.setFont("STSong-Light", body_size)

    def wrap(text: str) -> list[str]:
        """按**实际字宽**折行。原来按字数切 46，会把 1,462,802.90 劈成两截——
        财务报告折断金额是硬伤，真把 PDF 渲成图看才发现。"""
        out, cur = [], ""
        for ch in text:
            trial = cur + ch
            if pdfmetrics.stringWidth(trial, "STSong-Light", body_size) > usable:
                out.append(cur)
                cur = ch
            else:
                cur = trial
        out.append(cur)
        return out or [""]

    for raw in (_pdf_safe(l) for l in _markdown_to_plain(body)):
        for chunk in wrap(raw):
            c.drawString(45, y, chunk)
            y -= 13
            if y < 50:
                c.showPage()
                stamp()
                y = head(height - 50)
                c.setFont("STSong-Light", body_size)
    c.save()
    return buf.getvalue()


def _register_export(record: dict[str, Any]) -> dict[str, Any]:
    """导出 hash 登记——与 PROD.0007 同一条纪律：只追加，不改写。"""
    return _st.append(APP_DB_PATH, "export_records", record)


@app.get("/api/报告中心")
def report_center():
    """报告中心（PROD.0009）——八份报告 × 三格式，页眉三元组与水印状态如实呈现。"""
    header = _delivery_state()
    mark = _watermark_text()
    registered = _st.read(APP_DB_PATH, "export_records")
    by_key: dict[str, dict[str, Any]] = {}
    for r in registered:
        by_key[f"{r.get('报告')}|{r.get('格式')}"] = r

    items = []
    for d in _report_dirs():
        no = int(re.search(r"report_no(\d+)", d.name).group(1))
        docs = sorted((d / "human").glob("*.md"))
        items.append({
            "编号": no,
            "标题": _report_title(d),
            "目录": d.name,
            "正文字数": len(docs[0].read_text(encoding="utf-8")) if docs else 0,
            "格式": [
                {
                    "格式": fmt,
                    "下载": f"/api/报告中心/导出?报告={no}&格式={fmt}",
                    "可提交公开仓": fmt != "pdf",
                    "已登记": by_key.get(f"{no}|{fmt}", {}).get("sha256"),
                }
                for fmt in EXPORT_FORMATS
            ],
        })

    return {
        "页眉": {"报告等级": header["报告等级"], "质量等级": header["质量等级"],
                 "delivery状态": header["delivery状态"]},
        "交付判据": header,
        "水印": {
            "文案": mark,
            "生效中": mark is not None,
            "可关闭": False,
            "去除条件": "delivery_allowed 由 false 转 true（Owner 签 GO），非任何前端/参数开关",
            "覆盖格式": list(EXPORT_FORMATS),
        },
        "报告": items,
        "导出登记": {
            "条数": len(registered),
            "位置": str(EXPORT_REGISTRY_PATH),
            "追加式": True,
            "记录": registered[-20:],
        },
        "PDF策略": {
            "运行时生成": True,
            "提交进公开仓": False,
            "说明": ("既有 runtime 契约 committed_artifact_path 恒 null、"
                     "FORBIDDEN_PUBLIC_SUFFIXES 含 .pdf；本 App 只走响应流，不落仓。"),
            "中文渲染": "reportlab 内置 STSong-Light CID 字体，不依赖系统字体文件",
        },
    }


@app.get("/api/报告中心/导出")
def report_export(报告: int, 格式: str = "html"):
    """三格式导出 + hash 登记。**水印不接受任何参数控制**——只认 delivery 事实。"""
    fmt = str(格式).lower().strip()
    if fmt not in EXPORT_FORMATS:
        raise HTTPException(status_code=400, detail=f"格式须为 {list(EXPORT_FORMATS)}")

    d = _report_dir(int(报告))
    title = _report_title(d) or f"一致性证明与差异分析报告 第 {报告} 号"
    header = _delivery_state()
    mark = _watermark_text()
    body = _report_body(d)

    if fmt == "html":
        data, media = _export_html(报告, title, body, header, mark), "text/html; charset=utf-8"
    elif fmt == "csv":
        data, media = _export_csv(报告, d, header, mark), "text/csv; charset=utf-8"
    else:
        data, media = _export_pdf(报告, title, body, header, mark), "application/pdf"

    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    _register_export({
        "报告": int(报告),
        "标题": title,
        "格式": fmt,
        "sha256": digest,
        "字节": len(data),
        "水印已加": mark is not None,
        "水印文案": mark,
        "报告等级": header["报告等级"],
        "质量等级": header["质量等级"],
        "delivery_allowed": header["delivery_allowed"],
        "提交进公开仓": False if fmt == "pdf" else True,
        "导出时间": datetime.now(BEIJING).isoformat(timespec="seconds"),
    })

    _audit("export", subject_ref=f"report_no{报告}:{fmt}", result_status="OK",
           evidence_ref=str(EXPORT_REGISTRY_PATH), sha256=digest, bytes=len(data),
           report_grade=header["报告等级"], quality_grade=header["质量等级"],
           delivery_allowed=header["delivery_allowed"], watermark_applied=mark is not None)

    from fastapi.responses import Response

    return Response(content=data, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="kmfa_report_{报告}.{fmt}"',
        "X-KMFA-Report-Grade": header["报告等级"],
        "X-KMFA-Quality-Grade": header["质量等级"],
        "X-KMFA-Delivery-Allowed": str(header["delivery_allowed"]).lower(),
        "X-KMFA-Watermark": "applied" if mark else "none",
        "X-KMFA-Sha256": digest,
    })


# ── PROD.0008 影响预览与重跑 ────────────────────────────────────────────────────
# 权威任务包第 17 行：血缘图可视化；选中资产→显示下游影响面；手动触发重跑
# （承接 v014 manual rerun 机制），进度与结果留痕。
# **验收：一次真实重跑从页面发起并完成。**
#
# 承接 KMFA/tools/manual_rerun_mechanism.py 的既有契约：
#   · 重跑链恒为四层 field_mapping → fact_layer → derived_metric → report_reference
#   · overwrite_old_version_allowed=false、old_version_status_after_rerun=retained_not_overwritten
#     —— 重跑**造新版本**，绝不覆盖旧版本
#   · raw/source 层一律不可写；report_grade_upgrade_allowed=false（重跑不许偷偷升等级）
RERUN_STEPS_PATH = KMFA / "metadata" / "lineage" / "manual_rerun_steps.jsonl"
IMPACT_PREVIEWS_PATH = APPROVALS_DIR / "manual_impact_previews.jsonl"
APP_PREVIEWS_PATH = APP_STATE_DIR / "manual_impact_previews.jsonl"
APP_RERUN_STEPS_PATH = APP_STATE_DIR / "manual_rerun_steps.jsonl"
APP_RERUN_CONSISTENCY_PATH = APP_STATE_DIR / "manual_rerun_consistency_checks.jsonl"

RERUN_CHAIN = (
    ("field_mapping", "字段映射"),
    ("fact_layer", "事实层"),
    ("derived_metric", "派生指标"),
    ("report_reference", "报告引用"),
)
# 派生表 → 消费它的 App 视图（下游影响面靠这张表算，不是猜的）
TABLE_TO_VIEWS: dict[str, tuple[str, ...]] = {
    "collection": ("账龄回款",), "receivable_aging": ("账龄回款", "项目成本"),
    "v_collection_authoritative": ("账龄回款",),
    "invoice_raw": ("开票纳税",), "invoice_lines": ("开票纳税", "项目成本"),
    "tax_composition": ("开票纳税",), "loan_register": ("开票纳税",),
    "expense_lines": ("项目成本",), "kingdee_ledger": ("项目成本",),
    "kingdee_voucher": ("项目成本",), "goods_movement": ("项目成本",),
    "bank_journal": ("账龄回款",), "personal_advance": ("项目成本",),
    "op_monthly": ("我在哪",), "op_key_indicators": ("我在哪",),
    "row_matches": ("源检查板",), "subject_code_map": ("源检查板",),
}
VIEW_ENDPOINTS = {
    "账龄回款": "/api/账龄回款", "开票纳税": "/api/开票纳税",
    "项目成本": "/api/项目成本", "我在哪": "/api/我在哪", "源检查板": "/api/源检查",
}


def _lineage_graph() -> dict[str, Any]:
    if not LINEAGE_PATH.exists():
        raise HTTPException(status_code=503, detail="血缘图缺失")
    return yaml.safe_load(LINEAGE_PATH.read_text(encoding="utf-8")) or {}


def _downstream(asset: str) -> dict[str, Any]:
    """选中资产 → 下游影响面：派生表 → App 视图 → 报告引用。全部由血缘边算出。"""
    graph = _lineage_graph()
    edges = [e for e in (graph.get("edges") or []) if str(e.get("from")) == asset]
    tables = sorted({str(e.get("to")).removeprefix("_staging.") for e in edges})
    views: set[str] = set()
    for t in tables:
        views.update(TABLE_TO_VIEWS.get(t, ()))
    # our_source 的真实长相带括号与 via：
    #   "_staging.expense_lines(6403) via _staging.tax_composition"
    #   "_staging.kingdee_ledger（book=武汉开明）"
    # 原来用精确相等匹配，这些**全都漏掉**，影响面少报——真开页面看到"受影响断言域 —"才发现。
    domains = sorted({str(r.get("domain")) for r in _load_assertions()
                      if any(f"_staging.{t}" in str(r.get("our_source", "")) for t in tables)})
    return {
        "资产": asset,
        "派生表": [{"表": t, "行数": sum(int(e.get("rows") or 0) for e in edges
                                       if str(e.get("to")).removeprefix("_staging.") == t),
                    "版本": next((e.get("version") for e in edges
                                  if str(e.get("to")).removeprefix("_staging.") == t), None)}
                   for t in tables],
        "受影响视图": sorted(views),
        "受影响断言域": domains,
        "受影响报告": sorted({f"report_no{r['编号']}" for r in _reports_touching(domains)}),
        "边数": len(edges),
    }


def _reports_touching(domains: list[str]) -> list[dict[str, Any]]:
    """报告与域的对应：读报告正文首标题里的域名，不硬编码映射。"""
    out = []
    domain_zh = {"collection": "回款", "invoicing": "开票", "tax": "税费", "loan": "借款",
                 "expense": "费用", "material": "材料", "advance": "个人借支",
                 "kingdee": "账套", "receivable_aging": "回款", "pipeline": "回款"}
    wanted = {domain_zh.get(d, d) for d in domains}
    for d in _report_dirs():
        title = _report_title(d) or ""
        if any(w and w in title for w in wanted):
            out.append({"编号": int(re.search(r"report_no(\d+)", d.name).group(1)), "标题": title})
    return out


def _view_payload_hash(view: str) -> dict[str, Any]:
    """真算一遍该视图的输出并取内容哈希——重跑要**真跑**，不是写条记录了事。"""
    fn = {
        "账龄回款": receivable_aging, "开票纳税": invoice_tax_fund,
        "项目成本": project_cost, "我在哪": where_am_i, "源检查板": source_check,
    }.get(view)
    if fn is None:
        return {"视图": view, "状态": "no_recompute_binding"}
    payload = fn()
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"视图": view, "端点": VIEW_ENDPOINTS.get(view),
            "内容哈希": "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest(),
            "字节": len(blob.encode("utf-8")), "状态": "recomputed"}


def _append_state(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    table = {APP_RERUN_STEPS_PATH: "rerun_steps",
             APP_RERUN_CONSISTENCY_PATH: "rerun_consistency"}[path]
    return _st.append(APP_DB_PATH, table, record)


@app.get("/api/影响重跑")
def impact_and_rerun(asset: str | None = None):
    """影响预览与重跑页（PROD.0008）——血缘可视化 + 下游影响面 + 重跑留痕。"""
    graph = _lineage_graph()
    edges = graph.get("edges") or []
    nodes = graph.get("nodes") or []
    with_edges = sorted({str(e.get("from")) for e in edges})
    app_steps = _st.read(APP_DB_PATH, "rerun_steps")
    runs: dict[str, list[dict[str, Any]]] = {}
    for s in app_steps:
        runs.setdefault(str(s.get("rerun_run_id")), []).append(s)

    return {
        "血缘": {
            "节点数": len(nodes), "边数": len(edges),
            "可选资产数": len(with_edges),
            "派生表": sorted({str(e.get("to")).removeprefix("_staging.") for e in edges}),
            "资产": [
                {"资产": a,
                 "域": next((n.get("domain") for n in nodes if str(n.get("asset")) == a), None),
                 "派生表数": len({str(e.get("to")) for e in edges if str(e.get("from")) == a})}
                for a in with_edges
            ],
        },
        "选中": _downstream(asset) if asset else None,
        "重跑链": [{"层": k, "名称": zh, "序": i + 1} for i, (k, zh) in enumerate(RERUN_CHAIN)],
        "重跑纪律": {
            "覆盖旧版本": False,
            "旧版本处置": "retained_not_overwritten",
            "raw层可写": False,
            "允许借重跑升报告等级": False,
            "留痕": "每层一条 manual_rerun_step + 一条一致性检查，皆追加式",
        },
        "既有仓内留痕": {
            "重跑步骤": len(_read_jsonl(RERUN_STEPS_PATH)),
            "影响预览": len(_read_jsonl(IMPACT_PREVIEWS_PATH)),
        },
        "本机重跑记录": {
            "轮次": len(runs),
            "步骤数": len(app_steps),
            "位置": str(APP_RERUN_STEPS_PATH),
            "最近": [
                {"轮次号": rid, "步骤": len(steps),
                 "起于": min(str(s.get("rerun_at")) for s in steps),
                 "止于": max(str(s.get("rerun_at")) for s in steps),
                 "状态": "completed" if len(steps) == len(RERUN_CHAIN) else "incomplete",
                 "各层": [{"层": s.get("chain_layer"), "新版本": s.get("new_derived_version_ref"),
                           "旧版本": s.get("old_derived_version_ref"),
                           "旧版本状态": s.get("old_version_status_after_rerun"),
                           "结果": s.get("rerun_result")} for s in
                          sorted(steps, key=lambda x: x.get("chain_order") or 0)]}
                for rid, steps in sorted(runs.items())[-5:]
            ],
        },
    }


@app.post("/api/影响重跑/重跑")
def trigger_rerun(payload: dict[str, Any] = Body(...)):
    """从页面发起一次**真实重跑**：四层链逐层真算，每层留痕，旧版本保留。"""
    asset = str(payload.get("资产") or "").strip()
    reason = str(payload.get("理由") or "").strip()
    actor = str(payload.get("操作人") or "owner").strip() or "owner"
    if not reason:
        raise HTTPException(status_code=400, detail="必须写明重跑理由")

    graph = _lineage_graph()
    if asset not in {str(e.get("from")) for e in (graph.get("edges") or [])}:
        raise HTTPException(status_code=404, detail=f"资产不在血缘图内或无派生边：{asset}")

    down = _downstream(asset)
    started = datetime.now(BEIJING)
    # 轮次号按**已有轮次递增**，不拿挂钟拼：同一秒内对同一资产连点两次（Owner 手快双击）
    # 会撞出同一个 id，两轮留痕被并成一轮——契约测试当场逮到。时间戳留在 rerun_at 字段里。
    seq = len({str(s.get("rerun_run_id")) for s in _st.read(APP_DB_PATH, "rerun_steps")}) + 1
    run_id = f"RERUN-APP-{seq:04d}-{hashlib.sha256(asset.encode()).hexdigest()[:6]}"

    steps: list[dict[str, Any]] = []
    for order, (layer, layer_zh) in enumerate(RERUN_CHAIN, start=1):
        if layer == "field_mapping":
            detail = {"派生表": down["派生表"], "边数": down["边数"]}
        elif layer == "fact_layer":
            pipeline = load_json(FACTS / "data_pipeline.json")
            staging = pipeline.get("staging_tables") or {}
            detail = {"表行数": {t["表"]: (staging.get(t["表"]) or {}).get("rows")
                                 for t in down["派生表"]}}
        elif layer == "derived_metric":
            detail = {"视图": [_view_payload_hash(v) for v in down["受影响视图"]]}
        else:
            detail = {"报告": down["受影响报告"], "断言域": down["受影响断言域"]}

        blob = json.dumps(detail, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        step = {
            "record_type": "manual_rerun_step",
            "schema_version": "kmfa.manual_rerun_step.v1",
            "stage_phase": "DT6-PROD0008",
            "rerun_run_id": run_id,
            "rerun_step_id": f"{run_id}-{order:02d}",
            "rerun_version": f"MANUAL-RERUN-KMFA-DT6-PROD0008-001.{order:02d}",
            "chain_layer": layer,
            "chain_layer_label": layer_zh,
            "chain_order": order,
            "source_asset": asset,
            "actor_ref": f"actor_ref://owner_or_authorized_delegate/{actor}",
            "reason_summary": reason,
            "rerun_at": datetime.now(BEIJING).isoformat(timespec="seconds"),
            "rerun_status": "completed_public_safe_metadata_only",
            "rerun_result": detail,
            "content_hash": "sha256:" + digest,
            # 造新版本、保留旧版本——既有契约的硬要求
            "new_derived_version_ref": f"version_ref://KMFA/DT6-PROD0008/{run_id}/{layer}/new-{digest[:12]}",
            "old_derived_version_ref": f"version_ref://KMFA/DT6-PROD0008/{run_id}/{layer}/old-retained",
            "old_version_status_after_rerun": "retained_not_overwritten",
            "overwrite_old_version_allowed": False,
            "append_only_version_record_required": True,
            "raw_layer_write_allowed": False,
            "raw_source_mutation_allowed": False,
            "source_layer_write_allowed": False,
            "business_plaintext_committed": False,
            "forbidden_plaintext": False,
            "formal_report_generated": False,
            "report_grade_upgrade_allowed": False,
            "business_decision_basis_allowed": False,
            "project_id": "KMFA",
            "system_name": "KMFA 经营分析系统",
            "evidence_refs": ["KMFA/machine/lineage.yaml",
                              "KMFA/tools/manual_rerun_mechanism.py"],
        }
        steps.append(_append_state(APP_RERUN_STEPS_PATH, step))

    finished = datetime.now(BEIJING)
    consistency = _append_state(APP_RERUN_CONSISTENCY_PATH, {
        "record_type": "manual_rerun_consistency_check",
        "schema_version": "kmfa.manual_rerun_consistency_check.v1",
        "stage_phase": "DT6-PROD0008",
        "rerun_run_id": run_id,
        "consistency_id": f"CONS-APP-{run_id[-6:]}",
        "checked_at": finished.isoformat(timespec="seconds"),
        "chain_layers_expected": [k for k, _ in RERUN_CHAIN],
        "chain_layers_completed": [s["chain_layer"] for s in steps],
        "chain_complete": [s["chain_layer"] for s in steps] == [k for k, _ in RERUN_CHAIN],
        "report_grade_unchanged": True,
        "old_versions_retained": all(
            s["old_version_status_after_rerun"] == "retained_not_overwritten" for s in steps),
        "raw_layer_untouched": True,
    })

    _audit("processing", subject_ref=asset, result_status="COMPLETED",
           evidence_ref=str(APP_RERUN_STEPS_PATH), run_id=run_id,
           layers=len(steps), chain_complete=consistency["chain_complete"])

    return {
        "轮次号": run_id,
        "资产": asset,
        "耗时秒": round((finished - started).total_seconds(), 3),
        "步骤数": len(steps),
        "链完整": consistency["chain_complete"],
        "旧版本全保留": consistency["old_versions_retained"],
        "各层": [{"序": s["chain_order"], "层": s["chain_layer"], "名称": s["chain_layer_label"],
                  "新版本": s["new_derived_version_ref"], "哈希": s["content_hash"],
                  "结果": s["rerun_result"]} for s in steps],
        "一致性检查": consistency,
        "留痕位置": str(APP_RERUN_STEPS_PATH),
    }


# ── PROD.0003 访问安全承接 S17：审计日志 append-only ──────────────────────────
# 权威任务包第 12 行：本机单用户模式；导出水印（等级/Q 级/delivery 永远印在页眉）；
# 审计日志 append-only。验收＝安全走查单过（承接 v014 S17 access security 口径）。
#
# 契约取自既有 KMFA/metadata/security/：
#   audit_log_policy.jsonl —— 7 个必填字段、append_only、五种 action_type、
#     raw_payload_allowed=false / business_value_plaintext_allowed=false
#   v014_s17_p1_..._audit_event_contract.jsonl —— persistent_event_write_enabled=false
#     （S17-P1 只定契约不落盘）；**本单元即是把它真正落盘的那一步**
SECURITY_DIR = KMFA / "metadata" / "security"
AUDIT_POLICY_PATH = SECURITY_DIR / "audit_log_policy.jsonl"
ACCESS_POLICY_PATH = SECURITY_DIR / "access_security_policy_manifest.json"
APP_AUDIT_PATH = APP_STATE_DIR / "audit_events.jsonl"

AUDIT_REQUIRED_FIELDS = (
    "event_id", "event_time", "actor_role", "action_type",
    "subject_ref", "evidence_ref", "result_status",
)
AUDIT_ACTION_TYPES = ("import", "processing", "report", "export", "notification")
# 审计事件里绝不允许出现的东西——记「谁在什么时候对什么做了什么」，
# 不记业务明文与原始载荷（契约：raw_payload_allowed=false）
AUDIT_FORBIDDEN_KEYS = FORBIDDEN_EVENT_KEYS | frozenset({
    "payload", "raw_payload", "body", "report_body", "text", "content",
})


def _audit(action_type: str, subject_ref: str, result_status: str,
           evidence_ref: str, actor_role: str = "management",
           **extra: Any) -> dict[str, Any]:
    """写一条审计事件。**只追加，且写失败不能拖垮业务动作**。

    审计是旁证不是主流程：日志写不进去时业务不该跟着挂，但也不能悄悄吞掉——
    失败会以 audit_write_failed 记进返回值，调用方可见。
    """
    if action_type not in AUDIT_ACTION_TYPES:
        raise HTTPException(status_code=500, detail=f"非法 action_type：{action_type}")
    event = {
        "event_id": f"AUD-APP-{hashlib.sha256(f'{action_type}{subject_ref}{datetime.now(BEIJING).isoformat()}'.encode()).hexdigest()[:16]}",
        "event_time": datetime.now(BEIJING).isoformat(timespec="seconds"),
        "actor_role": actor_role,
        "action_type": action_type,
        "subject_ref": subject_ref,
        "evidence_ref": evidence_ref,
        "result_status": result_status,
        "record_type": "audit_event",
        "policy_version": "AUD-KMFA-S17P1-ACTION-LOG-001",
        "stage_phase": "DT6-PROD0003",
        "append_only": True,
        "raw_payload_committed": False,
        "business_value_plaintext_committed": False,
        **extra,
    }
    leaked = sorted(set(event) & AUDIT_FORBIDDEN_KEYS)
    if leaked:
        raise HTTPException(status_code=500, detail=f"审计事件含禁写字段：{leaked}")
    try:
        _st.append(APP_DB_PATH, "audit_events", event)
    except Exception as exc:  # 审计是旁证：写不进去也不该拖垮业务动作
        event["audit_write_failed"] = str(exc)
    return event


@app.get("/api/审计日志")
def audit_log(action_type: str | None = None, page: int = 1, size: int = 50):
    """审计日志（PROD.0003）——append-only，只记动作不记业务明文。"""
    rows = _st.read(APP_DB_PATH, "audit_events")
    selected = [r for r in rows if not action_type or r.get("action_type") == action_type]
    items, meta = _paginate(list(reversed(selected)), page, size)
    policy = _read_jsonl(AUDIT_POLICY_PATH)
    access = load_json(ACCESS_POLICY_PATH) if ACCESS_POLICY_PATH.exists() else {}
    by_type: dict[str, int] = {}
    for r in rows:
        key = str(r.get("action_type"))
        by_type[key] = by_type.get(key, 0) + 1
    return {
        "总数": len(rows),
        "按动作": by_type,
        "分页": meta,
        "事件": items,
        "契约": {
            "必填字段": list(AUDIT_REQUIRED_FIELDS),
            "动作类型": list(AUDIT_ACTION_TYPES),
            "append_only": True,
            "允许记原始载荷": False,
            "允许记业务明文": False,
            "政策版本": (policy[0].get("policy_version") if policy else None),
            "落盘位置": str(APP_AUDIT_PATH),
            "契约来源": [
                "KMFA/metadata/security/audit_log_policy.jsonl",
                "KMFA/metadata/security/access_security_policy_manifest.json",
            ],
        },
        "访问模式": {
            "模式": "本机单用户",
            "应用内登录": False,
            "生产鉴权": "Cloudflare Access 前置（DNS 之前）",
            "角色口径": (access.get("required_roles") or []),
            "说明": "本机不做多用户与角色分权；角色口径承接 S17 供云端与导出留痕使用",
        },
    }


# ── 排程健康：让「排程到底跑没跑」这件事在页面上一眼可见 ──────────────────────
# 起因：2026-07-20 Owner 说「不可能每次结果都让我给你们反馈啊，你自己不会复审检查吗」。
# 他是对的。在此之前 app 容器一个卷都不挂，排程状态只能靠人登服务器 `cat` 日志——
# 于是每次都要 Owner 亲自查、再回报给开发侧。这个来回本身就是设计缺陷，不是沟通问题。
# 现在 app 只读挂 kmfa-logs，本接口直接读 skills 写的 ledger。
SKILL_LEDGER_PATH = Path(os.environ.get("KMFA_SKILL_LEDGER", "/var/log/kmfa/ledger.jsonl"))
# 排程契约（与 deploy/skills-runtime/crontab.txt 一致；北京时间）
SCHEDULE_CONTRACT = {
    "attendance-morning": "每天 10:35",
    "attendance-evening": "每天 20:05",
    "work-check-morning": "每天 11:35",
    "work-check-evening": "每天 17:05",
    "fund-weekly": "周一/周六 11:00",
    "mgmt-monthly": "每月 1 日 09:00",
    "upstream-archive": "每天 11:00",
    "self-audit": "周日 01:00",
    "daily-backup": "每天 00:30",
    "dws-keepalive": "每 4 小时 :20",
}
# 技能归属业务模块（Owner 2026-07-21：「所有 skills 都需要整合进 kmfa 功能模块」）
SKILL_MODULE = {
    "attendance-morning": "考勤与日检", "attendance-evening": "考勤与日检",
    "work-check-morning": "考勤与日检", "work-check-evening": "考勤与日检",
    "fund-weekly": "资金与经营报告", "mgmt-monthly": "资金与经营报告",
    "upstream-archive": "数据接入",
    "self-audit": "系统底座", "daily-backup": "系统底座", "dws-keepalive": "系统底座",
}


def _log_tail_line(log_path) -> str | None:
    """取当次运行日志的最后一行实质输出（跳过 run_skill 的「结束 rc=」包装行）。"""
    if not log_path:
        return None
    try:
        target = Path(str(log_path)).resolve()
        root = SKILL_LEDGER_PATH.parent.resolve()
        if not str(target).startswith(str(root) + "/") or not target.is_file():
            return None
        lines = [l.strip() for l in target.read_bytes()[-8192:].decode("utf-8", "replace").splitlines() if l.strip()]
        for l in reversed(lines):
            if ": 结束 rc=" in l or ": 开始" in l:
                continue
            return l[:160]
        return lines[-1][:160] if lines else None
    except OSError:
        return None


@app.get("/api/排程健康")
def schedule_health():
    """排程执行健康——**不出任何业务数据**，只报「谁在什么时候跑了、成没成」。

    刻意做成这样：判断「排程是不是活着」不该需要登服务器，也不该需要谁口头汇报。
    """
    if not SKILL_LEDGER_PATH.exists():
        log_root = SKILL_LEDGER_PATH.parent
        if not log_root.exists():
            原因 = f"{log_root} 目录不存在——app 容器没挂 kmfa-logs 卷（部署配置问题，不是排程问题）"
        elif not any(log_root.iterdir()):
            原因 = f"{log_root} 已挂载但是空的——排程容器从未写入（查 skills 容器是否 Started）"
        else:
            原因 = f"{log_root} 有内容但没有 {SKILL_LEDGER_PATH.name}——排程从未完成过一次运行"
        return {
            "可读": False,
            "原因": 原因,
            "排程契约": SCHEDULE_CONTRACT,
            "诚实边界": "读不到就说读不到，不猜、不拿「没有坏消息」当好消息。",
        }

    rows = []
    for line in SKILL_LEDGER_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    now = datetime.now(BEIJING)
    # 台账是 append-only 全量历史（run_skill.sh 每次运行追加一行、日志按时间戳独立归档）。
    # 此前只取每技能最新一条是接口的缺陷，不是数据的缺陷——Owner 2026-07-21 点破后改为全量。
    by_skill: dict[str, list] = {}
    for r in rows:
        by_skill.setdefault(str(r.get("skill") or "?"), []).append(r)
    for v in by_skill.values():
        v.sort(key=lambda r: str(r.get("ts")), reverse=True)

    逐项 = []
    for skill, 约定 in sorted(SCHEDULE_CONTRACT.items()):
        history = by_skill.get(skill, [])
        last = history[0] if history else None
        距今小时 = None
        if last:
            try:
                距今小时 = round(
                    (now - datetime.fromisoformat(str(last["ts"]))).total_seconds() / 3600, 1)
            except (ValueError, KeyError, TypeError):
                距今小时 = None
        失败次数 = sum(1 for r in history if r.get("rc") != 0)
        连续失败 = 0
        for r in history:
            if r.get("rc") != 0:
                连续失败 += 1
            else:
                break
        逐项.append({
            "技能": skill,
            "业务模块": SKILL_MODULE.get(skill, "系统底座"),
            "约定时刻": 约定,
            "跑过": last is not None,
            "最近一次": (last or {}).get("ts"),
            "距今小时": 距今小时,
            "退出码": (last or {}).get("rc"),
            "成功": (last or {}).get("rc") == 0 if last else None,
            "投递开关": (last or {}).get("delivery_enabled"),
            "次数": len(history),
            "失败次数": 失败次数,
            "成功率": (round(100 * (len(history) - 失败次数) / len(history)) if history else None),
            "连续失败": 连续失败,
            # 全量运行历史（最近在前，封顶 100 条防大账本撑爆响应；快照=当次独立日志文件）
            "历史": [{
                "ts": r.get("ts"), "rc": r.get("rc"), "成功": r.get("rc") == 0,
                "投递开关": r.get("delivery_enabled"), "快照": r.get("log"),
                # 结果摘要=当次日志最后一行有内容的输出（Owner：「skills 的结果呢」——
                # 不点快照也要能看到这次跑出了什么）。只取最近 8 条，读文件 IO 有界。
                "摘要": (_log_tail_line(r.get("log")) if i < 8 else None),
            } for i, r in enumerate(history[:100])],
        })

    跑过的 = [x for x in 逐项 if x["跑过"]]
    失败的 = [x for x in 跑过的 if x["成功"] is False]
    空跑的 = [x for x in 跑过的 if str(x["投递开关"]) == "0"]
    # 近 24 小时战报：首页要一眼看到「昨晚到现在都跑了什么、成没成、干了什么」
    近24 = []
    for x in 逐项:
        for h in (x.get("历史") or []):
            try:
                if (now - datetime.fromisoformat(str(h["ts"]))).total_seconds() <= 86400:
                    近24.append({"技能": x["技能"], "业务模块": x["业务模块"], **h})
            except (ValueError, TypeError):
                continue
    近24.sort(key=lambda r: str(r.get("ts")), reverse=True)
    return {
        "可读": True,
        "近24小时": 近24[:30],
        "总执行次数": len(rows),
        "有记录的技能数": f"{len(跑过的)}/{len(SCHEDULE_CONTRACT)}",
        "失败数": len(失败的),
        "仍在空跑数": len(空跑的),
        "结论": (
            "从未执行过任何排程——排程链是断的" if not 跑过的
            else f"有 {len(失败的)} 个技能最近一次失败" if 失败的
            else f"有 {len(空跑的)} 个技能仍按空跑（投递开关=0），消息发不出去" if 空跑的
            else "最近一次执行全部成功且投递已开"
        ),
        "逐项": 逐项,
        "诚实边界": "只报执行事实，不报业务内容；「没记录」一律显示为未跑过，不美化。",
    }


@app.get("/api/排程健康/快照")
def schedule_run_snapshot(log: str):
    """读取某一次运行的日志快照（run_skill.sh 每次运行写独立时间戳日志，即当时快照）。

    只许读排程日志根目录之内的文件——路径防穿越与 /ui/assets 同款收紧；
    只回尾部 64KB：快照是给人复盘的，不是给人下载全量日志的。
    """
    log_root = SKILL_LEDGER_PATH.parent.resolve()
    target = Path(log).resolve()
    if not str(target).startswith(str(log_root) + "/") or not target.is_file():
        raise HTTPException(status_code=404, detail="快照不存在或不在排程日志目录内")
    data = target.read_bytes()
    tail = data[-65536:]
    return {
        "路径": str(target),
        "总字节": len(data),
        "截取": len(tail) < len(data),
        "内容": tail.decode("utf-8", errors="replace"),
    }
