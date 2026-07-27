# -*- coding: utf-8 -*-
"""S07/P7.2 —— Range 与断点续传（AC-DL-002）。

## 为什么 Range 挂在 POST 上，而不是把下载改成 GET

RFC 9110 把 Range 定义在 GET 上，但并不禁止其它方法支持它。这里必须留在 POST，
理由有两条，任何一条单独成立都够：

  · T-S07-01 的 stop_condition 是「下载 URL 可被枚举」。GET 的 URL 会进浏览器
    历史、Referer、代理日志和书签，等于把制品地址散出去。
  · AC-DL-004 要求**读取请求无业务副作用**。本仓的下载会写审计事件
    （`_audit_artifact_download`）——那就是副作用。改成 GET 会当场违反 AC-DL-004。
    审计不能砍：它是越权追溯的唯一依据。

所以 POST 是两个验收条款共同钉死的，不是随手选的。

## 「续传 hash 一致」不是 Range 本身能保证的

这是本任务最容易做漏的一处。设想：制品 v1 共 1000 字节，客户端拿到 0-499；
此时 v2 覆盖了它；客户端接着要 500-999。两段拼起来**既不是 v1 也不是 v2**，
而且长度对、状态码对、没有任何一层会报错——你得到一个校验不过的文件，
却不知道是网络坏了还是磁盘坏了。

本仓的下载端点取的是 `latest_artifact_version`，**制品在两次请求之间真的会变**，
所以这不是假想。防线是 HTTP 早就给好的：

  · 响应带**强 ETag**（制品 sha256——内容变则 ETag 必变，这正是强验证器的定义）；
  · 客户端续传时带 `If-Range: <etag>`；
  · 服务端发现 ETag 已变，就**回 200 整份**而不是 206 片段——
    让客户端从头拿，而不是拼出一个坏文件。

失败方式从「静默损坏」变成「多下一次」。这就是 AC-DL-002 的
「续传 hash 一致」真正要求的东西。

## 多重 Range 一律不给片段

`Range: bytes=0-1,2-3,4-5,...` 在协议上合法，服务端应答 `multipart/byteranges`。
本实现**不支持**，遇到多段就当没有 Range、回 200 整份（RFC 9110 明说服务端
可以忽略 Range）。理由是放大攻击：一个请求里塞几千个小段，每段都要一份
MIME 分隔头和一次寻道，响应体和 CPU 都被单个请求撬起来。
批量下载的正当需求由 ZIP 那条路（`batch_archive`）满足，它有条目数与字节上限。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

#: 单次读盘上限。Range 响应可能覆盖整个大文件，必须分块读——
#: 一次 `read()` 读完等于把文件塞进内存，正是 T-S07-02 的 stop_condition。
CHUNK_SIZE = 64 * 1024

#: 只认 bytes 单位。RFC 9110：不认识的 range unit 必须忽略整个 Range 头。
_RANGE_HEADER = re.compile(r"^\s*bytes\s*=\s*(?P<spec>.+)$", re.IGNORECASE)
_SINGLE = re.compile(r"^\s*(?P<first>\d*)\s*-\s*(?P<last>\d*)\s*$")


@dataclass(frozen=True)
class ByteRange:
    """闭区间 [start, end]，和 `Content-Range` 的语义一致（end 是**含**的）。

    用闭区间而不是 Python 惯用的半开区间，是为了和线上格式一一对应：
    多一次 ±1 转换就多一处 off-by-one 的机会，而 off-by-one 在这里的表现是
    「文件少一个字节」——hash 不过，但看上去像网络问题。
    """

    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start + 1

    def content_range(self, total: int) -> str:
        return f"bytes {self.start}-{self.end}/{total}"


class _Unsatisfiable:
    """请求的区间完全落在资源之外 —— 416，且必须带 `Content-Range: bytes */total`。

    单独一个哨兵类型，是为了和「没有 Range」区分开：两者都不返回 ByteRange，
    但一个回 200、一个回 416，混在一起用 None 表示迟早会错。
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return "UNSATISFIABLE"


UNSATISFIABLE = _Unsatisfiable()


def etag_for(sha256: str) -> str:
    """强 ETag。内容摘要天然满足强验证器的要求：字节不同则 ETag 必不同。

    不加 `W/` 前缀——弱 ETag 明确**不允许**用于 Range 比对（RFC 9110 §13.1.5），
    因为弱验证器允许「语义等价但字节不同」，而续传拼接要的正是字节相同。
    """
    return f'"{sha256}"'


def if_range_satisfied(if_range: str | None, current_etag: str) -> bool:
    """没带 If-Range 视为满足——客户端没要求校验，就不替它加条件。

    带了就必须**精确**匹配当前 ETag。这里只支持 ETag 形式，不支持 HTTP-date 形式：
    date 形式的分辨率是秒，同一秒内的两次改动无法区分，用它做续传校验
    等于留一个一秒宽的损坏窗口。
    """
    if if_range is None:
        return True
    return if_range.strip() == current_etag


def parse_range(header: str | None, total: int) -> ByteRange | _Unsatisfiable | None:
    """解析 Range 头。

    返回值三态：
      · `None`          —— 没有 Range 或语法不合法/多段 ⇒ 回 200 整份
      · `UNSATISFIABLE` —— 语法合法但区间在资源之外 ⇒ 回 416
      · `ByteRange`     —— 回 206

    语法不合法回 None 而不是 400，是 RFC 9110 的要求：无效 Range 必须被忽略，
    当作普通请求处理。对客户端更友好——拿到整份总比拿到错误页有用。
    """
    if not header:
        return None
    match = _RANGE_HEADER.match(header)
    if not match:
        return None

    parts = match.group("spec").split(",")
    if len(parts) != 1:
        # 多段：不给片段，回整份。理由见模块文档（放大攻击）。
        return None

    single = _SINGLE.match(parts[0])
    if not single:
        return None
    first, last = single.group("first"), single.group("last")

    if not first and not last:
        return None  # `bytes=-` 无意义

    if not first:
        # 后缀形式 `bytes=-N`：最后 N 个字节。
        suffix = int(last)
        if suffix == 0:
            # 「最后 0 个字节」不可满足，不是「整份」。
            return UNSATISFIABLE
        if total == 0:
            return UNSATISFIABLE
        start = max(0, total - suffix)
        return ByteRange(start, total - 1)

    start = int(first)
    if total == 0 or start >= total:
        # 空资源上任何区间都不可满足；起点越界同理。
        return UNSATISFIABLE

    if not last:
        return ByteRange(start, total - 1)

    end = int(last)
    if end < start:
        # `bytes=500-100` 语法合法但语义颠倒 ⇒ 按无效忽略，回整份。
        return None
    # 终点越界要**截断**而不是报错：RFC 9110 明确允许客户端要多于实际长度，
    # 这正是「不知道总长时先要一大段」的常见用法。
    return ByteRange(start, min(end, total - 1))


def iter_file_range(
    path: Path,
    byte_range: ByteRange | None,
    *,
    chunk_size: int = CHUNK_SIZE,
) -> Iterator[bytes]:
    """按块读出指定区间。`byte_range=None` 表示整份。

    每次最多驻留 `chunk_size` 字节 —— 这是 pass_gate「资源受控」在单文件侧的落点。
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正")
    with path.open("rb") as handle:
        if byte_range is None:
            while True:
                block = handle.read(chunk_size)
                if not block:
                    return
                yield block
            return
        handle.seek(byte_range.start)
        remaining = byte_range.length
        while remaining > 0:
            block = handle.read(min(chunk_size, remaining))
            if not block:
                # 文件在读的过程中被截短了。**必须报错而不是静默少发**：
                # 少发的字节数会让客户端拼出一个短文件，而 Content-Length
                # 已经承诺了长度——静默少发是「hash 不一致」的直接来源。
                raise IOError(
                    f"制品在读取过程中变短：还差 {remaining} 字节"
                )
            remaining -= len(block)
            yield block
