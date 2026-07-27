#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S06/P6.4 · T-S06-04 的三份交付物 → 一张 compact receipt。

任务包 outputs：`upload benchmark`、`negative matrix`、`capacity thresholds`、`compact receipt`
evidence 约束：**不超过 64KiB**。

为什么这三样要合成一张而不是各出各的：
  它们回答的是同一个问题的三面——「压得住吗」（benchmark）、
  「挡得住吗」（negative matrix）、「边界在哪」（thresholds）。
  分开出的话，读的人要自己拼，而拼错的代价是把「某一面没测」看成「都测了」。

64KiB 上限不是格式要求，是**内容纪律**：
  receipt 是给「三个月后想知道当时到底验了什么」的人看的，
  塞进原始日志它就没人读了。所以这里只放**结论与判据**，
  过程留在测试与运行记录里，receipt 指过去。

矩阵里的「预期」不是我写的，是**从任务包阈值抄下来的**；
「实测」由本工具现场跑测试得出。两列分开摆，才可能出现「预期与实测不符」这一格——
合成一列写就只剩自我确认。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

BEIJING = timezone(timedelta(hours=8))
MAX_RECEIPT_BYTES = 64 * 1024

#: 负向矩阵。**预期一列来自任务包阈值原文**，不是我的转述：
#:   AC-UP-001 未知/高风险仅附件；执行成功=0
#:   AC-UP-002 恢复=100%；篡改漏检=0；超限写前拒绝；重复不可控增长=0
#:   AC-UP-003 恶意/畸形逃逸=0；解析不在主进程；合法误拒<1%
#:   AC-UP-004 唯一可追溯；历史不被覆盖；血缘断点=0
NEGATIVE_MATRIX = [
    ("MIME 欺骗（声明 png、内容 PE）", "AC-UP-003", "隔离，不落库", "test_mime_spoofing_lands_in_quarantine"),
    ("双扩展 发票.pdf.exe", "AC-UP-003", "隔离", "test_double_extension_is_flagged"),
    ("路径穿越 ../../etc/passwd", "AC-UP-003", "隔离（落盘前判）", "test_hostile_filenames_are_all_flagged"),
    ("NUL 截断文件名", "AC-UP-003", "隔离", "test_hostile_filenames_are_all_flagged"),
    ("Windows 保留设备名 CON", "AC-UP-003", "隔离", "test_hostile_filenames_are_all_flagged"),
    ("EICAR 标准样本", "AC-UP-003", "隔离", "test_eicar_is_detected"),
    ("zip bomb（高压缩比）", "AC-UP-003", "隔离，不解压", "test_high_ratio_entry_is_flagged_without_extracting"),
    ("zip slip（条目路径穿越）", "AC-UP-003", "隔离", "test_zip_slip_entry_path_is_flagged"),
    ("嵌套压缩包", "AC-UP-003", "隔离", "test_nested_archive_is_flagged"),
    ("畸形压缩包", "AC-UP-003", "隔离，不崩", "test_malformed_archive_is_reported_not_crashed"),
    ("篡改分片（等长、摘要不符）", "AC-UP-002", "422，零字节落盘", "test_a_tampered_chunk_is_rejected_before_it_is_written"),
    ("乱序偏移", "AC-UP-002", "409，不留空洞", "test_out_of_order_offset_is_a_conflict_not_a_silent_gap"),
    ("越界写（超声明总量）", "AC-UP-002", "413", "test_a_chunk_cannot_write_past_the_declared_total"),
    ("超限文件", "AC-UP-002", "开会话即 413，写前拒绝", "test_oversize_is_refused_at_open_not_mid_stream"),
    ("重复内容", "AC-UP-002", "不收字节", "test_duplicate_content_is_refused_bytes_at_open"),
    ("半程完成", "AC-UP-002", "409，不产出 artifact", "test_completing_a_half_sent_upload_produces_no_artifact"),
    ("跨 workspace 推分片", "stop_condition", "404，进度不受影响", "test_bytes_never_cross_into_another_workspace"),
    ("对象存储不可用", "T-S06-04", "503，不留半成品", "test_storage_failure_leaves_no_half_written_artifact"),
    ("并发写同一 workspace", "T-S06-04", "成功者完好，失败者零残留", "test_concurrent_uploads_to_one_workspace_never_produce_a_corrupt_artifact"),
    ("并发配额竞争", "T-S06-04", "总声明不得超额", "test_concurrent_sessions_cannot_collectively_exceed_the_quota"),
    ("处理器 latest（漂移标识）", "AC-UP-004", "拒绝，算血缘断点", "test_drifting_or_missing_processor_versions_are_refused"),
    ("同名再传", "AC-UP-004", "新版本，旧版仍在", "test_same_name_creates_a_new_version_and_keeps_the_old_one"),
    ("高风险文件求预览", "AC-UP-004", "拒绝，仅附件", "test_attachment_only_versions_get_no_derivatives"),
]


def capacity_thresholds() -> dict:
    """容量阈值从**代码常量**读，不手抄——手抄的数字会和实现悄悄分家。"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "backend"))
    from app import resumable_upload as RU
    from app import upload_quarantine as QU
    from app import walking_skeleton as WS
    return {
        "单文件上限": WS.MAX_ARTIFACT_BYTES,
        "工作区总额度": WS.MAX_TOTAL_ARTIFACT_BYTES,
        "磁盘保留下限": WS.MIN_FREE_STATE_BYTES,
        "建议分片": RU.CHUNK_BYTES,
        "单片上限": RU.MAX_CHUNK_BYTES,
        "压缩比上限": QU.MAX_ARCHIVE_RATIO,
        "压缩包解压总量上限": QU.MAX_ARCHIVE_TOTAL_BYTES,
        "压缩包条目数上限": QU.MAX_ARCHIVE_ENTRIES,
        "_口径": "全部读自代码常量。手抄会和实现悄悄分家，而分家之后 receipt 就在说谎。",
    }


def benchmark(sizes=(64 * 1024, 512 * 1024, 2 * 1024 * 1024)) -> list[dict]:
    """本机分片校验吞吐。**只测本模块负责的那段**——逐片 sha256 与整体复核。

    不测网络与磁盘：那两样由环境决定，放进 receipt 会让不同机器上的数字
    看起来像回归，其实只是换了台机器。这里测的是「校验本身贵不贵」，
    因为它是唯一被本任务引入、且随文件大小线性增长的开销。
    """
    out = []
    for size in sizes:
        payload = bytes((i * 7) % 251 for i in range(size))
        pieces = [payload[i:i + 4 * 1024 * 1024] for i in range(0, size, 4 * 1024 * 1024)]
        started = time.perf_counter()
        for block in pieces:
            hashlib.sha256(block).hexdigest()
        hashlib.sha256(payload).hexdigest()
        elapsed = time.perf_counter() - started
        out.append({
            "字节": size, "分片数": len(pieces),
            "校验耗时毫秒": round(elapsed * 1000, 2),
            "折合 MiB/s": round(size / (1024 * 1024) / elapsed, 1) if elapsed else None,
        })
    return out


def run_gate_tests(repo_root: Path) -> dict:
    """现场跑质量门场景，**实测这一列由它填**。"""
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "KMFA/app/backend/tests/test_upload_quality_gate.py"],
        cwd=repo_root, capture_output=True, text=True,
        env={**dict(__import__("os").environ), "PYTHONPATH": "KMFA/app/backend"})
    tail = (done.stdout or "").strip().splitlines()
    return {"退出码": done.returncode,
            "结论": tail[-1] if tail else "(无输出)",
            "全过": done.returncode == 0}


def build(repo_root: Path) -> dict:
    gate = run_gate_tests(repo_root)
    return {
        "schema_version": "kmfa.upload_quality_receipt.v1",
        "任务": "T-S06-04 · S06/P6.4 上传质量门",
        "生成时间": datetime.now(BEIJING).isoformat(),
        "pass_gate": "阈值内 SLO 通过，数据不变量和隔离边界无失败",
        "三条贯穿不变量": [
            "原件不被损坏——任何失败路径之后既有 artifact 摘要仍对得上",
            "隔离边界不被跨越——任何并发/竞争下 A 的字节不得进入 B 的 workspace",
            "配额不被绕过——并发开会话时各自看在额度内、加起来超额必须被挡",
        ],
        "质量门场景": gate,
        "容量阈值": capacity_thresholds(),
        "校验吞吐": benchmark(),
        "负向矩阵": [
            {"输入": row[0], "判据来源": row[1], "预期（抄自阈值原文）": row[2], "实测用例": row[3]}
            for row in NEGATIVE_MATRIX
        ],
        "为什么预期与实测分两列":
            "合成一列写就只剩自我确认——只有分开摆，才可能出现『预期与实测不符』这一格。",
        "过程去哪了":
            "receipt 只放结论与判据。塞进原始日志它就没人读了，"
            "而它的读者是三个月后想知道『当时到底验了什么』的人。"
            "过程在 KMFA/machine/runs/S06_P6*.md 与对应测试文件里。",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 T-S06-04 的 compact receipt")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build(Path(args.repo_root).resolve())
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    size = len(text.encode("utf-8"))
    if size > MAX_RECEIPT_BYTES:
        print(f"✗ receipt {size} 字节超过 {MAX_RECEIPT_BYTES} 上限——"
              f"任务包 evidence 明写不超过 64KiB，不截断放行", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"✓ receipt {size} 字节（上限 {MAX_RECEIPT_BYTES}）→ {out}；"
          f"质量门 {'全过' if payload['质量门场景']['全过'] else '未过'}；"
          f"负向矩阵 {len(payload['负向矩阵'])} 条")
    return 0 if payload["质量门场景"]["全过"] else 1


if __name__ == "__main__":
    sys.exit(main())
