# -*- coding: utf-8 -*-
"""S07/P7.3 —— 受控导出任务（AC-DL-003 / AC-DL-004）。

## 起因：一条 GET 在写业务记录

`GET /api/报告中心/导出` 每次调用都渲染一份报告、往导出登记册追加一条记录、
再写一条审计。TEST-DL-004 枚举 64 条读路由，只有它改了状态。

这为什么要紧，不是洁癖：

  · **GET 会被别人替你按**。浏览器预取、链接预览、爬虫、代理预热、
    用户手抖刷新——每一次都在登记册里落一条「导出过」。
    登记册是交付事实的依据，被这些噪声灌满之后就不再是依据了。
  · **GET 应当可缓存**。一个既产生业务记录又可缓存的端点，
    语义上自相矛盾：缓存命中时记录没产生，未命中时产生了，
    而调用方无从知道自己撞上了哪一边。
  · **成本**。渲染 PDF 不便宜。挂在 GET 上等于把一个昂贵操作放在
    任何人都能无限触发的位置。

所以改成命令：**POST 创建任务**（带幂等键），**GET 只读状态与制品**。

## 幂等键的两条规则，第二条才是关键

  1. 同键 + 同请求 ⇒ 返回同一个任务，不重复干活；
  2. 同键 + **不同**请求 ⇒ 409，绝不执行。

第二条常被漏掉，而漏掉它幂等键就成了摆设：客户端复用一个键去要另一份报告，
系统会「幂等地」返回上一份——它拿到的是一个**它没要过的东西**，
而且看起来一切正常。所以请求内容要指纹化并与键绑死。

## 同步执行，以及这对「取消」意味着什么

今天任务在 POST 里同步跑完，不排队。据此说清楚边界：

  · **取消**只对非终态任务有意义。同步执行下，任务在响应返回时已是终态，
    于是取消恒返回 409 并**如实报出当前状态**。AC-DL-003 要的是
    「取消/失败/过期状态确定」——确定，不是「总能取消」。
  · 换成真 worker 时，本模块的状态机一行都不用改：
    `queued → running → succeeded/failed/cancelled` 本来就是为排队写的，
    只是今天 queued 停留的时间是零。

把这件事写清楚，是因为「有 job 接口 = 异步」是个太自然的误读。

## 只追加，不改写

任务状态存成事件序列，当前状态由折叠得出。这与本仓导出登记册、审计事件
同一条纪律。好处不只是审计：**「任务为什么变成 failed」这个问题，
在可改写的表里是查不到的**——最后一次写覆盖了原因。
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

#: 同时在跑的任务上限。**无界并发=0** 是 AC-DL-003 的阈值。
#: 导出会渲染 PDF，无上限时几个并发请求就能吃满 CPU，
#: 而 HTTP 层的 worker 数不是上限——它只是「同时有多少请求」，
#: 不区分请求贵不贵。贵的操作要自己的闸。
MAX_CONCURRENT_JOBS = 2

#: 单个 workspace 的在库任务上限，防止把登记册撑爆。
MAX_JOBS_PER_OWNER = 200

#: 制品有效期（秒）。过期不是删除，是**状态**——
#: 「制品没了」和「任务从来不存在」必须能区分开，否则排查时无从下手。
ARTIFACT_TTL_SECONDS = 24 * 3600

#: 单份制品字节上限。渲染出一个几百 MB 的 PDF 不是功能，是事故。
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024

#: 幂等键形状：与 S06 续传上传同一条规则，全仓一致。
#: 太短的键会撞（不同客户端各自用 "1"），所以下限 16。
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9._~-]{16,128}$")

TERMINAL_STATES = frozenset({"succeeded", "failed", "cancelled", "expired"})
ALL_STATES = frozenset({"queued", "running"}) | TERMINAL_STATES


class ExportJobError(Exception):
    """带 HTTP 状态码的业务错误。`code` 是给机器看的稳定令牌，
    `message` 是给人看的——两者分开，免得有人去 parse 人话。"""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def validate_idempotency_key(raw: str | None) -> str:
    if not raw or not IDEMPOTENCY_KEY_RE.fullmatch(raw):
        raise ExportJobError(
            422, "idempotency_key_invalid",
            "Idempotency-Key 需为 16–128 位的 [A-Za-z0-9._~-]。"
            "长度下限不是形式主义：太短的键会在不同客户端之间意外相撞，"
            "而相撞的后果是有人拿到别人的导出结果。")
    return raw


def request_fingerprint(request: Mapping[str, Any]) -> str:
    """把请求内容压成指纹，与幂等键绑死。

    `sort_keys` 保证键序不影响指纹——否则同一个请求换个字段顺序
    就会被判成「不同请求」，把正当重试变成 409。
    """
    canonical = json.dumps(request, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def job_id_for(owner: str, key: str) -> str:
    """任务 id 由 (owner, 幂等键) 决定，**不含随机数**。

    这样「同键同请求返回同一个任务」不依赖任何查表是否成功：
    id 本身就是幂等的。查表只用来判断第二条规则（同键不同请求 ⇒ 409）。
    owner 进 id 是为了让两个 workspace 用同一个键时互不干扰——
    幂等键是客户端自己取的，不能假设它全局唯一。
    """
    digest = hashlib.sha256(f"{owner}\x00{key}".encode("utf-8")).hexdigest()
    return f"exp_{digest[:32]}"


def fold_job(events: Iterable[Mapping[str, Any]]) -> dict[str, Any] | None:
    """把事件序列折叠成当前状态。**终态之后的事件一律忽略**。

    忽略而不是报错：重复的取消请求、worker 崩溃后的迟到回报，
    都会产生终态之后的事件。让它们无害地落地，比让系统在这里抛异常安全——
    抛异常会把一个已经完成的任务变成读不出来的任务。
    """
    state: dict[str, Any] | None = None
    for event in events:
        kind = str(event.get("event"))
        if kind == "created":
            if state is not None:
                continue  # 同一个 id 的重复创建：第一条为准
            state = {
                "job_id": event["job_id"],
                "owner": event["owner"],
                "idempotency_key": event["idempotency_key"],
                "fingerprint": event["fingerprint"],
                "request": event.get("request") or {},
                "state": "queued",
                "created_at": event.get("at"),
                "updated_at": event.get("at"),
                "artifact": None,
                "failure": None,
            }
            continue
        if state is None or state["state"] in TERMINAL_STATES:
            continue
        if kind == "started":
            state["state"] = "running"
        elif kind == "succeeded":
            state["state"] = "succeeded"
            state["artifact"] = event.get("artifact")
        elif kind == "failed":
            state["state"] = "failed"
            state["failure"] = event.get("failure")
        elif kind == "cancelled":
            state["state"] = "cancelled"
        else:
            continue
        state["updated_at"] = event.get("at")
    return state


def is_expired(job: Mapping[str, Any], now_epoch: int) -> bool:
    """过期只对**成功且有制品**的任务有意义。

    失败的任务没有制品可过期；把它也标成 expired 会掩盖失败原因，
    而失败原因正是排查时唯一有用的东西。
    """
    if job.get("state") != "succeeded":
        return False
    artifact = job.get("artifact") or {}
    produced = artifact.get("produced_at_epoch")
    if not isinstance(produced, int):
        return False
    return now_epoch - produced > ARTIFACT_TTL_SECONDS


def project(job: Mapping[str, Any], now_epoch: int) -> dict[str, Any]:
    """对外呈现的状态，含过期折算。

    过期是**读的时候算出来的**，不是写进去的：靠定时任务改状态的话，
    定时任务没跑的那段时间里，系统会拿着过期制品当有效的发。
    """
    view = dict(job)
    if is_expired(job, now_epoch):
        view["state"] = "expired"
        view["artifact"] = dict(view.get("artifact") or {}, available=False)
    elif view.get("artifact"):
        view["artifact"] = dict(view["artifact"], available=True)
    view.pop("fingerprint", None)  # 指纹是内部判据，不对外
    return view


def admit(
    *,
    owner: str,
    key: str,
    request: Mapping[str, Any],
    existing: Mapping[str, Any] | None,
    running_count: int,
    owner_job_count: int,
) -> dict[str, Any]:
    """决定这次 POST 该做什么。**纯函数**——不碰存储、不碰时钟。

    返回 `{"action": ...}`：
      · `reuse`  —— 同键同请求，返回既有任务，不重复干活
      · `create` —— 新任务
    冲突与超限直接抛。
    """
    validate_idempotency_key(key)
    fingerprint = request_fingerprint(request)

    if existing is not None:
        if existing.get("fingerprint") != fingerprint:
            # **第二条规则。** 复用同一个键去要别的东西，绝不能「幂等地」
            # 返回上一份——那样客户端拿到的是它没要过的东西，且看不出异常。
            raise ExportJobError(
                409, "idempotency_key_reused",
                "同一个 Idempotency-Key 用在了内容不同的请求上。"
                "换一个键；沿用它会让你拿到上一次的结果，而那不是你要的东西。")
        return {"action": "reuse", "job": existing, "fingerprint": fingerprint}

    if running_count >= MAX_CONCURRENT_JOBS:
        raise ExportJobError(
            429, "export_concurrency_limit",
            f"同时最多 {MAX_CONCURRENT_JOBS} 个导出任务在跑。"
            "导出要渲染报告，无上限时几个并发就能吃满 CPU。稍后重试。")
    if owner_job_count >= MAX_JOBS_PER_OWNER:
        raise ExportJobError(
            429, "export_job_quota_exhausted",
            f"在库导出任务已达 {MAX_JOBS_PER_OWNER} 个上限。")

    return {
        "action": "create",
        "job_id": job_id_for(owner, key),
        "fingerprint": fingerprint,
    }


def plan_cancel(job: Mapping[str, Any] | None, now_epoch: int) -> dict[str, Any]:
    """取消的判定。终态不可取消，且**必须报出当前是什么状态**。

    只回一个「不能取消」而不说现在是什么，会让调用方去猜——
    猜错的方向通常是「再试一次」，于是把一次误操作变成一串。
    """
    if job is None:
        raise ExportJobError(404, "export_job_not_found", "没有这个导出任务。")
    view = project(job, now_epoch)
    if view["state"] in TERMINAL_STATES:
        raise ExportJobError(
            409, "export_job_already_terminal",
            f"任务已处于终态 {view['state']}，不可取消。")
    return {"action": "cancel", "job_id": job["job_id"]}


def artifact_response_plan(
    job: Mapping[str, Any] | None, now_epoch: int
) -> dict[str, Any]:
    """取制品前的判定。四种「拿不到」要分得清清楚楚——
    它们对调用方意味着完全不同的下一步。"""
    if job is None:
        raise ExportJobError(404, "export_job_not_found", "没有这个导出任务。")
    view = project(job, now_epoch)
    state = view["state"]
    if state == "expired":
        raise ExportJobError(
            410, "export_artifact_expired",
            f"制品已过期（有效期 {ARTIFACT_TTL_SECONDS // 3600} 小时）。重新创建任务。")
    if state == "failed":
        raise ExportJobError(
            409, "export_job_failed",
            f"任务失败，没有制品。原因：{view.get('failure') or '未记录'}")
    if state == "cancelled":
        raise ExportJobError(409, "export_job_cancelled", "任务已取消，没有制品。")
    if state != "succeeded":
        raise ExportJobError(
            409, "export_job_not_ready", f"任务尚未完成（当前 {state}）。")
    return {"action": "serve", "artifact": view["artifact"]}
