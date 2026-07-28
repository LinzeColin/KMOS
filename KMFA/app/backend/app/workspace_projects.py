# -*- coding: utf-8 -*-
"""S08/P8.1 —— 项目、步骤、进度、分数与文件关联（AC-PROD-001）。

pass_gate：核心 CRUD/恢复一致，**冲突不静默丢失**。
stop_condition：迁移会不可逆丢失现有项目/分数。

## 「冲突不静默丢失」比「检测到冲突」严格得多

乐观锁能检测冲突，这一步本仓已有（`row_version`）。但只回一个 409，
**丢失照样发生**——只是从服务端搬到了客户端：用户敲了十分钟的备注，
提交时被告知「版本冲突」，页面一刷新，他敲的东西没了。

所以冲突响应必须把三样东西一起给回去：

  · `submitted` —— 他刚才想写的，原样奉还，让前端能重填；
  · `current`   —— 现在库里是什么，让他看得见冲突在哪；
  · `row_version` —— 重试要用的版本号，不必再查一次。

有了这三样，「冲突」才是一次**可恢复**的事件，而不是一次数据丢失。

## 为什么不做「后写者赢」

后写者赢在实现上最省事，但它把丢失变成**静默的**：两个人同时改进度，
一个人的改动消失，谁都不会收到任何提示。本任务的 pass_gate 恰恰禁止这个。

也不做自动合并：进度和分数是标量，"合并"两个标量没有正确答案，
系统猜一个等于替用户做了他没做的决定。冲突交还给人，是唯一诚实的处理。

## 步骤（steps）与文件关联

步骤有序，排序键单独存（`sort_order`）而不是靠插入顺序：
靠顺序的列表在并发插入下会互相错位，而错位的表现是「步骤顺序偶尔不对」——
这类缺陷复现不了，因为它依赖两次写入的时间差。

文件关联只存**引用**（`artifact_version_id`），不复制内容：
复制会立刻产生「关联里的副本和原件不一致」这种状态，
而 T-S06-03 花了一整个任务保证血缘无断点。
"""
from __future__ import annotations

import re
from typing import Any, Mapping

#: 进度取值域。用整数百分比而不是浮点：0.1+0.2 的那类问题在进度条上表现为
#: 「明明拖到 100% 却显示 99%」，而它的成因和金额里的浮点误差完全相同。
PROGRESS_MIN, PROGRESS_MAX = 0, 100

#: 分数取值域，同样是整数。
SCORE_MIN, SCORE_MAX = 0, 100

#: 单个 workspace 的步骤上限。没有上限时一次脚本调用就能灌满库，
#: 而清理需要人工介入——上限是给自动化留的刹车，不是给人用的。
MAX_STEPS_PER_WORKSPACE = 500

#: 步骤标题长度上限。
MAX_TITLE_BYTES = 200

_TITLE_FORBIDDEN = re.compile(r"[\x00-\x1f\x7f]")


class ProjectError(Exception):
    def __init__(self, status_code: int, code: str, message: str,
                 payload: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.payload = dict(payload or {})


def validate_progress(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProjectError(422, "progress_invalid",
                           "进度必须是整数百分比。浮点进度会出现「拖到 100% 却显示 99%」，"
                           "成因与金额里的浮点误差相同。")
    if not (PROGRESS_MIN <= value <= PROGRESS_MAX):
        raise ProjectError(422, "progress_out_of_range",
                           f"进度须在 {PROGRESS_MIN}–{PROGRESS_MAX} 之间，收到 {value}。")
    return value


def validate_score(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProjectError(422, "score_invalid", "分数必须是整数。")
    if not (SCORE_MIN <= value <= SCORE_MAX):
        raise ProjectError(422, "score_out_of_range",
                           f"分数须在 {SCORE_MIN}–{SCORE_MAX} 之间，收到 {value}。")
    return value


def validate_title(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ProjectError(422, "title_required", "步骤标题不能为空。")
    title = raw.strip()
    if _TITLE_FORBIDDEN.search(title):
        raise ProjectError(422, "title_has_control_characters",
                           "标题含控制字符——它们在日志与终端里会改变显示，"
                           "让人看到的和存下来的不是同一个东西。")
    if len(title.encode("utf-8")) > MAX_TITLE_BYTES:
        raise ProjectError(422, "title_too_long",
                           f"标题超过 {MAX_TITLE_BYTES} 字节。")
    return title


def check_version(
    *,
    expected: Any,
    current: int,
    submitted: Mapping[str, Any],
    current_state: Mapping[str, Any],
) -> None:
    """乐观锁校验。**冲突时把用户刚才写的东西原样奉还。**

    只回一个 409 不算达成 pass_gate：丢失并没有消失，
    只是从服务端搬到了客户端——用户敲了十分钟的东西，一刷新就没了。
    """
    if expected is None:
        raise ProjectError(
            428, "version_required",
            "改动必须带 `If-Match: <row_version>`。不带版本号的写入无法判断"
            "「你看到的是不是你要改的那一版」，覆盖会静默发生。",
            {"current": dict(current_state), "row_version": current})
    try:
        expected_version = int(expected)
    except (TypeError, ValueError):
        raise ProjectError(422, "version_invalid", "If-Match 必须是整数版本号。")
    if expected_version != current:
        raise ProjectError(
            409, "version_conflict",
            "这条记录在你编辑期间被改过了。你的输入原样在 `submitted` 里，"
            "当前值在 `current` 里，用 `row_version` 重试。",
            {"submitted": dict(submitted),
             "current": dict(current_state),
             "row_version": current})


def next_sort_order(existing: list[Mapping[str, Any]]) -> int:
    """新步骤排在末尾。**取最大值 +10 而不是 len()+1**：

    用 `len()` 的话，删掉中间一条再插入就会和现存的某条撞号；
    撞号之后两条步骤的相对顺序由数据库返回顺序决定，也就是不确定。
    留 10 的间隔还让「插到两条之间」不必重排整张表。
    """
    if not existing:
        return 10
    return max(int(row.get("sort_order") or 0) for row in existing) + 10


def plan_step_insert(
    *, title: Any, existing: list[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(existing) >= MAX_STEPS_PER_WORKSPACE:
        raise ProjectError(
            429, "step_quota_exhausted",
            f"步骤已达 {MAX_STEPS_PER_WORKSPACE} 条上限。"
            "上限是给自动化留的刹车——没有它，一次脚本调用就能灌满库，"
            "而清理需要人工介入。")
    return {"title": validate_title(title), "sort_order": next_sort_order(existing)}


def plan_step_reorder(
    *, order: Any, existing: list[Mapping[str, Any]]
) -> list[tuple[str, int]]:
    """重排。要求**给全**当前步骤 id，缺一个就拒绝。

    允许只给一部分的话，没给到的那些排在哪里由实现决定，
    而"由实现决定"在用户眼里就是"顺序自己变了"。
    """
    if not isinstance(order, list) or not all(isinstance(x, str) for x in order):
        raise ProjectError(422, "order_invalid", "order 必须是 task_id 的字符串数组。")
    known = [str(row["task_id"]) for row in existing]
    if sorted(order) != sorted(known):
        missing = sorted(set(known) - set(order))
        extra = sorted(set(order) - set(known))
        raise ProjectError(
            422, "order_incomplete",
            "重排必须给全当前所有步骤 id。只给一部分的话，"
            "没给到的那些排在哪里由实现决定——在用户眼里就是顺序自己变了。",
            {"missing": missing, "unknown": extra})
    return [(task_id, (index + 1) * 10) for index, task_id in enumerate(order)]


def link_artifact(
    *, artifact_version_id: Any, known_versions: set[str]
) -> str:
    """文件关联只存**引用**，不复制内容。

    复制会立刻产生「关联里的副本和原件不一致」这种状态，
    而 T-S06-03 用一整个任务保证血缘无断点——在这里复制等于把它推翻。
    """
    if not isinstance(artifact_version_id, str) or not artifact_version_id:
        raise ProjectError(422, "artifact_ref_required", "必须给出制品版本 id。")
    if artifact_version_id not in known_versions:
        # 404 而不是 422：本 workspace 里没有这个制品，
        # 与「格式不对」是两回事，前者说明客户端拿错了 id。
        raise ProjectError(
            404, "artifact_not_found",
            "本 workspace 里没有这个制品版本。关联的是引用而不是副本，"
            "所以引用必须指向真实存在的版本。")
    return artifact_version_id


def project_view(project: Mapping[str, Any], steps: list[Mapping[str, Any]],
                 links: list[Mapping[str, Any]]) -> dict[str, Any]:
    """对外呈现。`row_version` **必须**出现在响应里——
    客户端下一次写入要用它，不给就等于逼着对方先读一次再写，
    而那一读一写之间正是冲突窗口。"""
    return {
        "project_id": project.get("project_id"),
        "name": project.get("name"),
        "progress": project.get("progress"),
        "score": project.get("score"),
        "row_version": project.get("row_version"),
        "lifecycle_state": project.get("lifecycle_state"),
        "steps": [
            {"task_id": row.get("task_id"), "title": row.get("title"),
             "status": row.get("status"), "sort_order": row.get("sort_order"),
             "row_version": row.get("row_version")}
            for row in sorted(steps, key=lambda r: (int(r.get("sort_order") or 0),
                                                    str(r.get("task_id"))))
        ],
        "artifacts": [
            {"artifact_version_id": row.get("artifact_version_id"),
             "original_name": row.get("original_name")}
            for row in links
        ],
    }
