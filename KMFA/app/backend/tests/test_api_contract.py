"""TSK.KMFA.PROD.0002 契约测试：后端数据 API 的 OpenAPI 契约与真实数据形态。

铁律：本文件断言的全部是**真实仓内数据**（machine/facts、machine/lineage.yaml、
metadata/quality/assertions.jsonl、stage_artifacts 八份报告），不使用 mock/占位——
本线曾犯「用健康检查冒充完备性」的错，契约测试必须咬住真实内容。
"""
import json
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
    schema = client.get("/openapi.json").json()
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
