#!/usr/bin/env python3
"""归档红圈 Downloads 中已完成的一级业务源。

这是 ``kmfa-hongquan-daily`` 直接调用的无参数入口。默认只读取
``~/Downloads``，并投递到 KMFA 红圈一级原始数据根目录；测试必须把
``HONGQUAN_BASE`` 指到临时目录。该变量同时把默认输入改为
``$HONGQUAN_BASE/Downloads``，把归档根改为 ``$HONGQUAN_BASE``，从而不会
触及真实共享盘。``HONGQUAN_DOWNLOADS`` 与 ``HONGQUAN_ARCHIVE_ROOT`` 可用
于显式覆盖这两个路径。

标准输出只有 automation 识别的固定标记：
``ARCHIVE_OK``、``ARCHIVE_NONE``、``ARCHIVE_LOCKED``、``SMB_UNAVAILABLE``、
``ARCHIVE_FAILED``；``--verify-only`` 输出 ``SMB_WRITABLE``。
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from xml.etree import ElementTree

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python 3.8 fallback
    ZoneInfo = None  # type: ignore


DEFAULT_ARCHIVE_ROOT = Path(
    "/Volumes/share/03_资料库/MetaData/KMFA_MetaData/财务/一级原始数据/业务原始"
)
VALID_SUFFIXES = {".xlsx", ".xls", ".zip"}
XML_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


class ArchiveFailure(Exception):
    """A recoverable archive operation failure with no sensitive stderr."""


class SmbUnavailable(ArchiveFailure):
    """The configured archive base cannot be used."""


def shanghai_now() -> datetime:
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo("Asia/Shanghai"))
        except Exception:
            pass
    return datetime.now(timezone(timedelta(hours=8)))


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def remove_chrome_copy_suffix(stem: str) -> str:
    return re.sub(r"\s*\(\d+\)$", "", stem).strip()


def classify_source(path: Path) -> Optional[str]:
    """Classify only a completed red-circle export by its stable visible name."""

    if path.name.startswith("._") or path.name.endswith(".crdownload"):
        return None
    if path.suffix.lower() not in VALID_SUFFIXES:
        return None

    name = remove_chrome_copy_suffix(path.stem)
    normalized = re.sub(r"[\s_\-]+", "", name)
    if "付款审批" in normalized or "日常费用" in normalized:
        return "付款审批（日常费用）"
    if "收款登记" in normalized or "销售会计回款" in normalized:
        return "收款登记"
    if "项目资金支出" in normalized or "资金支出" in normalized:
        return "项目资金支出"
    if "项目开票" in normalized:
        return "项目开票"
    if "招标信息" in normalized:
        return "招标信息"
    if "投标记录" in normalized:
        return "投标记录"
    if "投标主合同" in normalized or ("投标" in normalized and "主合同" in normalized):
        return "投标主合同"
    if "主合同" in normalized:
        return "主合同"
    return None


def candidate_sources(downloads: Path) -> List[Tuple[Path, str]]:
    """Inspect only the immediate Downloads directory; never recurse through it."""

    if not downloads.is_dir():
        return []
    found: List[Tuple[Path, str]] = []
    try:
        entries = sorted(downloads.iterdir(), key=lambda item: item.name)
    except OSError:
        return []
    for entry in entries:
        if not entry.is_file():
            continue
        business_type = classify_source(entry)
        if business_type is not None:
            found.append((entry, business_type))
    return found


def xlsx_text_rows(path: Path) -> List[List[str]]:
    """Read only string cells needed to validate the two all-history exports."""

    if path.suffix.lower() != ".xlsx":
        return []
    try:
        with zipfile.ZipFile(path) as workbook:
            names = set(workbook.namelist())
            if "xl/sharedStrings.xml" not in names:
                return []
            shared_root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
            shared: List[str] = []
            for item in shared_root.findall("x:si", XML_NS):
                shared.append("".join(item.itertext()))

            sheet_names = sorted(
                name for name in names
                if name.startswith("xl/worksheets/") and name.endswith(".xml")
            )
            rows: List[List[str]] = []
            for sheet_name in sheet_names:
                root = ElementTree.fromstring(workbook.read(sheet_name))
                for row in root.findall(".//x:sheetData/x:row", XML_NS):
                    values: Dict[int, str] = {}
                    for cell in row.findall("x:c", XML_NS):
                        ref = cell.attrib.get("r", "")
                        match = re.match(r"([A-Z]+)", ref)
                        if not match:
                            continue
                        column = 0
                        for char in match.group(1):
                            column = column * 26 + ord(char) - ord("A") + 1
                        raw = cell.findtext("x:v", default="", namespaces=XML_NS)
                        cell_type = cell.attrib.get("t")
                        if cell_type == "s" and raw.isdigit() and int(raw) < len(shared):
                            values[column] = shared[int(raw)]
                        elif cell_type == "inlineStr":
                            inline = cell.find("x:is", XML_NS)
                            values[column] = "" if inline is None else "".join(inline.itertext())
                        else:
                            values[column] = raw
                    if values:
                        last = max(values)
                        rows.append([values.get(index, "") for index in range(1, last + 1)])
            return rows
    except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError):
        return []


def all_history_status(path: Path, business_type: str) -> Tuple[bool, str]:
    """Require a named date column and at least two observed calendar years."""

    header_key = "收款日期" if business_type == "收款登记" else "申请日期"
    rows = xlsx_text_rows(path)
    for index, row in enumerate(rows[:20]):
        matched = [position for position, value in enumerate(row) if header_key in value]
        if not matched:
            continue
        column = matched[0]
        years: Set[str] = set()
        for data_row in rows[index + 1:]:
            if column >= len(data_row):
                continue
            years.update(re.findall(r"(?<!\d)(20\d{2})(?!\d)", data_row[column]))
        if len(years) >= 2:
            return True, "全历史导出口径已复读"
        return False, "导出口径未达全历史"
    return False, "导出口径待确认"


def extract_task_id(path: Path) -> str:
    match = re.search(r"(?:任务|导出文件)[_\-\s]*(\d+)", remove_chrome_copy_suffix(path.stem))
    return match.group(1) if match else ""


def output_filename(
    source: Path,
    business_type: str,
    snapshot_ym: str,
    export_date: str,
    all_history: bool,
) -> str:
    suffix = source.suffix.lower()
    task_id = extract_task_id(source)
    task_suffix = "_任务%s" % task_id if task_id else ""
    if business_type == "主合同":
        return "%s_红圈主合同_全部主合同_原始导出%s%s" % (export_date, task_suffix, suffix)
    if business_type == "投标主合同":
        return "%s_红圈投标主合同_截至%s_原始导出%s" % (snapshot_ym, export_date, suffix)
    if business_type == "招标信息":
        return "%s_红圈招标信息_截至%s_原始导出%s" % (snapshot_ym, export_date, suffix)
    if business_type == "投标记录":
        return "%s_红圈投标记录_截至%s_原始导出%s" % (snapshot_ym, export_date, suffix)
    if business_type == "项目开票":
        return "%s_红圈项目开票_截至%s_原始导出%s" % (snapshot_ym, export_date, suffix)
    if business_type == "项目资金支出":
        return "%s_红圈项目资金支出_截至%s_原始导出%s" % (snapshot_ym, export_date, suffix)
    if business_type == "收款登记":
        if all_history:
            return "红圈收款登记_全历史导出_%s%s" % (export_date, suffix)
        return "%s_红圈收款登记_截至%s_原始导出%s" % (snapshot_ym, export_date, suffix)
    if business_type == "付款审批（日常费用）":
        if all_history:
            return "红圈付款审批（日常费用）_全历史导出_%s%s" % (export_date, suffix)
        return "%s_红圈付款审批（日常费用）_截至%s_原始导出%s" % (snapshot_ym, export_date, suffix)
    raise ArchiveFailure("unknown_business_type")


def run_rsync(source: Path, target: Path) -> None:
    """The only file write channel used for the shared archive."""

    try:
        completed = subprocess.run(
            ["/usr/bin/rsync", "-a", "--inplace", "--", str(source), str(target)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ArchiveFailure("rsync_unavailable") from exc
    if completed.returncode != 0:
        raise ArchiveFailure("rsync_failed")


def archive_mount_point(archive_root: Path) -> Optional[Path]:
    """归档根在 /Volumes/<卷名>/ 下时返回挂载点；测试用的临时目录返回 None（不查挂载）。"""

    parts = Path(archive_root).parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "Volumes":
        return Path("/Volumes") / parts[2]
    return None


def smb_mounted(mount_point: Path, mount_table: Optional[str] = None) -> bool:
    """挂载表里这个点确实是 smbfs 才算共享盘在线。

    共享盘掉线后 macOS 常把 /Volumes/share 留成一个本机空目录：这时 mkdir、rsync、md5 读回
    全都会在本机「成功」，文件其实没进共享盘，源件却被删了。所以只认挂载表，不认目录在不在。
    """

    if mount_table is None:
        try:
            mount_table = subprocess.run(["/sbin/mount"], capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.TimeoutExpired):
            return False
    needle = " on %s (smbfs" % mount_point
    return any(needle in line for line in mount_table.splitlines())


def ensure_archive_root(archive_root: Path, mount_table: Optional[str] = None) -> None:
    mount_point = archive_mount_point(archive_root)
    if mount_point is not None and not smb_mounted(mount_point, mount_table):
        raise SmbUnavailable("share_not_mounted")
    try:
        archive_root.mkdir(parents=True, exist_ok=True)
        if not archive_root.is_dir():
            raise SmbUnavailable("archive_root_not_directory")
    except (OSError, SmbUnavailable) as exc:
        if isinstance(exc, SmbUnavailable):
            raise
        raise SmbUnavailable("archive_root_unavailable") from exc


WRITE_ATTEMPTS = 2
INCOMING_PREFIX = ".__incoming__"      # 以 ._ 开头：下游一律跳过，写到一半的件永远不会被当成正式件


def is_partial_file(path: Path) -> bool:
    """共享盘上写坏的残件：0 字节；xlsx/zip 却没有 zip 文件头；或有文件头但 zip 不完整（写到一半）。"""

    try:
        if path.stat().st_size == 0:
            return True
        if path.suffix.lower() in {".xlsx", ".zip"}:
            with path.open("rb") as handle:
                if handle.read(4) != b"PK\x03\x04":
                    return True
            return not zipfile.is_zipfile(str(path))
    except OSError:
        return False
    return False


def remove_partial(target: Path) -> None:
    for path in (target, target.with_name("._" + target.name)):
        try:
            path.unlink()
        except OSError:
            pass


def put_verified(source: Path, target: Path, expected_md5: str) -> None:
    """先写同目录的临时名、读回 md5 一致再改成正式名：正式名上不会出现写到一半的文件。

    2026-09-11 一次投递在共享盘上留下 0 字节空壳、整批中止；写后读回不一致就再写一次，
    仍不一致就删掉临时件再报错，正式名始终保持原样。
    """

    incoming = target.with_name(INCOMING_PREFIX + target.name)
    failure = ArchiveFailure("target_md5_mismatch")
    for _ in range(WRITE_ATTEMPTS):
        try:
            run_rsync(source, incoming)
            if md5_file(incoming) != expected_md5:
                failure = ArchiveFailure("target_md5_mismatch")
                continue
            os.replace(str(incoming), str(target))
            return
        except ArchiveFailure as exc:
            failure = exc
        except OSError:
            failure = ArchiveFailure("target_readback_failed")
    remove_partial(incoming)
    raise failure


def archive_file(source: Path, target: Path) -> Tuple[str, Path]:
    """投递单个文件，返回 (md5, 最终落盘路径)。同名位置上的残件视为没写成、直接重写。"""

    source_md5 = md5_file(source)
    if target.exists() and not is_partial_file(target):
        try:
            if md5_file(target) == source_md5:
                return source_md5, target
        except OSError as exc:
            raise ArchiveFailure("target_readback_failed") from exc

        digest_target = target.with_name("%s_%s%s" % (target.stem, source_md5[:12], target.suffix))
        if digest_target.exists() and not is_partial_file(digest_target):
            try:
                if md5_file(digest_target) == source_md5:
                    return source_md5, digest_target
            except OSError as exc:
                raise ArchiveFailure("target_readback_failed") from exc
        target = digest_target

    put_verified(source, target, source_md5)
    return source_md5, target


KEY_COLUMNS = {
    "主合同": "合同编号",
    "投标主合同": "合同编号",
    "项目开票": "发票号码",
    "收款登记": "收款编号",
    "项目资金支出": "申请编号",
    "招标信息": "招标项目名称",
    "投标记录": "投标名称",
    "付款审批（日常费用）": "付款编号",
}


def looks_like_export(path: Path, business_type: str) -> bool:
    """人工或旧流程落进 Downloads 的件，先证明是完整的红圈导出再入库：zip 完整、表头含该对象主键列、至少一行数据。"""

    if path.suffix.lower() != ".xlsx" or is_partial_file(path):
        return False
    rows = xlsx_text_rows(path)
    key = KEY_COLUMNS.get(business_type, "")
    return len(rows) >= 2 and bool(key) and any(key in cell for cell in rows[0])


def split_valid(sources: Sequence[Tuple[Path, str]], quarantine: Path) -> Tuple[List[Tuple[Path, str]], List[str]]:
    """不像完整红圈导出的件移到隔离区（不入库、也不留在 Downloads），返回 (可入库的件, 被隔离的文件名)。"""

    valid: List[Tuple[Path, str]] = []
    moved: List[str] = []
    for path, business_type in sources:
        if looks_like_export(path, business_type):
            valid.append((path, business_type))
            continue
        try:
            quarantine.mkdir(parents=True, exist_ok=True)
            os.replace(str(path), str(quarantine / ("%d_%s" % (int(time.time()), path.name))))
        except OSError:
            pass
        moved.append(path.name)
    return valid, moved


def runtime_root() -> Path:
    base = os.environ.get("HONGQUAN_BASE")
    return Path(base).expanduser() if base else Path.home() / ".local" / "share" / "kmfa-hongquan"


def manifest_header() -> str:
    return (
        "# 红圈业务源归档清单\n\n"
        "| 来源页面 | 原始文件名 | 最终 SMB 路径 | 主体字段 | 报告期间 | 来源快照期间 | "
        "实际来源截止日 | 记录状态 | 下游使用边界 | MD5 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )


def markdown_cell(value: str) -> str:
    return value.replace("|", "／").replace("\n", " ").strip()


def append_manifest(
    manifest: Path,
    rows: Sequence[Tuple[str, str, Path, str, str, str, str]],
) -> None:
    """Append local text then use rsync and an MD5 readback for the SMB file."""

    try:
        current = manifest.read_text(encoding="utf-8") if manifest.exists() else manifest_header()
    except (OSError, UnicodeDecodeError) as exc:
        raise ArchiveFailure("manifest_read_failed") from exc

    additions: List[str] = []
    for business_type, source_name, target, report_period, snapshot_period, status, file_md5 in rows:
        marker = "| %s |" % markdown_cell(str(target))
        if marker in current or marker in additions:
            continue
        additions.append(
            "| {page} | {source} | {target} | 原件未提供 | {report} | {snapshot} | "
            "{cutoff} | {status} | 业务观察；未与金蝶、税票、银行逐笔闭合 | {md5} |\n".format(
                page=markdown_cell(business_type),
                source=markdown_cell(source_name),
                target=markdown_cell(str(target)),
                report=markdown_cell(report_period),
                snapshot=markdown_cell(snapshot_period),
                cutoff=shanghai_now().strftime("%Y%m%d"),
                status=markdown_cell(status),
                md5=file_md5,
            )
        )
    if not additions:
        return

    content = current
    if not content.endswith("\n"):
        content += "\n"
    content += "".join(additions)
    with tempfile.TemporaryDirectory(prefix="hongquan-manifest-") as temporary:
        local_manifest = Path(temporary) / manifest.name
        local_manifest.write_text(content, encoding="utf-8")
        put_verified(local_manifest, manifest, md5_file(local_manifest))


_HELD_LOCKS: Dict[str, int] = {}


def lock_path_for(archive_root: Path) -> Path:
    identity = hashlib.md5(str(archive_root).encode("utf-8")).hexdigest()
    return runtime_root() / "locks" / ("hongquan_archive_%s.lock" % identity)


def acquire_lock(lock_path: Path) -> bool:
    """内核文件锁：持有进程一死就自动释放——不会有陈旧锁，也不怕 PID 被别的进程复用。"""

    if str(lock_path) in _HELD_LOCKS:
        return False
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    except OSError:
        return False
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(descriptor)
        return False
    os.ftruncate(descriptor, 0)
    os.write(descriptor, ("%d\n%d\n" % (os.getpid(), int(time.time()))).encode("ascii"))
    _HELD_LOCKS[str(lock_path)] = descriptor
    return True


def holder_is_alive(lock_path: Path) -> bool:
    """有进程正持有这把锁就返回 True；只探测，不占用。"""

    if str(lock_path) in _HELD_LOCKS:
        return True
    try:
        descriptor = os.open(str(lock_path), os.O_RDONLY)
    except OSError:
        return False
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return True
    else:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        return False
    finally:
        os.close(descriptor)


def release_lock(lock_path: Path) -> None:
    descriptor = _HELD_LOCKS.pop(str(lock_path), None)
    if descriptor is None:
        return
    try:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def resolve_paths() -> Tuple[Path, Path]:
    base = os.environ.get("HONGQUAN_BASE")
    if base:
        archive_root = Path(os.environ.get("HONGQUAN_ARCHIVE_ROOT", base)).expanduser()
        downloads = Path(os.environ.get("HONGQUAN_DOWNLOADS", str(Path(base).expanduser() / "Downloads"))).expanduser()
    else:
        archive_root = Path(os.environ.get("HONGQUAN_ARCHIVE_ROOT", str(DEFAULT_ARCHIVE_ROOT))).expanduser()
        downloads = Path(os.environ.get("HONGQUAN_DOWNLOADS", str(Path.home() / "Downloads"))).expanduser()
    return downloads, archive_root


def archive_sources(sources: Sequence[Tuple[Path, str]], archive_root: Path) -> int:
    """逐件投递并追加清单；全部读回校验通过后才删源件，返回件数。

    任何一件失败都抛 ``ArchiveFailure``：已投递的件留在共享盘、源件一律不删，
    下一轮同 md5 直接认领，补写清单后再删源件。调用方负责加锁。
    """

    now = shanghai_now()
    snapshot_ym = now.strftime("%Y%m")
    export_date = now.strftime("%Y%m%d")
    report_period = os.environ.get("HONGQUAN_REPORT_PERIOD", snapshot_ym)
    manifest = archive_root / snapshot_ym / "红圈" / "00_归档清单" / (
        "%s_红圈业务源归档清单.md" % export_date
    )
    ensure_archive_root(archive_root)          # 写之前确认共享盘仍在线，掉线的挂载点上不建任何目录
    manifest.parent.mkdir(parents=True, exist_ok=True)

    manifest_rows: List[Tuple[str, str, Path, str, str, str, str]] = []
    completed_sources: List[Path] = []
    for source, business_type in sources:
        all_history = False
        status = "原件已归档"
        if business_type in {"收款登记", "付款审批（日常费用）"}:
            all_history, status = all_history_status(source, business_type)
        filename = output_filename(source, business_type, snapshot_ym, export_date, all_history)
        target_dir = archive_root / snapshot_ym / "红圈" / business_type
        target_dir.mkdir(parents=True, exist_ok=True)
        file_md5, target = archive_file(source, target_dir / filename)
        manifest_rows.append(
            (business_type, source.name, target, report_period, snapshot_ym, status, file_md5)
        )
        completed_sources.append(source)

    append_manifest(manifest, manifest_rows)
    ensure_archive_root(archive_root)          # 删源件前再确认一次：中途掉线就保留源件
    for source in completed_sources:
        try:
            source.unlink()
        except OSError as exc:
            raise ArchiveFailure("source_cleanup_failed") from exc
    return len(completed_sources)


def run(verify_only: bool, downloads: Optional[Path] = None, archive_root: Optional[Path] = None) -> int:
    default_downloads, default_root = resolve_paths()
    downloads = downloads or default_downloads
    archive_root = archive_root or default_root
    try:
        ensure_archive_root(archive_root)
    except SmbUnavailable:
        print("SMB_UNAVAILABLE")
        return 1

    if verify_only:
        print("SMB_WRITABLE")
        return 0

    lock_path = lock_path_for(archive_root)
    if not acquire_lock(lock_path):
        print("ARCHIVE_LOCKED")
        return 0

    try:
        sources, quarantined = split_valid(candidate_sources(downloads), runtime_root() / "quarantine")
        for name in quarantined:
            print("QUARANTINED %s" % name)
        if not sources:
            print("ARCHIVE_NONE")
            return 0
        count = archive_sources(sources, archive_root)
        print("ARCHIVE_OK n=%d" % count)
        return 0
    except (ArchiveFailure, OSError, ValueError):
        print("ARCHIVE_FAILED")
        return 2
    finally:
        release_lock(lock_path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    return run(args.verify_only)


if __name__ == "__main__":
    raise SystemExit(main())
