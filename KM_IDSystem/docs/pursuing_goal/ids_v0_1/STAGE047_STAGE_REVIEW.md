# STAGE-047 Whole-Stage Independent Review

- Task: `IDS-V0_1-STAGE047-REVIEW`
- Acceptance: `ACC-STAGE-047`
- Result: `PASS_REVIEWED_LOCAL_PARSER_OUTPUT_RUNTIME_DISABLED`
- Review gate: `IDS-STAGE047-REVIEW-GATE`（本地通过）
- Next gate: `IDS-STAGE048-P1-GATE`（仅允许独立后续 run）
- Phase 4 commit: `007ef85e6ee30e155269284dc9c0fe89572c8161`
- Phase 4 root tree: `779309d42552653af35f4a06701fecc7a6fe62d5`
- Phase 4 `KM_IDSystem` tree: `5c31c7341c8d3b546066b5565c273885fbd8fe11`
- Phase 4 parent: `595a507519b443faa49fca9fa0a6e8bd21cb9dde`
- Finding count: 6（Critical 2 / Important 4 / Minor 0）
- Resolved: 6；Open: 0

## Review Verdict

本次独立整阶段复审重新读取并哈希批准的 task-pack、roadmap 和 instructions，重放
Phase 1–4 checker，验证 Phase 4 commit/tree/parent 仍为当前 HEAD 的精确祖先，并对六项
发现执行独立反例。Stage047 达到 `completed_reviewed_local`；该结论只证明解析器输出合同
与纯内存控制归一化失败关闭，不证明任何真实 parser 已实现、业务文件已读取、输出质量已
通过、fallback 已运行、Stage048 已开始或可生产使用。

## Approved Source And Immutable Phase 4 Binding

- archive: `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`
- NFC 归一化后唯一 Stage047 member:
  `e1d5bdb219b6f16ca7fec4e4455e7acba1ecbae9803a7c13721b75895671d2f4`
- roadmap: `a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6`
- instructions: `ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8`

最终 checker 不信任历史布尔值：每次 live rehash 上述来源，并从 Git 对象库复核 Phase 4
commit、root tree、`KM_IDSystem` tree、parent、HEAD ancestry 及五项 Phase4 工件哈希。
任一缺失或漂移均回到 `IDS-STAGE047-REVIEW-GATE`。

## Findings And Resolution

### STAGE047-REVIEW-F0 — Critical — resolved

Phase1 的五字段 input wrapper 没有携带 Stage046 `routing_request`，无法完整证明
source、detection、request、route result 与 parser output 处于同一条来源链。现行合同改为
六字段 wrapper，精确校验 request identity、result identity 与 source reference 的双向
绑定。已提交 Phase1 五字段快照仍作为历史事实保留，runtime contract 明确记录这是 review
repair，而不是改写历史快照。

### STAGE047-REVIEW-F1 — Critical — resolved

未配对 UTF-16 surrogate 会在 UTF-8 编码时抛出 `UnicodeEncodeError`，绕过结构化
`OUTPUT_REJECTED_FAIL_CLOSED`。现所有有界文本在接受前验证可编码性，非法 Unicode 只产生
脱敏拒绝结果，不回显 payload，也不泄漏异常、路径或调用栈。

### STAGE047-REVIEW-F2 — Important — resolved

原 canonical reference 仍接受换行、非 ASCII、点前缀与大写 segment。现所有 control
reference tail 只能由有界 lower-ASCII token segment 组成；URI、slash、dot segment、
uppercase、Unicode、空段和控制字符全部失败关闭。

### STAGE047-REVIEW-F3 — Important — resolved

原引用验证只保证目标存在，允许 table 声明 page/section 而反向 `table_refs` 缺失。现
table↔page 与 table↔section 都必须完全互惠；任一方向缺失、多余或不一致都拒绝整个输出，
不能留下单向证据图。

### STAGE047-REVIEW-F4 — Important — resolved

原 route `human_status` 与 safe-error code/message key 缺少精确或长度约束。现 route
状态必须等于治理合同的固定中文值；error code 最多 96 字符、message key 最多 128 字符，
且继续禁止原始异常、路径、secret、credential 与业务正文。

### STAGE047-REVIEW-F5 — Important — resolved

原合同允许 `produced_at` 早于 `requested_at`。现 normalizer 与 envelope validator 均要求
生产时间不早于请求时间；逆序时间只返回结构化失败关闭结果，不能生成候选输出身份。

## Independent Review Controls

- `check_parser_output_stage_review.py` 每次 live rehash 四项批准来源证据。
- 重放 P1 contract、P2 isolated normalization、P3 sixteen scenarios 与 P4 delivery。
- 精确验证 Phase4 commit/root/KMIDS tree/parent/ancestry 与五项不可变工件哈希。
- 六项 finding 均有机器可执行反例；任一 false 都使 result 变为 `FAIL_CLOSED`。
- review 文档、checker、tests、治理、事件、机器记录和 owner views 必须 Git tracked 且
  与 index 一致，避免只验证工作区临时内容。
- durable route 只关闭 `ACC-STAGE-047` 并指向独立的
  `IDS-STAGE048-P1-GATE`；本轮 `stage048_entry_allowed=false`、
  `push_allowed=false`。

## Validation

- Repair TDD RED：6 个测试按预期得到 9 failures / 3 errors；最终 repair suite `6/6`
  （`0.026s`）。
- Review TDD RED：8 个测试按预期得到 4 failures / 1 error，另 3 个已通过；缺失项精确
  对应 review 文档、治理/事件、机器记录和 Git-index binding。
- P1–P2 `26/26`（`3.440s`）与 P3–P4 `32/32`（`5.914s`）在六项修复后通过。
- 最终 Stage047 focused `72/72`（`41.853s`）、Stage005 `178/178`
  （`57.178s`）、Stage041–047 aggregate `485/485`（`1261.140s`）与完整
  IDS v0.1 discovery `1241/1241`（`1689.670s`）全部通过。
- Stage038–047 十个独立 review checker `10/10`；`230` 条治理事件全部可解析且 ID
  唯一；七文件 owner render 双次幂等，`05_执行与验收.md` 为 `100/100` 行；项目
  dual-plane PASS。失败运行未计作 PASS。
- sparse worktree 缺少根 `scripts/lean_governance.py`，仓库级完整治理只能报告
  `SPARSE_CONFLICT`；不扩展 sparse，也不进入其他项目。

## Rollback

只回滚本 review 的六项修复、文档、checker/tests、machine run、事件、batch/roadmap/
HANDOFF、machine facts 与渲染 owner views，即回到已提交 Stage047 Phase4 的
`IDS-STAGE047-REVIEW-GATE`。保留 P1–P4、Stage041–046 复审证据、批准来源、GitHub 与
app 状态；不得用 rollback 删除来源、历史审计证据或运行 `git gc --prune=now`。

## Stop Conditions

- `NO_STAGE048_THIS_RUN`
- `NO_BATCH_REVIEW_OR_UPLOAD`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`
- `NO_RAW_METADATA_ACCESS`
- `NO_IDS_BUSINESS_SOURCE_READ`
- `NO_PARSER_OR_FALLBACK_RUNTIME`
- `NO_QUALITY_GATE_OR_PERSISTENCE`
- `NO_PRODUCTION_ACTIVATION`
