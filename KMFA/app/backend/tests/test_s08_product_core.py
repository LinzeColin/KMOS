# -*- coding: utf-8 -*-
"""S08 —— 产品核心：项目/检索/发布/统计与迁移。

| 任务 | 验收 | pass_gate |
|---|---|---|
| T-S08-01 | AC-PROD-001 | 核心 CRUD/恢复一致，**冲突不静默丢失** |
| T-S08-02 | AC-PROD-002 | **私密命中=0**，相关性与 P95 达阈值 |
| T-S08-03 | AC-PROD-003 | **默认公开命中=0**；白名单外字段=0；撤销在 SLA 内 |
| T-S08-04 | AC-PROD-004 / AC-MIG-001 | 核心事件可用≥99%、**敏感命中=0**；迁移差异=0 且回滚通过 |

## 每条 pass_gate 都测「反向」，不只测「正向」

正向（功能能用）人人会写。真正决定这些门禁成立与否的是反向：
冲突时用户的输入还在不在、检索谓词被改坏时会不会静默泄露、
新增字段会不会默认公开、事件里混进原值会不会被写进去。
"""
from __future__ import annotations

import time

import pytest

from app import privacy_analytics as PA
from app import publication as PUB
from app import workspace_projects as WP
from app import workspace_search as WS


# ═════════ T-S08-01 冲突不静默丢失 ═════════

def test_conflict_hands_the_user_input_back():
    """**本组最重要的一条。**

    只回一个 409 不算达成 pass_gate：丢失并没有消失，只是从服务端搬到了客户端——
    用户敲了十分钟的东西，一刷新就没了。
    """
    with pytest.raises(WP.ProjectError) as caught:
        WP.check_version(expected=3, current=7,
                         submitted={"progress": 80, "note": "敲了十分钟的备注"},
                         current_state={"progress": 45})
    error = caught.value
    assert error.status_code == 409
    assert error.code == "version_conflict"
    assert error.payload["submitted"]["note"] == "敲了十分钟的备注", "用户的输入丢了"
    assert error.payload["current"] == {"progress": 45}, "没告诉他冲突在哪"
    assert error.payload["row_version"] == 7, "没给重试要用的版本号"


def test_writing_without_a_version_is_refused_not_last_write_wins():
    """不带版本号的写入必须拒绝。「后写者赢」把丢失变成**静默的**：
    两个人同时改，一个人的改动消失，谁都不会收到提示。"""
    with pytest.raises(WP.ProjectError) as caught:
        WP.check_version(expected=None, current=2, submitted={"progress": 1},
                         current_state={"progress": 9})
    assert caught.value.status_code == 428
    assert caught.value.payload["row_version"] == 2, "拒绝时要顺手给版本号，省一次往返"


def test_matching_version_passes():
    WP.check_version(expected=5, current=5, submitted={}, current_state={})


@pytest.mark.parametrize("bad", [1.5, "50", True, None, -1, 101])
def test_progress_rejects_non_integer_and_out_of_range(bad):
    """浮点进度会出现「拖到 100% 却显示 99%」——
    成因与金额里的浮点误差完全相同。"""
    with pytest.raises(WP.ProjectError):
        WP.validate_progress(bad)


@pytest.mark.parametrize("bad", [1.5, "80", True, None, -1, 101])
def test_score_rejects_non_integer_and_out_of_range(bad):
    with pytest.raises(WP.ProjectError):
        WP.validate_score(bad)


def test_sort_order_never_collides_after_a_delete():
    """用 `len()+1` 的话，删掉中间一条再插入就会和现存的某条撞号，
    而撞号之后两条的相对顺序由数据库返回顺序决定——也就是不确定。"""
    existing = [{"sort_order": 10}, {"sort_order": 20}, {"sort_order": 30}]
    del existing[1]  # 删掉中间一条
    assert WP.next_sort_order(existing) == 40
    assert WP.next_sort_order([]) == 10


def test_reorder_demands_every_id():
    """只给一部分的话，没给到的那些排在哪里由实现决定——
    在用户眼里就是顺序自己变了。"""
    existing = [{"task_id": "a"}, {"task_id": "b"}, {"task_id": "c"}]
    assert WP.plan_step_reorder(order=["c", "a", "b"], existing=existing) == [
        ("c", 10), ("a", 20), ("b", 30)]
    with pytest.raises(WP.ProjectError) as caught:
        WP.plan_step_reorder(order=["c", "a"], existing=existing)
    assert caught.value.payload["missing"] == ["b"]


def test_step_title_rejects_control_characters():
    """控制字符在日志与终端里会改变显示，让人看到的和存下来的不是同一个东西。"""
    for bad in ("标题\x00截断", "标题\x1b[31m", "标题\r\n伪造行"):
        with pytest.raises(WP.ProjectError):
            WP.validate_title(bad)
    assert WP.validate_title("  正常标题  ") == "正常标题"


def test_step_quota_is_bounded():
    with pytest.raises(WP.ProjectError) as caught:
        WP.plan_step_insert(title="x", existing=[{}] * WP.MAX_STEPS_PER_WORKSPACE)
    assert caught.value.code == "step_quota_exhausted"


def test_artifact_link_is_a_reference_to_something_real():
    """关联只存引用不存副本——复制会立刻产生「副本与原件不一致」，
    而 T-S06-03 用一整个任务保证血缘无断点。"""
    assert WP.link_artifact(artifact_version_id="art/v1",
                            known_versions={"art/v1"}) == "art/v1"
    with pytest.raises(WP.ProjectError) as caught:
        WP.link_artifact(artifact_version_id="art/v9", known_versions={"art/v1"})
    assert caught.value.status_code == 404


def test_view_always_carries_row_version():
    """不给版本号就等于逼着对方先读一次再写，而那一读一写之间正是冲突窗口。"""
    view = WP.project_view({"project_id": "p", "row_version": 4},
                           [{"task_id": "b", "sort_order": 20},
                            {"task_id": "a", "sort_order": 10}], [])
    assert view["row_version"] == 4
    assert [s["task_id"] for s in view["steps"]] == ["a", "b"], "步骤没按 sort_order 排"


# ═════════ T-S08-02 私密命中 = 0 ═════════

def test_there_is_no_way_to_build_a_query_without_a_workspace_predicate():
    """**「让调用方决定要不要加权限条件」这种设计，迟早会有人决定不加。**

    所以本模块不提供不带 workspace 的构造出口——这条用例把它钉住。
    """
    for builder in (WS.build_sqlite_query, WS.build_postgres_query):
        with pytest.raises(WS.SearchError):
            builder(workspace_id="", query="报告", page_size=10, offset=0)
        sql, _ = builder(workspace_id="ws_1", query="报告", page_size=10, offset=0)
        assert "workspace_id =" in sql, "权限谓词不在 WHERE 里"


def test_cross_workspace_row_in_results_is_a_hard_failure():
    """纵深防御：WHERE 负责不查出来，这一条负责在谓词被改坏时立刻暴露，
    而不是等到有人看到别人的数据。"""
    with pytest.raises(WS.SearchError) as caught:
        WS.assert_no_cross_workspace(
            [{"workspace_id": "ws_1"}, {"workspace_id": "ws_2"}], "ws_1")
    assert caught.value.code == "search_scope_violation"
    WS.assert_no_cross_workspace([{"workspace_id": "ws_1"}], "ws_1")


def test_page_size_is_bounded():
    """没有上限的检索接口是最省事的导出通道——
    一次查询把全库拉走，比任何导出端点都方便。"""
    assert WS.validate_page_size(None) == WS.DEFAULT_PAGE_SIZE
    with pytest.raises(WS.SearchError):
        WS.validate_page_size(WS.MAX_PAGE_SIZE + 1)
    for bad in (0, -1, "x", 1.5):
        with pytest.raises(WS.SearchError):
            WS.validate_page_size(bad)


def test_chinese_is_bigram_tokenized_and_does_not_miss():
    """中文用 bigram：召回略宽（会命中「营报」这种非词），但**不漏**。
    对内部检索而言，宁可多几条让人自己看，也不要少一条让人以为没有。"""
    tokens = WS.tokenize("经营报告")
    assert tokens == ["经营", "营报", "报告"]
    assert "报告" in WS.tokenize("2026年度经营报告v2")
    assert "2026" in WS.tokenize("2026年度经营报告v2")


def test_fts_syntax_in_user_input_cannot_leak_into_the_match_expression():
    """用户输入里的 `*` `-` `NEAR` 若被当成 FTS 语法，既是注入面，
    也是「搜不到」的来源。"""
    expression = WS.sqlite_match_expression("NEAR* -报告")
    assert expression.count('"') % 2 == 0
    assert "NEAR*" not in expression.replace('"', "")
    for token in expression.split(" OR "):
        assert token.startswith('"') and token.endswith('"')


def test_ranking_is_the_same_contract_across_backends():
    """SQLite 的 bm25() 越小越相关，Postgres 的 ts_rank 越大越相关。
    不统一的话换后端时排序会**整个倒过来**，而没有任何东西会报错——
    页面照常渲染，只是最相关的那条掉到了最后。"""
    rows = [{"doc_id": "a", "rank": 1.0}, {"doc_id": "b", "rank": 5.0}]
    sqlite_top = WS.rank_results(rows, backend="sqlite")[0]["doc_id"]
    postgres_top = WS.rank_results(rows, backend="postgres")[0]["doc_id"]
    assert sqlite_top == "a" and postgres_top == "b"
    assert WS.rank_results(rows, backend="sqlite")[0]["score"] >= \
        WS.rank_results(rows, backend="sqlite")[1]["score"]


def test_index_text_only_takes_what_it_is_given():
    """不做「把整行 dump 进去」——那会把内部 id、存储键、
    甚至将来新增的敏感字段一起变成可检索的。"""
    text = WS.build_index_text("经营报告", None, 2026)
    assert "报告" in text and "2026" in text


def test_search_latency_budget_is_declared_and_enforced():
    """P95 阈值必须是**声明的数值**，不是「感觉挺快」。
    这里用纯函数路径实测切词+构造，锁住它不会某天变成正则回溯灾难。"""
    started = time.perf_counter()
    for _ in range(2000):
        WS.build_sqlite_query(workspace_id="ws_1", query="2026年度经营报告与差异分析",
                              page_size=20, offset=0)
    elapsed = time.perf_counter() - started
    assert elapsed < 2.0, f"2000 次查询构造耗时 {elapsed:.2f}s——切词可能退化了"


# ═════════ T-S08-03 默认公开命中 = 0 ═════════

def test_nothing_is_public_by_default():
    """**默认不是「有对象但标记为私有」，是「根本不存在公开对象」。**

    两者在正常情况下看不出差别，在出错时差别是全部：
    前者的失败模式是「没发出去」，后者是「全泄露了」。
    """
    assert PUB.default_visibility() == "private"
    assert PUB.public_listing([
        {"slug": "a", "title": "未发布", "visibility": "private"},
        {"slug": "b", "title": "草稿", "visibility": "draft"},
    ]) == []


def test_only_whitelisted_fields_reach_the_snapshot():
    """黑名单默认放行、白名单默认拦住。在「泄露」这件事上，
    默认值的方向决定了失误的后果。"""
    snapshot = PUB.build_snapshot({
        "slug": "kmfa-1", "title": "季度经营", "summary": "摘要", "progress": 60,
        "workspace_secret": "绝不能出去", "internal_note": "客户压价到 3 折",
        "storage_key": "abc.blob", "owner_email": "a@b.com",
    })
    assert set(snapshot) <= set(PUB.PUBLIC_FIELDS)
    for leaked in ("workspace_secret", "internal_note", "storage_key", "owner_email"):
        assert leaked not in snapshot


def test_a_private_canary_in_the_snapshot_stops_publication():
    """canary 不依赖谁记得检查什么——它出现在快照里就说明隔离破了。
    这是 T-S08-03 的 stop_condition。"""
    with pytest.raises(PUB.PublicationError) as caught:
        PUB.build_snapshot({"slug": "x", "title": "含 CANARY-7f3a 的标题"},
                           canaries=["CANARY-7f3a"])
    assert caught.value.code == "canary_leaked_into_snapshot"


@pytest.mark.parametrize("value,why", [
    ("联系 13800138000", "手机号"),
    ("发到 owner@example.com", "邮箱"),
    ("ghp_abcdefghijklmnop1234", "凭据"),
    ("见 /var/lib/kmfa/state", "服务器路径"),
    ("卡号 6222021234567890123", "长数字"),
])
def test_values_that_look_private_are_refused_not_scrubbed(value, why):
    """**不做清洗后放行**：清洗会让你以为发出去的是原文，而实际不是。"""
    with pytest.raises(PUB.PublicationError) as caught:
        PUB.build_snapshot({"slug": "x", "title": value})
    assert caught.value.code == "snapshot_value_looks_private", why


@pytest.mark.parametrize("bad", ["A-Upper", "有中文", "x", "-lead", "trail-",
                                 "with space", "a" * 70, "../etc/passwd"])
def test_slug_shape_is_strict(bad):
    """slug 会进 URL，而 URL 里的意外字符是路径穿越与缓存键污染的入口。"""
    with pytest.raises(PUB.PublicationError):
        PUB.validate_slug(bad)
    assert PUB.validate_slug("kmfa-2026-q1") == "kmfa-2026-q1"


def test_snapshot_carries_its_own_content_hash():
    a = PUB.build_snapshot({"slug": "s", "title": "t", "progress": 1})
    b = PUB.build_snapshot({"progress": 1, "title": "t", "slug": "s"})
    assert a["content_sha256"] == b["content_sha256"], "字段顺序影响了摘要"
    c = PUB.build_snapshot({"slug": "s", "title": "t2", "progress": 1})
    assert c["content_sha256"] != a["content_sha256"]


def test_revoke_is_not_complete_until_every_cache_is_purged():
    """删了源快照但 CDN / 代理 / 搜索索引里还有一份，等于没撤销。"""
    plan = PUB.purge_plan("kmfa-1")
    partial = {"purged": [{"ref": "public/kmfa-1.json", "ok": True}]}
    with pytest.raises(PUB.PublicationError) as caught:
        PUB.revoke_is_complete(partial, plan, elapsed_seconds=1)
    assert caught.value.code == "revoke_incomplete"
    assert "/p/kmfa-1" in caught.value.payload["未清"]

    full = {"purged": [{"ref": item["ref"], "ok": True} for item in plan["targets"]]}
    PUB.revoke_is_complete(full, plan, elapsed_seconds=1)


def test_revoke_beyond_the_sla_is_a_failure():
    """没有时限的撤销承诺，在泄露发生时等于没有承诺。"""
    plan = PUB.purge_plan("kmfa-1")
    full = {"purged": [{"ref": item["ref"], "ok": True} for item in plan["targets"]]}
    with pytest.raises(PUB.PublicationError) as caught:
        PUB.revoke_is_complete(full, plan,
                               elapsed_seconds=PUB.REVOKE_SLA_SECONDS + 1)
    assert caught.value.code == "revoke_sla_missed"


# ═════════ T-S08-04 敏感命中 = 0 / 迁移差异 = 0 ═════════

def test_event_names_are_an_enum_not_free_text():
    """自由字符串迟早会被写成 f"viewed_{project_name}"，项目名就此进了统计表。"""
    with pytest.raises(PA.AnalyticsError) as caught:
        PA.validate_event("viewed_武汉开明项目", {})
    assert caught.value.code == "event_name_not_allowed"
    assert PA.validate_event("page_view", {"route": "dashboard"})["event"] == "page_view"


@pytest.mark.parametrize("key,value", [
    ("route", "13800138000"), ("outcome", "a@b.com"),
    ("route", "武汉开明"), ("backend", "/var/lib/kmfa"),
    ("route", "ws_Xh3k5Rji4cfFTZyhTNV2Q"),
])
def test_sensitive_values_never_enter_analytics(key, value):
    with pytest.raises(PA.AnalyticsError):
        PA.validate_event("page_view", {key: value})


def test_only_buckets_are_recorded_never_raw_values():
    """桶足以回答「大额操作多不多」，原值除了泄露没有额外用处。"""
    # 入参是**整数分**：40,960,322.77 元 = 4_096_032_277 分
    assert PA.bucket_amount(4_096_032_277) == "gte_1e6"
    assert PA.bucket_amount(1250) == "lt_1e2"          # 12.50 元
    with pytest.raises(PA.AnalyticsError):
        PA.bucket_amount(40960322.77)                   # float 一律拒收
    assert PA.bucket_size(500) == "lt_1k"
    assert PA.bucket_duration(0.05) == "lt_100ms"
    with pytest.raises(PA.AnalyticsError):
        PA.validate_event("export_requested", {"amount_bucket": "40960322.77"})
    PA.validate_event("export_requested",
                      {"amount_bucket": PA.bucket_amount(4_096_032_277)})


def test_unknown_properties_are_refused():
    with pytest.raises(PA.AnalyticsError) as caught:
        PA.validate_event("page_view", {"project_name": "x"})
    assert caught.value.code == "event_property_not_allowed"


def test_actor_hash_is_salted_or_it_is_not_anonymised_at_all():
    """不加盐的摘要可以被撞库还原回去——任何拿到统计表的人
    都能拿一份 workspace id 列表去撞。"""
    with pytest.raises(PA.AnalyticsError):
        PA.anonymous_actor("ws_1", "")
    a = PA.anonymous_actor("ws_1", "salt-a")
    assert a != PA.anonymous_actor("ws_1", "salt-b"), "换了盐结果没变，盐没生效"
    assert a != "ws_1" and "ws_1" not in a
    assert a == PA.anonymous_actor("ws_1", "salt-a"), "同盐同输入必须稳定"


def test_availability_denominator_is_expected_not_recorded():
    """用「发出去的事件数」当分母，丢了的事件不在分母里，
    可用率永远是 100%——这是最常见的一种指标自欺。"""
    assert PA.availability(1000, 995) == pytest.approx(0.995)
    assert PA.availability(1000, 500) == 0.5
    assert PA.availability(0, 0) == 1.0
    assert PA.availability(100, 200) == 1.0, "多记不应让可用率超过 1"


def test_scan_reports_every_sensitive_hit():
    hits = PA.scan_for_sensitive([
        {"event": "page_view", "route": "dashboard"},
        {"event": "search_performed", "route": "13800138000"},
    ])
    assert len(hits) == 1 and "手机号" in hits[0]


def test_migration_cannot_switch_reads_with_a_nonzero_diff():
    with pytest.raises(PA.AnalyticsError) as caught:
        PA.next_phase("verify", diff_count=3, rollback_verified=True)
    assert caught.value.code == "migration_diff_not_zero"


def test_migration_cannot_switch_reads_before_rollback_is_proven():
    """「先切过去，回滚等出事再说」的问题是：出事时你既没时间
    也没心情去发现回滚脚本本身有 bug。"""
    with pytest.raises(PA.AnalyticsError) as caught:
        PA.next_phase("verify", diff_count=0, rollback_verified=False)
    assert caught.value.code == "migration_rollback_unverified"
    assert PA.next_phase("verify", diff_count=0,
                         rollback_verified=True) == "switch-read"


def test_diff_compares_content_not_row_counts():
    """行数相同而内容错位，是迁移里最典型也最难发现的一类缺陷。"""
    old = [{"id": "1", "v": 10}, {"id": "2", "v": 20}]
    new = [{"id": "1", "v": 10}, {"id": "2", "v": 99}]
    result = PA.diff_rows(old, new, key="id")
    assert len(old) == len(new)
    assert result["diff_count"] == 1 and result["changed"] == ["2"]
    assert PA.diff_rows(old, old, key="id")["diff_count"] == 0
