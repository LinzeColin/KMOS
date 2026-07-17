#!/usr/bin/env python3
"""Weekly DWS maintenance smoke test. Does not upgrade production automatically."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DWS = str(Path.home() / ".local/bin/dws")
REPORTS = ROOT / "reports"
CONFIG = ROOT / "config" / "target_groups.yaml"


def run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run([DWS, *args], cwd=ROOT, text=True, capture_output=True, timeout=60)
    return proc.returncode, (proc.stdout + "\n" + proc.stderr).strip()


def redact(text: str) -> str:
    sensitive_keys = [
        "corp_id",
        "user_id",
        "clientId",
        "corpId",
        "userId",
        "openConversationId",
        "ownerOpenDingtalkId",
        "senderOpenDingTalkId",
        "openMessageId",
    ]
    for key in sensitive_keys:
        text = __import__("re").sub(
            rf'("{key}"\s*:\s*")([^"]+)(")',
            lambda m: m.group(1) + m.group(2)[:6] + "..." + m.group(2)[-4:] + m.group(3),
            text,
        )
    text = re.sub(r"(mediaId=)([^\s\)]+)", lambda m: m.group(1) + m.group(2)[:6] + "..." + m.group(2)[-4:], text)
    text = re.sub(r"(fileId[：:\s]+)([^\s\"，,}]+)", lambda m: m.group(1) + m.group(2)[:6] + "..." + m.group(2)[-4:], text)
    text = re.sub(r"(cid[A-Za-z0-9+/=]{12,})", lambda m: m.group(1)[:6] + "..." + m.group(1)[-4:], text)
    return text


def configured_groups() -> list[tuple[str, str]]:
    groups: list[tuple[str, str]] = []
    current_name = ""
    current_id = ""
    for raw in CONFIG.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("- canonical_name:"):
            if current_name:
                groups.append((current_name, current_id))
            current_name = line.partition(":")[2].strip().strip('"')
            current_id = ""
        elif line.startswith("open_conversation_id:"):
            current_id = line.partition(":")[2].strip().strip('"')
    if current_name:
        groups.append((current_name, current_id))
    return groups


def summarize_json_success(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return text[:1200]
    data = json.loads(text[start : end + 1])
    if "result" in data and isinstance(data["result"], dict) and "messages" in data["result"]:
        data["result"]["messages"] = data["result"]["messages"][:1]
    return json.dumps(data, ensure_ascii=False, indent=2)[:1200]


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    checks = []
    for label, args in [
        ("version", ["version", "--format", "json"]),
        ("auth status", ["auth", "status", "--format", "json"]),
        ("download-media help", ["chat", "message", "download-media", "--help", "--format", "json"]),
        ("drive download help", ["drive", "download", "--help", "--format", "json"]),
        ("doc download help", ["doc", "download", "--help", "--format", "json"]),
        ("upgrade check", ["upgrade", "--check"]),
    ]:
        code, out = run(args)
        checks.append((label, code, out[:1200]))
    for group_name, group_id in configured_groups():
        code, out = run(["chat", "search", "--query", group_name, "--limit", "10", "--cursor", "0", "--format", "json"])
        checks.append((f"group search: {group_name}", code, summarize_json_success(out)))
        if group_id:
            code, out = run(["chat", "message", "list", "--group", group_id, "--time", "2026-06-01 00:00:00", "--limit", "1", "--forward", "true", "--format", "json"])
            checks.append((f"group read: {group_name}", code, summarize_json_success(out)))
    lines = ["# C 方案每周维护报告", "", f"运行时间：{dt.datetime.now().astimezone().isoformat(timespec='seconds')}", ""]
    for label, code, out in checks:
        lines += [f"## {label}", f"- exit_code: {code}", "```text", redact(out), "```", ""]
    lines.append("策略：本脚本只检查更新、目标群读取和下载能力，不自动升级。升级前需小群 smoke test 成功。")
    (REPORTS / "weekly_maintenance_report.md").write_text("\n".join(lines), encoding="utf-8")
    required = [item for item in checks if item[0] != "upgrade check"]
    return 0 if all(code == 0 for _, code, _ in required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
