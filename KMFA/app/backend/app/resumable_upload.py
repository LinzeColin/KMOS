# -*- coding: utf-8 -*-
"""S06/P6.1 · T-S06-01：任意类型、配额、断点续传。

绑定判据（任务包 acceptance_contract.yaml 原文，不是本文件的转述）：

  AC-UP-001 任意文件类型可存储
    阈值：所有合规样本可安全存储；未知/高风险仅附件；**执行成功 = 0**

  AC-UP-002 大文件与断点续传
    阈值：允许范围内**恢复成功率 = 100%**；**篡改漏检 = 0**；
          超限**在写入预算前**拒绝；重复对象不可控增长 = 0

四条阈值各自对应本模块的一个设计决定，逐条说明它为什么必须这么写：

  ① 「超限在写入预算前拒绝」⇒ 开会话时就要拿到 `total_bytes` 并当场核配额。
     不能等到分片写进来再算——那时字节已经落盘，攻击者可以用必然失败的上传
     反复占用空间。所以 `open_session()` 是唯一的准入点，且它先查后写。

  ② 「篡改漏检 = 0」⇒ **每一片都带自己的 sha256，先验后写**。
     只在最后校验整体摘要是不合格的：坏片已经落盘，且失败时无法分辨是哪一片坏的，
     续传就退化成整传。逐片验让篡改在它到达的那一刻就被拒绝。

  ③ 「恢复成功率 100%」⇒ 进度必须是**持久且可查询**的。
     `received_bytes` 落库、每片 fsync 之后才更新；HEAD 随时可问「我传到哪了」。
     进度只存在内存里的话，进程一重启客户端就只能从头再来。

  ④ 「重复对象不可控增长 = 0」⇒ 开会话时按内容摘要查重，命中就直接返回既有对象，
     一个字节都不收。放到完成时再查重意味着重复内容已经完整传了一遍。

  AC-UP-001 的「未知/高风险仅附件、执行成功=0」由 `disposition_for()` 负责：
  **白名单之外一律 attachment + octet-stream**，不是「黑名单里的才拦」。
  黑名单永远漏——漏掉的那个正好是能在浏览器里执行的那个。
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

#: 分片大小。客户端可以传更小的片，但不得更大——单片过大等于回到整传，
#: 断一次就白传一次，「恢复成功率」这个指标也就失去意义。
CHUNK_BYTES = 4 * 1024 * 1024
MAX_CHUNK_BYTES = 8 * 1024 * 1024

#: 允许**内联**渲染的类型白名单。白名单之外一律附件下载。
#: 之所以是白名单：黑名单永远漏，而漏掉的那个恰好就是能在浏览器里执行的那个
#: （AC-UP-001 要求执行成功=0，这是零容忍指标，不能靠「记得拦住」实现）。
INLINE_SAFE_MEDIA_TYPES = frozenset({
    "text/plain", "text/csv", "application/json", "application/pdf",
    "image/png", "image/jpeg", "image/gif", "image/webp",
})

#: 会话 id 形状。**服务端生成**，不接受客户端指定——
#: 客户端可控的话就能猜别人的会话、往里塞分片。
_UPLOAD_ID = re.compile(r"^up_[A-Za-z0-9_-]{22,64}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


class ResumableUploadError(RuntimeError):
    """带 HTTP 状态码与稳定错误码——错误码进契约，说明文本不进。"""

    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code


@dataclass(frozen=True)
class UploadSession:
    upload_id: str
    workspace_id: str
    original_name: str
    media_type: str
    total_bytes: int
    expected_sha256: str
    received_bytes: int
    part_path: Path


def new_upload_id() -> str:
    return f"up_{secrets.token_urlsafe(24)}"


def validate_upload_id(value: str) -> str:
    if not isinstance(value, str) or not _UPLOAD_ID.match(value):
        raise ResumableUploadError(422, "invalid_upload_id")
    return value


def validate_sha256(value: str, *, code: str = "invalid_sha256") -> str:
    """摘要必须是小写十六进制 64 位。

    不做大小写归一化：客户端送大写说明它算法或编码与服务端不一致，
    悄悄接受会把一类真实的实现分歧藏起来，而这类分歧最后表现为「偶发校验失败」。
    """
    if not isinstance(value, str) or not _SHA256.match(value):
        raise ResumableUploadError(422, code)
    return value


def disposition_for(media_type: str | None) -> tuple[str, str]:
    """返回（下发用的 Content-Type, Content-Disposition）。

    AC-UP-001「未知/高风险仅附件；执行成功=0」。
    白名单之外**一律**改写成 application/octet-stream + attachment：
      · 改写 Content-Type 是关键一步——只加 attachment 而保留 text/html
        在部分场景仍可能被当作可渲染内容处理；
      · 未知扩展、可执行样本、脚本、SVG（可内嵌脚本）全部落在白名单外，
        因此不需要为它们各写一条规则，也就不存在「漏写一条」的风险。
    """
    normalized = (media_type or "").split(";", 1)[0].strip().lower()
    if normalized in INLINE_SAFE_MEDIA_TYPES:
        return normalized, "inline"
    return "application/octet-stream", "attachment"


def plan_session(
    *,
    total_bytes: int,
    expected_sha256: str,
    max_artifact_bytes: int,
    remaining_quota_bytes: int,
) -> None:
    """开会话前的准入检查——**必须在任何字节落盘之前**跑完（AC-UP-002）。

    分成三个错误码而不是一个笼统的 413：客户端要能分辨
    「这个文件本身太大」和「你的额度不够了」——前者换文件没用，后者删旧的就行。
    """
    if not isinstance(total_bytes, int) or total_bytes < 0:
        raise ResumableUploadError(422, "invalid_total_bytes")
    validate_sha256(expected_sha256, code="invalid_expected_sha256")
    if total_bytes > max_artifact_bytes:
        raise ResumableUploadError(413, "artifact_too_large")
    if remaining_quota_bytes <= 0:
        raise ResumableUploadError(429, "artifact_capacity_reached")
    if total_bytes > remaining_quota_bytes:
        raise ResumableUploadError(429, "artifact_capacity_reached")


@dataclass(frozen=True)
class DedupeDecision:
    """开会话时的查重结论。`accept_bytes=False` 表示一个字节都不用收。"""

    accept_bytes: bool
    existing_artifact_version_id: str | None
    reason: str


def dedupe_decision(
    *, expected_sha256: str, existing_version_id: str | None
) -> DedupeDecision:
    """内容摘要已存在就直接复用既有对象——**在收字节之前判**（AC-UP-002）。

    放到完成时再查重是没有意义的：那时重复内容已经完整传了一遍、也完整落过盘，
    「不可控增长」已经发生过了，事后删除只是把它清掉，挡不住下一次。

    注意这里只按**内容**判重，不按文件名。同名不同内容必须各存一份
    （那是两个版本，AC-UP-004 的血缘要求它们都在）；
    不同名同内容则共用一个对象——重复的是字节，不是记录。
    """
    validate_sha256(expected_sha256, code="invalid_expected_sha256")
    if existing_version_id:
        return DedupeDecision(False, existing_version_id, "content_already_stored")
    return DedupeDecision(True, None, "new_content")


def validate_chunk(
    *,
    session: UploadSession,
    offset: int,
    payload: bytes,
    chunk_sha256: str,
) -> None:
    """收一片之前的全部检查。**任何一条不过都不写盘。**

    顺序是有意的：先查偏移（廉价、且能挡住乱序重放），再查长度（防止越界写），
    最后才算摘要（最贵）。反过来会让攻击者用坏片逼服务端做无用的哈希计算。
    """
    if not isinstance(offset, int) or offset < 0:
        raise ResumableUploadError(422, "invalid_upload_offset")
    if offset != session.received_bytes:
        # 偏移对不上不是「继续传」，是状态分歧。让客户端先 HEAD 问清楚再来。
        raise ResumableUploadError(409, "upload_offset_conflict")
    if not payload:
        raise ResumableUploadError(422, "empty_chunk")
    if len(payload) > MAX_CHUNK_BYTES:
        raise ResumableUploadError(413, "chunk_too_large")
    if offset + len(payload) > session.total_bytes:
        raise ResumableUploadError(413, "upload_exceeds_declared_total")
    validate_sha256(chunk_sha256, code="invalid_chunk_sha256")
    if hashlib.sha256(payload).hexdigest() != chunk_sha256:
        # 篡改在它到达的这一刻就被拒——这是 AC-UP-002「篡改漏检=0」的落点。
        raise ResumableUploadError(422, "chunk_checksum_mismatch")


def append_chunk(session: UploadSession, payload: bytes) -> int:
    """把一片追加到暂存文件并 fsync，返回新的已收字节数。

    fsync 不是可选项：`received_bytes` 一旦落库就是对客户端的承诺
    （「这些字节我收下了，别再传」）。落库先于落盘的话，断电后承诺就成了谎话，
    续传会从一个服务端其实没有的位置开始。
    """
    descriptor = os.open(session.part_path, os.O_WRONLY | os.O_APPEND)
    try:
        with os.fdopen(descriptor, "ab") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise ResumableUploadError(503, "upload_storage_unavailable") from exc
    return session.received_bytes + len(payload)


def verify_complete(session: UploadSession, actual_sha256: str) -> None:
    """完成前的终检：字节数与整体摘要都必须与开会话时的声明一致。

    逐片已经验过，这一步仍然要做——它挡的是另一类问题：
    片本身没坏，但顺序被换、有片被重放、或者暂存文件在传输之外被改动过。
    逐片校验管不到这些，整体摘要管得到。
    """
    if session.received_bytes != session.total_bytes:
        raise ResumableUploadError(409, "upload_incomplete")
    if actual_sha256 != session.expected_sha256:
        raise ResumableUploadError(422, "upload_checksum_mismatch")


def file_sha256(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()
