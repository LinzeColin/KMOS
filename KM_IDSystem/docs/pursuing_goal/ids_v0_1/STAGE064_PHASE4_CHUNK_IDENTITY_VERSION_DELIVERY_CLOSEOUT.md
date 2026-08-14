# Stage064 Phase 4 · Chunk 身份与版本交付证据、回滚与中文反馈

状态：`phase4_completed_local`
任务：`IDS-V0_1-STAGE064-P4`
下一门：`IDS-STAGE064-REVIEW-GATE`

## 本阶段交付

本阶段只从 P3 的六类固定、非业务、`reference-only` Chunk 身份与版本控制场景，派生以下内存交付证据：

- 六条 metadata-only Chunk JSONL 样例；每条只保留场景、`chunk_identity_version_record_ref`、章节感知 chunk 控制引用、保护语义面、显式人工处置和六维控制追溯检查计数，不保留真实 chunk、身份、Hash、版本、页码或来源内容。
- 一份控制覆盖率报告；它只说明六类固定场景、三条唯一控制身份/版本记录和三十六次控制追溯检查被完整保留，不计算真实文档、页码或 chunk 覆盖率。
- 六条低质量待人工清单；所有条目均为 `CONTROL_BOUNDARY_UNVERIFIED_REQUIRES_HUMAN_REVIEW`，不表示发现了真实低质量 chunk，也不执行自动降级。
- 一份控制回归结果；它只复用 P3 的 `6/6` 场景、零静默丢弃和未执行 embedding/index 写入边界，不能解释为真实身份/版本或切块质量回归。
- 一份 Chunk 身份与版本策略适用边界和回到 P3 的重新生成/版本回退说明；它只允许纯内存 control 重放，不实现真实 chunk、身份、Hash、版本、重生成、索引回退或业务写入。

## 适用边界

长文档、跨页参数表、施工步骤、参数表、引用页码和重复 chunk 场景都必须保留业务线白箱人工复核。固定控制标签、JSONL 样例、覆盖率、低质量清单和回归结果均不能替代来源文档，不能成为业务事实、真实质量结论、真实来源追溯、真实去重、生产验收或决策依据。

## 中文确认

- 请确认 JSONL 样例仅为 Chunk 身份与版本控制元数据，不代表真实 chunk、身份、Hash、页码或来源内容。
- 请确认覆盖率报告只覆盖六类固定控制场景，真实文档、chunk 与页码覆盖率仍需业务线白箱核验。
- 请确认重新生成与版本回滚说明只允许回到 P3 控制状态，不执行真实资料、身份、版本、索引或数据库回退。

## 恢复与回滚

若本 P4 需要撤回，只撤回本说明、交付合同、纯内存模块、聚焦用例、machine run、事件、机器事实投影、治理路线和生成中文视图，恢复到 `PHASE3_CHUNK_IDENTITY_AND_VERSION_CONTROLLED_SCENARIOS_RUNTIME_DISABLED`。不得改变 P1/P2/P3、冻结任务包、真实资料、`00_ORIGINAL_RAW_DATA`、manifest、evidence ledger、audit log、事实库、数据库、索引、GitHub、OVH 或应用状态。

## Stage Review 交接条件

后续整阶段复审只能机械检查 P1--P4 合同、三条 P2 控制记录、六类 P3 场景、P4 metadata-only 交付计数、中文确认和回到 P3 的回退说明。若把控制交付误作真实 chunk、身份/版本管理、真实覆盖率、真实来源反查、真实去重或生产能力，必须保留人工处置并停止自动推进。
