# -*- coding: utf-8 -*-
"""S06/P6.3 补齐 —— 真正生成派生物（text extract）。

## 为什么这份文件是补齐而不是新增

T-S06-03 的 outputs 写的是 `immutable original` / `preview/thumbnail/text extract` /
`完整 lineage graph`。我当时只建了血缘模型与策略（三条 pass_gate 确实都证了），
**没有真正产出任何派生物**。AC-DL-001 又点名要下载「预览、派生文件」——
这个洞于是挡在 S07 路上。按「不得擅自缩减范围」，在这里补。

## 为什么只做 text extract，不做 image thumbnail / pdf preview

不是省事，是 T-S06-03 的 stop_condition 顶着：
**「处理器需要执行用户文件中的代码或宏」即停止。**

  · text extract 对 `text/plain`、`text/csv` 只做**字节解码 + 截断**。
    没有格式解析器，也就没有解析器漏洞面——用户内容再恶意也只是一段字节。
  · thumbnail / pdf preview 必须把不可信字节喂给图像/PDF 解码器。
    那类库的历史漏洞几乎全是「构造畸形文件触发解码器」。在本仓引入它们，
    等于把 T-S06-02 挡住的东西从后门放进来。

所以这里**明确不做**，并把理由写在这里而不是留白：
留白会让后来的人以为「忘了做」，于是补上它——把守住的边界重新打开。
真要做，前置条件是隔离进程/沙箱与资源上限，那属于另一个任务，不在 T-S06-03 范围。

## 解码为什么用 errors="replace" 而不是抛错

派生物是**便利品**，不是权威副本——权威副本永远是原件。
一个含坏字节的文本文件仍然应该能出摘要，让用户看到「大概是什么」；
为了几个坏字节让整个派生失败，是把便利品当成了权威。
原件本身一个字节都不动，所以这里的宽松不会污染任何权威结论。
"""
from __future__ import annotations

import hashlib

#: 能安全提取文本的类型。**白名单**，与 T-S06-02 同一个理由：
#: 黑名单永远漏，而漏掉的那个正好是需要解析器的那个。
TEXT_EXTRACTABLE = frozenset({"text/plain", "text/csv", "application/json"})

#: 提取上限。派生物是便利品，不该因为一个巨大的文本把内存吃光。
MAX_EXTRACT_BYTES = 256 * 1024

#: 处理器标识必须钉死版本（T-S06-03 的血缘要求，`latest` 会被判断点）。
TEXT_EXTRACT_PROCESSOR = "text-extract@1.0.0"


def can_extract_text(media_type: str | None, attachment_only: bool) -> bool:
    """能不能提。`attachment_only` 的一律不提——那是 T-S06-03 的 pass_gate
    「高风险文件仅附件」，不因为「只是提个文本」就破例。"""
    if attachment_only:
        return False
    normalized = (media_type or "").split(";", 1)[0].strip().lower()
    return normalized in TEXT_EXTRACTABLE


def extract_text(payload: bytes) -> tuple[str, str]:
    """返回（文本, 该文本的 sha256）。

    摘要算在**输出**上而不是输入上：血缘要回答的是「这个派生物是什么」，
    用输入摘要充当输出摘要会让两个不同的派生物看起来是同一个。
    """
    text = payload[:MAX_EXTRACT_BYTES].decode("utf-8", errors="replace")
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def unsupported_reason(media_type: str | None, attachment_only: bool) -> str:
    """说清**为什么**没有派生物——空着会被当成「生成失败」去排查。"""
    if attachment_only:
        return "高风险文件仅附件，不生成任何需要读取内容的派生物"
    normalized = (media_type or "").split(";", 1)[0].strip().lower()
    if normalized in {"image/png", "image/jpeg", "image/gif", "image/webp",
                      "application/pdf"}:
        return ("缩略图/预览需要把不可信字节喂给图像或 PDF 解码器，"
                "而 T-S06-03 的 stop_condition 明令处理器不得执行用户文件中的内容。"
                "要做须先有隔离进程与资源上限，属另一个任务。")
    return f"{normalized or '未知类型'} 无安全的文本提取路径"
