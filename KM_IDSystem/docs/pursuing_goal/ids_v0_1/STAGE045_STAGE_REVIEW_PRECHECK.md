# STAGE-045 Whole-Stage Review Precheck — Source Blocked

- Task: `IDS-V0_1-STAGE045-REVIEW`
- Acceptance: `ACC-STAGE-045`
- Result: `BLOCKED_SOURCE_UNAVAILABLE_REPAIRS_VERIFIED`
- Review gate: `IDS-STAGE045-REVIEW-GATE`（保持未通过）
- Next gate: `IDS-STAGE045-REVIEW-GATE`（不得进入 Stage046）
- Phase 4 commit: `c0b2f3e2069d371125b70a5621031b1332403f95`
- Phase 4 root tree: `2c07695af1e78c33f62dfb6f50db13f1bbe7a4b1`
- Phase 4 `KM_IDSystem` tree: `b00bab20eb5c265b7c3c3b25c0a7618d50cac2af`
- Finding count: 7（Critical 3 / Important 4 / Minor 0）
- Repaired: 6；Open blocker: 1

## Why This Is Not A Completed Stage Review

P1–P4 精确绑定的三份批准来源在本轮 review preflight 时已不在其记录路径：

- `/Users/linzezhang/Downloads/IDS_Taskpack_v0_1_only_中文修订版.zip`
- `/Users/linzezhang/Downloads/IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt`
- `/Users/linzezhang/Downloads/IDS_Codex使用说明_v0_1_only_中文修订版.txt`

精确文件名 Spotlight 查询、Trash 精确路径和已批准的 KMIDS 迁移备份均未找到同名
副本。没有扫描 Downloads，也没有读取、列出、stat、hash 或触碰
`/Users/linzezhang/Downloads/IDS_MetaData`。

因此，本轮不能重新计算 archive/member/roadmap/instructions SHA-256，也不能把 P4
时期的历史验证升级为本轮的 live independent source verification。当前治理必须继续
停在 `IDS-STAGE045-REVIEW-GATE`；本文不是 `STAGE045_STAGE_REVIEW.md`，不构成
`completed_reviewed_local` 证据。

## Findings And Repairs

### STAGE045-REVIEW-F0 — Critical — open blocker

批准 task-pack、roadmap 和 instructions 当前不可读，独立 review 缺少 live source
rehash。不得通过删除 `source_live` 检查、信任历史布尔值、改写 source binding 或使用
其他文件替代。唯一修复是恢复完全相同的三份源文件并验证既有 SHA-256。

### STAGE045-REVIEW-F1 — Critical — repaired

PDF、PNG、JPEG、TIFF 原实现只凭 magic prefix 就返回 `TYPE_CONFIRMED/HIGH`；截断
payload 也会得到 parser candidate，违反 Phase 1“签名不是一票通过”的格式级验证
要求。现在分别要求 bounded PDF EOF、CRC-valid PNG IHDR/IDAT/IEND、JPEG SOI/EOI、
TIFF byte-order magic + in-bounds IFD。magic 命中但结构无效统一
`TYPE_INPUT_BLOCKED`。

### STAGE045-REVIEW-F2 — Critical — repaired

有效 ZIP 缺少 OOXML markers 时，原实现会退回匹配 MIME/`.docx` 或 `.xlsx` 并形成
`ROUTE_CANDIDATE`，等价于在 container validation 失败后重新相信文件名。现在返回
`OOXML_CONTAINER_MARKERS_MISSING`、`TYPE_UNKNOWN_REVIEW_REQUIRED` 和
`ROUTE_REVIEW_REQUIRED`，MIME/extension 不能重新进入候选 route。

### STAGE045-REVIEW-F3 — Important — repaired

ZIP 中 `word/../...` 等非规范成员和重复 `[Content_Types].xml` 可冒充 OOXML marker。
现在只接受 canonical relative POSIX member name，拒绝 absolute、backslash、空段、
dot、parent traversal、NUL 和 duplicate member；namespace 还必须至少含一个非目录成员。

### STAGE045-REVIEW-F4 — Important — repaired

MIME schema 声明 `UNKNOWN`，但 builder 无条件 `.lower()` 后会拒绝 `UNKNOWN`，造成
builder 与 validator 不一致。现在大小写不敏感输入只规范为一个 `UNKNOWN` 表示，
其余 MIME 继续规范为小写。

### STAGE045-REVIEW-F5 — Important — repaired

`requested_at` 原来只匹配字符形状，`2026-02-30`、第 13 月和 `24:00:00` 都能进入
request ID。现在同时执行严格 UTC 格式和真实 calendar/time 解析，无效值在 ID 创建前
失败关闭。

### STAGE045-REVIEW-F6 — Important — repaired

超限/无效 evidence excerpt 原先在 signature/container inspection 之后才阻断，但返回
结果又声称 inspection 未发生。现在 excerpt type/length 在任何 signature observation 前
验证，阻断结果与真实执行顺序一致。

## TDD And Rebound Evidence

- 有效初始 review RED：6 项反例产生 10 个断言失败和 1 个缺失能力错误。
- 追加 ZIP-marker fallback 反例：1 项测试产生 1 个断言失败。
- 修复后 review repair suite：8/8 PASS（含修复合同绑定检查）。
- Phase 2 runtime contract 增加精确 format validation、OOXML lexical/duplicate、UNKNOWN
  MIME、真实 UTC 和 evidence precheck 约束。
- Phase 3 合成 PNG/JPEG/TIFF controls 已改为满足新的 bounded structure；P2→P3→P4
  哈希链按修复后 snapshot 重新绑定。
- 现有 phase checker 仍保留 live source 验证；源文件缺失时必须返回 fail closed。

## Validation Snapshot

- P1 contract checker: `21/22`，唯一失败项 `source_live`。
- P2 contract checker: `16/17`，唯一失败项 `source_live`。
- P3 contract checker: `15/16`，唯一失败项 `source_live`。
- P4 contract checker: `15/16`，唯一失败项 `source_binding_live`。
- Stage045 P1-P4 + review repair 聚合：`67` tests，`50` passed、`13` failures、
  `4` errors；所有 failure/error 都是 live source 缺失的直接或上游 fail-closed
  级联，不能计为 Stage PASS。
- 独立修复反例：`8/8 PASS`；Stage005 治理回归：`172/172 PASS`。
- 机器可读预检记录：
  `machine/runs/2026-07-20-stage045-review-precheck-local.json`。

## Required Unblock Evidence

1. 将三份批准源恢复到合同记录的精确路径，或由 Owner 明确批准一个新的 canonical
   source binding；不得由 agent 自行替换 authority。
2. 重新验证 archive SHA-256、唯一 Stage045 member SHA-256、roadmap SHA-256 和
   instructions SHA-256 与现有绑定完全一致。
3. 在同一 Git-index snapshot 重跑 P1–P4 checker、review counterexamples、Stage005、
   Stage041–045 aggregate、全量 discovery、历史 review checker、events、render 和
   dual-plane。
4. 只有全部通过后才能创建最终 `STAGE045_STAGE_REVIEW.md`、治理事件和
   `completed_reviewed_local -> IDS-STAGE046-P1-GATE` 路由。

## Stop Conditions

- `NO_COMPLETED_STAGE_REVIEW`
- `NO_STAGE046`
- `NO_BATCH_REVIEW_OR_UPLOAD`
- `NO_GITHUB_PUSH_OR_MERGE`
- `NO_APP_REINSTALL`
- `NO_REAL_SOURCE_OR_RAW_METADATA_ACCESS`
- `NO_PARSER_OR_FALLBACK_RUNTIME`
- `NO_PERSISTENCE_OR_PRODUCTION_ACTIVATION`
