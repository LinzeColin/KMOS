# STAGE-046 Whole-Stage Independent Review

- Task: `IDS-V0_1-STAGE046-REVIEW`
- Acceptance: `ACC-STAGE-046`
- Result: `PASS_REVIEWED_LOCAL_PARSER_AND_FALLBACK_DISABLED`
- Review gate: `IDS-STAGE046-REVIEW-GATE`（本地通过）
- Next gate: `IDS-STAGE047-P1-GATE`（仅允许独立后续 run）
- Phase 4 commit: `5dee024cd44e2e772776487ee21761f274c7708e`
- Phase 4 root tree: `0d0508144b84e1dea5ab92f4c629255d2d22e6a9`
- Phase 4 `KM_IDSystem` tree: `20da3db8680bb39acf7ac5348d8587a97e8ad393`
- Phase 4 parent: `49b876ec68ec8f92f0b9df72d57cca7b2d1d3344`
- Finding count: 6（Critical 2 / Important 3 / Minor 1）
- Resolved: 6；Open: 0

## Review Verdict

本次独立整阶段复审重新读取并哈希批准的 task-pack、roadmap 和 instructions，重放
Phase 1–4 checker，验证 Phase 4 commit/tree/parent 仍为当前 HEAD 的精确祖先，并对六项
发现执行独立反例。Stage046 达到 `completed_reviewed_local`；该结论只证明解析器路由的
有界、仅元数据、非生产控制合同通过，不证明任何 parser 已实现、真实文件已解析、解析
质量已验证、fallback 已运行、Stage047 已开始或可生产使用。

## Approved Source And Immutable Phase 4 Binding

- archive: `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`
- NFC 归一化后唯一 Stage046 member:
  `955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39`
- roadmap: `a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6`
- instructions: `ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8`

最终 checker 不信任历史布尔值：每次 live rehash 上述来源，并从 Git 对象库复核 Phase 4
commit、root tree、`KM_IDSystem` tree、parent 与 HEAD ancestry。任一缺失或漂移均回到
`IDS-STAGE046-REVIEW-GATE`。

## Findings And Resolution

### STAGE046-REVIEW-F0 — Critical — resolved

原 Phase2 只用 Stage045 `detection_request_id` 和 fingerprint 标识输入请求；同一检测请求
可被重组为互相矛盾的 PDF/DOCX 路由，而没有结果级身份。现以九个精确字段的 canonical
projection 生成 `detection-result:sha256:<digest>`，router 同时验证 projection digest。
该 digest 仅证明投影完整性，明确标记为
`INTEGRITY_ONLY_NOT_EXTERNAL_PROVENANCE`，不证明外部来源、生产授权或真实文件身份。

### STAGE046-REVIEW-F1 — Critical — resolved

原 invalid request 的失败结果会回显未验证的 ID、类型、状态、置信度和 instruction marker，
并错误标作 candidate fact。现先验证再投影；失败结果清空全部身份引用，类型/置信度规范化
为 `UNKNOWN`，状态为 `TYPE_INPUT_BLOCKED`，marker 不保留，fact level 为 `INVALID`，且只
返回有界错误 `INVALID_ROUTING_REQUEST`。

### STAGE046-REVIEW-F2 — Important — resolved

原 reference 只做宽松字符串检查，`file:///...`、双斜杠和 dot segment 可在
`source_path_allowed=false` 下进入路由结果。现 source identity 与 detection evidence
仅接受有界、冒号分段的 canonical reference；URI、slash、dot/parent segment 和空段均在
request ID 创建前失败关闭。

### STAGE046-REVIEW-F3 — Important — resolved

原 route result 不论候选、复审、不支持或阻断均标为 `CANDIDATE`。现 fact level 由实际
action 精确派生为 `CANDIDATE`、`REVIEW_REQUIRED`、`UNSUPPORTED` 或 `BLOCKED`；invalid
request 独立使用 `INVALID`，不能被下游误读为可执行候选。

### STAGE046-REVIEW-F4 — Important — resolved

原 Phase3 PASS 只比较 route outcome，没有把 exact errors、fact level、candidate flag、
dispatch block reason、parser version/status 与 result identity 纳入 PASS。现每个 action 有
精确 invariants；删除错误码或把 identity 改为 `UNVERIFIED` 都会得到 `FAIL_CLOSED`。

### STAGE046-REVIEW-F5 — Minor — resolved

Phase3 文档曾写成 Phase4 会完成全 Stage 独立复审，与独立 review gate 冲突。现改为
“Phase4 完成交付，整 Stage 复审由后续独立 run 执行”，并用测试锁定该边界。

## Independent Review Controls

- `check_parser_routing_stage_review.py` 每次 live rehash 四项批准来源证据。
- 重新执行 P1 contract、P2 isolated slice、P3 fourteen scenarios 与 P4 delivery checker。
- Phase 4 commit、root tree、`KM_IDSystem` tree、parent 与 HEAD ancestry 必须精确。
- 六项 finding 均有机器可执行反例；任一 false 都使 result 变为 `FAIL_CLOSED`。
- review 文档、checker、tests、治理、事件、机器记录和 owner views 必须 Git tracked 且与
  index 一致，避免只验证工作区临时内容。
- durable route 只关闭 `ACC-STAGE-046` 并指向独立的 `IDS-STAGE047-P1-GATE`；本轮
  `stage047_entry_allowed=false`、`push_allowed=false`。

## Validation

- Repair TDD RED：6 个测试按预期得到 10 failures / 1 error；最终 repair suite `6/6`。
- Review TDD RED：最终 checker 尚不存在时按预期得到 1 个 missing-checker error。
- 最终 Stage046 focused `70/70`（`35.357s`）、review `8/8`（`28.458s`）、Stage005
  `175/175`（`51.308s`）、Stage041–046 aggregate `413/413`（`1221.575s`）及 IDS v0.1
  full discovery `1166/1166`（`1605.381s`）全部通过。
- 首轮 aggregate 的 `5/413` 失败和首轮 full discovery 的 `9/1166` 失败均精确暴露
  Stage038–045 历史测试缺少当前 `Stage046 Review → Stage047 P1` 前向路由；修复只追加该
  精确 route，保留全部历史 Phase4/index/事件断言。兼容 focused `9/9`（`12.501s`）通过；
  失败运行未计为 PASS。
- 历史与当前 review checker `9/9` 通过；events 共 `225` 条，`0` parse error、`0`
  duplicate ID、`0` semantic error；owner render 哈希幂等、project dual-plane 与
  `git diff --check` 通过。
- sparse worktree 缺少根 `scripts/lean_governance.py`，仓库级完整治理只能报告
  `SPARSE_CONFLICT`；不扩展 sparse，也不进入其他项目。

## Rollback

只回滚本 review 的六项修复、文档、checker/tests、machine run、事件、batch/roadmap/
HANDOFF、machine facts 与渲染 owner views，即回到已提交 Stage046 Phase4 的
`IDS-STAGE046-REVIEW-GATE`。保留 P1–P4、Stage041–045 复审证据、批准来源、GitHub 与
app 状态；不得用 rollback 删除来源、历史审计证据或运行 `git gc --prune=now`。

## Stop Conditions

- `NO_STAGE047_THIS_RUN`
- `NO_BATCH_REVIEW_OR_UPLOAD`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`
- `NO_RAW_METADATA_ACCESS`
- `NO_IDS_BUSINESS_SOURCE_READ`
- `NO_PARSER_OR_FALLBACK_RUNTIME`
- `NO_PERSISTENCE_OR_PRODUCTION_ACTIVATION`
