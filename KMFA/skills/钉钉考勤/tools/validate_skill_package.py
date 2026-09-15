#!/usr/bin/env python3
"""Validate the public-safe KMFA DingTalk attendance skill package."""

from __future__ import annotations

import subprocess

import re
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent

REQUIRED_FILES = [
    ROOT / "SKILL.md",
    ROOT / "README.md",
    ROOT / "automation" / "morning_prompt.md",
    ROOT / "automation" / "evening_prompt.md",
    ROOT / "automation" / "codex_automation_manifest.md",
    ROOT / "references" / "runbook.md",
    ROOT / "references" / "configuration.md",
    ROOT / "references" / "decision-impact.md",
    ROOT / "references" / "operating_contract.md",
    ROOT / "references" / "source_of_truth_contract.md",
    ROOT / "scripts" / "month_gate.py",
    ROOT / "scripts" / "stage2_consensus_gate.py",
    ROOT / "scripts" / "write_stage2_run_artifacts.py",
    ROOT / "scripts" / "run_stage2_accepted_rehearsal.py",
    ROOT / "scripts" / "validate_database_contract.py",
    ROOT / "scripts" / "resolve_stage2_source.py",
    ROOT / "scripts" / "prepare_database_landing_bundle.py",
    ROOT / "scripts" / "prepare_preconsensus_postgres_landing_bundle.py",
    ROOT / "scripts" / "prepare_postgres_landing_loader.py",
    ROOT / "scripts" / "validate_postgres_load_plan.py",
    ROOT / "scripts" / "execute_postgres_load_plan.py",
    ROOT / "scripts" / "verify_postgres_landing_state.py",
    ROOT / "scripts" / "apply_stage2_database_proof.py",
    ROOT / "scripts" / "inspect_raw_archive_month.py",
    ROOT / "scripts" / "prepare_raw_replay_day_fact_bundle.py",
    ROOT / "scripts" / "prepare_stage2_source_from_raw_replay.py",
    ROOT / "templates" / "env.local.example",
    ROOT / "templates" / "notification_targets.local.example.json",
    ROOT / "templates" / "codex-startup-prompt.md",
    ROOT / "tools" / "validate_skill_package.py",
]

REQUIRED_TEXT = {
    "SKILL.md": [
        "REST_REQUIRED_THRESHOLD_DAYS = 23",
        "丁春法",
        "李永占",
        "KMFA_DINGTALK_ATTENDANCE_ALLOW_DWS_COMMANDS",
        "attendance_ledger.sqlite",
    ],
    "references/runbook.md": [
        "REST_REQUIRED_THRESHOLD_DAYS = 23",
        "REST_REQUIRED_EXCLUDED_NAMES",
        "python3 KMFA/tools/dingtalk_attendance/healthcheck.py --config-only",
        "salary",
    ],
    "references/configuration.md": [
        "DINGTALK_ROBOT_URL",
        "KMFA_DINGTALK_ATTENDANCE_ALLOW_DWS_COMMANDS=0",
        "salary_basis_allowed=false",
    ],
    "references/decision-impact.md": [
        "SWOT",
        "Token",
        "Data Quality",
        "Salary",
    ],
    "automation/morning_prompt.md": [
        "$kmfa-dingtalk-attendance-skill",
        "Asia/Shanghai",
        "automation prompt file",
        "REST",
    ],
    "automation/evening_prompt.md": [
        "$kmfa-dingtalk-attendance-skill",
        "Asia/Shanghai",
        "stage-2",
        "payroll baseline",
    ],
    # 断言换成现行这一代该有的东西。旧的三项（kmfa-3 / Beijing / GitHub）是
    # 2026-07 之前那一代的痕迹：kmfa-3 这条 automation 早就没了，kmfa 也被挪去做月结。
    "automation/codex_automation_manifest.md": [
        "BYDAY=MO,TU,WE,TH,FR",                        # 只在工作日触发
        "create_automation",                           # 必须走官方接口建，不许手写 toml
        "北京 17:15",                                   # 出报时刻
        "台账只存事实",                                  # 截止线会改，判断不许存死
        "备位",                                         # 夏令时必须有第二个钟点
        "幂等是无条件的",                                # --force 也不放行已发标记
        "SEND_COMPLETED",                              # 判读认标记不认中文
        "私聊",                                         # 出事要发到手机，不是只写在 Codex 里
        "kmfa_brief_run.log",                          # 运行日志
    ],
}


# 「这个包实际会交出去的文件」只有一份口径，校验和再生都用它。
# private_runtime/ 装的是真凭据，靠 .gitignore 挡在仓库外，不属于交付内容。
EXCLUDED_PREFIXES = ("private_runtime/",)
EXCLUDED_NAMES = {".DS_Store"}

def package_files(root: Path) -> list[str]:
    out = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in EXCLUDED_NAMES:
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(EXCLUDED_PREFIXES):
            continue
        out.append(rel)
    return sorted(out)

FORBIDDEN_FILE_PATTERNS = [
    ".env.local",
    ".sqlite",
    ".db",
    ".jsonl",
    ".jsonl.gz",
    ".raw.json",
    ".raw.jsonl",
    ".raw.jsonl.gz",
]

_DINGTALK_QUERY_KEY = "access" + "_token="
_KNOWN_PRIVATE_USER_ID = "1iv-" + "1t2oesv2yd"

FORBIDDEN_CONTENT_PATTERNS = [
    re.compile(re.escape(_DINGTALK_QUERY_KEY), re.IGNORECASE),
    re.compile(r"https://oapi\.dingtalk\.com/robot/send\?" + re.escape(_DINGTALK_QUERY_KEY), re.IGNORECASE),
    re.compile(re.escape(_KNOWN_PRIVATE_USER_ID)),
    re.compile(r"cid[A-Za-z0-9+/=]{10,}"),
    re.compile(r"(?:secret|token|password|credential)\s*=\s*(?!<)[A-Za-z0-9_./+=-]{12,}", re.IGNORECASE),
]

ALLOWED_BINARY_FILES = {
    "task_pack_report.pdf",
}

OLD_PACKAGE_PATH = ".agents/skills/" + "kmfa-dingtalk-attendance"


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def regenerate() -> int:
    """把清单和校验和按当前文件重写一遍。

    这两份东西每次动代码都会过期，手改必然漏 —— 所以给它一条命令：
        python3 tools/validate_skill_package.py --fix
    """
    files = package_files(ROOT)
    (ROOT / "source_manifest.txt").write_text(
        "\n".join(files) + "\n", encoding="utf-8")
    lines = [f"{hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()}  {rel}"
             for rel in files if rel != "source_checksums.sha256"]
    (ROOT / "source_checksums.sha256").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    print(f"已重写 source_manifest.txt（{len(files)} 个文件）与 source_checksums.sha256")
    return 0


def main() -> int:
    if "--fix" in sys.argv[1:]:
        return regenerate()
    missing = [path for path in REQUIRED_FILES if not path.exists()]
    if missing:
        fail("missing files: " + ", ".join(str(path.relative_to(REPO_ROOT)) for path in missing))

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\nname: kmfa-dingtalk-attendance-skill\n"):
        fail("SKILL.md frontmatter is missing or invalid")
    if "description: Use when" not in skill:
        fail("SKILL.md description must start with a use trigger")

    # 只扫 Git 真会带走的文件。private_runtime/ 存的就是真凭据，它被 .gitignore 挡在
    # 仓库外面 —— 扫它等于把「私密值放对了地方」判成「泄露」，方向正好反了。
    # 先证明它确实被忽略，再据此跳过；忽略规则要是哪天没了，这里立刻 FAIL。
    env_file = ROOT / "private_runtime" / "kmfa_brief.env"
    if env_file.exists():
        ignored = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q",
                                  str(env_file)]).returncode == 0
        if not ignored:
            fail("private_runtime/kmfa_brief.env 没有被 .gitignore 挡住，真凭据会进仓库")

    for rel in package_files(ROOT):
        path = ROOT / rel
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            fail(f"generated Python cache is not allowed in skill package: {rel}")
        if rel.endswith(".example"):
            pass
        elif any(rel.endswith(pattern) for pattern in FORBIDDEN_FILE_PATTERNS):
            fail(f"forbidden private/runtime file in skill package: {rel}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            if rel not in ALLOWED_BINARY_FILES:
                fail(f"non-UTF-8 file is not allowed in skill package: {rel}")
            if path.stat().st_size > 200_000:
                fail(f"allowed binary file is unexpectedly large: {rel}")
            continue
        for pattern in FORBIDDEN_CONTENT_PATTERNS:
            if pattern.search(text):
                fail(f"forbidden sensitive-looking content in {rel}: {pattern.pattern}")
        if OLD_PACKAGE_PATH in text and rel not in {
            "source_manifest.txt",
            "source_checksums.sha256",
        }:
            fail(f"old package path leaked into active file: {rel}")
        if "$kmfa-dingtalk-attendance" in text and "$kmfa-dingtalk-attendance-skill" not in text:
            fail(f"old skill invocation leaked into active file: {rel}")

    for rel, needles in REQUIRED_TEXT.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        missing_needles = [needle for needle in needles if needle not in text]
        if missing_needles:
            fail(f"{rel} missing required text: {', '.join(missing_needles)}")

    manifest_path = ROOT / "source_manifest.txt"
    checksum_path = ROOT / "source_checksums.sha256"
    manifest_files = [line.strip() for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    current_files = package_files(ROOT)
    if manifest_files != current_files:
        missing = sorted(set(current_files) - set(manifest_files))
        extra = sorted(set(manifest_files) - set(current_files))
        fail(
            "source_manifest.txt is not current"
            + (f"; missing={missing}" if missing else "")
            + (f"; extra={extra}" if extra else "")
        )

    checksum_entries: dict[str, str] = {}
    for lineno, line in enumerate(checksum_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            fail(f"source_checksums.sha256 line {lineno} is malformed")
        digest, rel = parts[0], parts[1].strip()
        checksum_entries[rel] = digest

    expected_checksum_files = [rel for rel in manifest_files if rel != "source_checksums.sha256"]
    missing_checksums = sorted(set(expected_checksum_files) - set(checksum_entries))
    extra_checksums = sorted(set(checksum_entries) - set(expected_checksum_files))
    if missing_checksums or extra_checksums:
        fail(
            "source_checksums.sha256 file list mismatch"
            + (f"; missing={missing_checksums}" if missing_checksums else "")
            + (f"; extra={extra_checksums}" if extra_checksums else "")
        )
    for rel in expected_checksum_files:
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if checksum_entries[rel] != actual:
            fail(f"source_checksums.sha256 mismatch for {rel}")

    print("PASS: KMFA DingTalk attendance skill package is public-safe and complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
