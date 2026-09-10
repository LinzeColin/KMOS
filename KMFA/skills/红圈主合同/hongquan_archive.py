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


def ensure_archive_root(archive_root: Path) -> None:
    try:
        archive_root.mkdir(parents=True, exist_ok=True)
        if not archive_root.is_dir():
            raise SmbUnavailable("archive_root_not_directory")
    except (OSError, SmbUnavailable) as exc:
        if isinstance(exc, SmbUnavailable):
            raise
        raise SmbUnavailable("archive_root_unavailable") from exc


def archive_file(source: Path, target: Path) -> str:
    source_md5 = md5_file(source)
    if target.exists():
        try:
            if md5_file(target) == source_md5:
                return source_md5
        except OSError as exc:
            raise ArchiveFailure("target_readback_failed") from exc

        digest_target = target.with_name("%s_%s%s" % (target.stem, source_md5[:12], target.suffix))
        if digest_target.exists():
            try:
                if md5_file(digest_target) == source_md5:
                    return source_md5
            except OSError as exc:
                raise ArchiveFailure("target_readback_failed") from exc
        target = digest_target

    run_rsync(source, target)
    try:
        if md5_file(target) != source_md5:
            raise ArchiveFailure("target_md5_mismatch")
    except OSError as exc:
        raise ArchiveFailure("target_readback_failed") from exc
    return source_md5


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
    except OSError as exc:
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
        local_md5 = md5_file(local_manifest)
        run_rsync(local_manifest, manifest)
        try:
            if md5_file(manifest) != local_md5:
                raise ArchiveFailure("manifest_md5_mismatch")
        except OSError as exc:
            raise ArchiveFailure("manifest_readback_failed") from exc


def lock_path_for(archive_root: Path) -> Path:
    identity = hashlib.md5(str(archive_root).encode("utf-8")).hexdigest()
    return Path(tempfile.gettempdir()) / ("hongquan_archive_%s.lock" % identity)


def holder_is_alive(lock_path: Path) -> bool:
    try:
        pid = int(lock_path.read_text(encoding="utf-8").splitlines()[0])
    except (OSError, ValueError, IndexError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def acquire_lock(lock_path: Path) -> bool:
    try:
        descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        if holder_is_alive(lock_path):
            return False
        try:
            lock_path.unlink()
        except OSError:
            return False
        return acquire_lock(lock_path)
    try:
        os.write(descriptor, ("%d\n%d\n" % (os.getpid(), int(time.time()))).encode("ascii"))
    finally:
        os.close(descriptor)
    return True


def release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except OSError:
        pass


def resolve_paths() -> Tuple[Path, Path]:
    base = os.environ.get("HONGQUAN_BASE")
    if base:
        archive_root = Path(os.environ.get("HONGQUAN_ARCHIVE_ROOT", base)).expanduser()
        downloads = Path(os.environ.get("HONGQUAN_DOWNLOADS", str(Path(base).expanduser() / "Downloads"))).expanduser()
    else:
        archive_root = Path(os.environ.get("HONGQUAN_ARCHIVE_ROOT", str(DEFAULT_ARCHIVE_ROOT))).expanduser()
        downloads = Path(os.environ.get("HONGQUAN_DOWNLOADS", str(Path.home() / "Downloads"))).expanduser()
    return downloads, archive_root


def run(verify_only: bool) -> int:
    downloads, archive_root = resolve_paths()
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
        sources = candidate_sources(downloads)
        if not sources:
            print("ARCHIVE_NONE")
            return 0

        now = shanghai_now()
        snapshot_ym = now.strftime("%Y%m")
        export_date = now.strftime("%Y%m%d")
        report_period = os.environ.get("HONGQUAN_REPORT_PERIOD", snapshot_ym)
        manifest = archive_root / snapshot_ym / "红圈" / "00_归档清单" / (
            "%s_红圈业务源归档清单.md" % export_date
        )
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
            target = target_dir / filename
            file_md5 = archive_file(source, target)
            if target.exists() and md5_file(target) != file_md5:
                # ``archive_file`` may choose a digest suffix if the first name
                # is occupied by a different source; discover that deterministic
                # sibling for the manifest.
                target = target.with_name("%s_%s%s" % (target.stem, file_md5[:12], target.suffix))
            manifest_rows.append(
                (business_type, source.name, target, report_period, snapshot_ym, status, file_md5)
            )
            completed_sources.append(source)

        append_manifest(manifest, manifest_rows)
        for source in completed_sources:
            try:
                source.unlink()
            except OSError as exc:
                raise ArchiveFailure("downloads_cleanup_failed") from exc
        print("ARCHIVE_OK n=%d" % len(completed_sources))
        return 0
    except (ArchiveFailure, OSError):
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
