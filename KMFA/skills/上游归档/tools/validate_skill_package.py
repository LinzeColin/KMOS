#!/usr/bin/env python3
"""Validate the public-safe DWS archive skill package without live DWS access."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "SKILL.md",
    ".gitignore",
    "references/operating_contract.md",
    "references/开发记录.md",
    "references/功能清单.md",
    "references/模型参数文件.md",
    "references/recovery.md",
    "templates/target_groups.example.yaml",
    "scripts/archive_dingtalk_all_files.py",
    "scripts/validate_dws_output_structure.py",
    "scripts/sync_notion_skill_backup.py",
    "scripts/run_daily.sh",
    "scripts/run_weekly.sh",
    "scripts/test_dws_output_layout.py",
    "automation/com.linze.dingtalk-dws-archive.daily.plist",
    "automation/com.linze.dingtalk-dws-archive.weekly.plist",
]

PRIVATE_PATTERNS = {
    "real_open_conversation_id": re.compile(r"cid[A-Za-z0-9+/]{12,}={0,2}"),
    "old_machine_path": re.compile("392b1a986ba68033" + "8068ddc1c2a0fd0e"),
    "credential_literal": re.compile(
        r"(?im)^\s*(?:token|access_token|refresh_token|password|api_key|webhook)\s*[:=]\s*['\"](?!<|\$|\{)[A-Za-z0-9_./+=-]{12,}['\"]"
    ),
}


def run(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"command failed: {' '.join(command)}: {details}")


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"missing:{relative}")

    text_files = [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() not in {".pyc", ".png", ".jpg", ".jpeg"}
    ]
    for path in text_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in PRIVATE_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{name}:{path.relative_to(ROOT)}")

    template = ROOT / "templates/target_groups.example.yaml"
    if template.is_file():
        template_text = template.read_text(encoding="utf-8")
        if 'enabled: false' not in template_text:
            errors.append("template_group_must_default_disabled")
        if "<private-open-conversation-id>" not in template_text:
            errors.append("template_missing_private_id_placeholder")

    if not errors:
        try:
            py_files = [str(path.relative_to(ROOT)) for path in (ROOT / "scripts").glob("*.py")]
            run([sys.executable, "-m", "py_compile", *py_files])
            run(["/bin/sh", "-n", "scripts/run_daily.sh", "scripts/run_weekly.sh"])
            run(["plutil", "-lint", "automation/com.linze.dingtalk-dws-archive.daily.plist"])
            run(["plutil", "-lint", "automation/com.linze.dingtalk-dws-archive.weekly.plist"])
        except RuntimeError as exc:
            errors.append(str(exc))

    result = {
        "status": "PASS" if not errors else "FAIL",
        "package": "KMFA/skills/上游归档",
        "required_file_count": len(REQUIRED),
        "scanned_text_file_count": len(text_files),
        "live_dws_called": False,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
