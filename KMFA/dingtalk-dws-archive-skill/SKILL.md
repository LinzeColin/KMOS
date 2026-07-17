---
name: dingtalk-dws-archive-skill
description: Use when operating, restoring, reviewing, migrating, or modifying the KMFA DingTalk DWS all-file archive, its private runtime, Codex automation, output validation, or public-safe source package.
---

# DingTalk DWS Archive Skill

This is the portable public-safe source entry for the KMFA upstream DWS archive.

Canonical repository: `LinzeColin/KMOS`, path `KMFA/dingtalk-dws-archive-skill/`.

Before acting, read:

1. `references/operating_contract.md`
2. `references/开发记录.md`
3. `references/功能清单.md`
4. `references/模型参数文件.md`
5. `references/recovery.md`
6. the exact script/config you will touch

## Hard boundaries

- Repo contains source, validators, disabled launchd examples and sanitized config templates only.
- Real `open_conversation_id`, group scope, Notion page id, message/file bodies, SQLite, ZIP, archives, reports, logs, tokens and credentials stay in private runtime.
- Do not run a live DWS command, mutate group scope, send a message, or delete archive data without explicit current-thread authorization.
- Only official DWS CLI is allowed; never read browser cookies, Keychain, DingTalk local databases or private APIs.
- Local unattended launchd remains disabled. Normal execution is Codex-controlled and requires `DWS_CODEX_CONTROLLED=1`.
- Cursor updates, project auto-completion and archive cleanup fail closed as documented in `references/operating_contract.md`.

## Public validation

Run from repo root:

```bash
python3 KMFA/dingtalk-dws-archive-skill/tools/validate_skill_package.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest KMFA/dingtalk-dws-archive-skill/scripts/test_dws_output_layout.py -q
```

The private runtime recovery point and automation path are recorded in `KMFA/HANDOFF.md`. Do not copy that private data into this package.
