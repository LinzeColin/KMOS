#!/usr/bin/env bash
# 【已作废】 这是 2026-07 之前那一代考勤自动化的遗留文件，里面的 cwd（`/Documents/Codex/KMOS`）、automation id（`kmfa` / `kmfa-3`）和钟点都已经不成立。
# 现行调度是两条 Codex automation（主 `automation` 19:15 + 备位 `automation-2` 20:15），说明见 `automation/codex_automation_manifest.md`。
# 保留本文件只是因为包校验器还在引用它。

set -euo pipefail
cd /Users/linzezhang/Documents/Codex/KMOS
export KMFA_RUN_SLOT=evening
codex exec --sandbox workspace-write --json \
  "$(cat KMFA/skills/钉钉考勤/automation/evening_prompt.md)" \
  > KMFA/metadata/dingtalk_attendance/private_runtime/automation_runs/evening_$(date +%Y%m%dT%H%M%S).jsonl
