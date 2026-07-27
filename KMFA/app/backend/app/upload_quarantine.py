# -*- coding: utf-8 -*-
"""S06/P6.2 · T-S06-02：quarantine-first 文件安全流水线。

绑定判据（acceptance_contract.yaml · AC-UP-003 原文）：
  输入：MIME 欺骗、路径穿越、双扩展、宏、EICAR、zip bomb、畸形媒体、解析器超时
  阈值：**恶意/畸形逃逸 = 0；解析不在主进程执行；标准合法夹具误拒 < 1%**

「quarantine-first」这个名字是整个设计的全部：
**默认隔离，只有明确判干净的才放行。** 反过来做（默认放行、发现坏的再拦）
在这里是行不通的——阈值要求逃逸为 0，而「发现坏的」永远滞后于「出现新的坏的」。

四条判定各自解决一类逃逸，缺一条就有一整类漏网：

  ① 文件名 —— 路径穿越、NUL 截断、Windows 保留名、结尾点/空格。
     这些在**存储**层出事（写到隔离区之外），所以必须在落盘前判，而不是预览前。
  ② magic vs 声明 MIME —— 「说自己是 png，头两个字节是 MZ」。
     只信客户端声明等于没验；只看扩展名同理。以**内容**为准。
  ③ 内容签名 —— EICAR 这类必须命中。它是行业约定的自检样本，
     命不中说明这条链根本没在扫。
  ④ 压缩包结构 —— **只读中央目录，绝不解压**。zip bomb 的杀伤力正来自解压，
     解压之后再判大小已经晚了。看压缩比、总解压体积、条目数、嵌套深度、条目路径。

「解析不在主进程」这条：本模块**不做任何解析**，只做判定，并输出
`may_parse` 让上层决定是否交给隔离的解析器。判定本身零解析，
所以恶意文件不可能在判定阶段触发解析器漏洞——这是结构性保证，不是纪律要求。

「合法误拒 < 1%」：所有规则都针对**可指名的攻击形态**，不做「看着可疑就拦」。
每加一条规则都要能回答「哪个正常文件会被它误伤」，答不上来的规则不加。
"""
from __future__ import annotations

import re
import struct
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

#: 扫描状态机。**只有 clean 允许被解析/预览**，其余一律 attachment-only。
#: `scan_timeout` 单列而不并进 quarantined：前者是「我们没判完」，
#: 后者是「我们判定它坏」。混在一起会让「扫描器挂了」看起来像「文件是恶意的」，
#: 运维会去查错的方向。
STATE_CLEAN = "clean"
STATE_QUARANTINED = "quarantined"
STATE_SCAN_TIMEOUT = "scan_timeout"
STATE_PENDING = "pending"

#: 上限。超过即判定为压缩炸弹，不解压。
MAX_ARCHIVE_RATIO = 120           # 单条目压缩比
MAX_ARCHIVE_TOTAL_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 20_000
MAX_ARCHIVE_DEPTH = 2             # 压缩包里再套压缩包

#: EICAR 标准反病毒测试串。命不中说明这条链根本没在扫。
EICAR = (b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-"
         b"ANTIVIRUS-TEST-FILE!$H+H*")

#: Windows 保留设备名。在 Windows 上以它们命名会写到设备而不是文件。
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

#: 可执行/脚本类扩展。用于识别**双扩展**（`发票.pdf.exe`）——
#: 它骗的是「只看最后一个扩展的人」和「只看第一个扩展的人」，两边各能骗一批。
_DANGEROUS_EXT = {
    ".exe", ".dll", ".scr", ".com", ".bat", ".cmd", ".pif", ".msi",
    ".sh", ".bash", ".zsh", ".ps1", ".vbs", ".js", ".jse", ".wsf", ".hta",
    ".jar", ".app", ".dmg", ".pkg", ".lnk",
}

#: magic 签名 → 它真正是什么。只列**能被伪装成正常文件**的那些。
_MAGIC = (
    (b"MZ", "application/x-msdownload"),
    (b"\x7fELF", "application/x-executable"),
    (b"\xca\xfe\xba\xbe", "application/java-vm"),
    (b"#!", "application/x-sh"),
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"PK\x03\x04", "application/zip"),
    (b"\xd0\xcf\x11\xe0", "application/x-ole-storage"),   # 老式 Office，宏的常见载体
)

#: 声明类型与 magic 判定的**可接受**组合。zip 是容器，docx/xlsx 都以它为壳，
#: 所以 zip magic 配 Office 类型不算欺骗——不列出来会造成大批误拒。
_MAGIC_COMPATIBLE = {
    "application/zip": {
        "application/zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/epub+zip", "application/java-archive",
    },
    "application/x-ole-storage": {
        "application/x-ole-storage", "application/msword",
        "application/vnd.ms-excel", "application/vnd.ms-powerpoint",
    },
}


@dataclass
class ScanVerdict:
    state: str
    reasons: list[str] = field(default_factory=list)
    detected_type: str | None = None
    may_parse: bool = False
    attachment_only: bool = True

    @property
    def is_clean(self) -> bool:
        return self.state == STATE_CLEAN


def safe_filename(raw: str | None) -> tuple[str, list[str]]:
    """归一化文件名并报出所有问题。**在落盘前调用**——路径穿越是存储层的事。

    返回（安全名, 问题清单）。问题非空即进隔离，不是「清洗后放行」：
    悄悄改名会让用户拿到一个他没上传过的文件名，而攻击者拿到的是一次免费重试。
    """
    problems: list[str] = []
    if not raw or not raw.strip():
        return "", ["文件名为空"]
    name = unicodedata.normalize("NFC", raw)

    if "\x00" in name:
        problems.append("含 NUL——用于截断路径，让检查看到的名字和写盘的不是同一个")
    if any(unicodedata.category(ch).startswith("C") for ch in name):
        problems.append("含控制字符")
    if "/" in name or "\\" in name:
        problems.append("含路径分隔符——路径穿越")
    if name in {".", ".."} or name.startswith("../") or "/../" in name:
        problems.append("路径穿越")
    if re.match(r"^[A-Za-z]:", name) or name.startswith("/"):
        problems.append("绝对路径")

    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    stem = base.split(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED:
        problems.append(f"Windows 保留设备名 {stem}——写它等于写设备而不是文件")
    if base != base.rstrip(". "):
        problems.append("结尾有点或空格——Windows 会静默去掉，得到与检查时不同的名字")

    suffixes = [s.lower() for s in Path(base).suffixes]
    if len(suffixes) >= 2 and suffixes[-1] in _DANGEROUS_EXT:
        problems.append(f"双扩展 {''.join(suffixes)}——最后一段是可执行类")
    elif suffixes and suffixes[-1] in _DANGEROUS_EXT:
        problems.append(f"可执行类扩展 {suffixes[-1]}")

    if len(base.encode("utf-8")) > 255:
        problems.append("文件名过长")
    return base, problems


def detect_magic(head: bytes) -> str | None:
    """按内容头判断它**真正**是什么。判不出返回 None——判不出不等于安全。"""
    for signature, media_type in _MAGIC:
        if head.startswith(signature):
            return media_type
    return None


def magic_conflicts(declared: str | None, detected: str | None) -> bool:
    """声明与实测是否冲突。

    只在**两边都明确**时才判冲突：detected 为 None（判不出）不算欺骗，
    否则所有未知格式都会被误拒，直接违反「合法误拒 < 1%」。
    """
    if not detected or not declared:
        return False
    normalized = declared.split(";", 1)[0].strip().lower()
    if normalized == detected:
        return False
    return normalized not in _MAGIC_COMPATIBLE.get(detected, set())


def inspect_archive(path: Path) -> list[str]:
    """检查压缩包结构——**只读中央目录，绝不解压**。

    zip bomb 的杀伤力全部来自解压：先解压再看大小，那时机器已经在挨打了。
    中央目录里就有原始大小与压缩大小，判定不需要解压一个字节。
    """
    problems: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
    except zipfile.BadZipFile:
        return ["压缩包结构损坏"]
    except Exception as exc:                      # noqa: BLE001
        return [f"压缩包读取失败 {type(exc).__name__}"]

    if len(infos) > MAX_ARCHIVE_ENTRIES:
        problems.append(f"条目数 {len(infos)} 超过 {MAX_ARCHIVE_ENTRIES}")
    total = 0
    for info in infos:
        total += info.file_size
        name = info.filename
        if name.startswith("/") or ".." in Path(name).parts or re.match(r"^[A-Za-z]:", name):
            problems.append(f"条目路径穿越：{name[:80]}")
        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
            if ratio > MAX_ARCHIVE_RATIO:
                problems.append(f"压缩比 {ratio:.0f}:1 超过 {MAX_ARCHIVE_RATIO}:1——压缩炸弹形态")
        if Path(name).suffix.lower() in {".zip", ".gz", ".bz2", ".xz", ".7z"}:
            problems.append(f"内嵌压缩包 {name[:60]}——嵌套解压是炸弹的常见放大手法")
    if total > MAX_ARCHIVE_TOTAL_BYTES:
        problems.append(f"解压后总量 {total} 超过上限")
    return problems


def scan(
    *,
    path: Path,
    declared_name: str | None,
    declared_media_type: str | None,
    head_bytes: int = 4096,
) -> ScanVerdict:
    """完整判定。**默认隔离**——只有一条问题都没有才判 clean。

    顺序：文件名 → magic → 内容签名 → 压缩包结构。
    先判文件名是因为它关乎**写到哪里**；其余关乎「能不能给解析器」。
    """
    reasons: list[str] = []
    _, name_problems = safe_filename(declared_name)
    reasons.extend(name_problems)

    try:
        with path.open("rb") as handle:
            head = handle.read(head_bytes)
    except OSError as exc:
        return ScanVerdict(STATE_SCAN_TIMEOUT,
                           [f"读不到内容 {type(exc).__name__}——判不了就不放行"],
                           None, False, True)

    detected = detect_magic(head)
    if magic_conflicts(declared_media_type, detected):
        reasons.append(f"声明 {declared_media_type} 与实际内容 {detected} 不符——MIME 欺骗")
    if EICAR in head:
        reasons.append("命中 EICAR 标准测试样本")
    if detected == "application/zip":
        reasons.extend(inspect_archive(path))

    if reasons:
        return ScanVerdict(STATE_QUARANTINED, reasons, detected, False, True)
    return ScanVerdict(STATE_CLEAN, [], detected, True, False)


def rollback_verdict(reason: str) -> ScanVerdict:
    """任务包 rollback 条款：所有未判定文件降级为 attachment-only、停预览处理器。

    降级不是「当作干净的处理」——`may_parse` 仍为 False。
    回滚的语义是「停止冒险」，不是「放弃检查」。
    """
    return ScanVerdict(STATE_PENDING, [reason], None, False, True)
