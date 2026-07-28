# -*- coding: utf-8 -*-
"""S08/P8.4 —— 隐私统计与数据/路由迁移（AC-PROD-004 / AC-MIG-001）。

pass_gate：**核心事件可用 ≥99%、敏感命中=0；迁移差异=0 且回滚通过**。
stop_condition：第三方数据处理条款不满足隐私边界，或迁移无回退。

## 统计不发第三方，这是设计不是省事

第三方统计要成立，得先满足「数据处理条款符合隐私边界」——
而本仓的用户是匿名 workspace，连账号都没有；把匿名标识发给第三方，
等于替用户做了一个他没同意、也无法撤回的决定。

所以统计**留在自己这里**：事件写进本地 append-only 表，聚合在本地算。
代价是没有现成看板，收益是隐私边界不需要靠任何一份别人的合同来保证。

## 事件里放什么：白名单，且是**枚举**不是字符串

事件名从固定枚举里取，属性也是。理由和公开快照的白名单一样，
但这里还多一层：`event_name` 若允许自由字符串，调用方迟早会把
`f"viewed_{project_name}"` 当事件名发——项目名就此进了统计表。

所以事件名是枚举，属性值只允许「桶」而不是原值：
不记「金额 12345.67」，记「金额桶 1e4–1e5」。桶足以回答
「大额操作多不多」，而原值除了泄露没有额外用处。

## 「核心事件可用 ≥99%」怎么算

分母是**应该产生的事件数**，不是「发出去的事件数」。
用后者当分母，丢了的事件不在分母里，可用率永远是 100%——
这是最常见的一种指标自欺。所以埋点处成对记录：
预期计数器 + 实际写入计数器，两者相除。

## 迁移：expand-contract，且**回滚先于切换**验证

先扩（新旧并存、双写）→ 校验差异=0 → 切读 → 观察 → 再收缩（删旧）。
关键是：**回滚路径在切换之前就要验证过**。
「先切过去，回滚等出事再说」的问题是，出事时你既没时间也没心情去发现
回滚脚本本身有 bug。
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable, Mapping

#: 允许的事件名。**枚举，不是自由字符串**——
#: 自由字符串迟早会被写成 f"viewed_{project_name}"，项目名就此进了统计表。
EVENT_NAMES = frozenset({
    "page_view", "workspace_created", "workspace_recovered",
    "artifact_uploaded", "artifact_downloaded", "export_requested",
    "search_performed", "publication_published", "publication_revoked",
})

#: 允许的属性键。同样是白名单。
EVENT_PROPERTIES = frozenset({"route", "outcome", "size_bucket", "duration_bucket",
                              "amount_bucket", "count_bucket", "backend"})

#: 属性值只允许这些形状：短、无空格、非自由文本。
_VALUE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,39}$")

#: `*_bucket` 属性**必须是桶标签**，不能是数字。
#:
#: 这条是补上一个真实缺口：`_VALUE_RE` 允许数字和点，于是 `"40960322.77"`
#: 作为 `amount_bucket` 能原样混过去——**原始金额就这样进了统计表**，
#: 而它看起来完全合规。桶标签必须含字母（`lt_1e2` / `gte_1g` / `1k_1m`），
#: 纯数字一律拒绝。
_BUCKET_RE = re.compile(r"^(?=.*[a-z])[a-z0-9][a-z0-9._-]{0,39}$")

#: 敏感形状。命中即拒绝——统计里出现任何一条都算 pass_gate 失败。
_SENSITIVE = (
    (re.compile(r"1[3-9]\d{9}"), "手机号"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "邮箱"),
    (re.compile(r"(?:gh[pousr]_|sk-|xox[bap]-)"), "凭据前缀"),
    (re.compile(r"\bws_[A-Za-z0-9_-]{10,}"), "workspace 标识"),
    (re.compile(r"/(?:var|opt|home|Users)/"), "服务器路径"),
    (re.compile(r"[一-鿿]"), "中文自由文本（可能是项目名或备注）"),
)


class AnalyticsError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def bucket_amount(cents: int) -> str:
    """金额分桶。**不记原值**——桶足以回答「大额操作多不多」，
    原值除了泄露没有额外用处。

    入参是**整数分**，不是元、更不是 float。第一版写成 `int | float` 并在内部
    `float(value)`，被仓内的 `check_no_float_money.py` 当场拦下——门禁是对的：
    这个函数收 float，就意味着上游某处已经有一个 float 金额了，
    而那正是 S09 花一整个任务消灭的东西。分桶不需要小数，边界用整数分表示即可。
    """
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise AnalyticsError("bucket_amount_requires_int_cents",
                             "分桶只接受整数分——收 float 就意味着上游已经有一个"
                             "float 金额，而那是 S09 明令消灭的。")
    amount = abs(cents)
    # 边界写成整数分：100 元 = 10_000 分，依此类推。
    for edge, label in ((10_000, "lt_1e2"), (100_000, "1e2_1e3"),
                        (1_000_000, "1e3_1e4"), (10_000_000, "1e4_1e5"),
                        (100_000_000, "1e5_1e6")):
        if amount < edge:
            return label
    return "gte_1e6"


def bucket_size(num_bytes: int) -> str:
    for edge, label in ((1024, "lt_1k"), (1024 ** 2, "1k_1m"),
                        (10 * 1024 ** 2, "1m_10m"), (1024 ** 3, "10m_1g")):
        if num_bytes < edge:
            return label
    return "gte_1g"


def bucket_duration(seconds: float) -> str:
    for edge, label in ((0.1, "lt_100ms"), (0.5, "100ms_500ms"),
                        (2.0, "500ms_2s"), (10.0, "2s_10s")):
        if seconds < edge:
            return label
    return "gte_10s"


def anonymous_actor(workspace_id: str, salt: str) -> str:
    """把 workspace 标识换成**加盐摘要**，用于「独立访客数」这类聚合。

    加盐是关键：不加盐的话，任何拿到统计表的人都能拿一份 workspace id
    列表去撞库，把匿名标识还原回去。盐只存在服务端，且不进任何导出。
    """
    if not salt:
        raise AnalyticsError("analytics_salt_missing",
                             "缺少盐——不加盐的摘要可以被撞库还原，等于没脱敏。")
    return hashlib.sha256(f"{salt}\x00{workspace_id}".encode("utf-8")).hexdigest()[:32]


def validate_event(name: str, properties: Mapping[str, Any]) -> dict[str, Any]:
    """校验一条事件。任何一条不合规都**拒绝写入**而不是清洗后写入：
    清洗过的事件看起来正常，于是没人会去查为什么它和预期不一样。"""
    if name not in EVENT_NAMES:
        raise AnalyticsError(
            "event_name_not_allowed",
            f"事件名 {name!r} 不在枚举里。事件名必须是枚举——自由字符串迟早会被"
            "写成 f\"viewed_{project_name}\"，项目名就此进了统计表。")
    clean: dict[str, Any] = {}
    for key, value in properties.items():
        if key not in EVENT_PROPERTIES:
            raise AnalyticsError("event_property_not_allowed",
                                 f"属性 {key!r} 不在白名单里。")
        text = str(value)
        pattern = _BUCKET_RE if key.endswith("_bucket") else _VALUE_RE
        if not pattern.fullmatch(text):
            raise AnalyticsError(
                "event_value_not_bucketed",
                f"属性 {key} 的值 {text!r} 不是桶标签。统计只收桶，不收原值——"
                "桶标签必须含字母（lt_1e2 / 1k_1m / gte_1g），纯数字一律拒绝。")
        for pattern, label in _SENSITIVE:
            if pattern.search(text):
                raise AnalyticsError("event_value_sensitive",
                                     f"属性 {key} 的值命中{label}。")
        clean[key] = text
    return {"event": name, "properties": clean}


def scan_for_sensitive(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """整表扫敏感命中。**pass_gate 的「敏感命中=0」按这个算。**"""
    hits: list[str] = []
    for row in rows:
        blob = " ".join(f"{k}={v}" for k, v in row.items())
        for pattern, label in _SENSITIVE:
            if pattern.search(blob):
                hits.append(f"{row.get('event', '?')}：{label}")
    return hits


def availability(expected: int, recorded: int) -> float:
    """核心事件可用率。**分母是应该产生的事件数，不是发出去的事件数。**

    用后者当分母，丢了的事件不在分母里，可用率永远是 100%——
    这是最常见的一种指标自欺。
    """
    if expected < 0 or recorded < 0:
        raise AnalyticsError("availability_negative", "计数不能为负。")
    if expected == 0:
        return 1.0
    return min(1.0, recorded / expected)


# ── 迁移：expand-contract ───────────────────────────────────────────────────

MIGRATION_PHASES = ("expand", "dual-write", "verify", "switch-read",
                    "observe", "contract")


def next_phase(current: str, *, diff_count: int, rollback_verified: bool) -> str:
    """迁移推进判定。**回滚必须在切读之前就验证过。**

    「先切过去，回滚等出事再说」的问题是：出事时你既没时间也没心情
    去发现回滚脚本本身有 bug。
    """
    if current not in MIGRATION_PHASES:
        raise AnalyticsError("migration_phase_unknown", f"未知阶段 {current!r}。")
    index = MIGRATION_PHASES.index(current)
    if current == "verify":
        if diff_count != 0:
            raise AnalyticsError(
                "migration_diff_not_zero",
                f"新旧两侧差异 {diff_count} 条，不为 0 不得切读。")
        if not rollback_verified:
            raise AnalyticsError(
                "migration_rollback_unverified",
                "回滚路径尚未验证。切换之前必须先证明能回来——"
                "出事时没有时间去发现回滚脚本本身有 bug。")
    if current == "contract":
        return "contract"
    return MIGRATION_PHASES[index + 1]


def diff_rows(old: Iterable[Mapping[str, Any]], new: Iterable[Mapping[str, Any]],
              *, key: str) -> dict[str, Any]:
    """逐行比对。**按内容摘要比，不按行数比**——
    行数相同而内容错位，是迁移里最典型也最难发现的一类缺陷。"""
    def index(rows):
        return {str(r[key]): hashlib.sha256(
            repr(sorted(r.items())).encode("utf-8")).hexdigest() for r in rows}

    left, right = index(old), index(new)
    missing = sorted(set(left) - set(right))
    extra = sorted(set(right) - set(left))
    changed = sorted(k for k in set(left) & set(right) if left[k] != right[k])
    return {"missing": missing, "extra": extra, "changed": changed,
            "diff_count": len(missing) + len(extra) + len(changed)}
