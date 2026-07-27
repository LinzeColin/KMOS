# -*- coding: utf-8 -*-
"""S06/P6.3 · T-S06-03：不可变原件 + 安全派生物 + 完整血缘。

绑定判据（AC-UP-004 原文）：
  输入：同名、同内容、修改版、派生预览、重新处理
  阈值：**每个版本唯一可追溯；历史不被覆盖；血缘断点 = 0**
  pass_gate 另加一条：**高风险文件仅附件**

三条阈值分别否定了三种「看起来对」的做法：

  ①「历史不被覆盖」否定了**按文件名去重覆盖**。
     同名再传一次是**新版本**，不是替换。覆盖掉的那一版可能正是审计要看的。
     所以版本号只增不减，`(artifact_id, version_number)` 一旦写下就不可变。

  ②「血缘断点 = 0」否定了**派生物只记「我是谁生成的」**。
     派生物必须同时记住三件事：从哪个**版本**来（不是从哪个文件来——
     文件会有多个版本）、用**哪个处理器的哪个版本**生成、以及**内容摘要**。
     少任何一个都无法回答「这张预览图对应的是不是当前这一版原件」。

  ③「每个版本唯一可追溯」否定了**用时间戳或自增 id 当版本标识**。
     那些在重建、迁移、并发写入时都可能重复或错序。标识必须由
     `artifact_id + version_number` 决定，且内容摘要独立记录用于比对。

「重新处理」是这一项最容易做错的地方：
  同一个原件用新版本处理器再跑一次，产出的是**新的派生物**，
  而**原件那一版不变**。把重新处理写成「更新派生物」会让血缘出现断点——
  旧派生物指向的处理器版本消失了，就再也答不出「当时那张图是怎么来的」。

原件不可改是硬约束：`rollback` 条款明写「派生物可删除重建，原件不可改」。
所以本模块只提供**追加**语义，不提供任何原件的修改入口。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

#: 派生物类型。高风险文件**只允许 attachment**，不生成任何需要解析的派生物——
#: 生成预览就意味着要解析它，而 stop_condition 明写「处理器需要执行用户文件中的
#: 代码或宏」即停止。不解析就不可能触发这条。
DERIVATIVE_PREVIEW = "preview"
DERIVATIVE_THUMBNAIL = "thumbnail"
DERIVATIVE_TEXT = "text_extract"
DERIVATIVE_KINDS = (DERIVATIVE_PREVIEW, DERIVATIVE_THUMBNAIL, DERIVATIVE_TEXT)

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
#: 处理器版本必须是**可比较且可追溯**的具体版本，不接受 "latest" 这种漂移标识。
#: 允许 `name@1.2.3` 或 `name@<12位摘要>`。
_PROCESSOR = re.compile(r"^[a-z][a-z0-9_-]{1,40}@(?:\d+\.\d+\.\d+|[a-f0-9]{12,64})$")


class LineageError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ArtifactVersion:
    artifact_id: str
    version_number: int
    sha256: str
    original_name: str
    media_type: str
    attachment_only: bool

    @property
    def version_id(self) -> str:
        """版本标识由 (artifact_id, version_number) 决定。

        不用时间戳、不用自增 id：那些在重建、迁移、并发写入时会重复或错序，
        而阈值要求「唯一可追溯」。内容摘要独立记录，供比对而非充当标识——
        同内容可以有多个版本（不同文件名、不同时间上传都是合法的历史）。
        """
        return f"{self.artifact_id}/v{self.version_number}"


@dataclass(frozen=True)
class Derivative:
    kind: str
    parent_version_id: str
    processor: str
    sha256: str


@dataclass
class LineageGraph:
    versions: list[ArtifactVersion] = field(default_factory=list)
    derivatives: list[Derivative] = field(default_factory=list)


def validate_sha256(value: str, code: str) -> str:
    if not isinstance(value, str) or not _SHA256.match(value):
        raise LineageError(code)
    return value


def validate_processor(value: str) -> str:
    """处理器标识必须钉死版本。

    接受 "latest" 之类的漂移标识等于放弃血缘：过一段时间再问「这张预览是怎么来的」，
    答案会变成「用当时的 latest」——而那是什么已经查不到了。
    """
    if not isinstance(value, str) or not _PROCESSOR.match(value):
        raise LineageError("invalid_processor_version")
    return value


def next_version_number(existing: list[ArtifactVersion], artifact_id: str) -> int:
    """下一个版本号 = 现有最大值 + 1。**只增不减，且不复用空洞。**

    即使中间某版被删除，号也不回填：回填会让「v3」在不同时间指向不同内容，
    而阈值要求每个版本唯一可追溯。
    """
    numbers = [v.version_number for v in existing if v.artifact_id == artifact_id]
    return (max(numbers) + 1) if numbers else 1


def append_version(
    graph: LineageGraph,
    *,
    artifact_id: str,
    sha256: str,
    original_name: str,
    media_type: str,
    attachment_only: bool,
) -> ArtifactVersion:
    """追加一个版本。**同名不覆盖、同内容也不合并。**

    同名再传一次是新版本而不是替换——覆盖掉的那一版可能正是审计要看的。
    同内容也各存一版：它们是两次真实发生的上传，历史里都该有。
    （字节层面的去重是**存储**的事，由 content-addressed 对象层负责；
      血缘层面必须如实记录发生过几次。两件事分开，否则会为了省空间而丢历史。）
    """
    validate_sha256(sha256, "invalid_version_sha256")
    if not artifact_id:
        raise LineageError("invalid_artifact_id")
    version = ArtifactVersion(
        artifact_id=artifact_id,
        version_number=next_version_number(graph.versions, artifact_id),
        sha256=sha256, original_name=original_name,
        media_type=media_type, attachment_only=attachment_only,
    )
    graph.versions.append(version)
    return version


def attach_derivative(
    graph: LineageGraph,
    *,
    kind: str,
    parent: ArtifactVersion,
    processor: str,
    sha256: str,
) -> Derivative:
    """给某个**版本**挂一个派生物。

    parent 是版本而不是 artifact：一个 artifact 有多个版本，
    只记「属于哪个文件」就答不出「这张预览对应的是不是当前这一版」。
    """
    if kind not in DERIVATIVE_KINDS:
        raise LineageError("unknown_derivative_kind")
    if parent.attachment_only:
        # pass_gate「高风险文件仅附件」。生成预览就要解析它，而 stop_condition
        # 明写处理器需要执行用户文件中的代码或宏即停止。不解析就不会触发。
        raise LineageError("attachment_only_has_no_derivatives")
    if parent not in graph.versions:
        raise LineageError("parent_version_not_in_graph")
    validate_processor(processor)
    validate_sha256(sha256, "invalid_derivative_sha256")
    derivative = Derivative(kind=kind, parent_version_id=parent.version_id,
                            processor=processor, sha256=sha256)
    graph.derivatives.append(derivative)
    return derivative


def reprocess(
    graph: LineageGraph, *, kind: str, parent: ArtifactVersion,
    processor: str, sha256: str,
) -> Derivative:
    """用新处理器重新生成派生物——**追加一条，不改旧的**。

    把重新处理写成「更新派生物」会当场制造血缘断点：
    旧派生物指向的处理器版本消失，就再也答不出「当时那张图是怎么来的」。
    原件那一版当然也不动——rollback 条款写死了「原件不可改」。
    """
    return attach_derivative(graph, kind=kind, parent=parent,
                             processor=processor, sha256=sha256)


def broken_lineage(graph: LineageGraph) -> list[str]:
    """血缘断点清单。**阈值要求它恒为空。**

    断点的定义是「顺着指针走不到头」：派生物指向一个不存在的版本，
    或指向的处理器标识不可追溯。两者都会让「这东西怎么来的」无法回答。
    """
    known = {v.version_id for v in graph.versions}
    problems: list[str] = []
    for derivative in graph.derivatives:
        if derivative.parent_version_id not in known:
            problems.append(f"派生物 {derivative.kind} 指向不存在的版本 "
                            f"{derivative.parent_version_id}")
        if not _PROCESSOR.match(derivative.processor or ""):
            problems.append(f"派生物 {derivative.kind} 的处理器标识不可追溯："
                            f"{derivative.processor}")
    return problems


def history_of(graph: LineageGraph, artifact_id: str) -> list[ArtifactVersion]:
    """按版本号升序的完整历史。**任何时候都不该变短。**"""
    return sorted((v for v in graph.versions if v.artifact_id == artifact_id),
                  key=lambda v: v.version_number)
