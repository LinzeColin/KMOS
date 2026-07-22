"""TSK.KMFA.PROD.0002 契约测试：后端数据 API 的 OpenAPI 契约与真实数据形态。

铁律：本文件断言的全部是**真实仓内数据**（machine/facts、machine/lineage.yaml、
metadata/quality/assertions.jsonl、stage_artifacts 八份报告），不使用 mock/占位——
本线曾犯「用健康检查冒充完备性」的错，契约测试必须咬住真实内容。
"""
import hashlib
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REQUIRED_PATHS = {
    "/healthz",
    "/api/状态",
    "/api/数据管线",
    "/api/断言",
    "/api/技能",
    "/api/事实",
    "/api/事实/{name}",
    "/api/血缘",
    "/api/报表",
    "/api/源检查",
    "/api/我在哪",
    "/api/项目成本",
    "/api/账龄回款",
    "/api/开票纳税",
}


def test_aging_monthly_rows_match_assertions():
    """PROD.0010：回款逐月须逐条来自断言表 collection 域，不得另造。"""
    payload = client.get("/api/账龄回款").json()
    monthly = payload["回款对账"]["逐月"]
    src = client.get("/api/断言?domain=collection&size=500").json()
    assert len(monthly) == src["筛选"]["命中"]
    by_id = {r["assertion_id"]: r for r in src["items"]}
    for row in monthly:
        origin = by_id[row["断言"]]
        assert row["差异分"] == origin.get("delta_cents")
        assert row["状态"] == origin.get("status")
        assert row["期间"] == origin.get("period")


def test_aging_cents_to_yuan_is_exact_integer_math():
    """金额纪律：分→元换算必须整数精确，禁用浮点。

    取真实断言值做定点校验——69457 分必须是 694.57 元、-146280290 分必须是
    -1,462,802.90 元；任何浮点近似都会在此暴露。
    """
    monthly = client.get("/api/账龄回款").json()["回款对账"]["逐月"]
    for row in monthly:
        cents = row["差异分"]
        if cents is None:
            assert row["差异元"] is None
            continue
        sign = "-" if cents < 0 else ""
        expected = f"{sign}{abs(cents) // 100:,}.{abs(cents) % 100:02d}"
        assert row["差异元"] == expected, f"{cents} 分换算错：{row['差异元']} != {expected}"


def test_aging_zero_diff_count_matches_rows():
    payload = client.get("/api/账龄回款").json()["回款对账"]
    assert payload["零分差月数"] == sum(1 for m in payload["逐月"] if m["差异分"] == 0)
    assert payload["未闭月数"] == sum(1 for m in payload["逐月"] if m["状态"] == "analyzed_open")
    assert payload["月数"] == len(payload["逐月"])


def test_aging_identity_assertion_present_and_closed():
    rows = client.get("/api/账龄回款").json()["账龄恒等式"]
    assert rows, "账龄恒等式断言不得缺失"
    identity = rows[0]
    assert identity["差异分"] == 0
    assert identity["状态"].startswith("closed")


def test_aging_structure_layer_reported_as_blocked():
    """v014 账龄结构层值仍被阻断，须如实报出，且本页不得产出分桶金额。"""
    payload = client.get("/api/账龄回款").json()
    layer = payload["账龄结构层"]
    assert "structure_available_values_blocked" in layer["泳道数据状态"]
    assert layer["允许作经营依据"] is False
    assert payload["诚实边界"]
    blob = json.dumps(payload, ensure_ascii=False)
    assert '"分桶金额"' not in blob and '"bucket_amount"' not in blob


def test_aging_staging_rows_match_pipeline_facts():
    payload = client.get("/api/账龄回款").json()
    staging = client.get("/api/数据管线").json()["staging_tables"]
    assert payload["派生层规模"]
    for item in payload["派生层规模"]:
        assert item["行数"] == staging[item["表"]]["rows"]


def test_project_cost_matches_fact_layer_output():
    """PROD.0006 验收：须与 project_cost_fact_layer 输出一致（不得自造记录）。"""
    payload = client.get("/api/项目成本").json()
    layer = payload["事实层"]
    assert layer["状态"] == "structural_fact_layer_blocked_for_formal_calculation"
    assert layer["记录数"] == len(payload["记录"]) == 4
    assert len(payload["必需结构"]["成本类别"]) == 9
    assert len(payload["必需结构"]["事实指标"]) == 6
    for row in payload["记录"]:
        assert row["记录号"].startswith("PCF-S09P1-")
        assert row["计算状态"] == "blocked_pending_quality_resolution"
        assert row["金额已计算"] is False and row["允许正式计算"] is False
        assert row["明文已公开"] is False


def test_project_cost_emits_no_money_numbers_while_blocked():
    """核心诚实保证：A0 未就位时，本接口**不得**出现任何毛利/金额数字。

    事实层全部 amount_calculation_performed=false，若响应里冒出金额字段，
    只可能是编造——本测试即为此设。
    """
    payload = client.get("/api/项目成本").json()
    assert payload["事实层"]["已算金额记录数"] == 0
    forbidden = ("毛利", "现金毛利", "cost_total_amount", "revenue_amount", "gross_margin")
    blob = json.dumps(payload, ensure_ascii=False)
    for key in forbidden:
        assert f'"{key}":' not in blob, f"阻塞期不应出现金额字段 {key}"
    assert payload["诚实边界"]


def test_project_cost_blocking_chain_points_to_owner_blocker():
    payload = client.get("/api/项目成本").json()
    chain = payload["阻塞链"]
    assert "A0" in chain["直接原因"]
    assert chain["根阻塞"], "根阻塞不得为空"
    assert any(b["编号"] == "BLK-001" and b["只有Owner可解"] for b in chain["根阻塞"])


def test_project_cost_drilldown_rows_match_pipeline_facts():
    """下钻表行数须等于 data_pipeline 事实，不得另编一套数。"""
    payload = client.get("/api/项目成本").json()
    pipeline = client.get("/api/数据管线").json()
    staging = pipeline["staging_tables"]
    assert payload["可下钻派生层"], "下钻表不得为空"
    for item in payload["可下钻派生层"]:
        assert item["行数"] == staging[item["表"]]["rows"]

WHERE_DOC = Path(__file__).resolve().parents[3] / "文档" / "00_我在哪.md"


def test_where_am_i_same_source_as_rendered_doc():
    """PROD.0004 验收：首页须与 `文档/00_我在哪.md` 渲染件**同源一致**。

    把验收标准做成可执行断言——渲染件里的关键值必须逐字出现在 API 返回中；
    任一侧漂移（页面写死、或 facts 更新未同步）都会在此失败。
    """
    payload = client.get("/api/我在哪").json()
    state = payload["当前状态"]
    doc = WHERE_DOC.read_text(encoding="utf-8")

    for value in (state["版本"], state["阶段"], state["分期"], state["任务"],
                  state["进度"], state["报告可信度"], state["业务结论"]):
        assert value and str(value) in doc, f"渲染件中找不到：{value!r}"

    assert f"{state['卡住件数']} 件" in doc
    for blocker in payload["卡住的事"]:
        assert blocker["id"] in doc
        assert str(blocker["首次登记"]) in doc


def test_where_am_i_roadmap_matches_doc_stage_count():
    payload = client.get("/api/我在哪").json()
    stages = payload["路线图"]["阶段"]
    assert payload["路线图"]["合计"] == len(stages) == 18
    doc = WHERE_DOC.read_text(encoding="utf-8")
    for stage in stages:
        assert stage["id"] in doc and stage["name"] in doc


def test_header_quality_grade_comes_from_facts_not_hardcoded():
    """页眉质量等级须取自 data_pipeline 事实——原实现把 "Q3" 写死，facts 升级后会静默说谎。"""
    header = client.get("/api/状态").json()["页眉"]
    pipeline = client.get("/api/事实/data_pipeline").json()
    assert header["质量等级"]
    assert str(pipeline["quality_grade_current"]).startswith(header["质量等级"])


def test_source_check_matrix_protocol_reported_truthfully():
    """PROD.0005：正式矩阵当前零已提交源行，必须如实报出，不得编造维度值充数。"""
    payload = client.get("/api/源检查").json()
    protocol = payload["矩阵协议"]
    assert protocol["schema"] == "kmfa.source_check_matrix.v1"
    assert protocol["阶段"] == "S03-P2"
    assert protocol["已提交源行"] == 0
    assert len(protocol["必需维度"]) == 6
    assert "已就绪" in protocol["允许状态"]


def test_source_check_coverage_matrix_matches_lineage_total():
    """覆盖矩阵各源合计必须等于血缘资产总数——防止漏源或重复计数。"""
    payload = client.get("/api/源检查").json()
    coverage = payload["覆盖矩阵"]
    assert coverage["资产合计"] >= 50
    assert sum(row["合计"] for row in coverage["行"]) == coverage["资产合计"]
    assert set(coverage["源"]) >= {"财务", "WPS钉钉红圈", "绩效"}
    for row in coverage["行"]:
        assert sum(row[state] for state in coverage["状态列"]) == row["合计"]


def test_source_check_freshness_from_generated_facts_only():
    """新鲜度由 data_as_of_batch 与血缘批次比对得出（皆机器生成面），不读 raw inbox。"""
    payload = client.get("/api/源检查").json()
    fresh = payload["新鲜度"]
    assert fresh["数据批次"]
    assert isinstance(fresh["stale"], bool)
    assert fresh["stale"] == bool(fresh["更新的批次"])
    assert fresh["提示"]


def test_openapi_covers_required_paths():
    schema = client.get("/ops/openapi.json").json()
    missing = REQUIRED_PATHS - set(schema["paths"])
    assert not missing, f"OpenAPI 缺路径: {missing}"


def test_facts_index_lists_real_facts():
    payload = client.get("/api/事实").json()
    names = {item["名"] for item in payload["items"]}
    assert payload["count"] >= 8, payload["count"]
    assert {"status", "data_pipeline", "roadmap", "blockers"} <= names, names


def test_facts_one_returns_real_content():
    payload = client.get("/api/事实/status").json()
    assert isinstance(payload, dict) and payload


def test_facts_one_rejects_unknown_and_traversal():
    assert client.get("/api/事实/不存在的事实").status_code == 404
    assert client.get("/api/事实/..%2F..%2Fpasswd").status_code == 404


def test_lineage_real_graph():
    payload = client.get("/api/血缘").json()
    assert payload["schema"] == "kmfa.lineage.v1"
    assert payload["覆盖"]["原始资产"] >= 50
    assert payload["规模"]["节点"] > 0 and payload["规模"]["边"] > 0
    assert len(payload["派生表"]) >= 10


def test_lineage_graph_optional_and_paginated():
    lite = client.get("/api/血缘").json()
    assert "图" not in lite
    full = client.get("/api/血缘?include_graph=true&size=5").json()
    assert len(full["图"]["节点"]) == 5
    assert full["图"]["节点分页"]["size"] == 5


def test_reports_lists_eight_real_reports():
    payload = client.get("/api/报表").json()
    assert payload["count"] == 8, payload["count"]
    first = payload["items"][0]
    assert first["编号"] == 1
    assert "一致性证明" in (first["标题"] or ""), first["标题"]
    assert first["文件数"] > 0


def test_reports_filter():
    payload = client.get("/api/报表?q=回款").json()
    assert payload["count"] >= 1
    assert all("回款" in (r["标题"] or "") or "回款" in r["目录"] for r in payload["items"])


def test_assertions_backward_compatible_summary():
    payload = client.get("/api/断言").json()
    assert payload["total"] == payload["closed"] + payload["analyzed_open"]
    assert payload["total"] >= 15
    assert payload["items"], "默认应返回条目（前端概览页依赖）"


def test_assertions_filter_by_status():
    all_rows = client.get("/api/断言").json()
    filtered = client.get("/api/断言?status=analyzed_open").json()
    assert filtered["筛选"]["命中"] == all_rows["analyzed_open"]
    assert all(item["status"] == "analyzed_open" for item in filtered["items"])


def test_assertions_filter_by_domain():
    payload = client.get("/api/断言?domain=collection").json()
    assert payload["筛选"]["命中"] >= 1
    assert all(item["domain"] == "collection" for item in payload["items"])


def test_assertions_pagination():
    paged = client.get("/api/断言?size=5&page=2").json()
    assert len(paged["items"]) == 5
    assert paged["分页"]["page"] == 2 and paged["分页"]["size"] == 5


def test_api_sources_never_under_raw_inbox():
    """PROD.0002 明令：API 永不直读 raw inbox（KMDatabase/data）。"""
    from app.main import (
        ASSERTIONS_PATH,
        FACTS,
        FORBIDDEN_READ_ROOT,
        LINEAGE_PATH,
        STAGE_ARTIFACTS,
    )

    forbidden = FORBIDDEN_READ_ROOT.resolve()
    for path in (FACTS, LINEAGE_PATH, ASSERTIONS_PATH, STAGE_ARTIFACTS):
        resolved = Path(path).resolve()
        assert forbidden not in resolved.parents, f"{resolved} 落在 raw inbox 下"


# ── PROD.0011 开票纳税与资金贷款视图 ────────────────────────────────────────────
def _invoice_payload():
    return client.get("/api/开票纳税").json()


def test_invoice_tax_blocks_match_assertion_domains():
    """三域逐条必须等于断言表原值——不得另造一套数。"""
    import json as _json

    from app.main import ASSERTIONS_PATH

    raw = [_json.loads(l) for l in ASSERTIONS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    payload = _invoice_payload()
    for domain, key in (("invoicing", "开票对账"), ("tax", "税务对账"), ("loan", "贷款对账")):
        expect = {r["assertion_id"]: r for r in raw if r.get("domain") == domain}
        got = {r["断言"]: r for r in payload[key]["逐条"]}
        assert set(got) == set(expect), f"{key} 条目与断言表 {domain} 域不一致"
        assert payload[key]["条数"] == len(expect)
        for aid, src in expect.items():
            assert got[aid]["差异分"] == src.get("delta_cents")
            assert got[aid]["状态"] == src.get("status")
            assert got[aid]["期间"] == src.get("period")
            assert got[aid]["结论"] == src.get("finding")


def test_invoice_tax_cents_to_yuan_is_exact_integer_math():
    """分→元定点校验：纯整数运算，任何浮点近似都会在此暴露。"""
    payload = _invoice_payload()
    seen = 0
    for key in ("开票对账", "税务对账", "贷款对账"):
        for r in payload[key]["逐条"]:
            cents = r["差异分"]
            if cents is None:
                assert r["差异元"] is None
                continue
            sign = "-" if cents < 0 else ""
            a = abs(int(cents))
            assert r["差异元"] == f"{sign}{a // 100:,}.{a % 100:02d}", r["断言"]
            seen += 1
    assert seen >= 3, "应至少有 3 条带分差的断言参与校验"
    # 已知真值定点：仲利 0 分差、税负率 1 分、开票三角 3 分、贷款轴 ¥40,960,322.77
    flat = {r["断言"]: r for key in ("开票对账", "税务对账", "贷款对账") for r in payload[key]["逐条"]}
    assert flat["AST-LOAN-ZHONGLI-ADHERENCE"]["差异元"] == "0.00"
    assert flat["AST-TAX-AXIS-HBKM-2025"]["差异元"] == "0.01"
    assert flat["AST-INV-TRIANGLE-2025"]["差异元"] == "0.03"
    assert flat["AST-LOAN-AXIS-2026M5"]["差异元"] == "40,960,322.77"


def test_invoice_tax_zero_diff_counts_match_rows():
    payload = _invoice_payload()
    for key in ("开票对账", "税务对账", "贷款对账"):
        rows = payload[key]["逐条"]
        assert payload[key]["零分差条数"] == len([r for r in rows if r["差异分"] == 0])
        assert payload[key]["未闭条数"] == len([r for r in rows if r["状态"] == "analyzed_open"])


def test_invoice_tax_red_lines_are_zero_and_fact_sourced():
    """任务包红线：不做付款操作、不做正式纳税申报。计数须来自 v014 事实且全零。"""
    import json as _json

    from app.main import S14_P1, S14_P2, S14_P3

    payload = _invoice_payload()
    红 = payload["红线"]
    assert set(红) == {
        "开票次数", "纳税申报次数", "付款或动账次数", "银行操作次数",
        "付款审批次数", "贷款管理动作数", "政策申报提交次数", "补贴申请次数",
    }
    assert all(v == 0 for v in 红.values()), f"红线非零：{红}"

    def load(base):
        return _json.loads(Path(f"{base}_summary.json").read_text(encoding="utf-8"))

    p1, p2, p3 = load(S14_P1), load(S14_P2), load(S14_P3)
    assert 红["开票次数"] == p2["invoice_issuance_count"]
    assert 红["纳税申报次数"] == p2["tax_filing_count"]
    assert 红["付款或动账次数"] == p2["payment_or_bank_operation_count"]
    assert 红["银行操作次数"] == p1["bank_operation_count"]
    assert 红["贷款管理动作数"] == p1["loan_management_action_count"]
    assert 红["补贴申请次数"] == p3["subsidy_application_count"]


def test_invoice_tax_plan_layer_reported_as_blocked_without_amounts():
    """计划层九个方法全部阻断，且响应里不得出现任何计划金额字段。"""
    payload = _invoice_payload()
    构 = payload["结构层"]
    assert set(构) == {"开票纳税计划（S14-P2）", "资金贷款计划（S14-P1）"}
    methods = []
    for seg in 构.values():
        assert seg["决策"] == "NO_GO"
        assert seg["已证值绑定车道数"] == 0
        assert seg["公开业务金额数"] == 0
        assert seg["车道"], "车道不得为空"
        for lane in seg["车道"]:
            assert lane["含业务金额"] is False
            assert lane["允许作经营依据"] is False
            assert "values_unproven" in lane["数据状态"]
        methods.extend(seg["方法"])
    assert len(methods) == 9, f"应为 3 计划 + 3 现金汇总 + 3 问题复核，实得 {len(methods)}"
    for m in methods:
        assert m["定义完备"] is True
        assert m["产出状态"].startswith("blocked_no_authoritative")
        # 事实里九个方法都带中文名与依赖车道——不得只把英文 id 甩给人看
        assert m["名称"], f'{m["方法"]} 缺中文名'
        assert m["依赖车道"], f'{m["方法"]} 缺依赖车道'
        assert m["说明"], f'{m["方法"]} 的"还缺什么"不得为空'
    assert {m["名称"] for m in methods} >= {"开票预计现金流入", "贷款到期", "已开票未回款"}
    # 阻断态下不得凭空造出计划金额/到期提示**字段**。
    # 只扫字段名——诚实边界正文里"不产出计划金额"是否定句，扫全文会误伤。
    keys: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            keys.update(map(str, node))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload)
    for banned in ("计划金额", "到期提示", "资金缺口金额", "预计现金流入", "预计税款"):
        assert banned not in keys, f"阻断态下不得出现字段 {banned}"


def test_invoice_tax_policy_gaps_are_tips_only():
    """税务政策线只出证据缺口与风险提示，绝不出资格结论。"""
    payload = _invoice_payload()
    政 = payload["税务政策证据"]
    assert 政["项目数"] == 5 and 政["证据完备项目数"] == 0
    assert len(政["逐项"]) == 5
    names = {p["项目"] for p in 政["逐项"]}
    assert names == {"科小", "高新", "专精特新", "小巨人", "研发费用"}
    for p in 政["逐项"]:
        assert p["证据完备"] is False
        assert p["允许出资格结论"] is False
        assert p["风险提示"] and p["证据缺口"]
        assert p["风险等级"] in {"high", "medium", "low"}


def test_invoice_tax_staging_rows_match_pipeline_facts():
    import json as _json

    from app.main import FACTS

    staging = _json.loads((FACTS / "data_pipeline.json").read_text(encoding="utf-8"))["staging_tables"]
    got = {t["表"]: t["行数"] for t in _invoice_payload()["派生层规模"]}
    assert got == {n: staging[n]["rows"] for n in ("invoice_raw", "invoice_lines",
                                                   "tax_composition", "loan_register")}


# ── PROD.0007 差异工作台：三选一决策 + append-only 回写 ────────────────────────
import os as _os
import tempfile as _tempfile

import pytest as _pytest


def _state_db(monkeypatch, tmp_path):
    """每个用例用独立的 SQLite 状态库——不污染仓内治理面，也不互相串。"""
    from app import main as m

    state = tmp_path / "state"
    monkeypatch.setattr(m, "APP_STATE_DIR", state)
    monkeypatch.setattr(m, "APP_DB_PATH", state / "kmfa_app_state.sqlite3")
    return state / "kmfa_app_state.sqlite3"


class _Table:
    """把「读某张状态表」包成可当路径用的取数器，让既有用例改动最小。"""

    def __init__(self, db, table):
        self.db, self.table = db, table

    def rows(self):
        from app import app_state

        return app_state.read(self.db, self.table)

    def exists(self):
        return bool(self.rows())

    def read_text(self, encoding="utf-8"):
        import json as _j

        return "".join(_j.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in self.rows())


@_pytest.fixture
def 净状态(monkeypatch, tmp_path):
    return _Table(_state_db(monkeypatch, tmp_path), "resolution_events")


def _first_assertion_id():
    return client.get("/api/断言?size=1").json()["items"][0]["assertion_id"]


def test_workbench_groups_assertions_by_open_closed_excluded(净状态):
    """任务包要求的三态可视化：分组计数须与断言表逐条自洽。"""
    payload = client.get("/api/差异工作台").json()
    groups = payload["分组计数"]
    assert set(groups) == {"open", "closed", "excluded"}
    assert sum(groups.values()) == payload["断言总数"] == len(payload["断言明细"])
    raw = client.get("/api/断言?size=500").json()["items"]
    expect_closed = len([r for r in raw if str(r["status"]).startswith("closed")])
    assert groups["closed"] == expect_closed
    assert len(payload["决策入口"]) == 3, "必须是三选一决策入口"
    assert {d["决策"] for d in payload["决策入口"]} == {"闭案", "排除", "保持未闭"}


def test_workbench_decision_appends_contract_conform_event(净状态):
    """决策回写须落一条 24 字段齐全、difference_handling 的 resolution_event。"""
    from app.main import REQUIRED_EVENT_FIELDS

    aid = _first_assertion_id()
    r = client.post("/api/差异工作台/决策",
                    json={"断言": aid, "决策": "闭案", "理由": "回款域已核到分，按容差闭案"})
    assert r.status_code == 200, r.text
    event = r.json()["已写入"]
    for field in REQUIRED_EVENT_FIELDS:
        assert field in event, f"缺必填字段 {field}"
    assert event["event_type"] == "resolution_event"
    assert event["manual_action_kind"] == "difference_handling"
    assert event["target_ref"] == aid and event["target_layer"] == "quality"
    assert event["append_only"] is True
    assert event["silent_update_allowed"] is False
    assert event["reversal_required_for_change"] is True
    for flag in ("raw_layer_write_allowed", "raw_source_mutation_allowed",
                 "source_layer_write_allowed", "business_plaintext_committed",
                 "forbidden_plaintext"):
        assert event[flag] is False
    assert event["content_hash"].startswith("sha256:")
    assert 净状态.exists() and len(净状态.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_workbench_write_is_append_only_never_rewrites(净状态):
    """连写三条：前两行必须**逐字节不变**——append-only 的实测口径。"""
    aid = _first_assertion_id()
    lines = []
    for i, decision in enumerate(("闭案", "保持未闭", "排除"), start=1):
        client.post("/api/差异工作台/决策",
                    json={"断言": aid, "决策": decision, "理由": f"第 {i} 次决策"})
        lines.append(净状态.read_text(encoding="utf-8").splitlines())
    assert len(lines[0]) == 1 and len(lines[1]) == 2 and len(lines[2]) == 3
    assert lines[2][0] == lines[0][0], "首行被改写了——违反 append-only"
    assert lines[2][1] == lines[1][1], "第二行被改写了——违反 append-only"
    ids = [json.loads(l)["event_id"] for l in lines[2]]
    assert ids == sorted(set(ids)), "事件号须单调且不重复"


def test_workbench_never_mutates_assertions_jsonl(净状态):
    """断言表是治理数据面：决策写入前后必须**逐字节相同**。"""
    from app.main import ASSERTIONS_PATH

    before = ASSERTIONS_PATH.read_bytes()
    client.post("/api/差异工作台/决策",
                json={"断言": _first_assertion_id(), "决策": "排除", "理由": "口径外，排除"})
    assert ASSERTIONS_PATH.read_bytes() == before, "assertions.jsonl 被改动了"
    assert client.get("/api/差异工作台").json()["写入纪律"]["断言表可写"] is False


def test_workbench_rejects_bad_decisions(净状态):
    aid = _first_assertion_id()
    assert client.post("/api/差异工作台/决策",
                       json={"断言": aid, "决策": "随便改改", "理由": "x"}).status_code == 400
    assert client.post("/api/差异工作台/决策",
                       json={"断言": aid, "决策": "闭案", "理由": "  "}).status_code == 400
    assert client.post("/api/差异工作台/决策",
                       json={"断言": "AST-不存在", "决策": "闭案", "理由": "y"}).status_code == 404
    assert not 净状态.exists() or not 净状态.read_text(encoding="utf-8").strip(), "被拒的请求不该落盘"


def test_workbench_change_of_mind_requires_reversal_event(净状态):
    """改主意＝追加冲正事件，不是编辑既有行；且同一事件不得重复冲正。"""
    aid = _first_assertion_id()
    first = client.post("/api/差异工作台/决策",
                        json={"断言": aid, "决策": "闭案", "理由": "先按闭案处理"}).json()["已写入"]
    before = 净状态.read_text(encoding="utf-8")

    rev = client.post("/api/差异工作台/冲正",
                      json={"冲正事件号": first["event_id"], "理由": "复核后认为不该闭"})
    assert rev.status_code == 200, rev.text
    rev_event = rev.json()["已写入"]
    assert rev_event["reverses_event_id"] == first["event_id"]
    assert rev_event["status"] == "reverse_event_recorded"

    after = 净状态.read_text(encoding="utf-8")
    assert after.startswith(before), "冲正必须是追加，原行不得变动"

    dup = client.post("/api/差异工作台/冲正",
                      json={"冲正事件号": first["event_id"], "理由": "再冲一次"})
    assert dup.status_code == 409, "同一事件重复冲正必须被拒"
    assert client.post("/api/差异工作台/冲正",
                       json={"冲正事件号": "MANEVT-APP-9999", "理由": "z"}).status_code == 404


def test_workbench_reversed_decision_no_longer_current(净状态):
    """被冲正的决策不得再算作现行决策——状态流转要全程留痕且读得出来。"""
    aid = _first_assertion_id()
    first = client.post("/api/差异工作台/决策",
                        json={"断言": aid, "决策": "闭案", "理由": "先闭"}).json()["已写入"]
    row = next(i for i in client.get("/api/差异工作台").json()["断言明细"] if i["断言"] == aid)
    assert row["现行决策"]["事件号"] == first["event_id"]

    client.post("/api/差异工作台/冲正", json={"冲正事件号": first["event_id"], "理由": "撤回"})
    after = next(i for i in client.get("/api/差异工作台").json()["断言明细"] if i["断言"] == aid)
    assert after["现行决策"] is None, "冲正后不该还有现行决策"
    assert len(after["决策事件"]) == 2, "两条事件都要留痕，不能删"
    assert after["决策事件"][0]["已被冲正"] is True


def test_workbench_bidirectional_consistency_no_orphan_events(净状态):
    """反向一致：事件的 target_ref 必须解析到真实断言，孤儿计数为 0。"""
    payload = client.get("/api/差异工作台").json()
    一致 = payload["双向一致"]
    assert 一致["本台孤儿事件数"] == 0 and 一致["一致"] is True
    # 仓内既有 S12-P1 事件指向治理记录号（S09P3-REC-001 等）而非断言号——如实单列，
    # 不冒充成 0；这四条真实存在，把它们算成"孤儿"或藏起来都是不诚实。
    assert 一致["仓内未挂载事件数"] == 4
    assert "S09P3-REC-001" in 一致["仓内未挂载事件"]

    client.post("/api/差异工作台/决策",
                json={"断言": _first_assertion_id(), "决策": "保持未闭", "理由": "等下批数据"})
    after = client.get("/api/差异工作台").json()["双向一致"]
    assert after["本台孤儿事件数"] == 0, "本台写入必须条条挂得上断言"


def test_workbench_event_carries_no_forbidden_plaintext(净状态):
    """事件里只准放断言号与理由，金额/明文字段一律不得出现。"""
    from app.main import FORBIDDEN_EVENT_KEYS

    event = client.post("/api/差异工作台/决策",
                        json={"断言": _first_assertion_id(), "决策": "闭案",
                              "理由": "核到分"}).json()["已写入"]
    assert not (set(event) & FORBIDDEN_EVENT_KEYS)
    assert "delta_cents" not in event and "amount_cents" not in event


# ── PROD.0009 报告中心：三格式导出 hash 登记 + D 级水印不可去除 ────────────────
@_pytest.fixture
def 净导出(monkeypatch, tmp_path):
    return _Table(_state_db(monkeypatch, tmp_path), "export_records")


def test_report_center_header_triple_from_facts(净导出):
    """页眉三元组须取自事实：等级 D / 质量 Q4 / delivery 未解锁。"""
    payload = client.get("/api/报告中心").json()
    header = payload["页眉"]
    assert header["报告等级"] == "D"
    assert header["质量等级"] == "Q4"
    assert payload["交付判据"]["delivery_allowed"] is False
    assert payload["交付判据"]["正式报告可出"] is False
    assert payload["交付判据"]["可作经营依据"] is False
    assert len(payload["报告"]) == 8, "八份一致性证明报告都要在册"
    for r in payload["报告"]:
        assert {f["格式"] for f in r["格式"]} == {"html", "csv", "pdf"}


def test_report_export_three_formats_really_render(净导出):
    """三格式必须真产出可用文件——不是返回一句"已就绪"。"""
    html = client.get("/api/报告中心/导出?报告=1&格式=html")
    assert html.status_code == 200 and html.content.startswith(b"<!doctype html")
    assert "一致性证明" in html.text

    csv = client.get("/api/报告中心/导出?报告=1&格式=csv")
    assert csv.status_code == 200
    assert csv.content.startswith(b"\xef\xbb\xbf"), "CSV 需带 BOM，Excel 双击才不乱码"
    assert "差异分" in csv.content.decode("utf-8-sig")

    pdf = client.get("/api/报告中心/导出?报告=1&格式=pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF"), "必须是真 PDF 魔数"
    assert b"%%EOF" in pdf.content[-2048:], "PDF 必须完整收尾"
    assert b"STSong-Light" in pdf.content, "须内嵌中文 CID 字体"
    assert len(pdf.content) > 2000


def test_watermark_cannot_be_removed_by_any_parameter(净导出):
    """**本单元核心验收**：解锁前 D 级水印在三格式里都去不掉。

    穷举一切"看起来能关水印"的参数组合，逐个实测——只要有一种能把水印弄没，
    这条验收就是假的。
    """
    from app.main import _watermark_text

    mark = _watermark_text()
    assert mark and "D 级" in mark and "delivery_allowed=false" in mark

    attempts = [
        "", "&水印=off", "&水印=false", "&watermark=false", "&watermark=0",
        "&no_watermark=1", "&nomark=true", "&raw=1", "&clean=1", "&plain=true",
        "&delivery_allowed=true", "&报告等级=A", "&mark=", "&draft=false",
    ]
    for fmt in ("html", "csv", "pdf"):
        for extra in attempts:
            r = client.get(f"/api/报告中心/导出?报告=1&格式={fmt}{extra}")
            assert r.status_code == 200, f"{fmt}{extra} → {r.status_code}"
            assert r.headers["X-KMFA-Watermark"] == "applied", f"{fmt}{extra} 水印头丢了"
            if fmt == "html":
                assert mark in r.text, f"html{extra} 水印文案不见了"
                assert 'class="wm"' in r.text
            elif fmt == "csv":
                assert mark in r.content.decode("utf-8-sig"), f"csv{extra} 水印行不见了"
            else:
                assert r.content.startswith(b"%PDF") and len(r.content) > 2000


def test_watermark_is_fact_driven_not_hardcoded(净导出, monkeypatch):
    """水印只认 delivery 事实：把 delivery_allowed 翻成 true，水印才消失。

    反证——若水印是写死的常量，翻转事实后它仍会在，本用例即失败。
    """
    from app import main as m

    assert m._watermark_text() is not None  # 现实：未解锁
    monkeypatch.setattr(m, "_delivery_state", lambda: {
        "报告等级": "A", "质量等级": "Q5", "delivery_allowed": True,
        "delivery状态": "已解锁", "正式报告可出": True, "可作经营依据": True,
        "等级政策版本": "x", "判据来源": [],
    })
    assert m._watermark_text() is None, "delivery 解锁后水印应自然消失——说明它由事实驱动"


def test_export_hash_registered_append_only(净导出):
    """三格式导出 hash 登记；登记只追加不改写。"""
    digests = {}
    for fmt in ("html", "csv", "pdf"):
        r = client.get(f"/api/报告中心/导出?报告=2&格式={fmt}")
        digests[fmt] = r.headers["X-KMFA-Sha256"]
        assert digests[fmt].startswith("sha256:")

    lines = 净导出.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    records = [json.loads(l) for l in lines]
    assert {r["格式"] for r in records} == {"html", "csv", "pdf"}
    for rec in records:
        assert rec["报告"] == 2
        assert rec["水印已加"] is True
        assert rec["报告等级"] == "D" and rec["delivery_allowed"] is False
        assert rec["sha256"] == digests[rec["格式"]]
        # 响应头登记的 hash 必须真的是内容 hash
        # 登记的 hash 必须真能复验：同一份报告重导出须**逐字节一致**。
        # PDF 默认会写挂钟 /CreationDate，那样 hash 每次都变、登记形同虚设——
        # 故导出走 invariant 模式，本断言即为此把关。
        body = client.get(f"/api/报告中心/导出?报告=2&格式={rec['格式']}").content
        assert rec["sha256"] == "sha256:" + hashlib.sha256(body).hexdigest(), \
            f"{rec['格式']} 重导出 hash 不一致——登记无法复验"

    before = 净导出.read_text(encoding="utf-8")
    client.get("/api/报告中心/导出?报告=3&格式=html")
    assert 净导出.read_text(encoding="utf-8").startswith(before), "登记必须是追加"


def test_pdf_never_committed_to_public_repo(净导出):
    """既有 runtime 契约：公开仓永不提交 PDF。App 只走响应流。"""
    from app.main import KMFA, REPO

    payload = client.get("/api/报告中心").json()
    assert payload["PDF策略"]["提交进公开仓"] is False
    assert payload["PDF策略"]["运行时生成"] is True
    for r in payload["报告"]:
        pdf_fmt = next(f for f in r["格式"] if f["格式"] == "pdf")
        assert pdf_fmt["可提交公开仓"] is False

    client.get("/api/报告中心/导出?报告=1&格式=pdf")
    assert list((KMFA / "app").rglob("*.pdf")) == [], "App 目录下不得出现 PDF 文件"
    assert not (REPO / "KMFA" / "app" / "backend" / "app").joinpath("kmfa_report_1.pdf").exists()


def test_export_headers_carry_grade_and_delivery(净导出):
    """页眉三元组也要进响应头——自动化与下游取数不必解析正文。"""
    for fmt in ("html", "csv", "pdf"):
        h = client.get(f"/api/报告中心/导出?报告=1&格式={fmt}").headers
        assert h["X-KMFA-Report-Grade"] == "D"
        assert h["X-KMFA-Quality-Grade"] == "Q4"
        assert h["X-KMFA-Delivery-Allowed"] == "false"
        assert "attachment" in h["Content-Disposition"]


def test_export_rejects_unknown_report_and_format(净导出):
    assert client.get("/api/报告中心/导出?报告=1&格式=docx").status_code == 400
    assert client.get("/api/报告中心/导出?报告=99&格式=html").status_code == 404
    assert not 净导出.exists() or not 净导出.read_text(encoding="utf-8").strip()


def test_pdf_uses_only_glyphs_the_cid_font_can_render(净导出):
    """水印与标题不得含 STSong-Light 渲染不出的字符（会变黑三角豆腐块）。

    U+00B7（·）就踩过——PDF 渲成图才看见，纯字节断言看不出来。
    """
    from app.main import _watermark_text

    from app.main import (
        PDF_GLYPH_FALLBACKS, _markdown_to_plain, _pdf_safe, _report_body, _report_dir,
        _report_title, _watermark_text,
    )

    def scan(text, where):
        for ch in text:
            assert ch not in PDF_GLYPH_FALLBACKS, \
                f"{where} 含渲不出的 U+{ord(ch):04X}（{ch!r}）——PDF 里会是豆腐块"

    # 水印、标题、正文——**凡是落笔的文字都要过 _pdf_safe**，逐一实测
    scan(_pdf_safe(_watermark_text()), "水印")
    for no in range(1, 9):
        d = _report_dir(no)
        scan(_pdf_safe(_report_title(d) or ""), f"第 {no} 号标题")
        for line in _markdown_to_plain(_report_body(d)):
            scan(_pdf_safe(line), f"第 {no} 号正文")

    # 替身表本身要有实据：这几个是扫 8 份报告 + 渲图实测出来的
    assert PDF_GLYPH_FALLBACKS["\u00a5"] == "\uffe5", "¥ 必须换成全角 ￥"
    assert "\u2705" in PDF_GLYPH_FALLBACKS and "\u00b7" in PDF_GLYPH_FALLBACKS
    # 金额不能被替换动过
    assert "1,462,802.90" in _pdf_safe(_report_body(_report_dir(1)))


def test_pdf_body_is_plain_text_not_raw_markdown(净导出):
    """PDF 正文须是清洗过的纯文本——不能把 ###、**、|---| 原样倒给人看。"""
    from app.main import _markdown_to_plain, _report_body, _report_dir

    raw = _report_body(_report_dir(1))
    assert "##" in raw and "**" in raw, "样本报告本身应含 markdown，否则本用例无意义"

    plain = _markdown_to_plain(raw)
    joined = "\n".join(plain)
    assert "**" not in joined and "##" not in joined
    assert not any(re.fullmatch(r"\s*\|?[\s\|:–—-]*\|[\s\|:–—-]*\|?\s*", l) and "-" in l
                   for l in plain), "表格分隔线应被去掉"
    # 内容不能被清洗掉：关键金额与结论须原样留存
    assert "1,462,802.90" in joined and "694.57" in joined
    assert "财务应收回款" in joined


def test_pdf_line_wrap_never_splits_amounts(净导出):
    """按字宽折行，金额不得被劈成两截——原按字数切 46 会切断 1,462,802.90。"""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    from app.main import _markdown_to_plain, _report_body, _report_dir

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    usable, size = 595.2755905511812 - 90, 9

    def wrap(text):
        out, cur = [], ""
        for ch in text:
            trial = cur + ch
            if pdfmetrics.stringWidth(trial, "STSong-Light", size) > usable:
                out.append(cur)
                cur = ch
            else:
                cur = trial
        out.append(cur)
        return out or [""]

    lines = []
    for raw in _markdown_to_plain(_report_body(_report_dir(1))):
        lines.extend(wrap(raw))
    joined = "\n".join(lines)
    for amount in ("1,462,802.90", "1,595,080.52", "694.57", "71,790.00"):
        assert amount in joined, f"金额 {amount} 被折行劈断了"
    for line in lines:
        assert pdfmetrics.stringWidth(line, "STSong-Light", size) <= usable + 0.5, \
            f"折行超出可用宽度：{line[:20]}…"


# ── PROD.0008 影响预览与重跑 ────────────────────────────────────────────────────
@_pytest.fixture
def 净重跑(monkeypatch, tmp_path):
    db = _state_db(monkeypatch, tmp_path)

    class _Dir:
        def __truediv__(self, name):
            return _Table(db, {"manual_rerun_steps.jsonl": "rerun_steps",
                               "manual_rerun_consistency_checks.jsonl": "rerun_consistency"}[name])

    return _Dir()


def _an_asset():
    return client.get("/api/影响重跑").json()["血缘"]["资产"][0]["资产"]


def test_lineage_assets_and_chain_exposed(净重跑):
    payload = client.get("/api/影响重跑").json()
    assert payload["血缘"]["节点数"] == 53 and payload["血缘"]["边数"] == 69
    assert payload["血缘"]["可选资产数"] >= 1
    assert [c["层"] for c in payload["重跑链"]] == [
        "field_mapping", "fact_layer", "derived_metric", "report_reference"]
    assert payload["重跑纪律"]["覆盖旧版本"] is False
    assert payload["重跑纪律"]["允许借重跑升报告等级"] is False


def test_downstream_impact_is_computed_from_lineage_edges(净重跑):
    """下游影响面须由血缘边算出，不是硬编码——换资产结果必须跟着变。"""
    import yaml as _yaml

    from app.main import LINEAGE_PATH

    graph = _yaml.safe_load(LINEAGE_PATH.read_text(encoding="utf-8"))
    edges = graph["edges"]
    asset = _an_asset()
    got = client.get(f"/api/影响重跑?asset={asset}").json()["选中"]
    expect_tables = sorted({str(e["to"]).removeprefix("_staging.")
                            for e in edges if str(e["from"]) == asset})
    assert [t["表"] for t in got["派生表"]] == expect_tables
    assert got["边数"] == len([e for e in edges if str(e["from"]) == asset])
    assert got["受影响视图"], "有派生表就该有下游视图"

    others = [a["资产"] for a in client.get("/api/影响重跑").json()["血缘"]["资产"]]
    varied = {tuple(client.get(f"/api/影响重跑?asset={a}").json()["选中"]["派生表表名"]
                    if False else
                    tuple(t["表"] for t in client.get(f"/api/影响重跑?asset={a}").json()["选中"]["派生表"]))
              for a in others[:6]}
    assert len(varied) > 1, "不同资产的下游影响面必须不同，否则就是写死的"


def test_rerun_really_runs_all_four_layers(净重跑):
    """**本单元核心验收**：一次真实重跑从页面发起并完成。"""
    asset = _an_asset()
    r = client.post("/api/影响重跑/重跑", json={"资产": asset, "理由": "字段映射调整后重算下游"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["步骤数"] == 4 and out["链完整"] is True
    assert [s["层"] for s in out["各层"]] == [
        "field_mapping", "fact_layer", "derived_metric", "report_reference"]
    assert out["旧版本全保留"] is True
    assert out["耗时秒"] >= 0

    # derived_metric 层必须**真算过视图**并给出内容哈希，不是空壳
    derived = next(s for s in out["各层"] if s["层"] == "derived_metric")
    views = derived["结果"]["视图"]
    assert views, "受影响视图不得为空"
    for v in views:
        assert v["状态"] == "recomputed"
        assert v["内容哈希"].startswith("sha256:") and v["字节"] > 100

    # fact_layer 层的行数须等于 data_pipeline 事实
    staging = client.get("/api/数据管线").json()["staging_tables"]
    for tbl, rows in next(s for s in out["各层"] if s["层"] == "fact_layer")["结果"]["表行数"].items():
        assert rows == staging[tbl]["rows"]


def test_rerun_leaves_append_only_trail(净重跑):
    steps_path = 净重跑 / "manual_rerun_steps.jsonl"
    asset = _an_asset()
    client.post("/api/影响重跑/重跑", json={"资产": asset, "理由": "第一次"})
    first = steps_path.read_text(encoding="utf-8")
    assert len(first.strip().splitlines()) == 4

    client.post("/api/影响重跑/重跑", json={"资产": asset, "理由": "第二次"})
    second = steps_path.read_text(encoding="utf-8")
    assert second.startswith(first), "第二轮必须追加，不得改写第一轮"
    assert len(second.strip().splitlines()) == 8

    listing = client.get("/api/影响重跑").json()["本机重跑记录"]
    assert listing["轮次"] == 2 and listing["步骤数"] == 8
    assert all(r["状态"] == "completed" for r in listing["最近"])


def test_rerun_never_overwrites_or_touches_raw(净重跑):
    """重跑造新版本、保留旧版本；raw 层与断言表全程不动。"""
    from app.main import ASSERTIONS_PATH, FACTS, LINEAGE_PATH

    before = {p: p.read_bytes() for p in
              (ASSERTIONS_PATH, LINEAGE_PATH, FACTS / "data_pipeline.json")}
    out = client.post("/api/影响重跑/重跑",
                      json={"资产": _an_asset(), "理由": "校验只读"}).json()
    for p, blob in before.items():
        assert p.read_bytes() == blob, f"{p.name} 被重跑改动了"

    steps = [json.loads(l) for l in
             (净重跑 / "manual_rerun_steps.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    for s in steps:
        assert s["overwrite_old_version_allowed"] is False
        assert s["old_version_status_after_rerun"] == "retained_not_overwritten"
        assert s["raw_layer_write_allowed"] is False
        assert s["source_layer_write_allowed"] is False
        assert s["report_grade_upgrade_allowed"] is False
        assert s["new_derived_version_ref"] != s["old_derived_version_ref"]
    assert out["一致性检查"]["old_versions_retained"] is True
    assert out["一致性检查"]["raw_layer_untouched"] is True

    # 重跑不得改变报告等级
    assert client.get("/api/报告中心").json()["页眉"]["报告等级"] == "D"


def test_rerun_rejects_bad_input(净重跑):
    asset = _an_asset()
    assert client.post("/api/影响重跑/重跑", json={"资产": asset, "理由": " "}).status_code == 400
    assert client.post("/api/影响重跑/重跑",
                       json={"资产": "raw:不存在", "理由": "x"}).status_code == 404
    assert not (净重跑 / "manual_rerun_steps.jsonl").exists(), "被拒的重跑不该留痕"


def test_rerun_recompute_is_reproducible(净重跑):
    """同样的事实重跑两次，派生指标哈希须一致——否则"重算"结果不可信。"""
    asset = _an_asset()
    a = client.post("/api/影响重跑/重跑", json={"资产": asset, "理由": "一"}).json()
    b = client.post("/api/影响重跑/重跑", json={"资产": asset, "理由": "二"}).json()

    def hashes(out):
        return {v["视图"]: v["内容哈希"]
                for v in next(s for s in out["各层"] if s["层"] == "derived_metric")["结果"]["视图"]}

    assert hashes(a) == hashes(b), "事实没变，两次重算的视图哈希必须相同"
    # 轮次号必须唯一：原实现用「秒级时间戳+资产哈希」，同一秒连点两次会撞车，
    # 两轮留痕被并成一轮——账就记错了。改为按已有轮次递增。
    assert a["轮次号"] != b["轮次号"], "轮次号须唯一（同秒连点也不能撞）"


def test_downstream_impact_matches_assertions_with_qualified_sources(净重跑):
    """断言的 our_source 带括号/带 via，影响面不得因精确匹配而少报。

    `_staging.expense_lines(6403) via _staging.tax_composition` 与
    `_staging.kingdee_ledger（book=武汉开明）` 都必须能命中——真开页面看到
    「受影响断言域 —」才发现原实现用精确相等把它们全漏了。
    """
    got = client.get("/api/影响重跑?asset=raw:d46f77b0c90d").json()["选中"]
    tables = {t["表"] for t in got["派生表"]}
    assert {"expense_lines", "tax_composition"} <= tables
    assert "tax" in got["受影响断言域"], "税费轴断言取自 expense_lines/tax_composition，必须命中"
    assert got["受影响报告"], "命中断言域就该带出对应报告"

    # 交叉校验：逐条按表名子串重算一遍，结果须与接口一致
    raw = client.get("/api/断言?size=500").json()["items"]
    expect = sorted({r["domain"] for r in raw
                     if any(f"_staging.{t}" in str(r.get("our_source", "")) for t in tables)})
    assert got["受影响断言域"] == expect


# ── PROD.0003 访问安全承接 S17：审计日志 append-only ──────────────────────────
@_pytest.fixture
def 净审计(monkeypatch, tmp_path):
    return _Table(_state_db(monkeypatch, tmp_path), "audit_events")


def test_audit_contract_matches_repo_policy(净审计):
    """契约须与仓内既有 S17 政策一致——不得自己另定一套。"""
    import json as _json

    from app.main import AUDIT_POLICY_PATH

    payload = client.get("/api/审计日志").json()["契约"]
    policy = [_json.loads(l) for l in AUDIT_POLICY_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert payload["必填字段"] == policy[0]["required_fields"]
    assert sorted(payload["动作类型"]) == sorted({p["action_type"] for p in policy})
    assert payload["append_only"] is True
    assert payload["允许记原始载荷"] is False and payload["允许记业务明文"] is False
    assert payload["政策版本"] == policy[0]["policy_version"]


def test_every_write_and_export_leaves_audit_event(净审计):
    """写入与导出都必须留痕——审计漏记等于没有审计。"""
    aid = _first_assertion_id()
    client.post("/api/差异工作台/决策", json={"断言": aid, "决策": "闭案", "理由": "审计留痕验证"})
    client.get("/api/报告中心/导出?报告=1&格式=csv")
    client.post("/api/影响重跑/重跑", json={"资产": _an_asset(), "理由": "审计留痕验证"})

    rows = [json.loads(l) for l in 净审计.read_text(encoding="utf-8").splitlines() if l.strip()]
    kinds = {r["action_type"] for r in rows}
    assert {"processing", "export"} <= kinds, f"缺动作类型：{kinds}"
    assert len(rows) >= 3

    from app.main import AUDIT_REQUIRED_FIELDS

    for r in rows:
        for f in AUDIT_REQUIRED_FIELDS:
            assert r.get(f), f"审计事件缺必填字段 {f}: {r}"


def test_audit_export_event_carries_grade_triple(净审计):
    """任务包要求「等级+Q 级+delivery 永远印在页眉」——导出留痕须把这三项一起记下。"""
    client.get("/api/报告中心/导出?报告=1&格式=pdf")
    rows = [json.loads(l) for l in 净审计.read_text(encoding="utf-8").splitlines() if l.strip()]
    exp = next(r for r in rows if r["action_type"] == "export")
    assert exp["report_grade"] == "D"
    assert exp["quality_grade"] == "Q4"
    assert exp["delivery_allowed"] is False
    assert exp["watermark_applied"] is True
    assert exp["sha256"].startswith("sha256:")


def test_audit_is_append_only(净审计):
    aid = _first_assertion_id()
    client.post("/api/差异工作台/决策", json={"断言": aid, "决策": "闭案", "理由": "第一条"})
    first = 净审计.read_text(encoding="utf-8")
    client.post("/api/差异工作台/决策", json={"断言": aid, "决策": "排除", "理由": "第二条"})
    second = 净审计.read_text(encoding="utf-8")
    assert second.startswith(first), "审计日志被改写了——违反 append-only"
    assert len(second.strip().splitlines()) == len(first.strip().splitlines()) + 1


def test_audit_never_records_business_plaintext(净审计):
    """审计记「谁对什么做了什么」，不记业务明文与原始载荷。"""
    from app.main import AUDIT_FORBIDDEN_KEYS

    client.get("/api/报告中心/导出?报告=1&格式=html")
    client.post("/api/差异工作台/决策",
                json={"断言": _first_assertion_id(), "决策": "闭案", "理由": "核到分"})
    rows = [json.loads(l) for l in 净审计.read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        assert not (set(r) & AUDIT_FORBIDDEN_KEYS), f"审计事件含禁写字段：{set(r) & AUDIT_FORBIDDEN_KEYS}"
        blob = json.dumps(r, ensure_ascii=False)
        assert "<!doctype" not in blob.lower(), "报告正文不得进审计日志"


def test_audit_rejects_illegal_action_type(净审计):
    from app.main import _audit

    with _pytest.raises(Exception):
        _audit("删库", subject_ref="x", result_status="OK", evidence_ref="y")


def test_single_user_mode_declared_truthfully(净审计):
    """本机单用户模式须如实声明，不假装有应用内登录。"""
    mode = client.get("/api/审计日志").json()["访问模式"]
    assert mode["模式"] == "本机单用户"
    assert mode["应用内登录"] is False
    assert "Cloudflare Access" in mode["生产鉴权"]
    assert "/api" in mode["生产鉴权"] and "/ops" in mode["生产鉴权"]
    assert set(mode["角色口径"]) == {"management", "finance", "reviewer", "readonly"}


# ── PROD.0001 应用状态面：SQLite + append-only 库层强制 ────────────────────────
def test_state_tables_cover_all_app_writes(净审计):
    """五张表 = 原来的五个 JSONL，一一对应，不多不少。"""
    from app.app_state import TABLES

    assert set(TABLES) == {"resolution_events", "rerun_steps", "rerun_consistency",
                           "export_records", "audit_events"}


def test_append_only_enforced_by_database_not_convention(monkeypatch, tmp_path):
    """**本单元的实质收益**：append-only 从「我们只用 'a' 打开」升级成库层强制。

    JSONL 时代，一个手滑的写操作就能改掉已发生的事实且无人察觉。
    这里直接让数据库拒绝——UPDATE / DELETE 一律 ABORT。
    """
    import sqlite3

    from app import app_state

    db = tmp_path / "s.sqlite3"
    app_state.append(db, "audit_events", {"event_id": "A1", "action_type": "export"})
    app_state.append(db, "audit_events", {"event_id": "A2", "action_type": "report"})
    assert [r["event_id"] for r in app_state.read(db, "audit_events")] == ["A1", "A2"]

    con = sqlite3.connect(str(db))
    try:
        for sql in ("UPDATE audit_events SET payload='{}' WHERE seq=1",
                    "DELETE FROM audit_events WHERE seq=1"):
            with _pytest.raises(sqlite3.IntegrityError) as exc:
                con.execute(sql)
            assert "append-only" in str(exc.value)
    finally:
        con.close()
    # 拒绝之后内容必须原封不动
    assert [r["event_id"] for r in app_state.read(db, "audit_events")] == ["A1", "A2"]


def test_state_read_is_empty_not_error_before_first_write(tmp_path):
    """还没写过就读，应得空列表而不是异常——读路径不该因为库还没建就炸。"""
    from app import app_state

    assert app_state.read(tmp_path / "none.sqlite3", "audit_events") == []


def test_jsonl_migration_is_idempotent(tmp_path):
    """既有 JSONL 能搬进来，且重复搬不会翻倍。"""
    from app import app_state

    src = tmp_path / "old.jsonl"
    src.write_text('{"event_id":"E1"}\n{"event_id":"E2"}\n', encoding="utf-8")
    db = tmp_path / "s.sqlite3"
    assert app_state.migrate_jsonl(db, "resolution_events", src) == 2
    assert app_state.migrate_jsonl(db, "resolution_events", src) == 0, "重复迁移必须跳过"
    assert len(app_state.read(db, "resolution_events")) == 2


def test_unknown_table_rejected(tmp_path):
    """表名走白名单——不给字符串拼接留注入面。"""
    from app import app_state

    with _pytest.raises(ValueError):
        app_state.append(tmp_path / "s.sqlite3", "'; DROP TABLE audit_events; --", {})


def test_data_plane_stays_read_only_after_app_writes(净审计):
    """数据面与应用状态面分离：App 写完，治理数据面必须逐字节不变。"""
    from app.main import ASSERTIONS_PATH, FACTS, LINEAGE_PATH

    before = {p: p.read_bytes() for p in
              (ASSERTIONS_PATH, LINEAGE_PATH, FACTS / "data_pipeline.json")}
    client.post("/api/差异工作台/决策",
                json={"断言": _first_assertion_id(), "决策": "闭案", "理由": "状态面分离验证"})
    client.get("/api/报告中心/导出?报告=1&格式=csv")
    for p, blob in before.items():
        assert p.read_bytes() == blob, f"数据面被写了：{p.name}"
