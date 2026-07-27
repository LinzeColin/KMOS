# -*- coding: utf-8 -*-
"""TEST-UP-004 —— S06/P6.3 · T-S06-03 不可变版本与来源血缘。

AC-UP-004 输入：同名、同内容、修改版、派生预览、重新处理
AC-UP-004 阈值：**每个版本唯一可追溯；历史不被覆盖；血缘断点 = 0**
pass_gate 另加：**高风险文件仅附件**

任务包点名的五种输入各有一组用例，一种都不许漏——
「历史不被覆盖」这类阈值的特点是：平时看不出来，等要用历史的时候才发现它没了。
"""
import pytest

from app.artifact_lineage import (
    DERIVATIVE_PREVIEW,
    DERIVATIVE_TEXT,
    DERIVATIVE_THUMBNAIL,
    ArtifactVersion,
    Derivative,
    LineageError,
    LineageGraph,
    append_version,
    attach_derivative,
    broken_lineage,
    history_of,
    next_version_number,
    reprocess,
    validate_processor,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64


def _graph():
    return LineageGraph()


def _add(graph, *, name="报表.xlsx", sha=A, artifact="art_1", attachment=False):
    return append_version(graph, artifact_id=artifact, sha256=sha,
                          original_name=name, media_type="application/octet-stream",
                          attachment_only=attachment)


# ─────────────── 输入①：同名 —— 是新版本，不是替换 ───────────────

def test_same_name_creates_a_new_version_and_keeps_the_old_one():
    """AC-UP-004「历史不被覆盖」。

    同名再传一次是**新版本**。覆盖掉的那一版可能正是审计要看的那一版。
    """
    graph = _graph()
    first = _add(graph, name="报表.xlsx", sha=A)
    second = _add(graph, name="报表.xlsx", sha=B)
    assert first.version_number == 1 and second.version_number == 2
    history = history_of(graph, "art_1")
    assert [v.sha256 for v in history] == [A, B], "旧版本必须还在"


def test_history_never_shrinks_across_many_versions():
    graph = _graph()
    for i in range(10):
        _add(graph, name="同一个名字.xlsx", sha=f"{i:064x}")
    assert len(history_of(graph, "art_1")) == 10


# ─────────────── 输入②：同内容 —— 血缘层如实记，不为省空间合并 ───────────────

def test_identical_content_still_records_two_separate_versions():
    """字节去重是**存储**的事；血缘必须如实记录发生过几次。

    两件事分开，否则会为了省空间而丢历史——而历史正是这一项要保的东西。
    """
    graph = _graph()
    first = _add(graph, name="a.pdf", sha=A)
    second = _add(graph, name="b.pdf", sha=A)
    assert first.version_id != second.version_id
    assert len(history_of(graph, "art_1")) == 2


# ─────────────── 输入③：修改版 —— 版本号只增不减，不复用空洞 ───────────────

def test_version_numbers_only_increase():
    graph = _graph()
    _add(graph, sha=A)
    _add(graph, sha=B)
    assert next_version_number(graph.versions, "art_1") == 3


def test_deleting_a_middle_version_does_not_let_the_number_be_reused():
    """回填会让「v3」在不同时间指向不同内容——直接违反「唯一可追溯」。"""
    graph = _graph()
    _add(graph, sha=A)
    v2 = _add(graph, sha=B)
    _add(graph, sha=C)
    graph.versions.remove(v2)                      # 模拟中间版本被清理
    assert next_version_number(graph.versions, "art_1") == 4, "不得回填到 2"


def test_version_id_is_derived_from_artifact_and_number_not_from_time():
    """时间戳/自增 id 在重建、迁移、并发写入时会重复或错序。"""
    version = ArtifactVersion("art_9", 3, A, "x", "text/plain", False)
    assert version.version_id == "art_9/v3"


def test_different_artifacts_have_independent_version_series():
    graph = _graph()
    _add(graph, artifact="art_1", sha=A)
    other = _add(graph, artifact="art_2", sha=B)
    assert other.version_number == 1, "另一个文件的版本号不该被前一个影响"


# ─────────────── 输入④：派生预览 —— 挂在版本上，不是挂在文件上 ───────────────

def test_a_derivative_hangs_off_a_version_not_an_artifact():
    """一个 artifact 有多个版本；只记「属于哪个文件」就答不出
    「这张预览对应的是不是当前这一版」。"""
    graph = _graph()
    v1 = _add(graph, sha=A)
    v2 = _add(graph, sha=B)
    d = attach_derivative(graph, kind=DERIVATIVE_PREVIEW, parent=v1,
                          processor="pdf-render@1.2.3", sha256=C)
    assert d.parent_version_id == v1.version_id != v2.version_id


@pytest.mark.parametrize("kind", [DERIVATIVE_PREVIEW, DERIVATIVE_THUMBNAIL, DERIVATIVE_TEXT])
def test_all_declared_derivative_kinds_are_supported(kind):
    graph = _graph()
    v1 = _add(graph, sha=A)
    assert attach_derivative(graph, kind=kind, parent=v1,
                             processor="preview-render@1.0.0", sha256=B).kind == kind


def test_unknown_derivative_kind_is_refused():
    graph = _graph()
    v1 = _add(graph, sha=A)
    with pytest.raises(LineageError) as caught:
        attach_derivative(graph, kind="随便造一个", parent=v1,
                          processor="preview-render@1.0.0", sha256=B)
    assert caught.value.code == "unknown_derivative_kind"


def test_a_derivative_cannot_hang_off_a_version_outside_the_graph():
    """挂在图外的版本上 = 当场制造一个血缘断点。"""
    graph = _graph()
    orphan = ArtifactVersion("art_x", 1, A, "x", "text/plain", False)
    with pytest.raises(LineageError) as caught:
        attach_derivative(graph, kind=DERIVATIVE_PREVIEW, parent=orphan,
                          processor="preview-render@1.0.0", sha256=B)
    assert caught.value.code == "parent_version_not_in_graph"


# ─────────────── pass_gate：高风险文件仅附件 ───────────────

def test_attachment_only_versions_get_no_derivatives():
    """生成预览就意味着要解析它，而 stop_condition 明写
    「处理器需要执行用户文件中的代码或宏」即停止。不解析就不可能触发。"""
    graph = _graph()
    risky = _add(graph, name="宏.xlsm", sha=A, attachment=True)
    with pytest.raises(LineageError) as caught:
        attach_derivative(graph, kind=DERIVATIVE_PREVIEW, parent=risky,
                          processor="preview-render@1.0.0", sha256=B)
    assert caught.value.code == "attachment_only_has_no_derivatives"


# ─────────────── 输入⑤：重新处理 —— 追加，不改旧的 ───────────────

def test_reprocessing_appends_and_leaves_the_old_derivative_intact():
    """把重新处理写成「更新派生物」会当场制造血缘断点：
    旧派生物指向的处理器版本消失，就再也答不出「当时那张图是怎么来的」。"""
    graph = _graph()
    v1 = _add(graph, sha=A)
    old = attach_derivative(graph, kind=DERIVATIVE_PREVIEW, parent=v1,
                            processor="pdf-render@1.2.3", sha256=B)
    new = reprocess(graph, kind=DERIVATIVE_PREVIEW, parent=v1,
                    processor="pdf-render@2.0.0", sha256=C)
    assert old in graph.derivatives and new in graph.derivatives
    assert old.processor != new.processor
    assert len([d for d in graph.derivatives if d.kind == DERIVATIVE_PREVIEW]) == 2


def test_reprocessing_does_not_touch_the_original_version():
    """rollback 条款写死：派生物可删除重建，**原件不可改**。"""
    graph = _graph()
    v1 = _add(graph, sha=A)
    before = (v1.sha256, v1.version_number, v1.original_name)
    reprocess(graph, kind=DERIVATIVE_THUMBNAIL, parent=v1,
              processor="thumb@9.9.9", sha256=C)
    assert (v1.sha256, v1.version_number, v1.original_name) == before


# ─────────────── 处理器标识：必须钉死版本 ───────────────

@pytest.mark.parametrize("processor", [
    "pdf-render@1.2.3", "thumb@0.0.1", "text-extract@a1b2c3d4e5f6",
])
def test_pinned_processor_versions_are_accepted(processor):
    assert validate_processor(processor) == processor


@pytest.mark.parametrize("processor", [
    "pdf-render@latest",       # 漂移标识——过后再问就查不到了
    "pdf-render",              # 没有版本
    "@1.2.3", "PDF@1.2.3", "pdf render@1.2.3", "", None,
])
def test_drifting_or_missing_processor_versions_are_refused(processor):
    """接受 latest 等于放弃血缘：过一段时间再问「这张预览怎么来的」，
    答案会变成「用当时的 latest」——而那是什么已经查不到了。"""
    with pytest.raises(LineageError) as caught:
        validate_processor(processor)
    assert caught.value.code == "invalid_processor_version"


# ─────────────── 阈值：血缘断点 = 0 ───────────────

def test_a_healthy_graph_has_no_broken_lineage():
    graph = _graph()
    v1 = _add(graph, sha=A)
    v2 = _add(graph, sha=B)
    attach_derivative(graph, kind=DERIVATIVE_PREVIEW, parent=v1,
                      processor="pdf-render@1.2.3", sha256=C)
    attach_derivative(graph, kind=DERIVATIVE_TEXT, parent=v2,
                      processor="text-extract@1.0.0", sha256=A)
    assert broken_lineage(graph) == []


def test_a_dangling_parent_pointer_is_reported():
    graph = _graph()
    v1 = _add(graph, sha=A)
    attach_derivative(graph, kind=DERIVATIVE_PREVIEW, parent=v1,
                      processor="preview-render@1.0.0", sha256=B)
    graph.versions.clear()                          # 版本没了，指针悬空
    assert any("不存在的版本" in p for p in broken_lineage(graph))


def test_an_untraceable_processor_is_reported_as_a_break():
    """血缘断点不只是「指针断了」——「指到了但查不到那是什么」同样答不出问题。"""
    graph = _graph()
    v1 = _add(graph, sha=A)
    graph.derivatives.append(
        Derivative(DERIVATIVE_PREVIEW, v1.version_id, "mystery@latest", B))
    assert any("处理器标识不可追溯" in p for p in broken_lineage(graph))


def test_checksums_are_validated_on_both_versions_and_derivatives():
    """摘要写错会让「这一版到底是什么内容」永远对不上。"""
    graph = _graph()
    with pytest.raises(LineageError) as caught:
        append_version(graph, artifact_id="art_1", sha256="不是摘要",
                       original_name="x", media_type="text/plain", attachment_only=False)
    assert caught.value.code == "invalid_version_sha256"

    v1 = _add(graph, sha=A)
    with pytest.raises(LineageError) as caught:
        attach_derivative(graph, kind=DERIVATIVE_PREVIEW, parent=v1,
                          processor="preview-render@1.0.0", sha256="XYZ")
    assert caught.value.code == "invalid_derivative_sha256"
