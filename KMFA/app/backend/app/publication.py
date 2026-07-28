# -*- coding: utf-8 -*-
"""S08/P8.3 —— 默认 Unlisted、显式发布与撤销（AC-PROD-003）。

pass_gate：**默认公开命中=0；白名单外字段=0；撤销在 SLA 内完成**。
stop_condition：无法证明公开快照与私有源隔离。

## 默认不公开，而且「默认」要是结构上的

「默认私有」如果靠一个 `is_public=False` 的默认值，那它就是一个**可以忘的默认**：
新增一张表、新增一条写入路径，谁忘了带上它，那份数据就是公开的。

本模块反过来：**公开的东西是一份单独产出的快照**，不是给私有记录打个标记。
没有主动发布，就根本不存在可公开的对象——不是"存在但标记为私有"。
两者在正常情况下看不出差别，在出错时差别是全部：
前者的失败模式是"没发出去"，后者的失败模式是"全泄露了"。

## 白名单，逐字段

快照只包含 `PUBLIC_FIELDS` 里列出的字段。**黑名单不行**：
将来新增一个字段，黑名单默认放行，白名单默认拦住。
在"泄露"这件事上，默认值的方向决定了失误的后果。

字段值也要过一遍：即使字段名在白名单里，值里也可能夹带私密内容
（用户把手机号写进了项目名）。所以另有一层 canary 与形状检查。

## 撤销必须连缓存一起

删了源快照但 CDN/代理里还有一份，等于没撤销。所以撤销返回一张
**purge 清单**（要清哪些路径、哪些索引），由调用方逐条执行并回报。
不返回清单、假装撤销完成，是本任务 stop_condition 里那个「不可撤销」的由来。
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

#: 公开快照允许出现的字段。**白名单**——将来新增字段默认不公开。
PUBLIC_FIELDS = ("slug", "title", "summary", "progress", "published_at",
                 "snapshot_version", "content_sha256")

#: 绝不允许出现在公开快照里的值形状。命中即拒绝发布，不是「清洗后放行」：
#: 清洗会让用户以为自己发出去的是原文，而实际不是。
_LEAKY_VALUE = (
    (re.compile(r"1[3-9]\d{9}"), "疑似手机号"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "疑似邮箱"),
    (re.compile(r"\b\d{15,19}\b"), "疑似银行卡/长数字标识"),
    (re.compile(r"(?:gh[pousr]_|sk-|xox[bap]-)[A-Za-z0-9_-]{10,}"), "疑似凭据"),
    (re.compile(r"[13][A-HJ-NP-Za-km-z1-9]{25,34}"), "疑似钱包地址"),
    (re.compile(r"/(?:var|opt|home|Users)/"), "疑似服务器路径"),
)

#: slug 形状。不接受任意字符：slug 会进 URL，而 URL 里的意外字符
#: 是路径穿越与缓存键污染的入口。
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,62}[a-z0-9])$")

#: 撤销 SLA（秒）。超过它就不算「撤销完成」——
#: 一个没有时限的撤销承诺，在泄露发生时等于没有承诺。
REVOKE_SLA_SECONDS = 300


class PublicationError(Exception):
    def __init__(self, status_code: int, code: str, message: str,
                 payload: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.payload = dict(payload or {})


def default_visibility() -> str:
    """默认可见性。**unlisted 不是 private 的同义词**：
    unlisted 表示"有链接可访问但不进索引"，private 表示"根本不存在公开对象"。
    本仓的默认是后者——没有发布动作就没有快照，不是"有快照但藏起来"。
    """
    return "private"


def validate_slug(raw: Any) -> str:
    if not isinstance(raw, str) or not SLUG_RE.fullmatch(raw):
        raise PublicationError(
            422, "slug_invalid",
            "slug 只接受小写字母、数字与连字符，长度 3–64，首尾须为字母数字。"
            "不接受任意字符：slug 会进 URL，而 URL 里的意外字符是路径穿越"
            "与缓存键污染的入口。")
    return raw


def scan_value(field: str, value: Any) -> list[str]:
    """逐个值扫形状。字段名在白名单里**不代表**值是安全的——
    用户会把手机号写进项目名。"""
    problems: list[str] = []
    text = "" if value is None else str(value)
    for pattern, label in _LEAKY_VALUE:
        if pattern.search(text):
            problems.append(f"{field}：{label}")
    return problems


def build_snapshot(
    source: Mapping[str, Any], *, canaries: Iterable[str] = ()
) -> dict[str, Any]:
    """从私有记录产出公开快照。**逐字段白名单，逐值扫描。**

    canary 是刻意埋进私有数据里的标记串。它出现在快照里，
    说明隔离已经破了——而这比任何"我检查过了"都可靠：
    它不依赖谁记得检查什么。
    """
    snapshot: dict[str, Any] = {}
    for field in PUBLIC_FIELDS:
        if field in source:
            snapshot[field] = source[field]

    extra = sorted(set(snapshot) - set(PUBLIC_FIELDS))
    if extra:  # 理论上不可能，留着是因为"理论上不可能"是事故报告的常见开头
        raise PublicationError(500, "snapshot_whitelist_violation",
                               f"快照里出现了白名单外字段：{extra}")

    problems: list[str] = []
    for field, value in snapshot.items():
        problems.extend(scan_value(field, value))
    blob = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    for canary in canaries:
        if canary and canary in blob:
            raise PublicationError(
                500, "canary_leaked_into_snapshot",
                "私有 canary 出现在公开快照里——公开面与私有源没有隔离。"
                "这是 T-S08-03 的 stop_condition，发布必须停下。")
    if problems:
        raise PublicationError(
            422, "snapshot_value_looks_private",
            "快照里的值看起来含私密内容，已拒绝发布。"
            "**不做清洗后放行**：清洗会让你以为发出去的是原文，而实际不是。",
            {"命中": problems})

    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    snapshot["content_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return snapshot


def purge_plan(slug: str) -> dict[str, Any]:
    """撤销要清的东西。**返回清单而不是假装清完了**——

    删了源快照但 CDN / 代理 / 搜索索引里还有一份，等于没撤销。
    清单让调用方逐条执行并回报，未回报的那条就是"还没撤销干净"。
    """
    return {
        "slug": slug,
        "sla_seconds": REVOKE_SLA_SECONDS,
        "targets": [
            {"kind": "snapshot", "ref": f"public/{slug}.json", "必须": True},
            {"kind": "http-cache", "ref": f"/p/{slug}", "必须": True},
            {"kind": "search-index", "ref": f"public:{slug}", "必须": True},
            {"kind": "sitemap", "ref": "/sitemap.xml", "必须": True},
        ],
    }


def revoke_is_complete(report: Mapping[str, Any], plan: Mapping[str, Any],
                       elapsed_seconds: float) -> None:
    """判定撤销是否真的完成。三条都要过，缺一条都不算。"""
    done = {str(item.get("ref")) for item in (report.get("purged") or [])
            if item.get("ok")}
    required = {str(item["ref"]) for item in plan["targets"] if item["必须"]}
    missing = sorted(required - done)
    if missing:
        raise PublicationError(
            409, "revoke_incomplete",
            "还有目标没清干净，撤销不算完成。删了源快照但缓存里还有一份，"
            "等于没撤销。",
            {"未清": missing})
    if elapsed_seconds > REVOKE_SLA_SECONDS:
        raise PublicationError(
            504, "revoke_sla_missed",
            f"撤销耗时 {elapsed_seconds:.0f}s，超过 {REVOKE_SLA_SECONDS}s 的 SLA。"
            "没有时限的撤销承诺，在泄露发生时等于没有承诺。")


def public_listing(published: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """公开列表只列**已发布**的。默认不出现在这里——
    这是「默认公开命中=0」的直接实现：没有发布动作就没有条目，
    而不是"有条目但被过滤掉了"。"""
    return [
        {field: row[field] for field in PUBLIC_FIELDS if field in row}
        for row in published
        if str(row.get("visibility")) == "published"
    ]
