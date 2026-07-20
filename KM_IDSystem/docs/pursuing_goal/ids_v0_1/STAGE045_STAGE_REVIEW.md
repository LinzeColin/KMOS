# STAGE-045 Whole-Stage Independent Review

- Task: `IDS-V0_1-STAGE045-REVIEW`
- Acceptance: `ACC-STAGE-045`
- Result: `PASS_REVIEWED_LOCAL_PARSER_AND_FALLBACK_DISABLED`
- Review gate: `IDS-STAGE045-REVIEW-GATE`（本地通过）
- Next gate: `IDS-STAGE046-P1-GATE`（仅允许独立后续 run）
- Phase 4 commit: `c0b2f3e2069d371125b70a5621031b1332403f95`
- Phase 4 root tree: `2c07695af1e78c33f62dfb6f50db13f1bbe7a4b1`
- Phase 4 `KM_IDSystem` tree: `b00bab20eb5c265b7c3c3b25c0a7618d50cac2af`
- Finding count: 7（Critical 3 / Important 4 / Minor 0）
- Resolved: 7；Open: 0

## Review Verdict

本次独立整阶段复审重新读取并哈希批准的 task-pack、roadmap 和 instructions，重放
Phase 1–4 checker，验证 Phase 4 commit/tree 仍为当前 HEAD 祖先，并对七项发现执行
独立反例。Stage045 达到 `completed_reviewed_local`；该结论只证明文件类型检测的有界
非生产控制合同与隔离内存切片通过，不证明真实业务文件解析、解析器质量、fallback、
持久化、生产运行或 Stage046 已开始。

## Approved Source Recovery And Live Binding

预检时三份精确绑定来源缺失，故当时严格停在 review gate。随后仅通过原始 Codex 会话
附件元数据与原始 ChatGPT 对话附件恢复三份批准来源到合同记录路径；未扫描 Downloads，
也未读取、列出、stat、hash、复制或修改 `IDS_MetaData`。最终 live rehash 结果：

- archive: `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`
- unique Stage045 member: `4eac237a7f63d764cf71789d4949a5168cbe8fe24e1fe7eb816baabe04bb4d27`
- roadmap: `a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6`
- instructions: `ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8`

`STAGE045_STAGE_REVIEW_PRECHECK.md` 保留为失败关闭与六项代码修复的历史证据；它不再是
当前 gate 状态，但没有被删除或改写成伪 PASS。

## Findings And Resolution

### STAGE045-REVIEW-F0 — Critical — resolved

三份批准来源已恢复到合同精确路径，archive、唯一成员、roadmap 和 instructions 的四个
SHA-256 均与 P1–P4 既有 binding 完全一致；最终 checker 不信任历史布尔值，而是每次
live rehash，任一缺失或漂移都会回到 `IDS-STAGE045-REVIEW-GATE`。

### STAGE045-REVIEW-F1 — Critical — resolved

PDF、PNG、JPEG、TIFF 不再凭 magic prefix 直接形成高置信 parser candidate。复审逐一
验证截断 payload 返回 `TYPE_INPUT_BLOCKED` / `ROUTE_BLOCKED`，并分别要求 bounded
PDF EOF、CRC-valid PNG 结构、JPEG EOI 和 in-bounds TIFF IFD。

### STAGE045-REVIEW-F2 — Critical — resolved

ZIP magic 命中但缺少 OOXML marker 时，MIME 和扩展名不能重新把 DOCX/XLSX 提升为
候选路线；结果固定为 `OOXML_CONTAINER_MARKERS_MISSING`、
`TYPE_UNKNOWN_REVIEW_REQUIRED` 和 `ROUTE_REVIEW_REQUIRED`。

### STAGE045-REVIEW-F3 — Important — resolved

OOXML member 必须使用唯一、规范、相对 POSIX 名称。absolute、backslash、空段、dot、
parent traversal、NUL 和 duplicate member 均失败关闭；复审覆盖 traversal 与重复
`[Content_Types].xml` 反例。

### STAGE045-REVIEW-F4 — Important — resolved

MIME builder 与 schema 统一使用唯一 `UNKNOWN` 表示；大小写输入规范化后产生相同请求，
其余已知 MIME 保持小写规范值。

### STAGE045-REVIEW-F5 — Important — resolved

`requested_at` 同时校验严格 RFC3339 UTC 字符形状和真实 calendar/time。非法月份、
不存在日期与 `24:00:00` 均在 request ID 创建前失败关闭。

### STAGE045-REVIEW-F6 — Important — resolved

evidence excerpt 的类型和长度在任何 signature/container inspection 前验证。超限文本
返回 `EVIDENCE_TEXT_LIMIT_EXCEEDED`，并如实记录
`file_signature_inspection_performed=false`。

## Independent Review Controls

- `check_file_type_detection_stage_review.py` 每次 live rehash 四项批准来源证据。
- 重新执行 P1 contract、P2 isolated slice、P3 14 scenarios 与 P4 delivery checker。
- Phase 4 commit/tree 必须存在并为当前 HEAD 祖先。
- 七项 finding 均有机器可执行反例；任一 false 都使 result 变为 `FAIL_CLOSED`。
- review 文档、checker、tests、治理、事件、机器记录和 owner views 必须 Git tracked 且
  与 index 一致，避免只验证工作区临时内容。
- durable route 只关闭 `ACC-STAGE-045` 并指向独立的 `IDS-STAGE046-P1-GATE`；本轮
  `stage046_entry_allowed=false`、`push_allowed=false`。

## Validation

- Review TDD RED：最终 checker 尚不存在时，focused test 按预期以 1 个 missing-checker
  error 失败。
- 来源恢复后 P1 checker `22/22`、P2 `17/17 + 5/5`、P3 `16/16 + 14/14`、P4
  `16/16 + 9/9` 均通过；P1–P4 + review repair suite `67/67` 通过。
- 最终 focused review `8/8`（`24.465s`）、Stage005 `172/172`（`41.976s`）、
  Stage041–045 aggregate `343/343`（`1171.188s`）及全量 discovery `1093/1093`
  （`1548.501s`）均通过；历史与当前 review checker `8/8` 通过。
- 首次历史兼容 focused suite 在 `39` 项中失败 `3` 项，准确暴露 Stage041–044 checker
  对当前 gate 的陈旧 HANDOFF 匹配；修复仅允许精确的 Stage045 review → Stage046 P1
  前向路由，并保留 Stage044 checker 的既有哈希绑定。Stage044 复验 `10/10`
  （`160.408s`）通过；失败运行未计为 PASS。
- events、owner render 与 project dual-plane 的最终结果记录在
  `machine/runs/2026-07-20-stage045-review-local.json`；任一最终门失败时本文结论自动失效。
- sparse worktree 缺少根 `scripts/lean_governance.py`，仓库级完整治理只能报告
  `SPARSE_CONFLICT`；未扩展 sparse，也未进入其他项目。

## Rollback

只回滚本 review 文档、checker/tests、review 机器记录、事件、batch/roadmap/HANDOFF、
machine facts 与渲染 owner views，即回到已提交 Stage045 Phase4 的
`IDS-STAGE045-REVIEW-GATE`。保留 P1–P4、precheck、七项修复、批准来源、Stage041–044
复审证据、GitHub 与 app 状态；不得用 rollback 删除来源或审计证据。

## Stop Conditions

- `NO_STAGE046_THIS_RUN`
- `NO_BATCH_REVIEW_OR_UPLOAD`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`
- `NO_RAW_METADATA_ACCESS`
- `NO_IDS_BUSINESS_SOURCE_READ`
- `NO_PARSER_OR_FALLBACK_RUNTIME`
- `NO_PERSISTENCE_OR_PRODUCTION_ACTIVATION`
