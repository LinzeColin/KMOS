# -*- coding: utf-8 -*-
"""S07/P7.2 —— 可验证的批量 ZIP（AC-DL-002）。

## stop_condition 决定了实现形态

T-S07-02 白纸黑字：**「批量实现需要把整个归档放入单进程内存」即停止。**
所以归档写到磁盘临时文件、逐块流式产出，任何时刻常驻内存的只有一个块。
500 个文件和 5 个文件的内存占用没有差别——这是本模块最硬的约束，
其余设计都要让位于它。

用标准库 `zipfile` 而不是手写 ZIP 结构：本地文件头、数据描述符、中央目录、
ZIP64 切换，每一处写错都表现为「大多数解压器能开、某一个不能」——
那是最难查的一类缺陷。手写唯一能换来的是省掉一个磁盘临时文件，不值。

## 归档是确定性的，因此「重试」是可验证的

AC-DL-002 要求「失败可重试」。可重试要有意义，得能判断「重试出来的和原来是同一份」。
所以本模块把归档做成**输入集合的纯函数**：

  · 条目按稳定键排序 —— 数据库返回顺序变了，归档不变；
  · 时间戳钉死在 ZIP 纪元 1980-01-01 —— 不写「打包时刻」，
    否则同样的输入每次都是不同的字节，重试永远无法自证；
  · 权限位钉死。

于是「重试」= 逐字节相同 = 归档 sha256 相同。这条性质可以直接断言。

## 重名：不去重就等于丢文件

`report.xlsx` 出现两次，两个条目同名写进 ZIP，多数解压器**静默用后者覆盖前者**——
用户以为拿到 2 个文件，实际拿到 1 个，而且没有任何错误提示。
AC-DL-002 的「无丢失/覆盖」就是在说这件事。

去重必须在**解压端的碰撞语义**下做，不是在字节相等下做：

  · 大小写 —— macOS 与 Windows 默认不区分大小写，`Report.xlsx` 和 `report.xlsx`
    在归档里是两个条目，落到用户盘上是一个。按字节比对的去重会漏掉它。
  · Unicode 规范化 —— macOS 用 NFD，多数来源用 NFC。`é` 的两种写法字节不同、
    看起来一样，解压时同样碰撞。
  · Windows 的静默截断 —— 结尾的点和空格会被悄悄去掉，`a .txt` 与 `a.txt` 因此碰撞。

所以碰撞键是「NFC 归一 + 去尾点尾空格 + casefold」。判碰撞用它，写进归档的仍是可读名。

## 归档端的路径穿越：方向和上传端相反

zip-slip 通常被当成解压漏洞。但这里我们是**生产者**：只要把 `../../etc/passwd`
写成条目名，任何一个没做防护的解压器都会被我们打穿。
所以条目名在写入前必须剥掉一切路径成分——我们不能生产恶意归档。

与 `upload_quarantine.safe_filename` 的区别要说清，两者不可互换：

  · 上传端**检测**，名字有问题就隔离——用户可以改名重传，拒绝的代价是一次重试；
  · 归档端**强制**，名字有问题就改写——文件早已入库、属于用户，
    因为名字不好看就把它排除在归档外，那叫「丢失」，正是 AC 禁止的。

被改写的名字连同原名一起进 manifest，所以没有任何东西是悄悄发生的。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

#: 同步接口的条目上限。超过就该走异步导出任务（T-S07-03 / AC-DL-003），
#: 而不是让一个 HTTP worker 被长任务占住——那是 T-S07-02 risk 里写的
#: 「长任务占满 worker」。`build_archive` 本身不设上限：它是流式的，
#: 500 个条目也只占一个块的内存，上限是**接口层的资源策略**，不是算法限制。
MAX_SYNC_ENTRIES = 50

#: 同步接口的字节上限。条目数少但每个都是 GB 级，同样能占满 worker。
MAX_SYNC_BYTES = 512 * 1024 * 1024

#: 单次读写块大小，归档内存占用的上界。
CHUNK_SIZE = 64 * 1024

#: ZIP 纪元。钉死时间戳换取确定性，理由见模块文档。
_FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)

#: 归档自带清单的条目名。前缀 `_kmfa_` 而不是朴素的 `manifest.json`，
#: 是为了降低与用户文件撞名的概率——撞了也不会丢文件（名字已预占），
#: 但用户文件被改名总是要解释的，能不发生就不发生。
MANIFEST_ENTRY_NAME = "_kmfa_manifest.json"

_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

_SEPARATORS = re.compile(r"[/\\]")
_DRIVE = re.compile(r"^[A-Za-z]:")


class ArchiveCancelled(Exception):
    """打包被取消。取消必须是异常而不是「返回一个短归档」——
    短归档看起来是完整的 ZIP，能打开、条目少，用户不会知道它被截断了。"""


@dataclass(frozen=True)
class ArchiveMember:
    """一个待打包的制品。`sort_key` 用于确定性排序，取制品版本 id 这类稳定值。"""

    source_path: Path
    original_name: str
    sha256: str
    size_bytes: int
    sort_key: str


def collision_key(name: str) -> str:
    """解压端会认为哪些名字是同一个文件。判重用它，不是用原名。

    三步各自对应一种真实的碰撞（详见模块文档）：NFC 归一、去尾点尾空格、casefold。
    `casefold` 而不是 `lower`：`lower` 处理不了 ß→ss 这类，
    而文件系统的不敏感折叠比 `lower` 更激进。
    """
    normalized = unicodedata.normalize("NFC", name)
    return normalized.rstrip(". ").casefold()


def coerce_entry_name(raw: str | None, *, fallback: str) -> tuple[str, list[str]]:
    """把任意原名压成一个可安全写入 ZIP 的条目名。

    返回（条目名, 改写原因清单）。清单进 manifest —— 改写必须留痕，
    否则用户看到归档里的名字和自己上传的不一样，无从判断是被改了还是拿错了文件。

    `fallback` 在原名被清空时兜底（取制品摘要前缀之类的确定性值），
    绝不能用随机名或序号：随机破坏确定性，序号依赖遍历顺序。
    """
    reasons: list[str] = []
    name = unicodedata.normalize("NFC", raw or "")

    if "\x00" in name:
        name = name.replace("\x00", "")
        reasons.append("去除 NUL（用于截断路径，让检查看到的名字和写盘的不是同一个）")

    if _DRIVE.match(name) or name.startswith("/"):
        reasons.append("去除绝对路径前缀")

    if _SEPARATORS.search(name):
        reasons.append("去除路径分隔符（归档端的路径穿越）")
    # 只取最后一段：同时解决分隔符、绝对路径和 `../` 三件事。
    name = _SEPARATORS.split(name)[-1]

    if name in {".", ".."}:
        reasons.append("剔除相对路径段")
        name = ""

    control = [ch for ch in name if unicodedata.category(ch).startswith("C")]
    if control:
        name = "".join(ch for ch in name if not unicodedata.category(ch).startswith("C"))
        reasons.append("去除控制字符")

    stripped = name.rstrip(". ")
    if stripped != name:
        # 主动去掉，而不是留给 Windows 悄悄去掉：让碰撞在我们这里可见。
        reasons.append("去除结尾的点或空格（Windows 会静默去掉，导致碰撞）")
        name = stripped

    stem = name.split(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED:
        name = f"_{name}"
        reasons.append(f"Windows 保留设备名 {stem}，前置下划线")

    if not name:
        name = fallback
        reasons.append("原名被清空，改用确定性兜底名")

    # ZIP 条目名以 UTF-8 存储，多数文件系统的单段上限是 255 字节。
    encoded = name.encode("utf-8")
    if len(encoded) > 200:
        suffix = "".join(Path(name).suffixes[-1:])
        head = encoded[: 200 - len(suffix.encode("utf-8"))]
        # 从字节切会切裂多字节字符，`errors="ignore"` 丢掉半个字符而不是产生乱码。
        name = head.decode("utf-8", errors="ignore") + suffix
        reasons.append("名称过长，已截断（保留扩展名）")

    return name, reasons


def assign_entry_names(
    members: Sequence[ArchiveMember],
    *,
    reserved: Iterable[str] = (),
) -> list[tuple[ArchiveMember, str, list[str]]]:
    """给每个条目定名并消解重名。**先排序再定名**，所以结果与输入顺序无关。

    重名后缀用 ` (2)`、` (3)`——和主流文件管理器一致，用户一眼知道是同名副本，
    而不是以为文件本身叫这个名字。

    `reserved` 是归档自身要占用的名字（清单文件）。**必须先占位再分配**：
    否则用户上传的同名文件会被清单覆盖，那是一次真实的数据丢失，
    而且发生在「防覆盖」这个功能内部。
    """
    ordered = sorted(members, key=lambda m: (m.sort_key, m.sha256))
    taken: set[str] = {collision_key(name) for name in reserved}
    result: list[tuple[ArchiveMember, str, list[str]]] = []

    for member in ordered:
        base, reasons = coerce_entry_name(
            member.original_name, fallback=f"artifact-{member.sha256[:12]}"
        )
        candidate = base
        if collision_key(candidate) in taken:
            stem = Path(base).stem
            suffix = "".join(Path(base).suffixes)
            index = 2
            while collision_key(f"{stem} ({index}){suffix}") in taken:
                index += 1
            candidate = f"{stem} ({index}){suffix}"
            reasons.append(f"与已有条目重名，改为「{candidate}」以免解压时互相覆盖")
        taken.add(collision_key(candidate))
        result.append((member, candidate, reasons))

    return result


def build_archive(
    members: Sequence[ArchiveMember],
    destination: Path,
    *,
    chunk_size: int = CHUNK_SIZE,
    should_cancel: Callable[[], bool] | None = None,
    manifest_entry_name: str | None = MANIFEST_ENTRY_NAME,
) -> dict:
    """流式打包到 `destination`，返回 manifest。

    先写到同目录的 `.partial`，成功后 `os.replace` 原子改名。
    中途取消或出错，落在磁盘上的只有 `.partial`，绝不会有一个**看起来完整**的归档
    ——半份 ZIP 是能打开的，条目少而已，静默截断比失败更难发现。

    manifest 逐条记录 `sha256`，让「解压并逐项 hash」可以离线复核，
    不必信任服务端自报的任何东西。同一份清单还会以 `manifest_entry_name`
    写进归档：归档一旦离开本系统（转发、备份、拷进 U 盘），响应头就没了，
    自带清单才能让它在任何地方都可自证。
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正")

    reserved = [manifest_entry_name] if manifest_entry_name else []
    planned = assign_entry_names(members, reserved=reserved)
    partial = destination.with_name(destination.name + ".partial")
    partial.parent.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    total_bytes = 0
    try:
        with zipfile.ZipFile(
            partial, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
        ) as archive:
            for member, entry_name, reasons in planned:
                if should_cancel is not None and should_cancel():
                    raise ArchiveCancelled("打包已取消")

                info = zipfile.ZipInfo(entry_name, date_time=_FIXED_DATE_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                # 0o644 常规文件。钉死权限位是确定性的一部分；
                # 同时避免把源文件的可执行位带进归档。
                info.external_attr = (0o100644 & 0xFFFF) << 16

                digest = hashlib.sha256()
                written = 0
                with archive.open(info, "w") as sink, member.source_path.open("rb") as src:
                    while True:
                        if should_cancel is not None and should_cancel():
                            raise ArchiveCancelled("打包已取消")
                        block = src.read(chunk_size)
                        if not block:
                            break
                        digest.update(block)
                        sink.write(block)
                        written += len(block)

                actual = digest.hexdigest()
                if actual != member.sha256:
                    # 入库时记的摘要和此刻读到的字节不一致 ⇒ 存储已损坏。
                    # 必须中断：继续下去会打出一个「manifest 与内容不符」的归档，
                    # 而它的自校验会通过，因为 manifest 抄的是数据库。
                    raise IOError(
                        f"制品字节与入库摘要不符：{entry_name}"
                        f"（库记 {member.sha256[:12]}…，实读 {actual[:12]}…）"
                    )

                entries.append(
                    {
                        "entry_name": entry_name,
                        "original_name": member.original_name,
                        "sha256": actual,
                        "size_bytes": written,
                        "renamed": bool(reasons),
                        "rename_reasons": reasons,
                    }
                )
                total_bytes += written

            if manifest_entry_name:
                info = zipfile.ZipInfo(manifest_entry_name, date_time=_FIXED_DATE_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100644 & 0xFFFF) << 16
                # `sort_keys` + 固定分隔符 ⇒ 同样的条目集合产出同样的字节，
                # 确定性不会因为清单而破功。
                archive.writestr(
                    info,
                    json.dumps(
                        {"entry_count": len(entries), "entries": entries},
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8"),
                )

        os.replace(partial, destination)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    return {
        "entry_count": len(entries),
        "total_bytes": total_bytes,
        "archive_sha256": _digest_file(destination, chunk_size=chunk_size),
        "archive_size_bytes": destination.stat().st_size,
        "deterministic": True,
        "entries": entries,
    }


def _digest_file(path: Path, *, chunk_size: int) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def sync_batch_rejection(entry_count: int, total_bytes: int) -> str | None:
    """同步批量能不能受理；不能则给出**为什么**和该走哪条路。

    返回 None 表示可以。返回文案时说清界限值——「太大了」这种提示会让人反复试探，
    每一次试探都是一次真实的资源消耗。
    """
    if entry_count > MAX_SYNC_ENTRIES:
        return (
            f"同步批量最多 {MAX_SYNC_ENTRIES} 个条目，本次 {entry_count} 个。"
            "更大的批量请走异步导出任务，避免单个请求长时间占住 worker。"
        )
    if total_bytes > MAX_SYNC_BYTES:
        return (
            f"同步批量最多 {MAX_SYNC_BYTES // (1024 * 1024)} MiB，"
            f"本次约 {total_bytes // (1024 * 1024)} MiB。"
            "更大的批量请走异步导出任务。"
        )
    return None


def iter_archive(path: Path, *, chunk_size: int = CHUNK_SIZE) -> Iterator[bytes]:
    """按块读出归档。和 `download_range.iter_file_range` 同一个理由：
    一次读完等于把归档放进内存，正是 stop_condition 禁止的。"""
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk_size)
            if not block:
                return
            yield block


def verify_archive(path: Path, manifest: dict) -> list[str]:
    """离线复核：打开归档，逐项重算 sha256，与 manifest 对照。

    这是「解压并逐项 hash」的可执行版本，也是测试与运维共用的同一段代码——
    验收脚本和生产排查用不同的实现，等于验收验的不是生产在跑的东西。

    返回问题清单，空表示一致。
    """
    problems: list[str] = []
    expected = {e["entry_name"]: e for e in manifest["entries"]}

    with zipfile.ZipFile(path) as archive:
        raw_names = archive.namelist()
        # 同名检测要在**去掉清单之前**做：清单也可能和用户文件撞名，
        # 先剔除就等于给自己开了后门。
        if len(raw_names) != len(set(raw_names)):
            problems.append("归档内存在同名条目——解压时会互相覆盖")
        collisions = [n for n in raw_names if raw_names.count(n) == 1]
        keys = [collision_key(n) for n in collisions]
        if len(keys) != len(set(keys)):
            problems.append(
                "归档内存在解压端会碰撞的条目名（大小写或 Unicode 规范化后同名）"
            )
        for name in raw_names:
            if "/" in name or "\\" in name or name.startswith("..") or _DRIVE.match(name):
                problems.append(f"条目名含路径成分（zip-slip）：{name!r}")

        names = [n for n in raw_names if n != MANIFEST_ENTRY_NAME]
        # 自带清单必须与返回的 manifest 一致，否则归档离开本系统后就自证不了。
        if MANIFEST_ENTRY_NAME in raw_names:
            embedded = json.loads(archive.read(MANIFEST_ENTRY_NAME).decode("utf-8"))
            if embedded.get("entries") != manifest["entries"]:
                problems.append("归档自带清单与返回的 manifest 不一致")

        missing = set(expected) - set(names)
        for name in sorted(missing):
            problems.append(f"manifest 列出但归档内缺失：{name!r}")
        extra = set(names) - set(expected)
        for name in sorted(extra):
            problems.append(f"归档内多出 manifest 未列的条目：{name!r}")

        for name in sorted(set(names) & set(expected)):
            digest = hashlib.sha256()
            size = 0
            with archive.open(name) as handle:
                while True:
                    block = handle.read(CHUNK_SIZE)
                    if not block:
                        break
                    digest.update(block)
                    size += len(block)
            record = expected[name]
            if digest.hexdigest() != record["sha256"]:
                problems.append(f"条目内容与 manifest 摘要不符：{name!r}")
            if size != record["size_bytes"]:
                problems.append(f"条目长度与 manifest 不符：{name!r}")

    return problems


def members_from_artifact_rows(
    rows: Iterable[dict],
    resolve_path: Callable[[dict], Path],
) -> list[ArchiveMember]:
    """把 `artifact_versions` 行转成打包条目。`resolve_path` 由调用方注入，
    因为对象落地方式（本地 / S3 物化）是存储层的事，本模块不该知道。"""
    members: list[ArchiveMember] = []
    for row in rows:
        members.append(
            ArchiveMember(
                source_path=resolve_path(row),
                original_name=str(row.get("original_name") or ""),
                sha256=str(row["sha256"]),
                size_bytes=int(row["size_bytes"]),
                sort_key=str(row.get("artifact_version_id") or row["sha256"]),
            )
        )
    return members
