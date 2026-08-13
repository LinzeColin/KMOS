# IDS / Industrial Data System Handoff

## Canonical Repository Override - 2026-07-18

- Canonical GitHub repository is `LinzeColin/KMOS`; KMIDS is stored in `KM_IDSystem/`.
- The local main tree `/Users/linzezhang/Documents/Codex/GithubProject/KMOS` is read-only. Development must use an isolated worktree under `/Users/linzezhang/Documents/Codex/GithubProject/_scratch/`.
- Older `LinzeColin/CodexProject`, `main_worktree/CodexProject/KM_IDS`, and `KM_IDS/KM_IDSystem` references below are historical evidence only and must not route new commits or pushes.
- This override changes repository routing only. It does not authorize any IDS Stage/phase entry, production activation, enterprise DWS access, external writes, or raw-data access.
- `/Users/linzezhang/Downloads/IDS_MetaData` remains a path-only no-read/no-list/no-hash/no-copy/no-modify boundary.
- Public-safe BidScout Skill contracts are integrated under `KM_IDSystem/搜标项目/`; they are not evidence that the full BidScout product or real-data pipeline has been implemented.

## Current Gate - Stage058 Phase 3 - 2026-08-13

- 本节是唯一当前交接；下方 Stage058 P2/P1、Stage057 Review/P4/P3/P2/P1、Stage056 Review 及更早章节均为已提交的历史证据，不重写其事实。
- 本轮完成 `IDS-V0_1-STAGE058-P3`：只以冻结 Stage058 任务包、P1/P2 合同和 Stage057 已复审工件为唯一合同上下文，重放两条固定、非业务、reference-only 控制记录与十一条 Schema profile 候选，覆盖空表、合并单元格、单位混乱、日期格式不一、异常值和重复行六类异常；没有建立第二权威事实源。
- 六类控制场景均有显式处置、静默丢弃为 `0` 且均要求人工处理。控制来源文档、工作表、表头行、行列范围和证据引用形状保持可追溯；这不证明真实文件、真实行列或真实证据已被验证。异常值场景阻断统计与模型确定性数值结论；不解合并、不规范化单位或日期、不去重、不评估实际异常值，事实与 RAG 摘要仍分别归后续 Stage059/060。
- 已验证：Stage058 P3 聚焦用例 `12/12`；Stage058 P3/P2/P1、Stage057 Review/P1-P4、Stage056 Review/P1-P4、Stage055 Review/P1-P4、Stage054 Review/P1-P4、Stage053 Review/P1-P4、Stage052 Review/P1-P4、Stage051 Review/P1-P4 与 BATCH041_050 的显式前序兼容回归 `401/401`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理回归为 `valid=true`。
- 没有读取、打开、检测、解析或评估真实 XLSX/CSV、生产记录、质量检验记录、授权 fixture、工作表、表头、单元格、公式、来源正文或物理路径；没有执行真实 Schema/字段/事实/质量验证、RAG 摘要、数值统计、数据库、持久化、Agent、模型调用、模型 Token、服务启动、OVH、生产、GitHub 上传或推送；`stage058_started=true`、`phase2_started=true`、`phase3_started=true`、`phase4_started=false`、`github_upload_allowed=false`、`push_allowed=false`。
- 回滚只撤回本 P3 说明、场景合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE2_TABLE_SCHEMA_INFERENCE_CONTROL_SLICE_RUNTIME_DISABLED`；保留 P1/P2、冻结任务包、真实资料、fixture、事实库、数据库、GitHub、OVH 和应用状态。
- 下一步唯一允许项是在新的独立 run 进入 `IDS-STAGE058-P4-GATE`。本 run 不进入 Phase4、OVH、生产或上传；全局上传仍延后至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage058 Phase 2 - 2026-08-13

- 本节保留 `IDS-V0_1-STAGE058-P2` 的已提交历史证据：两条固定、非业务、reference-only 十字段控制记录在内存中投影 `2` 个 Schema profile 组、`11` 条十八字段候选、`9` 类字段语义、`6` 类候选字段类型和 `11` 条来源位置引用；没有建立第二权威事实源。
- 已验证：Stage058 P2 聚焦用例 `8/8`，与前序的显式兼容回归 `389/389`；该切片不代表实际表头、真实 schema、真实事实、统计、数据库、OVH、生产或上传能力。
- P2 未读取、打开、检测或解析真实表格或 fixture，未创建真实 schema、字段映射、事实、RAG 摘要、数值统计、数据库或持久状态；其回滚目标为 `PHASE1_TABLE_SCHEMA_INFERENCE_CONTRACT_RUNTIME_DISABLED`。

## Superseded Gate - Stage057 Review - 2026-08-13

- 本节保留 Stage057 Review 的历史交接；下方 Stage057 P4/P3/P2/P1、Stage056 Review、Stage056 P4/P3/P2/P1、Stage055 Review 及更早章节均为已提交的历史证据，不重写其事实。
- 本轮完成 `IDS-V0_1-STAGE057-REVIEW`：只以冻结任务包、P1--P4 合同和 Stage056 已复审工件为唯一合同上下文，机械复审 `12/19/7/5/6` 静态形状、两条固定非业务控制记录、六类显式质量处置、六个 metadata-only 交付样例、人工处理、中文确认与重解析/事实回滚链；没有建立第二权威事实源。
- 复审只输出受控计数、边界和回滚结论，不是实际 XLSX/CSV、真实 schema、真实字段、真实事实、真实数值、真实来源追溯、真实质量验证或事实库。无法识别结构仍要求人工处理；重解析和事实回滚只回到 P3 control 状态，不能替代真实文件重解析或真实事实回滚。
- 已验证：Stage057 Review 聚焦用例 `11/11`；Stage057 Review/P1-P4、Stage056 Review/P1-P4、Stage055 Review/P1-P4、Stage054 Review/P1-P4、Stage053 Review/P1-P4、Stage052 Review/P1-P4、Stage051 Review/P1-P4 与 BATCH041_050 的显式前序兼容回归 `374/374`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理报告 `valid=true`；中文事实投影已重渲染 `7` 个文件。
- 没有读取、打开、检测或解析真实 XLSX/CSV、生产记录、质量检验记录、授权 fixture、工作表、单元格、公式、来源正文或物理路径；没有执行真实质量验证、真实来源追溯、数值统计、数据库、持久化、Agent、模型调用、模型 Token、服务启动、OVH、生产、GitHub 上传或推送；`whole_stage_review_performed=true`、`stage058_started=false`、`github_upload_allowed=false`、`push_allowed=false`。
- 回滚只撤回本 Review 说明、只读复审模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE4_XLSX_CSV_INGESTION_DELIVERY_EVIDENCE_RUNTIME_DISABLED`；保留 P1--P4、冻结任务包、真实资料、fixture、事实库、数据库、GitHub、OVH 和应用状态。
- 下一步唯一允许项是在新的独立 run 进入 `IDS-STAGE058-P1-GATE`。本 run 不进入 Stage058、OVH、生产或上传；全局上传仍延后至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage057 Phase 4 - 2026-08-13

- 本节仅保留 `IDS-V0_1-STAGE057-P4` 的历史交付证据：从 P3 六类固定、非业务、reference-only 控制场景派生 `6` 个 metadata-only 交付样例、`5` 个字段引用标签、`6` 条质量结果、`6` 条人工处理建议、`3` 条中文确认提示和重解析/事实回滚说明。
- 交付样例、字段推断和质量结果均为控制元数据，不是实际 XLSX/CSV、真实 schema、真实字段、真实事实、真实数值、真实来源追溯或事实库；重解析和事实回滚仅为未来控制重放说明。
- P4 聚焦用例历史记录为 `12/12`，且其前序兼容回归为 `363/363`；本阶段未读取、检测或解析真实表格、fixture、来源正文或物理路径，未执行真实质量验证、来源追溯、数值统计、数据库、持久化、Agent、模型 Token、OVH、生产、上传或推送。
- P4 的本地回滚只撤回其说明、交付合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE3_XLSX_CSV_INGESTION_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED`；不触及真实资料、fixture、事实库、数据库、运行状态、GitHub、OVH 或应用状态。

## Superseded Gate - Stage057 Phase 3 - 2026-08-13

- 本节是已提交的历史证据；P3 只重放 P2 两条固定、非业务、reference-only 控制记录的 `10` 个空值事实候选，覆盖空表、合并单元格、单位混乱、日期格式不一、异常值和重复行六类控制异常；没有建立第二权威事实源。
- 六类均有显式处置、静默丢弃为 `0`。空表、合并单元格、单位混乱、日期格式不一和重复行均要求人工处理；异常值场景明确阻断统计结论与模型确定性数值结论。未解合并、未规范化单位/日期、未去重、未评估实际异常值，所有 `typed_value` 仍保持空值。
- 每个场景保留 P2 候选的源文档、工作表、行列范围和证据引用，用于验证控制来源引用形状；这不证明真实源文件、真实行列或真实证据记录已经读取、验证或创建。
- 已验证：Stage057 P3 聚焦用例 `12/12`；Stage057 P2/P1、Stage056 Review/P1-P4、Stage055 Review/P1-P4、Stage054 Review/P1-P4、Stage053 Review/P1-P4、Stage052 Review/P1-P4、Stage051 Review/P1-P4 与 BATCH041_050 的显式前序兼容回归 `351/351`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理报告 `valid=true`；中文事实投影已重渲染 `7` 个文件。
- P3 没有读取、打开、检测或解析真实 XLSX/CSV、生产记录、质量检验记录、授权 fixture、工作表、单元格、公式、来源正文或物理路径；没有执行真实质量验证、真实来源追溯、数值统计、数据库、持久化、Agent、模型调用、模型 Token、服务启动、OVH、生产、GitHub 上传或推送。
- P3 回滚只撤回其说明、场景合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE2_XLSX_CSV_INGESTION_CONTROL_SLICE_RUNTIME_DISABLED`；不触及真实资料、fixture、数据库、运行状态、GitHub、OVH 或应用状态。

## Superseded Gate - Stage057 Phase 2 - 2026-08-13

- 本节是已提交的历史证据。P2 只以 P1 的 12 字段合同和两条固定、非业务、reference-only 控制记录，在内存中投影 XLSX/CSV schema profile、字段候选、19 字段空值事实候选、来源定位及 metadata-only RAG 摘要候选；没有建立第二权威事实源。
- 受控结果严格为 `2` 个 schema profile、`10` 个事实候选、`2` 个 RAG 摘要候选、`10` 个来源定位绑定候选和 `1` 个数值字段候选。所有 `typed_value` 保持空值，源文档仍为权威；RAG 摘要与事实层分离，不能替代事实或数值统计。
- P2 没有读取、打开、检测或解析真实 XLSX/CSV、生产记录、质量检验记录、授权 fixture、工作表、单元格、公式、来源正文或物理路径；没有生成真实 schema、事实、typed value、数值统计、RAG 内容、证据记录、数据库或持久化状态。
- 已验证：Stage057 P2 聚焦用例 `8/8`；Stage057 P1、Stage056 Review/P1-P4、Stage055 Review/P1-P4、Stage054 Review/P1-P4、Stage053 Review/P1-P4、Stage052 Review/P1-P4、Stage051 Review/P1-P4 与 BATCH041_050 的显式前序兼容回归 `339/339`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理报告 `valid=true`；中文事实投影已重渲染 `7` 个文件。
- P2 没有执行 Agent、模型调用、模型 Token、服务启动、OVH、生产、GitHub 上传或推送；`github_upload_allowed=false`、`push_allowed=false`。
- P2 回滚只撤回其说明、切片合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE1_XLSX_CSV_INGESTION_CONTRACT_RUNTIME_DISABLED`；不触及真实资料、数据库、运行状态、GitHub、OVH 或应用状态。

## Superseded Gate - Stage056 Review - 2026-08-13

- 本节是唯一当前交接；下方 Stage056 P4/P3/P2/P1、Stage055 Review 及更早章节均为已提交的历史证据，不重写其事实。
- 本轮完成 `IDS-V0_1-STAGE056-REVIEW`：只以冻结 Stage056 任务包、已提交的 P1--P4 合同和 Stage055 已复审工件为合同上下文，机械复审字段形状、五类受控场景、五个 metadata-only 样例、置信度、显式失败、候选复核、中文确认、零物理缓存与回滚链；没有建立第二权威事实源。
- 复审只输出字段和受控计数，不包含业务资料、授权 fixture、来源正文、真实路径、页面、图片、表格内容、OCR 文本、失败内容、实际缓存条目或磁盘信息。P3 五类均有显式处置、静默丢弃为零；P4 控制汇总为 `HIGH=2`、`MEDIUM=1`、`LOW=1`、`UNKNOWN=1`，一条失败保持禁止自动清理，三条 Stage054 候选复核路由均未排队且不能直接进入高可信证据层。
- 已验证：Stage056 Review 聚焦用例 `11/11`；Stage056 Review/P1--P4、Stage055 Review/P1--P4、Stage054 Review/P1--P4、Stage053 Review/P1--P4、Stage052 Review/P1--P4、Stage051 Review/P1--P4 与 BATCH041_050 的显式前序兼容回归 `323/323`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理报告 `valid=true`；中文事实投影已重渲染 `7` 个文件。
- 没有执行 Agent、模型调用、模型 Token、OCR 运行时、真实队列、真实按页输出、真实缓存、人工任务、OVH、生产、GitHub 上传或推送；`whole_stage_review_performed=true`，但 `stage057_started=false`、`stage057_entry_allowed=false`。
- 回滚只撤回本 Review 说明、只读复审模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE4_OCR_CACHE_RETENTION_POLICY_DELIVERY_EVIDENCE_RUNTIME_DISABLED`；不触及 P1--P4、真实资料、缓存、磁盘、运行状态、GitHub、OVH 或应用状态。
- 下一步唯一允许项是在新的独立 run 进入 `IDS-STAGE057-P1-GATE`。本 run 不进入 Stage057、OVH、生产或上传；全局上传仍延后至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage056 Phase 4 - 2026-08-13

- 本节仅保留 Stage056 P4 的历史交接证据；当前门已转为 Stage056 Review。
- 本轮完成 `IDS-V0_1-STAGE056-P4`：只以冻结 Stage056 任务包、P1/P2/P3 合同和 Stage055 已复审工件为合同上下文，从 P3 五类固定非业务缓存策略 control 场景派生五个 metadata-only 交付样例、控制置信度汇总、显式失败清单、候选复核路由证明、中文人工确认提示与非物理缓存重跑说明；没有建立第二权威事实源。
- 五个样例只保留固定场景、引用、语言、置信度、策略状态和处置，不包含业务资料、授权 fixture、来源正文、真实路径、页面、图片、表格内容、OCR 文本、失败内容、实际缓存条目或磁盘信息。控制置信度为 `HIGH=2`、`MEDIUM=1`、`LOW=1`、`UNKNOWN=1`；低质量 control 保持一条显式失败，低置信、中英文混合和失败 control 只保留三条未排队的 Stage054 复核候选，均不能直接进入高可信证据层。
- 质量限制与三条人工确认提示均为中文且不会自动确认。物理缓存条目为零；三条临时候选仍须未来 owner、明确标识和容量批准，失败产物禁止自动清理。重跑只重放内存 control，不扫描、删除、移动或写入任何目录；`NO_PHYSICAL_CACHE_CREATED_NO_CLEANUP_EXECUTED` 不是实际 OCR、实际缓存容量或真实清理证明。
- 已验证：P4 纯内存交付报告返回 `PASS_PHASE4_OCR_CACHE_RETENTION_POLICY_DELIVERY_RUNTIME_DISABLED`；Stage056 P4 聚焦用例 14/14；Stage056 P3/P2/P1、Stage055 Review/P1--P4、Stage054 Review/P1--P4、Stage053 Review/P1--P4、Stage052 Review/P1--P4、Stage051 Review/P1--P4 与 BATCH041_050 的显式前序兼容回归 312/312；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理报告 `valid=true`；中文事实投影已重渲染 7 个文件。
- 没有执行 Agent、模型调用、模型 Token、OCR 运行时、真实队列、真实按页输出、真实缓存、人工任务、OVH、生产、GitHub 上传或推送；`stage056_started=true`、`phase2_started=true`、`phase3_started=true`、`phase4_started=true`，但 `whole_stage_review_performed=false`。
- 回滚只撤回本 P4 说明、交付合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE3_OCR_CACHE_RETENTION_POLICY_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED`；不触及真实资料、缓存、磁盘、运行状态、GitHub、OVH 或应用状态。
- 下一步唯一允许项是在新的独立 run 进入 `IDS-STAGE056-REVIEW-GATE`。本 run 不进入整阶段复审、OVH、生产或上传；全局上传仍延后至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage056 Phase 3 - 2026-08-13

- 本节是唯一当前交接；下方 Stage056 P2/P1、Stage055 Review 及更早章节均为已提交的历史证据，不重写其事实。
- 本轮完成 `IDS-V0_1-STAGE056-P3`：只以冻结 Stage056 任务包、P1/P2 合同和 Stage055 已复审工件为合同上下文，重放四条固定非业务、reference-only 缓存策略候选，并以扫描 PDF、模糊图片、表格图片、中英文混合和低质量五类控制元数据形成显式候选、降级或失败处置；没有建立第二权威事实源。
- 五类均只保留类别、候选引用、语言、置信度、策略状态和处置，不包含样本、OCR 文本、来源正文、真实路径、页面、图像、表格内容、失败内容或实际缓存条目。扫描 PDF 与表格图片只为未评估候选；低置信和中英文混合为降级证据且声明 Stage054 复核路径但未排队；低质量为明确失败、禁止自动清理且不得提升高可信证据。
- P3 只重放 P2 内存候选，物理缓存条目为零，未创建缓存、路径、写入、清理、磁盘扫描或容量评估。`NO_PHYSICAL_CACHE_CREATED_NO_CLEANUP_EXECUTED` 仅证明控制重放无物理副作用，不证明真实 OCR、内置盘容量或真实缓存清理已验证。
- 已验证：Stage056 P3 聚焦用例 12/12；Stage056 P2/P1、Stage055 Review/P1--P4、Stage054 Review/P1--P4、Stage053 Review/P1--P4、Stage052 Review/P1--P4、Stage051 Review/P1--P4 与 BATCH041_050 的显式前序兼容回归 298/298；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理报告 `valid=true`；中文事实投影已重渲染 7 个文件。
- 没有执行 Agent、模型调用、模型 Token、OCR 运行时、真实队列、真实按页输出、真实缓存、人工任务、OVH、生产、GitHub 上传或推送；`stage056_started=true`、`phase2_started=true`、`phase3_started=true`，但 `phase4_started=false`、`whole_stage_review_performed=false`。
- 回滚只撤回本 P3 说明、场景合同、纯内存专项模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE2_OCR_CACHE_RETENTION_POLICY_CONTROL_SLICE_RUNTIME_DISABLED`；不触及真实资料、缓存、磁盘、运行状态、GitHub、OVH 或应用状态。
- 下一步唯一允许项是在新的独立 run 进入 `IDS-STAGE056-P4-GATE`。本 run 不进入 P4、整阶段复审、OVH、生产或上传；全局上传仍延后至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage056 Phase 2 - 2026-08-13

- 本节是唯一当前交接；下方 Stage056 P1、Stage055 Review 及更早章节均为已提交的历史证据，不重写其事实。
- 本轮完成 `IDS-V0_1-STAGE056-P2`：只以冻结 Stage056 任务包、P1 静态合同和 Stage055 已复审工件为合同上下文，用四条固定非业务、reference-only 控制记录投影 OCR 缓存保留策略的内存候选、来源页引用和中文可解释状态；没有建立第二权威事实源。
- 切片严格接受 P1 固定的 11 字段引用输入，返回 P1 定义的 10 字段策略候选。四条 control 只含标量引用，不含 OCR 文本、图片、业务正文、来源路径、失败内容或实际缓存条目；所有候选状态均为 `CANDIDATE_NOT_PERSISTED`。
- 中文简体临时页面图片、英文低置信中间文本、中英文混合中间文本与 UNKNOWN 失败产物分别覆盖可重建临时、低置信复核、混合语言复核和失败禁止自动清理边界。低置信、中英文混合和失败候选均未排队，不能直接进入高可信证据层，Stage054 仍为未来复核所有者。
- 临时候选仍需未来 owner 保留批准、容量批准和明确的临时产物标识；失败产物不得自动清理。没有指定物理路径、数值保留窗口、容量阈值或清理目标，没有创建或读取真实缓存、扫描磁盘、评估容量、写入缓存或执行清理。
- 已验证：Stage056 P2 聚焦用例 8/8；Stage056 P1、Stage055 Review/P1--P4、Stage054 Review/P1--P4、Stage053 Review/P1--P4、Stage052 Review/P1--P4、Stage051 Review/P1--P4 与 BATCH041_050 的显式前序兼容回归 286/286；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理报告 `valid=true`；中文事实投影已重渲染 7 个文件。
- 没有执行 Agent、模型调用、模型 Token、OCR 运行时、真实队列、真实按页输出、真实缓存、人工任务、OVH、生产、GitHub 上传或推送；`stage056_started=true`、`stage056_entry_authorized=true`、`phase2_started=true`，但 `phase3_started=false`、`whole_stage_review_performed=false`。
- 回滚只撤回本 P2 说明、切片合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE1_OCR_CACHE_RETENTION_POLICY_BOUNDARY_RUNTIME_DISABLED`；不触及真实资料、缓存、运行状态、GitHub、OVH 或应用状态。
- 下一步唯一允许项是在新的独立 run 进入 `IDS-STAGE056-P3-GATE`。本 run 不进入 P3、整阶段复审、OVH、生产或上传；全局上传仍延后至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage056 Phase 1 - 2026-08-13

- 本节只保留 `IDS-V0_1-STAGE056-P1` 的历史证据：P1 已定义 OCR 临时图片、中间文本和失败产物的引用式缓存保留与清理合同、11 字段未来输入、10 字段未来输出、双语默认、低置信隔离、未来容量前置条件和回滚边界。
- P1 没有创建或读取缓存、扫描磁盘、评估容量、写入或清理任何缓存；P2 只复用其静态合同，不改写其历史结论。P1 交接、合同、测试、machine run、事件和事实投影仍是 P2 的可追溯前序证据。

## Superseded Gate - Stage055 Review - 2026-08-13

- 本节仅保留 Stage055 Review 的历史交接证据；下方 Stage055 P4/P3/P2/P1、Stage054 Review 及更早章节均为已提交的历史证据，不重写其事实。
- 本轮完成 `IDS-V0_1-STAGE055-REVIEW`：只复审冻结 Stage055 P1--P4 合同、P3/P4 固定非业务 control 报告与既有回滚链；复审输出仅包含字段、场景、处置、置信度、失败、路由与边界计数，没有建立第二权威事实源。
- 复审保持 P1 的 10/11 字段引用结构、P2 的纯内存队列语义、P3 的五类明确处置与零静默丢弃，以及 P4 的五个 metadata-only 样例、`HIGH=1`、`MEDIUM=2`、`LOW=1`、`UNKNOWN=1`、一条显式失败和三条未排队 Stage054 复核路由。它们不是真实 OCR 输出、准确率、人工复核或生产验收。
- 缓存仍为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`，临时产物为 `0`，清理结论为 `NO_TEMPORARY_ARTIFACT_CREATED`；只声明 Stage056 将拥有缓存保留策略。本轮未读取或创建真实资料、fixture、样本、PDF、图片、页面、表格或 OCR 文本，也未选择、配置、调用或比较 OCR 引擎。
- 已验证：Stage055 Review 聚焦用例 `11/11`；Stage055 Review/P1--P4、Stage054 Review/P1--P4、Stage053 Review/P1--P4、Stage052 Review/P1--P4、Stage051 Review/P1--P4 与 BATCH041_050 的显式前序兼容回归 `270/270`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理报告 `valid=true`；中文事实投影已重渲染 `7` 个文件。
- 没有执行 Agent、模型调用、模型 Token、OCR 运行时、持久队列、持久按页输出、缓存、人工任务、OVH、生产、GitHub 上传或推送；`stage056_started=false` 且 `stage056_entry_authorized=false`。
- 回滚只撤回本 Review 说明、只读复审模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE4_OCR_REGRESSION_CORPUS_DELIVERY_EVIDENCE_RUNTIME_DISABLED`；不触及真实资料、P1--P4 已提交证据、运行状态、GitHub、OVH 或应用状态。
- 下一步唯一允许项是在新的独立 run 进入 `IDS-STAGE056-P1-GATE`。本 run 不进入 Stage056、OVH、生产或上传；全局上传仍延后至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage055 Phase 4 - 2026-08-13

- 本节覆盖下方 Stage055 P3/P2/P1、Stage054 Review、P1--P4、Stage053 Review、P1--P4、Stage052 Review、Stage051 Review 及更早交接的历史指向；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成 `IDS-V0_1-STAGE055-P4`：只从 P3 的五条固定非业务 OCR 回归语料 control 报告派生五个 metadata-only 交付样例、控制置信度汇总、显式失败清单、候选复核路由证明、质量限制、三条中文人工确认提示和缓存重跑说明。
- 五个样例只保留场景、control 来源页引用、语言、置信度、状态与处置；不含 OCR 文本、业务正文、真实文件路径、页面图像、表格单元、真实来源内容、失败原因或人工意见。它们不是真实 OCR 输出、准确率报告、实际人工复核记录或生产验收，因此没有建立第二权威事实源。
- 控制置信度为 `HIGH=1`、`MEDIUM=2`、`LOW=1`、`UNKNOWN=1`；低质量 control 保持一条显式失败，低置信、中英文混合和失败 control 只保留三条未排队的 Stage054 候选复核路由。候选、降级与失败均不能直接进入高可信证据层，且没有创建人工任务、队列或结果。
- 缓存仍为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`，未创建缓存或临时产物，清理结论为 `NO_TEMPORARY_ARTIFACT_CREATED`；重跑只在内存中重放固定 control，不扫描、删除或移动目录。这不构成真实 OCR 缓存容量、真实识别准确率或实际人工复核证明，容量、保留与清理仍归 Stage056。
- 没有读取、创建或评估真实资料、授权 fixture、样本、PDF、图片、页面、表格或 OCR 文本；没有选择、配置、调用或比较 OCR 引擎，也没有执行真实回归、持久队列、持久按页输出、缓存、复核、质量门、持久化、Agent、模型调用、模型 Token、OVH、生产、上传或推送。
- 已验证：Stage055 P4 聚焦用例 `14/14`；Stage055 P3/P2/P1、Stage054 Review/P1--P4、Stage053 Review/P1--P4、Stage052 Review/P1--P4、Stage051 Review/P1--P4 与 BATCH041_050 的显式前序兼容回归 `259/259`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理报告 `valid=true`；中文事实投影已重渲染 `7` 个文件。
- 回滚只撤回本 P4 说明、交付合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `PHASE3_OCR_REGRESSION_CORPUS_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED`；真实资料、既有 P1/P2/P3 证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 下一步只允许在新的独立 run 进入 `IDS-STAGE055-REVIEW-GATE`；本 run 不进入整阶段复审，所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage054 Review - 2026-08-13

- 本节覆盖下方 Stage054 P4/P3/P2/P1、Stage053 Review、P1--P4、Stage052 Review、Stage051 Review 及更早交接的历史指向；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成 `IDS-V0_1-STAGE054-REVIEW`：只复审 P1--P4 已提交合同并重放 P3/P4 固定非业务 control 报告，核验九字段复核输入、十字段候选请求、五类明确处置、metadata-only 交付、中文确认、缓存边界和回滚链。
- 复审只输出字段数、场景数、处置数、置信度计数、失败计数、候选复核路由计数和边界结论。P1/P2 的 9/10 字段结构、P3 的五个明确处置与零静默丢弃，以及 P4 的五个 metadata-only 样例、`HIGH=2`、`MEDIUM=1`、`LOW=1`、`UNKNOWN=1`、一条失败、三条候选路由和三条中文提示均保持一致。
- 候选复核路由仍不构成实际人工任务或队列；缓存仍为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`、临时产物为 `0`、清理结论为 `NO_TEMPORARY_ARTIFACT_CREATED`，回滚点为 `PHASE4_LOW_CONFIDENCE_REVIEW_ROUTE_DELIVERY_EVIDENCE_RUNTIME_DISABLED`。
- 没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容；没有打开样本、调用 OCR、创建实际复核、持久队列、缓存、审计或运行时；没有启动 Agent、模型调用、模型 Token、OVH、生产、上传或推送。
- 已验证：Stage054 Review 聚焦用例 `11/11`，与 Stage054 P1--P4、Stage053 Review/P1--P4、Stage052 Review/P1--P4、Stage051 Review/P1--P4 和 BATCH041_050 的合并前序回归 `218/218`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`，中文事实投影已重渲染 `7` 个文件。
- 下一步只允许在新的独立 run 进入 `IDS-STAGE055-P1-GATE`。本 run 不进入 Stage055；所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage054 Phase 4 - 2026-08-13

- 本节覆盖下方 Stage054 P3/P2/P1、Stage053 Review、P1--P4、Stage052 Review、Stage051 Review 及更早交接的历史指向；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成 `IDS-V0_1-STAGE054-P4`：只重放 P3 的五类固定非业务低置信度复核路由 control 报告，派生五个 metadata-only 交付样例、置信度汇总、一个显式失败清单、三条候选复核路由证明、质量限制、三条中文人工确认提示与缓存重跑说明。
- 五个样例均为 `CANDIDATE` / `UNASSESSED` 控制元数据，置信度为 `HIGH=2`、`MEDIUM=1`、`LOW=1`、`UNKNOWN=1`；低质量 control 保持显式失败，低置信、中英文混合和失败 control 只保留候选复核路径，不创建人工任务、队列、意见或结论，且不能直接进入高可信证据层。
- 缓存固定为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`，未创建缓存路径或临时产物，清理结论为 `NO_TEMPORARY_ARTIFACT_CREATED`；重跑只在内存中重放 P3 的固定 control，不扫描、删除或移动目录。缓存保留、容量和实际清理仍由 Stage056 负责。
- 没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容；没有打开样本、调用 OCR、创建实际复核、持久队列、缓存、审计或运行时；没有启动 Agent、模型调用、模型 Token、OVH、生产、上传或推送。
- 已验证：Stage054 P4 聚焦用例 `14/14`，与 Stage054 P3/P2/P1、Stage053 Review/P1--P4、Stage052 Review/P1--P4、Stage051 Review/P1--P4 和 BATCH041_050 的合并前序回归 `207/207`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`，中文事实投影已重渲染 `7` 个文件。
- 回滚只撤回本 P4 说明、交付合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE3_LOW_CONFIDENCE_REVIEW_ROUTE_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED`；真实资料、既有证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 下一步只允许在新的独立 run 进入 `IDS-STAGE054-REVIEW-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage054 Phase 3 - 2026-08-13

- 本节覆盖下方 Stage054 P2/P1、Stage053 Review、P1--P4、Stage052 Review、Stage051 Review 及更早交接的历史指向；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成 `IDS-V0_1-STAGE054-P3`：只以冻结 Stage054 任务包与 P1/P2 合同为合同上下文，重放 P2 的四条固定非业务 reference-only 控制路由，为扫描 PDF、模糊图片、表格图片、中英文混合和低质量五类标量场景形成明确候选、降级或失败处置。
- 英文低置信、中英文混合和失败控制页自动形成仅内存候选路由状态并降级证据，未创建人工任务、队列或复核结果；扫描 PDF 和表格类别保持 `CANDIDATE` / `UNASSESSED`。五类情形静默丢弃为零，均不能直接进入高可信证据层。
- 缓存固定为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`，未创建缓存路径或临时产物，清理结论为 `NO_TEMPORARY_ARTIFACT_CREATED`；容量、保留和清理仍由 Stage056 负责。本轮未执行缓存容量评估或清理操作。
- 没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容；没有打开样本、调用 OCR、执行语言检测、创建实际人工复核任务/结果、持久队列、缓存、审计、本地服务、OVH 或生产运行；运行时保持零 Agent、零模型 Token。
- 已验证：Stage054 P3 聚焦用例 `11/11`；Stage054 P2/P1 与 Stage053 Review/P1--P4 前序兼容 `70/70`，Stage052 Review/P1--P4 `53/53`，Stage051 Review/P1--P4 `53/53`，BATCH041_050 `6/6`，合并回归 `193/193`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`，中文事实投影已重渲染 `7` 个文件。
- 回滚只撤回本 P3 说明、场景合同、纯内存场景模块、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `PHASE2_LOW_CONFIDENCE_REVIEW_ROUTE_CONTROL_SLICE_RUNTIME_DISABLED`；真实资料、既有运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 下一步只允许在新的独立 run 进入 `IDS-STAGE054-P4`，门为 `IDS-STAGE054-P4-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage054 Phase 2 - 2026-08-13

- P2 已形成四条固定非业务 reference-only 控制记录的三个十字段候选复核请求、三种受控路由状态、四条中文反馈和来源页引用保留；其缓存和人工任务边界由当前 P3 继承为历史证据。

## Superseded Gate - Stage054 Phase 1 - 2026-08-13

- 本节覆盖下方 Stage053 Review、P1--P4、Stage052 Review、Stage051 Review 及更早交接的历史指向；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成 `IDS-V0_1-STAGE054-P1`：只以冻结 Stage054 任务包和 Stage053 已复审工件为合同上下文，定义低置信 OCR 复核路由的九字段 reference-only 输入、十字段未来复核请求、默认中文简体与英文、四种置信度引用、三种未来复核状态、缓存边界、中文反馈与回滚范围。
- LOW、UNKNOWN、中英文混合和失败页均不能直接进入高可信证据层；不设数值阈值、不执行语言检测、准确率评估、自动分派、人工复核或证据提升。未来复核状态只作合同定义，未创建请求、队列、任务或结果。
- 缓存只保留 `FUTURE_REBUILDABLE_DERIVED_CACHE_REFERENCE_ONLY` 边界，保留与清理所有权仍归 Stage056；未创建缓存、审计、manifest、evidence ledger、report、数据库或持久状态。
- 没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容；没有打开样本、调用 OCR、创建实际按页输出、图片引用、失败记录、复核任务/结果、队列、质量门、本地服务、OVH 或生产运行；运行时保持零 Agent、零模型 Token。
- 回滚只撤回本 P1 说明、静态合同、聚焦用例、machine run、事件、事实投影、治理路线和生成中文视图，恢复到 `STAGE053_REVIEWED_LOCAL_PER_PAGE_OCR_OUTPUT_RUNTIME_DISABLED`；真实资料、既有运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 已验证：Stage054 P1 聚焦用例 `8/8`，加 Stage053 Review/P1--P4、Stage052 Review/P1--P4、Stage051 Review/P1--P4 与 BATCH041_050 的回归共 `173/173`；Stage005 治理报告为 `valid=true`。
- 下一步只允许在新的独立 run 进入 `IDS-STAGE054-P2`，门为 `IDS-STAGE054-P2-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage053 Review - 2026-08-13

- 本节覆盖下方 Stage053 P4/P3/P2/P1、Stage052 Review、Stage051 Review 及更早交接的历史指向；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成 `IDS-V0_1-STAGE053-REVIEW`：只读取冻结 Stage053 任务包、Stage052 已复审工件和 P1--P4 已提交合同，重放 P3/P4 固定非业务 control 报告，独立复审十一字段按页结构、五类显式处置、metadata-only 交付、中文确认、缓存边界与回滚链。
- 复审输出仅保留字段、场景、处置、置信度、失败和复核路由的计数与边界结论。P1 维持七字段输入和十一字段输出，P2 为四页受控切片，P3 为五类显式处置且静默丢弃为零，P4 为五个 metadata-only 样例、HIGH=2/MEDIUM=1/LOW=1/UNKNOWN=1、1 条失败、2 条未排队复核路由与 3 条中文确认提示。
- 缓存继续为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`，临时产物为 `0`，清理结论为 `NO_TEMPORARY_ARTIFACT_CREATED`；重跑只重放已提交的固定 control 报告，不扫描、删除或移动目录。低置信、中英文混合和失败页仍不能直接进入高可信证据层，实际复核仍由后续 Stage054 管理。
- 没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容；没有打开样本、调用 OCR、图像处理、语言检测、表格提取、识别准确率评估、实际复核、质量门、本地服务、OVH 或生产运行；运行时保持零 Agent、零模型 Token。
- 回滚只撤回本复审说明、复审模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `PHASE4_PER_PAGE_OCR_DELIVERY_EVIDENCE_RUNTIME_DISABLED`；P1--P4、冻结任务包、Stage052 已复审证据、真实资料、既有运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 已验证：Stage053 Review 聚焦用例 `11/11`、Stage053 P1--P4 前序兼容 `42/42`、Stage052 Review 与 P1--P4 前序兼容 `53/53`、Stage051 Review 与 P1--P4 前序兼容 `53/53`、BATCH041_050 前序兼容 `6/6`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`。
- 下一步只允许在新的独立 run 进入 `IDS-STAGE054-P1`，门为 `IDS-STAGE054-P1-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage053 Phase 4 - 2026-08-13

- 本节覆盖下方 Stage053 P3/P2/P1、Stage052 Review、P4、P3、P2、P1、Stage051 Review 及更早交接的历史指向；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成 `IDS-V0_1-STAGE053-P4`：只以冻结 Stage053 任务包、Stage052 已复审中英文 OCR 工件和 Stage053 P1--P3 已提交工件为唯一上下文，从 P3 的五类固定非业务按页 OCR 质量 control 报告派生五个 metadata-only 交付样例、置信度汇总、一条显式失败清单、两条未排队复核路由证明、质量限制说明、三条中文人工确认提示和缓存重跑说明。
- 五个样例只保留场景、控制页引用、语言、置信度、状态与处置；不含 OCR 文本、业务正文、真实路径、页面图像、表格单元或真实来源内容。置信度汇总为 HIGH=2、MEDIUM=1、LOW=1、UNKNOWN=1，不代表识别准确率或质量门。低置信和中英文混合 control 只声明 Stage054 后续复核路径，未创建实际任务；失败页显式隔离，所有结果均不能直接进入高可信证据层。
- 缓存继续为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`：未创建缓存路径、未落盘、临时产物为 `0`，清理结论为 `NO_TEMPORARY_ARTIFACT_CREATED`。重跑只重放 P3 的五类固定非业务 control 报告，不扫描、删除或移动目录；实际缓存保留、容量和清理所有权仍归 Stage056。
- 没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容；没有打开样本、调用 OCR、图像处理、语言检测、表格提取、识别准确率评估、实际复核、质量门、本地服务、OVH 或生产运行；运行时保持零 Agent、零模型 Token。
- 回滚只撤回本 P4 说明、交付合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `PHASE3_PER_PAGE_OCR_CONTROLLED_QUALITY_SCENARIOS_ENGINE_DISABLED`；真实资料、既有证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 已验证：Stage053 P4 聚焦用例 `14/14`、Stage053 P3/P2/P1 与 Stage052 Review/P1--P4 前序兼容 `81/81`、Stage051 Review 与 P1--P4 前序兼容 `53/53`、BATCH041_050 前序兼容 `6/6`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`，中文事实投影已重渲染 `7` 个文件。
- 下一步只允许在新的独立 run 进入 `IDS-STAGE053-REVIEW`，门为 `IDS-STAGE053-REVIEW-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage053 Phase 3 - 2026-08-13

- 本节覆盖下方 Stage053 P2/P1、Stage052 Review、P4、P3、P2、P1、Stage051 Review 及更早交接的历史指向；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成 `IDS-V0_1-STAGE053-P3`：只以冻结 Stage053 任务包、Stage052 已复审中英文 OCR 工件和 Stage053 P1/P2 已提交工件为唯一上下文，重放 P2 的四页纯内存按页输出，为扫描 PDF、模糊图片、表格图片、中英文混合和低质量五个固定非业务类别建立候选、降级或失败处置。
- 五个类别只是标量控制元数据，不是文件、图像、真实页面、真实 OCR 结果、业务正文、来源路径、真实图片引用或实际失败记录；P3 报告不保留 P2 符号化 OCR 文本或图片引用。扫描 PDF 和表格图片只保留未评估候选，英文低置信和中英文混合显式降级为未排队的后续 `Stage054` 复核提示，低质量控制页保持显式失败；静默丢弃为零，所有结果都不能直接进入高可信证据层。
- 缓存继续为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`：未创建缓存路径、未落盘、临时产物为 `0`，清理结论为 `NO_TEMPORARY_ARTIFACT_CREATED`。实际缓存保留、容量和清理所有权仍归 Stage056；未创建实际队列、按页输出、audit、manifest、evidence ledger、report、数据库或持久状态。
- 没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容；没有打开样本、调用 OCR、图像处理、语言检测、表格提取、识别准确率评估、实际复核、质量门、本地服务、OVH 或生产运行；运行时保持零 Agent、零模型 Token。
- 回滚只撤回本 P3 说明、场景合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `PHASE2_PER_PAGE_OCR_CONTROLLED_OUTPUT_SLICE_ENGINE_DISABLED`；真实资料、既有证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 已验证：Stage053 P3 聚焦用例 `11/11`、Stage053 P2/P1 与 Stage052 Review/P1--P4 前序兼容 `70/70`、Stage051 Review 与 P1--P4 前序兼容 `53/53`、BATCH041_050 前序兼容 `6/6`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`，中文事实投影已重渲染 `7` 个文件。
- 下一步只允许在新的独立 run 进入 `IDS-STAGE053-P4`，门为 `IDS-STAGE053-P4-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage053 Phase 2 - 2026-08-13

- P2 已完成纯内存十一字段按页输出切片并只作为 P3 的前置工件；其控制标记、符号化 OCR 文本、图片引用和失败分类均不是业务资料、真实内容或持久运行结果。
- P2 的回滚点为 `PHASE1_PER_PAGE_OCR_OUTPUT_BOUNDARY_RUNTIME_DISABLED`；当前 P3 的独立回滚点为 `PHASE2_PER_PAGE_OCR_CONTROLLED_OUTPUT_SLICE_ENGINE_DISABLED`。

## Superseded Gate - Stage053 Phase 1 - 2026-08-13

- 本节覆盖下方 Stage052 Review、P4、P3、P2、P1、Stage051 Review 及更早交接的历史指向；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成 `IDS-V0_1-STAGE053-P1`：以冻结 Stage053 任务包与 Stage052 已复审中英文 OCR 合同为唯一上下文，固化未来按页 OCR 文本、置信度、图片引用、失败原因、默认中英文、低置信度隔离、缓存、审计引用、中文反馈和回滚边界的静态工程合同。
- 未来按页输出固定为 11 个字段：`source_identity_ref`、`source_page_ref`、`page_image_ref`、`ocr_text`、`language_profile`、`confidence_level`、`failure_reason`、`output_status`、`evidence_eligibility`、`cache_ref`、`review_route`。字段只是未来结构，未创建、保存、解释或回显 OCR 文本、图片引用、失败记录、来源正文、真实路径、页面或图片内容。
- 默认语言为中文简体与英文，允许中文简体、英文和中英文混合。未来置信度仅定义 `HIGH`、`MEDIUM`、`LOW`、`UNKNOWN` 四种状态且没有数值阈值；低置信度、中英文混合和失败页均不能直接进入高可信证据层，只声明后续 Stage054 受控复核路由。
- 缓存与审计均为 future reference-only 边界，缓存保留/清理仍归 Stage056；没有创建缓存、audit、manifest、evidence ledger、report、数据库或持久状态。没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容；没有打开样本、调用 OCR、图像处理、语言检测、创建实际按页输出/图片引用/失败记录、复核、质量门、本地服务、OVH 或生产运行；运行时保持零 Agent、零模型 Token。
- 回滚只撤回本 P1 说明、静态合同、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `STAGE052_REVIEWED_LOCAL_BILINGUAL_OCR_RUNTIME_DISABLED`；真实资料、既有证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 已验证：Stage053 P1 聚焦用例 `8/8`、Stage052 Review 与 P1--P4 前序兼容 `53/53`、Stage051 Review 与 P1--P4 前序兼容 `53/53`、BATCH041_050 前序兼容 `6/6`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`，中文事实投影已重渲染 `7` 个文件。
- 下一步只允许在新的独立 run 进入 `IDS-STAGE053-P2`，门为 `IDS-STAGE053-P2-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage052 Review - 2026-08-13

- 本节覆盖下方 Stage052 P4、P3、P2、P1、Stage051 Review 及更早交接的历史指向；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成 IDS-V0_1-STAGE052-REVIEW：独立复审 P1--P4 已提交合同与 P3/P4 固定非业务中英文 OCR control 报告的字段形状、双语边界、显式处置、metadata-only 交付、中文人工确认、缓存边界和回滚链。
- 唯一合同上下文是冻结 Stage052 任务包、P1--P4 合同与 Stage051 已复审控制证据。没有建立第二权威事实源，也没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容；复审输出只保留字段数、场景数、处置数、置信度计数、失败计数、复核路由计数和边界结论。
- P1 七字段/八字段/中文简体与英文默认声明、P2 四页显式状态、P3 五类明确处置且静默丢弃为零，以及 P4 的 5 个 metadata-only 样例、HIGH=2、MEDIUM=1、LOW=1、UNKNOWN=1、1 条失败、2 条未排队复核路由和 3 条中文确认提示均已复审；这些 control 汇总不是识别准确率、质量门或实际人工复核结论。
- 缓存保持 IN_MEMORY_REBUILDABLE_NOT_PERSISTED，临时产物数为 0，清理结论为 NO_TEMPORARY_ARTIFACT_CREATED；重跑只重放已提交的控制报告，不扫描、删除或移动目录。没有打开真实样本、调用 OCR、进行图像处理、创建持久队列/按页输出/缓存/复核记录、执行质量门、证据提升、持久状态、本地服务、OVH 或生产运行；运行时保持零 Agent、零模型 Token。
- 回滚只撤回本复审说明、纯内存复审模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 PHASE4_BILINGUAL_OCR_DELIVERY_EVIDENCE_RUNTIME_DISABLED；P1--P4、真实资料、既有证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 已验证：Stage052 Review 聚焦用例 11/11、Stage052 P1--P4 前序兼容 42/42、Stage051 Review 与 P1--P4 前序兼容 53/53、BATCH041_050 前序兼容 6/6；批次检查器返回 PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED，Stage005 治理报告为 valid=true，中文事实投影已重渲染 7 个文件。
- 下一步只允许在新的独立 run 进入 IDS-STAGE053-P1，门为 IDS-STAGE053-P1-GATE。所有上传继续延后，直至完整冻结任务包完成 ACC-STAGE-168。

## Superseded Gate - Stage052 P4 - 2026-08-13

- 本节覆盖下方 Stage052 P3、P2、P1、Stage051 Review 及更早交接的历史指向；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成 `IDS-V0_1-STAGE052-P4`：只从 P3 的五类固定非业务中英文 OCR 质量 control 报告派生五个 metadata-only 交付样例、置信度汇总、一条显式失败清单、两条未排队复核路由证明、质量限制说明、三条中文人工确认提示和缓存重跑说明。
- 唯一合同上下文是冻结 Stage052 任务包、P1--P3 合同与 Stage051 已复审控制证据。没有建立第二权威事实源，也没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容；样例不保留 OCR 文本、业务正文、真实路径、页面图像、表格单元或真实来源内容。
- 五个样例只保留场景、控制页引用、语言、置信度、状态与处置；置信度汇总为 HIGH=2、MEDIUM=1、LOW=1、UNKNOWN=1，不是识别准确率或质量门。低置信和中英文混合 control 只声明 Stage054 后续复核路径，未创建实际任务；失败页显式隔离，所有结果均不能直接进入高可信证据层。
- 缓存保持 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`，临时产物数为 `0`，清理结论为 `NO_TEMPORARY_ARTIFACT_CREATED`；重跑只能在内存中重放 P3 control 报告，不扫描、删除或移动目录。没有打开真实样本、调用 OCR、进行图像处理、创建持久队列/按页输出/缓存/复核记录、执行质量门、证据提升、持久状态、本地服务、OVH 或生产运行；运行时保持零 Agent、零模型 Token。
- 回滚只撤回 Stage052 P4 说明、交付合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `PHASE3_BILINGUAL_CONTROLLED_QUALITY_SCENARIOS_ENGINE_DISABLED`；真实资料、既有证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 已验证：Stage052 P4 聚焦用例 `14/14`、Stage052 P3/P2/P1 与 Stage051 Review 前序兼容 `39/39`、Stage051 P1--P4 前序兼容 `42/42`、BATCH041_050 前序兼容 `6/6`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`，中文事实投影已重渲染 `7` 个文件。
- 下一步只允许在新的独立 run 进入 `IDS-STAGE052-REVIEW`，门为 `IDS-STAGE052-REVIEW-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage052 P3 - 2026-08-13

- 本节仅保留 Stage052 P3 的历史交接证据；当前门已转为 Stage052 P4。
- 本轮完成 `IDS-V0_1-STAGE052-P3`：重放 P2 的四页固定非业务纯内存中英文 OCR control 队列，并以扫描 PDF、模糊图片、表格图片、中英文混合和低质量五类标量类别形成候选保留、降级复核提示、表格未评估和显式失败处置；五类均明确，静默丢弃为零。
- 唯一合同上下文是冻结 Stage052 任务包、P1/P2 合同与 Stage051 已复审控制证据。没有建立第二权威事实源，也没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容。质量类别不是文件、页面、图像、表格或真实 OCR 结果；P3 报告不保留 P2 符号化输出、来源正文或 OCR 文本。
- 扫描 PDF 与表格图片 control 仅为未评估候选；英文低置信和中英文混合 control 均显式降级为后续 `Stage054` 复核路径但未创建复核任务；低质量 control 显式失败，全部都不能直接进入高可信证据层。没有形成真实识别准确率或表格提取结论。
- 缓存保持 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`，临时产物数为 `0`，因此清理结论为 `NO_TEMPORARY_ARTIFACT_CREATED`；实际保留、容量与清理所有权仍归 Stage056。本轮没有打开真实样本、调用 OCR、进行图像处理、创建持久队列/按页输出/缓存/复核记录、执行质量门、证据提升、持久状态、本地服务、OVH 或生产运行；运行时保持零 Agent、零模型 Token。
- 回滚只撤回 Stage052 P3 说明、场景合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `PHASE2_BILINGUAL_CONTROLLED_QUEUE_SLICE_ENGINE_DISABLED`；真实资料、既有证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 已验证：Stage052 P3 聚焦用例 `11/11`、Stage052 P2/P1 与 Stage051 Review 前序兼容 `28/28`、Stage051 P1--P4 前序兼容 `42/42`、BATCH041_050 前序兼容 `6/6`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`，中文事实投影已重渲染 `7` 个文件。
- 下一步只允许在新的独立 run 进入 `IDS-STAGE052-P4`，门为 `IDS-STAGE052-P4-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage052 P2 - 2026-08-13

- 本节仅保留 Stage052 P2 的历史交接证据；当前门已转为 Stage052 P3。
- 本轮完成 `IDS-V0_1-STAGE052-P2`：在 P1 静态合同上，以四个固定非业务控制页实现纯内存中英文 OCR 队列记录、符号化八字段逐页结构、内存派生来源页引用、置信度和低置信/失败/中英混合可解释状态。
- 唯一合同上下文是冻结 Stage052 任务包、P1 静态合同与 Stage051 已复审合同/控制证据。没有建立第二权威事实源，也没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容。三个符号化控制输出只验证结构，不是 OCR 识别文本、来源正文或真实页面内容。
- 控制输入保持七字段 reference-only 合同；四个控制页只覆盖中文简体候选、英文低置信、中英混合和显式失败。低置信、失败和中英文混合均不能直接进入高可信证据层，当前未创建实际复核任务，后续实际复核仍归 Stage054。
- 缓存固定为仅内存可重建且未持久化，保留与清理所有权仍归 Stage056。本轮只返回内存值；没有创建真实队列、持久按页输出、缓存、复核记录、质量门、证据提升、持久状态、本地服务、OVH 或生产运行；运行时保持零 Agent、零模型 Token。
- 回滚只撤回 Stage052 P2 说明、切片合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `PHASE1_BILINGUAL_OCR_BOUNDARY_RUNTIME_DISABLED`；真实资料、既有证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 已验证：Stage052 P2 聚焦用例 `9/9`、Stage052 P1 与 Stage051 Review 前序兼容 `19/19`、Stage051 P1--P4 前序兼容 `42/42`、BATCH041_050 前序兼容 `6/6`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`，中文事实投影已重渲染 `7` 个文件。
- 下一步历史路线为 `IDS-STAGE052-P3-GATE`；该路线已在本轮关闭。

## Superseded Gate - Stage052 P1 - 2026-08-13

- 本节仅保留 Stage052 P1 的历史交接证据；当前门已转为 Stage052 P2。
- 本轮完成 `IDS-V0_1-STAGE052-P1`：在 Stage051 已复审 OCR 队列基线上，定义中文简体、英文和中英文混合页面的 reference-only 输入、八字段按页输出引用、低置信/混合语言隔离、缓存边界与后续复核路由。
- 唯一合同上下文是冻结 Stage052 任务包与 Stage051 已复审合同/控制证据。没有建立第二权威事实源，也没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容；本步骤不返回 OCR 文本。
- 默认语言为中文简体和英文，允许中文简体、英文及中英文混合三种语言档案。未选择或配置 OCR 引擎，也未进行语言检测；低置信和中英文混合页面均不能直接进入高可信证据层，后续仅声明为 Stage054 受控复核路由。
- 缓存仅声明为 Stage056 负责的可重建派生产物。本轮没有创建队列、按页输出、缓存、复核记录、质量门、证据提升、持久状态、本地服务、OVH 或生产运行；运行时保持零 Agent、零模型 Token。
- 回滚只撤回 Stage052 P1 范围说明、静态合同、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `STAGE051_REVIEWED_LOCAL_OCR_QUEUE_RUNTIME_DISABLED`；真实资料、既有证据、运行状态、GitHub、OVH 与应用状态不在回滚范围内。
- 已验证：Stage052 P1 聚焦用例 `8/8`、Stage051 Review 前序兼容 `11/11`、Stage051 P1--P4 前序兼容 `42/42`、BATCH041_050 前序兼容 `6/6`；批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`，中文事实投影已重渲染 `7` 个文件。
- 下一步只允许在新的独立 run 进入 `IDS-V0_1-STAGE052-P2`，门为 `IDS-STAGE052-P2-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage051 Review - 2026-08-13

- 本节仅保留 Stage051 Review 的历史交接证据；当前门已转为 Stage052 P1。
- 本轮完成 `IDS-V0_1-STAGE051-REVIEW`：独立复审 P1--P4 已提交合同与固定非业务控制报告的字段形状、明确处置、metadata-only 交付、中文确认、缓存边界和 P4→P3→P2→P1→BATCH041_050 回滚链。
- 唯一合同上下文是冻结的 Stage051 任务包、P1--P4 工件与 BATCH041_050 已完成本地复审工件；没有建立第二权威事实源，也没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容。复审输出只保留字段数、场景数、处置数、置信度计数、失败计数、复核路由计数和边界结论。
- P1 七字段/八字段/中英文默认声明、P2 四页显式状态、P3 五类明确处置且静默丢弃为零，以及 P4 的 5 个 metadata-only 样例、HIGH=2/MEDIUM=1/LOW=1/UNKNOWN=1、1 条失败、2 条未排队复核路由和 3 条中文确认提示均已复审；这些 control 汇总不是识别准确率、质量门或实际人工复核结论。
- 缓存保持仅内存可重建且临时产物数为 0；运行时继续为零 Agent、零模型 Token，未打开真实资料，未调用 OCR 引擎，未创建持久队列、缓存、复核记录、本地服务、OVH、生产、上传、推送或应用重装。
- 回滚只撤回本复审说明、复审模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `PHASE4_OCR_QUEUE_DELIVERY_EVIDENCE_RUNTIME_DISABLED`；必须保留 P1--P4、已复审证据、冻结任务包和历史交接。
- 已验证：Stage051 Review 聚焦用例 `11/11`、P1--P4 前序兼容 `42/42`、BATCH041_050 前序兼容 `6/6`，批次检查器返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`，Stage005 治理报告为 `valid=true`，中文事实投影已重渲染 `7` 个文件。
- 下一步只允许在新的独立 run 进入 `IDS-V0_1-STAGE052-P1`，门为 `IDS-STAGE052-P1-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - Stage051 P4 - 2026-08-13

- 本节仅保留 Stage051 P4 的历史交接证据；当前门已转为 Stage051 Review，下一门为 Stage052 P1。
- 本轮完成 IDS-V0_1-STAGE051-P4：只从 P3 五类固定非业务标量 control 报告派生 5 个 metadata-only 交付样例、置信度汇总、1 条显式失败、2 条未排队复核路由证明、质量限制、3 条中文人工确认提示和缓存重跑说明。
- 唯一合同上下文是冻结的 Stage051 任务包、P1--P3 工件与 BATCH041_050 已完成本地复审工件；没有建立第二权威事实源，也没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容。
- 交付样例不包含 OCR 文本、业务正文、真实路径、页面图像、表格单元或真实 OCR 输出；HIGH=2、MEDIUM=1、LOW=1、UNKNOWN=1 仅是 control 汇总，不是识别准确率或质量门。低置信与中英文混合仅声明 Stage054 后续复核路由，未创建实际复核任务或提升高可信证据。
- 缓存保持仅内存可重建且临时产物数为 0；清理结论为 NO_TEMPORARY_ARTIFACT_CREATED，不扫描、删除或移动目录。运行时继续为零智能体、零模型 Token，未打开真实资料，未调用 OCR 引擎，未创建持久队列、缓存、复核记录、本地服务、OVH、生产、上传、推送或应用重装。
- 回滚只撤回 Stage051 P4 说明、交付合同、纯内存模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 PHASE3_CONTROLLED_OCR_QUALITY_SCENARIOS_ENGINE_DISABLED；必须保留 P1--P3、已复审证据、冻结任务包和历史交接。
- 已验证：Stage051 P4 聚焦用例 14/14、Stage051 P3 前序兼容 11/11、Stage051 P2 前序兼容 9/9、Stage051 P1 前序兼容 8/8、BATCH041_050 前序兼容 6/6，Stage005 治理报告为 valid=true。
- 后续历史路线曾为 `IDS-STAGE051-REVIEW-GATE`；该路线已在本轮关闭。

## Superseded Gate - Stage051 P3 - 2026-08-13

- 本节覆盖下方 Stage051 P2/P1、BATCH041_050 Review 与 Stage050 Review 的当前指向；下方未特别标为当前的内容仅保留为历史阶段证据。
- 本轮完成 `IDS-V0_1-STAGE051-P3`：仅重放 P2 的四页固定非业务控制队列，以扫描 PDF、模糊图片、表格图片、中英文混合与低质量五类标量类别验证候选保留、降级复核提示、显式失败与零静默丢弃的受控处置。
- 唯一合同上下文是冻结的 Stage051 任务包、P1/P2 工件与 BATCH041_050 已完成本地复审工件；没有建立第二权威事实源，也没有读取 IDS 业务源、原始元数据、正文、文件路径、真实 PDF、图像、页面或表格内容。
- 当前工件为 P3 说明、场景合同、纯内存场景模块、聚焦单元用例、BATCH051_060 锁、machine run、事件、治理路线和机器事实。五类类别是控制标签，不是 OCR 识别准确率、表格提取、真实人工复核或真实缓存清理的结论；低置信、混合语言和失败页不能直接进入高可信证据层，后续实际复核所有权仍归 Stage054。
- 未选择或调用 OCR 引擎，未打开真实 PDF 或图片，未创建持久队列、持久按页输出、缓存、实际复核记录、质量门、证据提升、持久状态、智能体、模型调用、本地服务、OVH、生产运行、上传、推送或应用重装。缓存结果固定为仅内存可重建、未持久化，临时产物数为 `0`；运行时保持零智能体、零模型 Token。
- 回滚只撤回 Stage051 P3 说明、场景合同、纯内存场景模块、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `PHASE2_CONTROLLED_OCR_QUEUE_SLICE_ENGINE_DISABLED`；必须保留 P1/P2、已复审证据、冻结任务包和历史交接。
- 已验证：Stage051 P3 聚焦用例 `11/11`、Stage051 P2 前序兼容用例 `9/9`、Stage051 P1 前序兼容用例 `8/8`、BATCH041_050 前序兼容用例 `6/6`，Stage005 治理报告为 `valid=true`；中文事实投影已重渲染 `7` 个文件。
- 下一步仅允许在新的独立 run 进入 `IDS-V0_1-STAGE051-P4`，门为 `IDS-STAGE051-P4-GATE`。所有上传继续延后，直至完整冻结任务包完成 `ACC-STAGE-168`。

## Superseded Gate - BATCH041_050 Review - 2026-08-12

- 本轮完成 `IDS-V0_1-BATCH-041-050-REVIEW-GATE`，结论为 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`：十个既有整阶段复审工件、Stage041→050 责任链、治理路线、中文事实投影和回滚边界均已独立核验。
- 唯一事实来源仍为冻结任务包、既有复审证据及当前治理投影；没有建立第二权威事实源，也没有读取 IDS 业务源、原始元数据、正文、文件路径或来源内容。
- 历史验证：批次聚焦用例 `6/6`、治理回归 `178/178`、治理报告 `valid=true`、批次检查器 `review_valid=true` 且复审阶段数为 `10`，中文事实投影已渲染 `7` 个文件且双平面检查通过。
- 未执行文件检测、真实路线、parser、fallback、质量门、持久化、Agent、模型调用、本地服务、OVH、生产运行、批次上传、GitHub 上传、推送或应用重装。运行时保持零 Agent、零模型 Token。
- 回滚仅撤回本批次复审说明、合同、检查器、聚焦用例、machine run、事件、事实投影、治理状态和生成中文视图；必须保留 Stage041--050 的既有证据、任务包投影、审计记录和历史交接。

## Superseded Gate - Stage050 Review - 2026-08-12

- 本节覆盖下方的 Stage050 P4 历史交接；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成任务：`IDS-V0_1-STAGE050-REVIEW`。当前状态为 `STAGE050_REVIEWED_LOCAL_PROMPT_INJECTION_MARKER_RUNTIME_DISABLED`：独立重放 P1--P4 合同、P2 evidence-only 标记、P3 的 11 个格式标签化 control 场景，以及 P4 的 8 个 parser 输出结构样例、11 条非运行时处置记录、质量指标和五类失败分类。
- 唯一合同上下文仍是冻结的 Stage050 任务包文本、Stage050 P1--P4 合同与 Stage049 已复审工件；没有建立第二权威事实源，也没有保留业务正文、文件路径、来源引用、原始异常或原始元数据内容。复审样例只含空的 `text/tables/pages/sections` 结构和受控版本、置信度、处置标签。
- 复审确认 11/11 场景均明确处置、静默丢弃为零；指令样 control 只作 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`，不能成为系统规则、工具授权或策略覆盖。所有候选仍为 `CANDIDATE`，质量状态仍为 `UNASSESSED`，没有创建人工复核任务、自动 fallback 或高可信证据。
- 控制格式标签为 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF；运行时支持格式集合为空。control-fixture parser 版本仅作交付证据，不是运行时 parser 版本；Stage045 仍拥有文件检测，Stage046 仍拥有真实路由，Stage048 仍拥有 fallback，复审没有改写任何上游结论。
- 回滚只撤回 Stage050 复审文档、模块、聚焦用例、machine run、事件、事实投影和治理状态，恢复为 P4 待复审；必须保留 P1--P4 证据、原始资料、manifest、evidence ledger、audit 与已交付报告。
- 聚焦 Stage050 复审直接单元用例通过 `10/10`，P1--P4 前序兼容用例通过 `39/39`，Stage049 P1--P4 及复审前序兼容用例通过 `47/47`，Stage048 P1--P4 及复审前序兼容用例通过 `48/48`，治理回归报告为 `valid=true`。根项目与相邻白箱项目的双平面检查通过；根项目“执行与验收”投影为 `50/100` 行。证据为复审范围说明、复审实现、聚焦用例、本轮 machine run、event、batch/roadmap、机器事实与生成的中文视图。
- 未读取 IDS 业务源或原始元数据；未执行文件识别、真实路线、真实 parser、解析正文比较、真实 fallback、运行时提示注入标记、人工复核队列、质量门、证据提升、持久化、Agent、模型调用、本地服务、OVH 部署、生产激活、Stage051、批次复审、上传或推送。
- 下一步仅允许在独立 run 进入 `IDS-V0_1-BATCH-041-050-REVIEW-GATE`。Stage050 本地复审完成不等于真实标记应用、解析器运行、实际解析质量、OVH 部署、生产就绪或 GitHub 上传。

## Superseded Gate - Stage050 P4 - 2026-08-12

- 本节覆盖下方的 Stage050 P3 历史交接；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成任务：`IDS-V0_1-STAGE050-P4`。当前状态为 `PHASE4_PROMPT_INJECTION_MARKER_CLOSEOUT_EVIDENCE_ENABLED_REAL_PARSER_QUALITY_AND_PERSISTENCE_DISABLED`：只从 P3 的 11 个固定非业务、格式标签化 control 场景派生 8 个 parser 输出结构样例、11 条非运行时处置记录、质量指标、五类互斥失败分类、格式边界和 parser 配置回滚说明。
- 唯一合同上下文是冻结的 Stage050 任务包、P1--P3 合同与 Stage049 已复审工件；没有建立第二权威事实源，也没有打开或保留业务正文、文件路径、来源引用、原始异常、原始元数据、图像页面或真实解析输出。结构样例只含空的 `text/tables/pages/sections`、受控置信度、错误标签和处置标签。
- 8 个结构样例覆盖 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF；11/11 场景均有明确处置、静默丢弃为零。六项候选只保留 evidence-only 结构，两项低质量 control 仅记录未排队复核，指令样 TXT 继续为 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`，未知与坏输入保持明确关闭。
- control-fixture parser 版本仅是交付证据，不是运行时 parser 版本；运行时支持格式集合为空，未创建或改写 parser 配置。Stage048 继续拥有 fallback，Stage050 继续拥有提示注入标记职责；P4 没有改写上游结论。
- 回滚只撤回 Stage050 P4 的结构样例、非运行时处置记录、质量指标、失败分类、合同、聚焦用例、machine run、事件、事实投影和治理状态，恢复为 `PHASE3_CONTROLLED_PROMPT_INJECTION_MARKER_SCENARIOS_RUNTIME_DISABLED`；必须保留 P1--P3 证据、原始资料、manifest、evidence ledger、audit 与已交付报告。
- 聚焦 Stage050 P4 用例通过 `13/13`，Stage050 P1--P3 前序兼容用例通过 `26/26`，Stage049 P1--P4 及复审前序兼容用例通过 `47/47`，Stage048 P1--P4 及复审前序兼容用例通过 `48/48`；治理回归报告为 `valid=true`，中文视图已重渲染 `7` 个文件。证据为 P4 说明、合同、实现、聚焦用例、本轮 machine run、event、batch/roadmap 与机器事实。
- 未读取 IDS 业务源或原始元数据；未执行文件检测、真实路线、真实 parser、解析正文比较、真实 fallback、运行时提示注入标记、人工复核队列、质量门、证据提升、持久化、Agent、模型调用、本地服务、OVH 部署、生产激活、整阶段复审、批次复审、上传或推送。
- 下一步仅允许在独立 run 进入 `IDS-V0_1-STAGE050-REVIEW`，门为 `IDS-STAGE050-REVIEW-GATE`。P4 收口证据完成不等于真实标记应用、解析器运行、实际解析质量、OVH 部署、生产就绪或 GitHub 上传。

## Superseded Gate - Stage050 P3 - 2026-08-12

- 本节覆盖下方的 Stage050 P2 历史交接；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成任务：`IDS-V0_1-STAGE050-P3`。当前状态为 `PHASE3_CONTROLLED_PROMPT_INJECTION_MARKER_SCENARIOS_RUNTIME_DISABLED`：只重放 P2 的仅内存标记切片，以 11 个固定非业务、格式标签化 control 场景验证明确处置、零静默丢弃、低质量未排队复核与指令样文本规则不变性。
- 唯一合同上下文是冻结的 Stage050 任务包、P1/P2 合同与 Stage049 已复审工件；没有建立第二权威事实源，也没有打开或保留业务正文、文件路径、来源引用、原始异常、原始元数据内容、图像页面或真实解析输出。格式标签不是文件、签名、路线、解析正文或运行时支持声明。
- 场景覆盖 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF、未知、坏输入和指令样文本。11/11 均有明确处置；六项普通 control 维持 `CANDIDATE`/evidence-only，两项低质量 control 返回未排队复核，两项未知或坏输入明确拒绝，指令样 TXT control 固定为 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`。
- Stage045 继续拥有文件类型检测，Stage046 继续拥有 parser 路由，Stage047 继续拥有解析产物结构，Stage048 继续拥有 fallback，Stage049 继续拥有差异评估；P3 没有调用或改写任何上游职责。Stage048 仍是唯一 fallback 所有者，所有场景的 fallback 执行均为 `false`。
- 指令样 control 不能覆盖系统规则、工具授权或策略，也不能改变路线、触发 fallback、绕过质量门或提升为高可信证据。control 文本不返回或持久化；全部结果保持 `CANDIDATE` 与 `UNASSESSED`，无人工复核队列、质量门、证据提升、持久化或实际解析产物。
- 聚焦 Stage050 P3 用例通过 `9/9`，Stage050 P1/P2 前序兼容用例通过 `17/17`，Stage049 P1--P4 及复审前序兼容用例通过 `47/47`，Stage048 P1--P4 及复审前序兼容用例通过 `48/48`；治理回归报告为 `valid=true`，中文视图已重渲染 `7` 个文件。证据为 P3 说明、场景合同、实现、聚焦用例、本轮 machine run、event、batch/roadmap 与机器事实。
- 未读取 IDS 业务源或原始元数据；未执行文件检测、真实路线、真实 parser、解析正文比较、真实 fallback、运行时提示注入标记、人工复核队列、质量门、证据提升、持久化、Agent、模型调用、本地服务、OVH 部署、生产激活、Phase4、整阶段复审、批次复审、上传或推送。
- 回滚只撤回 Stage050 P3 场景模块、合同、聚焦用例、machine run、事件、事实投影和治理状态，恢复为 `PHASE2_CONTROLLED_PROMPT_INJECTION_MARKER_SLICE_RUNTIME_DISABLED`；必须保留真实资料、既有证据、manifest、evidence ledger、audit、已交付报告、GitHub、OVH 和应用状态。
- 下一步仅允许在独立 run 进入 `IDS-V0_1-STAGE050-P4`，门为 `IDS-STAGE050-P4-GATE`。Stage050 P3 场景验证完成不等于真实标记应用、解析器运行、实际解析质量、OVH 部署、生产就绪或 GitHub 上传。

## Superseded Gate - Stage050 P2 - 2026-08-12

- 本节覆盖下方的 Stage050 P1 历史交接；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成任务：`IDS-V0_1-STAGE050-P2`。当前状态为 `PHASE2_CONTROLLED_PROMPT_INJECTION_MARKER_SLICE_RUNTIME_DISABLED`：仅在内存中处理两个固定非业务 control 文本和 P1 的七字段 reference-only 候选元数据，记录 control-fixture parser 版本与解析置信度，不创建实际解析产物。
- 唯一合同上下文是冻结的 Stage050 任务包、P1 静态边界与 Stage049 已复审工件；没有建立第二权威事实源，也没有保留业务正文、文件路径、来源引用、原始异常、原始元数据内容或真实解析输出。
- Stage045 继续拥有文件类型检测，Stage046 继续拥有 parser 路由，Stage047 继续拥有解析产物结构，Stage048 继续拥有 fallback，Stage049 继续拥有差异评估；P2 不调用或改写任何上游职责。control-fixture parser 元数据只作受控记录，不是实际 parser 配置或执行结果。
- 指令样 control 返回 `CONTROL_INSTRUCTION_TEXT_MARKED_EVIDENCE_ONLY`，普通 control 返回 `CONTROL_EVIDENCE_TEXT_RETAINED_EVIDENCE_ONLY`；二者都固定为 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`，不能覆盖系统规则、工具授权或策略，不能改变路线、触发 fallback、绕过质量门或提升为高可信证据。
- 解析产物事实等级仍为 `CANDIDATE`、质量初始状态仍为 `UNASSESSED`。control 文本不被返回或持久化；非合同输入返回明确中文处置且不回显输入。
- 聚焦 Stage050 P2 用例已通过 `9/9`，Stage050 P1 前序兼容用例通过 `8/8`，Stage049 P1--P4 及复审前序兼容用例通过 `47/47`，Stage048 P1--P4 及复审前序兼容用例通过 `48/48`；治理回归报告为 `valid=true`。证据为 P2 说明、切片合同、实现、聚焦用例、本轮 machine run、event、batch/roadmap 与机器事实。
- 未读取 IDS 业务源或原始元数据；未执行文件检测、真实路线、真实 parser、解析正文比较、真实 fallback、差异评估、运行时提示注入标记、人工复核队列、质量门、证据提升、持久化、Agent、模型调用、本地服务、OVH 部署、生产激活、Phase3、整阶段复审、批次复审、上传或推送。
- 回滚只撤回 Stage050 P2 切片、合同、聚焦用例、machine run、事件、事实投影和治理状态，恢复为 `PHASE1_PROMPT_INJECTION_MARKER_BOUNDARY_RUNTIME_DISABLED`；必须保留真实资料、既有证据、manifest、evidence ledger、audit、已交付报告、GitHub、OVH 和应用状态。
- 下一步仅允许在独立 run 进入 `IDS-V0_1-STAGE050-P3`，门为 `IDS-STAGE050-P3-GATE`。Stage050 P2 仅内存切片完成不等于真实标记应用、解析器运行、实际解析质量、OVH 部署、生产就绪或 GitHub 上传。

## Superseded Gate - Stage050 P1 - 2026-08-12

- 本节覆盖下方的 Stage049 Review 历史交接；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成任务：`IDS-V0_1-STAGE050-P1`。当前状态为 `PHASE1_PROMPT_INJECTION_MARKER_BOUNDARY_RUNTIME_DISABLED`：只定义解析阶段提示注入标记的静态合同，不创建解析产物、不应用标记、不启动任何运行时服务。
- 唯一合同上下文是冻结的 Stage050 任务包文本与 Stage049 已复审工件；没有建立第二权威事实源，也没有保留业务正文、文件路径、来源引用、原始异常、原始元数据内容或真实解析输出。
- Stage045 继续拥有文件类型检测，Stage046 继续拥有 parser 路由，Stage047 继续拥有解析产物结构，Stage048 继续拥有 fallback，Stage049 继续拥有差异评估，Stage050 只定义标记边界；本轮没有改写任何上游结论。
- 未来候选输入只能是七字段 reference-only 元数据，未来解析产物核心字段固定为 `text/tables/pages/sections/confidence/errors`。提示文本固定为 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`：它不能覆盖系统规则、工具授权或策略，也不能绕过质量门、改变路线、触发 fallback 或提升为高可信证据。
- 解析产物事实等级仍为 `CANDIDATE`、质量初始状态仍为 `UNASSESSED`。中文反馈只说明未应用标记、文本不是系统指令、产物仍为候选、质量复核尚未执行；不承诺自动化、人工任务或生产可用。
- 回滚只撤回 Stage050 P1 范围说明、静态合同、聚焦用例、machine run、事件、事实投影和治理状态，恢复为 `STAGE049_REVIEWED_LOCAL_DIFFERENTIAL_EVALUATION_RUNTIME_DISABLED`；必须保留真实资料、既有证据、manifest、evidence ledger、audit、已交付报告、GitHub、OVH 和应用状态。
- 聚焦 Stage050 P1 用例已通过 `8/8`，治理回归报告为 `valid=true`，中文视图已重渲染 `7` 个文件。证据为范围说明、静态合同、聚焦用例、本轮 machine run、event、batch/roadmap 与机器事实。
- 未读取 IDS 业务源或原始元数据；未执行文件检测、真实路线、真实 parser、解析正文比较、真实 fallback、差异评估、提示注入标记、人工复核队列、质量门、证据提升、持久化、Agent、模型调用、OVH 部署、生产激活、Phase2、整阶段复审、批次复审、上传或推送。
- 下一步仅允许在独立 run 进入 `IDS-V0_1-STAGE050-P2`，门为 `IDS-STAGE050-P2-GATE`。Stage050 P1 静态合同完成不等于真实标记应用、解析器运行、实际解析质量、OVH 部署、生产就绪或 GitHub 上传。

## Superseded Gate - Stage049 Review - 2026-08-12

- 本节覆盖下方的 Stage049 P4 历史交接；下方未特别标为当前的内容只保留为阶段证据。
- 本轮完成任务：`IDS-V0_1-STAGE049-REVIEW`。当前状态为 `STAGE049_REVIEWED_LOCAL_DIFFERENTIAL_EVALUATION_RUNTIME_DISABLED`：独立重放 P1--P4 合同、P2 双候选资格、P3 的 11 个格式标签化 control 场景，以及 P4 的 20 个候选解析产物结构样例、11 条非运行时处置记录、质量指标和五类失败分类。
- 唯一合同上下文仍是冻结的 Stage049 任务包文本、Stage049 P1--P4 合同与 Stage048 已复审工件；没有建立第二权威事实源，也没有保留业务正文、文件路径、来源引用、原始异常或原始元数据内容。复审样例只含空的 `text/tables/pages/sections` 结构和受控版本、置信度、处置标签。
- 复审确认 11/11 场景均明确处置、静默丢弃为零；六项候选保留于质量边界、三项低质量 control 均不进入队列、指令样文本只作 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`、未知与坏文件控制维持明确关闭。所有候选仍为 `CANDIDATE`，质量状态仍为 `UNASSESSED`，没有创建人工复核任务、自动 fallback 或高可信证据。
- 控制格式标签为 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF；运行时支持格式集合为空。control-fixture parser 版本仅作交付证据，不是运行时 parser 版本；Stage046 仍拥有真实路由，Stage048 仍拥有 fallback，Stage050 仍拥有提示注入标记，复审没有改写任何上游结论。
- 回滚只撤回 Stage049 复审文档、模块、聚焦用例、machine run、事件、事实投影和治理状态，恢复为 P4 待复审；必须保留 P1--P4 证据、原始资料、manifest、evidence ledger、audit 与已交付报告。
- 聚焦 Stage049 复审直接单元用例通过 `10/10`，P1--P4 前序兼容用例通过 `37/37`，Stage048 P1--P4 及复审前序兼容用例通过 `48/48`，治理回归报告为 `valid=true`。证据为复审范围说明、复审实现、聚焦用例、本轮 machine run、event、batch/roadmap、机器事实与生成的中文视图。
- 未读取 IDS 业务源或原始元数据；未执行文件识别、真实路线、真实 parser、解析正文比较、真实 fallback、提示注入标记、运行时日志、人工复核队列、质量门、证据提升、持久化、Agent、模型调用、OVH 部署、生产激活、Stage050、批次复审、上传或推送。
- 下一步仅允许在独立 run 进入 `IDS-V0_1-STAGE050-P1`，门为 `IDS-STAGE050-P1-GATE`。Stage049 本地复审完成不等于真实路由、解析器运行、实际解析质量、OVH 部署、生产就绪或 GitHub 上传。

## Superseded Gate - Stage049 P4 - 2026-08-12

- 本节覆盖下方较早的“Current Gate”和 GitHub handoff 对当前任务的指向；下方未特别标为当前的内容只保留为历史交接证据。
- 本轮完成任务：`IDS-V0_1-STAGE049-P4`。当前状态为 `PHASE4_DIFFERENTIAL_EVALUATION_CLOSEOUT_EVIDENCE_ENABLED_REAL_PARSER_QUALITY_AND_PERSISTENCE_DISABLED`：从 P3 的 11 个格式标签化、reference-only control 场景派生 20 个候选解析产物结构样例、11 条非运行时处置记录、质量指标、五类失败分类、格式边界和回滚说明；它们不是文件、文件签名、真实路线、真实 parser 或解析正文。
- 唯一合同上下文仍是冻结的 Stage049 任务包文本、Stage049 P1--P3 合同与 Stage048 已复审工件；没有建立第二权威事实源，也没有保留业务正文、文件路径、来源引用、原始异常或原始元数据内容。所有样例只含空的 `text/tables/pages/sections` 结构和受控版本、置信度、处置标签。
- P4 交付保留 11/11 明确处置、静默丢弃为零；6 项候选保留于质量边界、2 项常规低质量 control 保持未排队复核、1 项指令样文本继续只是 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`、未知与坏文件控制维持明确关闭。所有候选仍为 `CANDIDATE`，质量状态仍为 `UNASSESSED`，没有创建人工复核任务、自动 fallback 或高可信证据。
- 控制格式标签为 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF；运行时支持格式集合为空。control-fixture parser 版本仅作交付证据，不是运行时 parser 版本；Stage046 仍拥有真实路由，Stage048 仍拥有 fallback，Stage050 仍拥有运行时提示注入标记，P4 没有改写任何上游结论。
- 回滚只撤回 Stage049 P4 的结构样例、非运行时处置记录、质量指标、失败分类、合同、范围说明、聚焦用例、machine run 和治理投影，回到 `PHASE3_CONTROLLED_DIFFERENTIAL_SCENARIOS_RUNTIME_DISABLED`；必须保留 P1--P3、既有阶段工件、原始资料、manifest、evidence ledger、audit 与已交付报告。
- 聚焦 Stage049 P4 直接单元用例通过 `13/13`，P1--P3 前序兼容用例通过 `24/24`，Stage048 P1--P4 及复审前序兼容用例通过 `48/48`，治理回归报告为 `valid=true`。证据为 P4 范围说明、交付合同、交付实现、聚焦用例、本轮 machine run、event、batch/roadmap、机器事实与生成的中文视图。
- 未读取 IDS 业务源或原始元数据；未执行文件识别、真实路线、真实 parser、解析正文比较、真实 fallback、提示注入扫描、运行时日志、人工复核队列、质量门、证据提升、持久化、Agent、模型调用、OVH 部署、生产激活、Stage049 整阶段复审、批次复审、上传或推送。
- 下一步仅允许在独立 run 进入 `IDS-V0_1-STAGE049-REVIEW`，门为 `IDS-STAGE049-REVIEW-GATE`。Stage049 P4 交付证据完成不等于真实路由、解析器运行、实际解析质量、OVH 部署、生产就绪或 GitHub 上传。

## Final GitHub Handoff - 2026-07-26

- Owner explicitly ended this thread and authorized a final GitHub handoff of all existing KMIDS progress, the taskpack and key iteration information.
- Owner then explicitly corrected the destination to `main`: existing PR [LinzeColin/KMOS #193](https://github.com/LinzeColin/KMOS/pull/193) is only the gated merge channel, and final cleanup must leave no open PR, remote task branch or issue created by this delivery. This follow-up supersedes the earlier Draft-only restriction after CI passes; it still does not authorize Stage048 entry, production activation or app reinstall.
- The branch preserves all Stage041–047 commits. `BATCH041_050` remains `7/10`; Stage048–050 and the ten-stage batch review have not started.
- Latest observed `origin/main` is `12d6fa9f46786387ee21d9bd3c682175464f3554`; merge base is `0495b8482b78ff937a92ee061c92980bcbde173b`. Before final handoff commits the branch was 38 commits ahead and 108 behind, so final integration must use GitHub's current merge context and pass CI before merge.
- The approved taskpack was imported as 183 byte-exact UTF-8 text files under `docs/taskpacks/IDS_v0_1_Final_Chinese_Revised/`; the ZIP itself, raw metadata, private data and runtime outputs were not committed. Source/provenance, checksums and iteration recommendations are in `docs/taskpacks/`.
- GitHub full-repo dual-plane CI was blocked only by `KM_IDSystem/搜标项目/文档/05_执行与验收.md` using this branch's newer shared parent renderer. After explicit Owner approval, the final-delivery commit refreshes that exact one-line projection and passes both nested-project and KMIDS dual-plane checks locally; GitHub CI must still pass before merge.
- Read `docs/FINAL_THREAD_HANDOFF_20260726.md` for the concise state, validation, unresolved risks and next-run instructions.
- After remote verification, this thread's local worktree is to be retired. The shared main checkout must remain clean on `main`; no `git gc --prune=now` is permitted.

## Current Gate - 2026-07-24

- Completed task in this run: `IDS-V0_1-STAGE047-REVIEW`. The independent whole-stage review live-rehashed the approved archive, unique Stage047 member, roadmap and instructions; rebound immutable Phase4 commit `007ef85e6ee30e155269284dc9c0fe89572c8161`, exact root/KMIDS trees, parent, HEAD ancestry and five Phase4 artifact hashes; and replayed Phase1-4.
- Six findings are repaired and machine-checked: `2 Critical / 4 Important / 0 Minor`. The current six-field input wrapper completes request/result/source lineage; unencodable Unicode rejects structurally; canonical refs use lower-ASCII token segments; table/page/section graphs are reciprocal; route/error text is exact and bounded; and `produced_at >= requested_at`.
- The committed Phase1 five-field snapshot remains historical evidence. The current Phase1 contract and Phase2 runtime contract explicitly distinguish that immutable snapshot from the review repair; no history was rewritten.
- Stage047 is `completed_reviewed_local`; `ACC-STAGE-047` is closed locally. The only next task is `IDS-V0_1-STAGE048-P1`, behind `IDS-STAGE048-P1-GATE` and only in a separate future run.
- Next allowed task: `IDS-V0_1-STAGE048-P1`; this is a forward route only, not evidence that Stage048 started in this run.
- Review evidence is `STAGE047_STAGE_REVIEW.md`, `check_parser_output_stage_review.py`, repair/final tests, the review machine run, event, batch/roadmap state, machine facts and rendered owner views. Any source, Phase4 binding, phase replay, finding, governance or Git-index mismatch returns `FAIL_CLOSED` to `IDS-STAGE047-REVIEW-GATE`.
- No IDS business source, raw metadata, actual route/parser, fallback, quality gate, evidence promotion, persistence, Stage048, batch review, GitHub action or app reinstall ran. `BATCH041_050` remains locked with seven of ten stages locally reviewed; `push_allowed=false`.
- Final GREEN passed Stage047 focused `72/72`, Stage005 `178/178`, Stage041-047 aggregate `485/485` in `1261.140s`, full IDS v0.1 discovery `1241/1241` in `1689.670s`, all ten Stage038-047 review checkers, `230` unique events, idempotent seven-document owner rendering and project dual-plane. Exact historical repairs only add the current `Stage047 Review -> Stage048 P1 Gate`; failed runs are not counted as PASS. Root governance remains `SPARSE_CONFLICT` because sparse checkout omits root `scripts/lean_governance.py`; do not expand other projects.
- Historical Stage047 Phase4 transition only follows below. Its `P4 -> REVIEW` route is no longer the current gate.

- Completed task in this run: `IDS-V0_1-STAGE047-P4`. The approved source and immutable Phase3 predecessor commit `595a507519b443faa49fca9fa0a6e8bd21cb9dde`, root tree `65a4db060a67ffbb4e7007b25d0dd453fbdbfc88`, KMIDS tree `d0e7058864e6669abcf213cf8c9defe4d57c6fa5`, parent and five Phase3 artifacts were live-rehashed across commit, index and working tree.
- `ids.stage047.parser_output.phase4.delivery.v1` replays all 16 committed control scenarios and derives eight `RECOMPUTED_SANITIZED_CONTROL_OUTPUT_NOT_RUNTIME` projections plus 16 `DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME` records. No fixture text, table cell, page/section text, formula value, raw exception, path, secret or credential is retained.
- Exact metrics remain 11 accepted, 3 rejected and 2 route-no-output results; output states are 6 candidate, 4 partial and 1 failed, with 11 unique output identities, 16 explicit dispositions and zero silent drops. Seven disjoint failure classes cover all ten non-candidate or failed scenarios.
- The eight control formats are explicitly separated from an empty runtime-supported-format set. Output-schema, normalizer and fixture-only parser versions are recorded, no parser configuration changed, and rollback removes only Phase4 artifacts/governance while returning to committed Phase3.
- Next allowed task: `IDS-V0_1-STAGE047-REVIEW`, only in a separate future run behind `IDS-STAGE047-REVIEW-GATE`; `stage_review_entry_authorized=false`, `NO_STAGE_REVIEW_THIS_RUN`, `NO_STAGE048_THIS_RUN`, `NO_BATCH_REVIEW_THIS_RUN`, `NO_GITHUB_UPLOAD`, `NO_APP_REINSTALL`.
- Phase4 evidence is `STAGE047_PHASE4_CLOSEOUT.md`, `parser_output/stage047_parser_output_delivery_contract.json`, `check_parser_output_delivery.py`, focused tests and the Phase4 machine run; any source, Phase3 snapshot, projection, log, metric, classification, boundary, governance or side-effect mismatch returns `FAIL_CLOSED` to `IDS-STAGE047-P4-GATE`.
- TDD RED recorded 13 tests with 16 expected failures and one expected missing-checker error. Core implementation passed 12/13; the sole remaining failure was the expected P4-to-review governance transition. Final layered validation is recorded in the Phase4 machine run and changelog.
- Final GREEN passed focused P4 `13/13`, Phase1-4 `58/58`, Stage005 `178/178`, Stage041-047 aggregate `471/471` in `1192.255s`, and full IDS v0.1 discovery `1227/1227` in `1590.578s`; all nine Stage038-046 review checkers, `229` unique event semantics, idempotent seven-document owner rendering and project dual-plane also pass. Root governance remains `SPARSE_CONFLICT` without sparse expansion.
- The initial aggregate failed 20 checks from six exact historical forward-route gaps plus expected unstaged index binding. The initial full discovery passed `1223/1227`; its four failures were three Stage038 next-gate allowlists and one Stage039 phase-to-gate map ending at P3. Repairs add only exact `P4 -> REVIEW-GATE` compatibility and do not weaken historical review or runtime-safety evidence.
- No IDS business source, raw metadata, actual business route evaluation, runtime parser selection/dispatch/execution, IDS business parser output, fallback attempt/execution/log, differential evaluation, prompt-injection scanner, formula, quality gate, evidence promotion, persistence, whole-stage review, Stage048, GitHub or app action ran. `BATCH041_050` remains locked with six reviewed Stages plus Stage047 Phase1-4 only.
- Historical Stage047 Phase3 transition only: Completed task in this run: `IDS-V0_1-STAGE047-P3`; Next allowed task: `IDS-V0_1-STAGE047-P4`. This is not the current gate.
- Historical Phase3 evidence records 16 bounded format-labelled controls, 11/3/2 dispositions, 6/4/1 output states, 11 unique identities, zero silent drops, instruction-route invariance and formula-text preservation without runtime parsing, fallback, quality evaluation or persistence.
- Historical Stage047 Phase2 transition only: completed task was `IDS-V0_1-STAGE047-P2`; its next allowed task was `IDS-V0_1-STAGE047-P3`. This is not the current gate.
- Historical Stage047 Phase1 transition only: completed task was `IDS-V0_1-STAGE047-P1`; its next allowed task was `IDS-V0_1-STAGE047-P2`. This is not the current gate.
- Historical Stage046 review transition only: Completed task in that run: `IDS-V0_1-STAGE046-REVIEW`. The independent review live-rehashed the approved sources, rebound Phase4 commit `5dee024cd44e2e772776487ee21761f274c7708e` and its exact trees/parent/ancestry, replayed Phase1-4 and repaired all six findings.
- The repaired route contract has a result-level projection digest, sanitized invalid results, canonical non-path references, action-specific fact levels and exact Phase3 PASS invariants. The digest is integrity-only, not external provenance, source authentication or runtime authorization.
- Historical Stage046 review next task only: Next allowed task was `IDS-V0_1-STAGE047-P1`, behind `IDS-STAGE047-P1-GATE`; this is not the current gate.
- Stage046 is `completed_reviewed_local`, but parser/fallback runtime, source I/O, persistence, upload and production activation remain disabled. Six of ten stages in BATCH041_050 are locally reviewed; the batch remains locked.
- Review evidence is `STAGE046_STAGE_REVIEW.md`, `check_parser_routing_stage_review.py`, repair/final tests and the review machine run; any source, Phase4 binding, phase replay, finding, governance or Git-index mismatch returns `FAIL_CLOSED` to `IDS-STAGE046-REVIEW-GATE`.
- Historical Stage046 Phase4 transition only: Completed task in this run: `IDS-V0_1-STAGE046-P4`. The approved sources were live-rehashed; Phase3 commit `49b876ec68ec8f92f0b9df72d57cca7b2d1d3344`, its trees, parent and five indexed artifacts were rebound.
- `ids.stage046.parser_routing.phase4.delivery.v1` derives six schema-only parser-output samples, fourteen non-runtime fallback control logs, exact quality metrics and five fail-closed classifications from all fourteen Phase3 controls; no business content enters the artifacts.
- Every output is `SCHEMA_ONLY_NOT_EXECUTED`, every parser version is `UNASSIGNED_NOT_IMPLEMENTED`, and every fallback record is `DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME` with zero attempts, silent drops or parser switches; Stage047/048/049/050 ownership is unchanged.
- Historical Stage046 Phase4 next task only: Next allowed task: `IDS-V0_1-STAGE046-REVIEW`, behind `IDS-STAGE046-REVIEW-GATE`; this is not the current gate.
- Phase4 evidence is `STAGE046_PHASE4_CLOSEOUT.md`, the delivery contract/checker/tests and machine run; any source, Phase3 snapshot, evidence, governance or side-effect mismatch returns `FAIL_CLOSED` to `IDS-STAGE046-P4-GATE`.
- Historical Stage045 review compatibility assertion only: Completed task in this run: `IDS-V0_1-STAGE045-REVIEW`; Next allowed task: `IDS-V0_1-STAGE046-P1`. This is not the current run or gate.
- Historical Stage044 review compatibility assertion only: Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`; Next allowed task: `IDS-V0_1-STAGE045-P1`. This is not the current run or gate.
- Final GREEN passed Phase4 `13/13`, Phase1-4 `56/56`, Stage005 `174/174`, Stage041-046 aggregate `399/399`, full IDS v0.1 discovery `1151/1151`, eight historical review checkers, `224` unique event semantics, idempotent owner rendering and project dual-plane; root governance remains `SPARSE_CONFLICT` without sparse expansion.
- Historical Stage046 Phase3 transition only: Completed task in this run: `IDS-V0_1-STAGE046-P3`; Next allowed task: `IDS-V0_1-STAGE046-P4`. This is not the current gate; the current gate is Stage046 whole-stage review.
- Historical Phase3 evidence: the approved archive,
  unique Stage046 member, roadmap and instructions were live-rehashed; Phase2
  commit `18c45ee39522891abe4ef65ed609eb5482f2f148`, root/KMIDS trees, parent and
  five Phase2 artifacts were rebound from that immutable snapshot.
- Historical Stage046 Phase2 transition only: Completed task in this run: `IDS-V0_1-STAGE046-P2`; Next allowed task: `IDS-V0_1-STAGE046-P3`. This is not the current gate; the current gate is Stage046 P4.
- Historical Stage046 Phase1 transition only: Completed task: `IDS-V0_1-STAGE046-P1`; Next allowed task: `IDS-V0_1-STAGE046-P2`. This is not the current gate; the current gate is Stage046 P4.
- `ids.stage046.parser_routing.phase3.scenarios.v1` reuses the committed Phase2
  request builder and router over fourteen metadata-only controls covering eight
  governed formats, unknown, corrupt, conflict, low-confidence, unsupported and
  instruction-marker behavior. All fourteen have explicit dispositions and
  `silent_drop_count=0`.
- Confirmed high-confidence inputs record only unavailable route candidates;
  medium, low, unknown, conflict, corrupt and unsupported inputs review or fail
  closed. Instruction-marker routing matches its non-instruction baseline, and
  caller parser override plus forged routing IDs are rejected. Parser dispatch,
  execution, fallback, output, evidence promotion, job/state mutation and
  persistence remain disabled. Stage047/048/049/050 ownership is unchanged.
- Next allowed task: `IDS-V0_1-STAGE046-P4`, only in a separate future run behind
  `IDS-STAGE046-P4-GATE`; `phase4_entry_authorized=false`, `NO_PHASE4_THIS_RUN`,
  `NO_STAGE_REVIEW_THIS_RUN`, `NO_BATCH_REVIEW_THIS_RUN`,
  `NO_GITHUB_UPLOAD_THIS_RUN`, `NO_APP_REINSTALL_THIS_RUN`.
- Final GREEN passes the Phase3 checker with 14/14 explicit scenario dispositions,
  zero silent drops and two rejected invalid requests; focused Phase3 `18/18`,
  Phase1-3 compatibility `43/43`, Stage005 `173/173` in `45.246s`,
  Stage041-046 aggregate `386/386` in `1169.916s`, and full IDS v0.1 discovery `1137/1137` in
  `1607.288s`. All eight Stage038-045 historical review checkers, `223` unique
  event semantics, idempotent owner rendering and project dual-plane pass.
- Layered fail-closed evidence repaired only the exact current
  `IDS-STAGE046-P3 -> IDS-STAGE046-P4-GATE` compatibility in nine historical
  assertions, the Stage005 P3 path/route allowlist, one unittest helper-name
  collision and untranslated P3 owner-view terms. An unstaged Stage039 review
  check correctly failed Git-index binding and passed after the exact KMIDS
  change set was staged; failed runs were not counted as PASS.
- Current source hashes: archive
  `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`,
  unique Stage046 member
  `955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39`,
  roadmap `a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6`,
  instructions `ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8`,
  execution index `2e0088153cd1e13a09d9aebd09a1bd0c8c7162acd0788360d45f5c7320af1e9a`.
- Phase3 evidence: `STAGE046_PHASE3_PARSER_ROUTING_SCENARIOS.md`,
  `parser_routing/stage046_parser_routing_scenarios_contract.json`,
  `scripts/check_parser_routing_scenarios.py`, focused tests and the Phase3 machine
  run. Any source, Phase2 snapshot, scenario outcome, explicit disposition,
  instruction invariance, governance or side-effect mismatch returns
  `FAIL_CLOSED` to `IDS-STAGE046-P3-GATE`.
- Historical Phase2 evidence: `STAGE046_PHASE2_PARSER_ROUTING_SLICE.md`,
  `parser_routing/stage046_parser_routing_runtime_contract.json`,
  `scripts/check_parser_routing_runtime.py`, focused tests and the Phase2 machine
  run. Any source, Phase1 snapshot, request shape, route, version, evidence-only,
  governance or side-effect mismatch returns `FAIL_CLOSED` to
  `IDS-STAGE046-P2-GATE`.
- Historical Phase1 evidence: `STAGE046_PHASE1_PARSER_ROUTING_SCOPE_BOUNDARY.md`,
  `parser_routing/stage046_parser_routing_contract.json`,
  `scripts/check_parser_routing.py`, focused tests and the machine run. Any source,
  predecessor, snapshot, route-family, ownership, quality, state or side-effect
  mismatch returns `FAIL_CLOSED` to `IDS-STAGE046-P1-GATE`.
- Completed task in this run: `IDS-V0_1-STAGE045-P4`; the approved source, committed Phase3 predecessor and five indexed Phase3 artifacts are bound into `ids.stage045.file_type_detection.phase4.delivery.v1`. The checker replays all fourteen Phase3 scenarios and derives six schema-only parser-output samples, seven non-runtime fallback-log samples, exact quality metrics and four fail-closed failure classes without parser or fallback execution.
- Preserved Stage045 Phase 4 transition: Completed task in this run: `IDS-V0_1-STAGE045-P4`; Next allowed task: `IDS-V0_1-STAGE045-REVIEW`. This is historical evidence, not the current gate.
- Preserved Stage045 Phase 3 transition: Completed task in this run: `IDS-V0_1-STAGE045-P3`; Next allowed task: `IDS-V0_1-STAGE045-P4`. This is historical evidence, not the current gate.
- Preserved Stage045 Phase 2 transition: Completed task in this run: `IDS-V0_1-STAGE045-P2`; Next allowed task: `IDS-V0_1-STAGE045-P3`. This is historical evidence, not the current gate.
- Preserved Stage045 Phase 1 transition: Completed task in this run: `IDS-V0_1-STAGE045-P1`; Next allowed task: `IDS-V0_1-STAGE045-P2`. This is historical evidence, not the current gate.
- Preserved Stage044 review transition: Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`; Next allowed task: `IDS-V0_1-STAGE045-P1`. This is historical evidence, not the current gate; `NO_STAGE045_THIS_RUN` applied to that prior review run.
- Preserved Stage044 Phase 4 transition: Completed task in this run: `IDS-V0_1-STAGE044-P4`; Next allowed task: `IDS-V0_1-STAGE044-REVIEW`. This is historical evidence, not the current gate.
- Workspace rule: `/Users/linzezhang/Documents/Codex/GithubProject/KMOS` remains the clean read-only `main` checkout. All work is isolated in `/Users/linzezhang/Documents/Codex/GithubProject/_scratch/kmos-kmids-stage041` on `codex/kmids-recovery-stage041-p1`, with scope limited to `KM_IDSystem/`.
- Approved source: the unique archive member `IDS_v0_1_Final_Chinese_Revised/stages/STAGE-045_文件类型检测.md` has SHA-256 `4eac237a7f63d764cf71789d4949a5168cbe8fe24e1fe7eb816baabe04bb4d27` inside archive SHA-256 `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`; roadmap and instruction hashes are bound exactly.
- Phase 3 binds Phase2 commit `e61e8f7cbf8795a3f5d2b33be4031f1885948b00`, root tree `94f820df60f592c516c61160ce40e059458d7b9f`, `KM_IDSystem` tree `2daa58d66a496e3b1aede42ed1154de271d80824` and parent `2f4051b7e9960e10698052b4e3f71fcb093f35e3`. Integration baseline `082565a958459fb4b9ad2b951a74982c30311a03` binds Phase2 with the fetched `origin/main` parent without changing the Stage045 gate.
- Detection precedence is `signature > MIME > filename extension`; extension is advisory only. ZIP magic alone never proves DOCX/XLSX: `[Content_Types].xml` plus `word/` or `xl/` is required.
- The contract defines ten canonical types and six detection states. Conflict, unknown, unsupported and corrupt/unreadable inputs fail closed to explicit error or owner review; no silent fallback is permitted.
- Phase 3 replays the Phase2 detector over PDF, DOCX, XLSX, CSV, TXT, PNG, JPEG, both TIFF endiannesses, unknown binary, corrupt ZIP, conflicting signals, extension-only and instruction-like text. All fourteen scenarios pass, `silent_drop_count=0`, and every non-high-quality result has an explicit quality review, owner review or error disposition.
- Phase 4 publishes schema-only samples for six parser-route candidates with exactly `text/tables/pages/sections/confidence/errors`; every sample is `SCHEMA_ONLY_NOT_EXECUTED`, has parser version `UNASSIGNED_STAGE046`, contains no business content and is not a runtime output.
- Seven non-high-quality Phase3 scenarios produce `DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME` fallback control records with `attempted=false`, `attempt_count=0`, `silent_drop=false` and `parser_switch_performed=false`. Stage048 remains the fallback runtime owner.
- Phase4 quality evidence recomputes `14/14` scenario pass, `8/8` governed-format coverage, confidence counts `7/3/1/3`, disposition counts `7/3/3/1`, seven explicitly disposed non-high-quality results and zero parser outputs. Unknown binary, corrupt ZIP, conflicting signals and extension-only low confidence remain fail closed.
- Phase4 final validation passes checker `16/16 + 9/9`, focused `13/13`, Phase1-4 compatibility `59/59`, Stage005 `172/172`, Stage041-045 aggregate `327/327` in `1138.506s`, and full IDS v0.1 discovery `1077/1077` in `1566.023s`; all seven historical review checkers, `219` clean events, exact 30-path event coverage, idempotent owner rendering and project dual-plane pass.
- The first aggregate reached `323/327` and the first full discovery reached `1073/1077`; the eight failures were stale Stage038/039/041-044 forward-route assertions ending at P3. Repairs add only the exact `IDS-STAGE045-P4 -> IDS-STAGE045-REVIEW-GATE` route and do not weaken historical review or runtime-safety evidence.
- Final-evidence synchronization later failed closed only the Stage042 review checker's staged-Handoff allowlist; extending it to the same exact P4 current task restored the checker and its `10/10` review tests in `253.879s`.
- Detector version remains `ids.file_type_detector.v0_1.stage045.p2`; all six parser versions are truthfully `UNASSIGNED_NOT_IMPLEMENTED`. No parser configuration was created or changed, and rollback returns only to the committed Phase3 scenario-only state while preserving all prior evidence.
- Instruction-like source-derived text remains `UNTRUSTED_EVIDENCE_TEXT`; its route matches the non-instruction baseline and it cannot authorize tools or override policy. Parser dispatch, normalized parser output, fallback logging/metrics and Stage050 prompt-injection scanning remain owned by Stage046-050.
- Valid TDD RED produced two governance failures and sixteen missing-artifact errors across eighteen tests before Phase3 artifacts existed. Final GREEN passed focused `18/18` in `1.069s`, Phase1-3 compatibility `46/46` in `2.069s`, Stage005 final evidence recheck `171/171` in `38.633s`, Stage041-045 aggregate `314/314` in `1083.079s`, full discovery `1063/1063` in `1540.095s`, all seven Stage038-044 review checkers, `218` clean events, idempotent owner rendering and project dual-plane.
- The first aggregate failed closed on fourteen historical current-route/index assertions and the first full discovery failed closed on four P3-to-P4 routes plus one stale owner render. A final-evidence Stage005 run failed closed on twenty-two exact result-binding checks before synchronization. Repairs were restricted to exact forward-route compatibility, preservation of existing historical safety invariants, generated owner views and the exact roadmap result binding; one wrong-workdir targeted command was interrupted and not counted as PASS.
- Pre-commit self-review repaired one Important fail-closed gap: the three instruction-control flags now derive from the bounded Phase2 evidence wrapper and are included in scenario PASS evaluation instead of being hard-coded false. The same existing test proves an unsafe wrapper forces `FAIL_CLOSED`; the test count remains eighteen.
- Project governance note: the sparse worktree does not contain root `scripts/lean_governance.py`, so the repository-wide command reports `SPARSE_CONFLICT`; no sparse expansion or unrelated-project inspection was performed.
- Current batch gate: `BATCH041_050` has five locally reviewed Stages plus Stage046 Phase1-4 only and remains locked with `push_allowed=false`; Stage046 review, Stage047-050, single-stage upload, GitHub action, merge, app reinstall, batch review and production action are not authorized.
- Preserve owner-controlled dependency/service paths (`backend/requirements.txt`, `frontend/package.json`, `frontend/pnpm-workspace.yaml`, `scripts/run_local_services.sh`); this phase does not modify them.
- `/Users/linzezhang/Downloads/IDS_MetaData` remains a path-only governance boundary and was not touched. Do not read, list, hash, open, scan, copy, move, delete, modify, dump, or normalize its contents.

## Purpose

IDS / Industrial Data System turns the original industrial-operations CLI prototype into a local Web + PDF industrial data and operations console. It provides dashboard views, module-specific analysis, visualization, report generation, model routing configuration, and recoverable local app launchers.

Legacy aliases such as `Wuhan Kaiming OpMe`, `OpMe`, and the Chinese legacy display name may remain only in migration notes, historical evidence, compatibility paths, or rollback context. New UI, reports, generated titles, and formal documentation should use `IDS / Industrial Data System`.

## Delivery Standard

Any future agent should preserve these standards:

- The app must start locally from `./scripts/run_local_services.sh` or the macOS click entry. Prefer the installed `.command` launcher when Gatekeeper blocks the `.app`.
- The backend health endpoint must return ok at `http://127.0.0.1:8000/api/health`.
- The frontend must load at `http://127.0.0.1:5173/`.
- Four core modules must keep working: dynamic kiln monitoring, fault diagnosis, gear repair, machining service.
- Every case should support dashboard visualization and PDF report generation.
- Missing model API keys must not block operation; offline rules must remain the fail-closed fallback.
- Formal user-facing outputs should remain PDF-first; JSON, CSV, SQLite, and Markdown are support artifacts.

## Current Architecture

- `backend/`: FastAPI service, SQLite persistence, rule analysis, model routing, PDF generation.
- `frontend/`: React + ECharts dashboard and workbench UI.
- `samples/`: small JSON/CSV inputs for demos and tests.
- `scripts/`: local service launcher, smoke test, sample report generation.
- `docs/`: handoff, cleanup, and continuity documents.
- `app_bundle/`: source macOS `.app` bundle resources and icon assets. `scripts/install_app_entries.sh` also installs `.command` launchers to Downloads and Applications.

## Runbook

```bash
./scripts/run_local_services.sh
```

Install local click entries:

```bash
./scripts/install_app_entries.sh
```

Installed entries:

- `/Applications/IDS Industrial Data System.command`
- `/Users/linzezhang/Downloads/IDS Industrial Data System.command`
- `/Applications/IDS Industrial Data System.app`
- `/Users/linzezhang/Downloads/IDS Industrial Data System.app`

Use `.command` as the primary local double-click entry. It runs the same service launcher in Terminal and avoids macOS LaunchServices/Gatekeeper silently blocking ad-hoc `.app` bundles. Keep the Terminal window open while using the app; closing it stops the local runtime.

Regenerate the macOS app icon:

```bash
.venv/bin/python scripts/generate_app_icon.py
./scripts/install_app_entries.sh
```

The tracked final assets remain `app_bundle/assets/OpMeIcon.png` and `app_bundle/assets/OpMeIcon.icns` as legacy asset paths; the intermediate `.iconset` directory is intentionally ignored.

For verification:

```bash
./scripts/smoke_test.sh
```

Quick launcher verification:

```bash
OPEN_BROWSER=0 ./scripts/run_local_services.sh
cat data/backend_port data/frontend_port
curl -fsS "http://127.0.0.1:$(cat data/backend_port)/api/health"
curl -fsS "http://127.0.0.1:$(cat data/frontend_port)/api/health"
```

If dependencies were removed during cleanup, the launcher restores them from:

- `backend/requirements.txt`
- `frontend/package-lock.json`

## GitHub Continuity Rule

All future development for this system should be synchronized into:

`LinzeColin/KMOS`

Use the subdirectory:

`KM_IDSystem/`

Commit/PR summaries must include:

- task purpose
- changed subsystems
- validation commands and results
- remaining risks
- local files that are intentionally not tracked

## IDS v0.1 Staged Development

- Read-only main checkout: `/Users/linzezhang/Documents/Codex/GithubProject/KMOS` (must remain on clean `main`).
- Active task worktree: `/Users/linzezhang/Documents/Codex/GithubProject/_scratch/kmos-kmids-stage041`.
- Project scope: `KM_IDSystem/` only.
- Current local state: `STAGE-031..STAGE-040` and their independent batch review are merged to GitHub `main`; `STAGE-041..STAGE-047` are locally reviewed. Parser/output/fallback/quality/persistence effects remain disabled.
- Current task: `IDS-V0_1-STAGE047-REVIEW` is complete; the only next task is `IDS-V0_1-STAGE048-P1` in a separate run behind `IDS-STAGE048-P1-GATE`. Stage048-050, ten-stage batch review, upload, merge and app reinstall remain separate gates.
- Stage043 review publishes `ids.stage043.worker_crash_recovery.stage_review.v1`, binds the committed Phase4 baseline, reruns all four phase checkers and machine-checks six repaired findings.
- Phase 2 remains valid at checker `18/18 + 15/15`; its canonical identity, candidate-only transition, fencing, idempotency and safe-reference boundaries are unchanged.
- Preserved Stage043 Phase 4 transition: Completed task in this run: `IDS-V0_1-STAGE043-P4`; Next allowed task: `IDS-V0_1-STAGE043-REVIEW`; `NO_STAGE_REVIEW_THIS_RUN`. This is historical evidence, not the current gate.
- Stage043 Phase 4 publishes `ids.stage043.worker_crash_recovery.phase4.delivery.v1`, binds the committed Phase3 baseline plus current indexed Stage038-042 delivery evidence, and returns `PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED` only when all 14 contract and 14 delivery checks pass.
- The closeout distinguishes three conditional handling candidates from current automatic-recovery eligibility: eligibility and observed success are both empty, all actual process/recovery/mutation/delete/persistence flags remain false, and the whole-stage review is now passed locally.
- Preserved Stage042 review transition: Completed task in this run: `IDS-V0_1-STAGE042-REVIEW`; Next allowed task: `IDS-V0_1-STAGE043-P1`. This is historical evidence, not the current gate.
- Stage042 review publishes `ids.stage042.automatic_lifecycle.stage_review.v1`, binds the committed Phase4 baseline, reruns all four phase checkers and machine-checks five repaired findings.
- Stage042 Phase 3 publishes `ids.stage042.automatic_lifecycle.phase3.scenarios.v1`, twelve isolated scenarios with actual lifecycle, process-crash recovery, termination, cleanup/delete, persistence and production effects disabled.
- Stage042 Phase 2 publishes `ids.automatic_lifecycle_policy.v0_1.stage042.p2`, an isolated reference-only in-memory candidate-decision slice. Canonical request IDs, positive versions, action-bound reasons, temporal resume evidence and paused-only cleanup now fail closed.
- `MOD-011`, `FORM-011`, and `PARAM-072..076` remain planned/proposed. The five timing values are derived from reviewed Stage040/041 bounds and require production calibration under `TASK-OPME-B-001`.
- Stage042 Phase 1 binds the unique approved source, reviewed Stage041 commit/tree and exact Stage037–041 contracts into `ids.stage042.automatic_lifecycle.phase1.v1`.
- The static contract preserves the authoritative state graph, owner/resource revalidation, Stage038–044 ownership, reference-only evidence, ordered shutdown and candidate-only cleanup while assigning no numeric parameters and performing no runtime.
- Stage041 review repaired `1 Critical / 3 Important / 0 Minor`: strict-integer CAS evidence, monotonic logical time/live-lease mutations, exact runtime contract semantics, and current handoff/governance truth are now machine checked and fail closed.
- `check_lock_registry_stage_review.py` reverifies the approved external source, reruns all four Stage041 phase checkers, machine-checks every repair, validates reviewed-local governance, and requires every review source to match the Git index.
- Stage041 Phase 4 binds the committed Phase 3 commit/tree and reviewed upstream hashes into an exact-shaped closeout contract plus stdout-only checker; no candidate commit or Stage42-43 review state was activated.
- The Phase 4 report composes the five-family lock lifecycle with the reviewed 8-type/11-state/4-terminal/21-transition graph, 3-attempt/2-retry dead-letter evidence, seven pressure signals and a two-class cleanup allowlist.
- One actual isolated acquire-renew-release sequence leaves zero active locks, two monotonic tombstone versions and a rejected stale commit. It is process-local orderly-shutdown evidence, not persistence, crash recovery or production readiness.
- Exact idempotent replay, matching-holder renewal and matching-holder release are lock decisions, not successful recovery. Automatic-recovery eligibility and observed success remain empty; manual cases stay fail-closed.
- Final Phase 4 validation: checker contract checks 16/16, delivery checks 6/6, focused 12/12, Stage005 157/157, Stage040-041 aggregate 109/109, full IDS v0.1 discovery 789/789, events 199 with zero parse/duplicate/semantic errors, and project-scoped dual-plane PASS.
- Stage041 Phase 1 binds the unique approved taskpack source and the terminal `BATCH031_040` lock hash into an exact-shaped metadata-only contract plus stdout-only fail-closed checker.
- The contract requires a shared source-pipeline guard plus an operation-specific lock, lexicographic multi-key ordering, atomic compare-and-set acquisition, one live holder, same-holder renewal, atomic fencing/version advance on takeover, and stale-token denial for commits, checkpoint/evidence mutation, renew, and release.
- Contention creates no queue record, runs no operation, consumes no retry budget, and assigns no implicit timing defaults. Automatic resume stays with STAGE-042, crash recovery with STAGE-043, and cleanup execution with STAGE-044.
- Final layered evidence: Stage041 checker `20/20`, focused tests `10/10`, Stage005 `156/156`, Stage037-040 `179/179`, historical Stage001-036 plus BATCH031-040 review compatibility `555/555`, and full IDS v0.1 discovery `744/744`. The first full run exposed 32 stale historical governance assertions; all were repaired without changing the immutable `BATCH031_040` hash. Pre-commit self-review also repaired one Important exact-shape gap so unknown nested fields and incomplete human-status projections fail closed.
- Batch review repaired one Critical and two Important findings by adding a strict ten-stage source/review/interface/index contract, a fail-closed checker, and a reviewed-no-upload governance/event route.
- `check_batch031_040_review.py` rehashes the approved archive, exact ten taskpack members, ten Stage review artifacts, reruns all Stage checkers, verifies Stage036-040 interface/hash bindings, and requires every review source to match the Git index.
- Final batch-review validation: batch tests `8/8`, Stage005 `151/151`, Stage031-039 `254/254`, Stage040 `55/55`, and full IDS v0.1 discovery `729/729`; six historical Stage038/039 compatibility assertions were repaired after the first full run exposed the new reviewed-no-upload state.
- Exact source status: `SOURCE_VERIFIED`; the unique Stage040 member is `IDS_v0_1_Final_Chinese_Revised/stages/STAGE-040_反压策略.md` with SHA-256 `f0ef128467300d7541796f8d51caca673f838cac2552eba2e415a94a07af614d`.
- Corrected Phase 1 defines queue/worker separation, envelope idempotency, retry/dead-letter, backpressure, lock granularity, automatic lifecycle, crash-recovery checkpoint, and cleanup allowlist interfaces. STAGE-039..044 retain dedicated runtime policy and implementation ownership.
- A six-surface finite-state check binds batch, roadmap, entry, Phase 1, source evidence, and review evidence. Independent review repaired `1 Critical / 1 Important / 0 Minor` and ended at `0 / 0 / 0`.
- Phase 2 implements one `asyncio` in-memory queue and worker over a real Git-tracked Phase 1 control document. Submission returns before completion; STAGE-037 transitions, Chinese status, duplicate admission, bounded-capacity backpressure, and input/output/error/checkpoint fields are exercised without persistence.
- The Phase 2 smoke runs only in `ISOLATED_NON_PRODUCTION_ASYNC_CONTROL_METADATA_SLICE` mode. It creates one real isolated control job, not an IDS business job, and does not activate a production service.
- Phase 3 repairs the resource conflict domain so `ARCHIVE`, `PARSE`, `INDEX`, and `REPORT` over one input share one lock key. Active conflicts pause before queue admission; terminal records permit a later same-source job.
- The seven Phase 3 scenarios validate duplicate click, an actual isolated worker exception, external-drive-offline control gating, actual project-volume free-space insufficiency, external-API-budget insufficiency without an API call, same-source cross-operation conflict, and protected cleanup denial. Physical drive removal, disk allocation, process termination, cleanup execution, and production runtime are not claimed.
- Phase 4 delivers the exact 8-type/11-state/21-transition graph, actual isolated failure record, capacity/resource/lock backpressure proofs, a two-class cleanup allowlist, an empty automatic-recovery set, six manual-action cases, orderly isolated shutdown proof, rollback steps, and known limits.
- The Phase 4 delivery checker returns `PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED`; this is closeout evidence, not production readiness or whole-stage acceptance.
- Stage040 whole-stage review repaired one Critical and two Important findings: malformed/non-JSON control metadata now returns structured fail-closed output without echoing invalid refs; active resource pauses project `暂停中` until `PAUSED`; and Stage040 explicitly records that scheduler-level starvation prevention is unproved and unimplemented.
- The Stage040 review checker independently rehashes the approved archive, unique ZIP member, roadmap, and instructions; revalidates the Phase 1-4 chain; and requires all review sources to match the Git index before returning `PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED`.
- The previous batch upload is complete. For the current reviewed Stage043 state, GitHub/PR/issue/merge, app reinstall, production runtime, raw metadata content access, Stage044 execution and batch review remain disabled; only `IDS-V0_1-STAGE044-P1` may run next in a separate run.
- Whole-stage review repaired exact contract shapes, the missing API-budget pause proof, and the false same-operation resubmission instruction; all review sources must match the Git index before `completed_reviewed_local` is valid.
- Stage039 Phase 1 publishes `ids.retry_dead_letter.v0_1.p1`. It keeps `FAILED`, `DEAD_LETTERED`, `SUCCEEDED`, and `CANCELLED` immutable; retryable failure uses `RUNNING -> RETRY_WAIT`, exhaustion uses only `RETRY_WAIT -> DEAD_LETTERED`, and permanent failure uses `RUNNING -> FAILED`.
- Retry reservation does not consume budget; only atomic eligible admission increments `retry_count`. Resource pauses consume no retry budget. Duplicate transition replay cannot consume twice.
- The terminal manual-rerun contract requires a future implementation to create a new owner-authorized linked job with new job/idempotency identity and lineage; Stage039 validates only a non-persisted candidate and never reopens the terminal job.
- Phase 2 supplies `ids.retry_policy.v0_1.stage039.p2` with `max_retries=2`, total-attempt limit `3`, `[5, 30]` backoff ceilings, deterministic bounded nonzero hash jitter, and an exact retryable-safe-error allowlist. These values are `PROPOSED`, are not production calibrated, and roll back to `NO_AUTOMATIC_RETRY`.
- The isolated slice uses one real Git-tracked Stage039 control reference, a Stage038 in-memory transport admission, and a separately derived Stage039 in-memory policy snapshot with Stage037 candidate-only CAS transitions. The two control identities differ, so `max_retries` remains immutable. Two due admissions increment budget once each; duplicate failure/admission replay does not increment; exhaustion reaches `DEAD_LETTERED` at `retry_count=2`.
- Input refs, empty failure output refs, safe error, actual tracked-control checkpoint digest, policy version, audit ref, and Chinese owner status are preserved without persistence.
- Phase 3 validates exactly ten isolated scenarios: duplicate retry reservation/admission, actual worker exception with process-crash recovery deferred, drive/disk/API resource pauses, same-source cross-operation locking, retry exhaustion, immutable terminal replay, owner-authorized manual-rerun candidate lineage, and five-class protected cleanup denial.
- Stage038 supplies the actual isolated worker exception and actual local disk-free observation. Phase 3 performs no process termination, physical drive removal, disk allocation, API call, cleanup/delete, production runtime, persistence, database action, raw metadata access, or fake IDS business-data use.
- Manual rerun is candidate-only and idempotent: it requires owner authorization plus a new linked job ID and idempotency key, but creates no job and writes no queue or database state. Protected cleanup verifies exact Git-tracked refs and exposes no deletion path.
- Phase 4 binds the exact Stage037 8-type/11-state/21-transition graph, six failure decisions, the actual isolated three-attempt retry/dead-letter history, five capacity/resource/conflict signals, and the two-class cleanup allowlist into one machine-checked delivery report.
- Automatic handling is narrowly stated: two exact safe codes can enter controlled retry only when policy, budget, resource, CAS, and idempotency gates pass. No successful automatic recovery was observed. Eight conditions remain manual-action cases.
- Safe shutdown reuses reviewed Stage038 isolated transport closure. Stage039 has no persistent scheduler or process-recovery runtime; after exit, only a new linked-job candidate may be revalidated, no job is created, and terminal history remains immutable.
- Stage039 whole-stage review repaired four Important findings: invalid governance enums/task links, total-count drift, overclaimed terminal-rerun creation wording, and the absent durable review gate. All review sources must match the Git index.
- Stage040 Phase 1 publishes `ids.backpressure_policy.v0_1.p1`. Healthy pressure may return `ADMIT`; soft queue pressure throttles admission; hard capacity creates no queue record; drive/disk/API resource pressure uses only legal STAGE-037 pause paths; unknown or stale pressure denies admission and requires manual review.
- Throttle, denial, and resource pause consume no retry budget. Priority cannot bypass a safety gate, terminal states stay immutable, and active jobs must pass through `PAUSE_REQUESTED` before `PAUSED`.
- Phase 1 assigns no numeric values. Queue thresholds, disk reserve, API budget window, high/low watermarks, observation TTL, per-job-type concurrency, and admission rate limit require separately sourced, versioned, tested, and rollback-ready Phase 2 selection.
- Stage040 Phase 2 publishes `ids.backpressure_policy.v0_1.stage040.p2` as an isolated non-production decision slice. Its explicit parameters are soft/hard queue thresholds `2/4`, disk free threshold `1 GiB` above a `512 MiB` reserve, API window `60 s`, queue low watermark `1`, observation TTL `30 s`, per-job-type concurrency `1`, and admission rate `4` per window.
- All nine Phase 2 values are `PROPOSED`, not production calibrated, and linked to `TASK-OPME-B-001`. `MOD-009`, `FORM-009`, and `PARAM-056..064` were the planned registrations at Stage040 Phase 2 completion, when totals were `9/9/64`; after Stage041 and Stage042 Phase 2, current totals are `11/11/76`, while active counts remain `7/7/49`.
- The decision engine is deterministic and in-memory: healthy observations admit, soft pressure/rate/concurrency throttle, hard capacity denies without a job, and drive/disk/API gates return legal pause candidates. Invalid or stale observations require manual review; terminal states remain immutable; duplicate decisions replay idempotently.
- Phase 2 observes actual free space only for the project filesystem and writes no runtime output. It performs no queue/worker/retry scheduler/lock/resume/cleanup/database/raw-source/API/production action and creates no IDS business job.
- Final Phase 2 validation: checker `18/18` contract and `8/8` slice checks; focused `15/15`; Stage040 `25/25`; Stage005 `147/147`; Stage031-039 `254/254`; Stage026-030 `75/75`; full IDS v0.1 discovery `687/687`; changed-only governance `0` errors / `0` warnings; `189` events with no duplicate ID; owner render drift/reference issues `0/0`.
- Stage040 Phase 3 validates eight isolated scenarios: duplicate decision replay, actual isolated worker exception boundary, external-drive-offline pause, actual project-filesystem disk observation plus a no-allocation low-disk boundary, API-budget pause, same-source cross-operation throttling, reviewed one-execution/three-conflict lock proof, and five-class protected cleanup denial.
- The worker exception and project free-space observation are actual isolated observations. Drive/API/low-disk boundary inputs are control metadata; no physical drive removal, disk allocation, process termination, external API call, cleanup/delete, Stage040 queue/worker runtime, production lock, crash recovery, persistence, database action, or production activation occurred.
- Phase 3 replays the reviewed Stage038/039 in-memory lock proof but keeps production lock/lease/fencing with STAGE-041. It verifies Git-tracked fact source, manifest, evidence ledger, report snapshot, and audit log refs without exposing a delete path; cleanup runtime remains owned by STAGE-044.
- Final Phase 3 validation: checker `18/18` contract and `8/8` scenario checks; focused `11/11`; Stage040 `36/36`; Stage005 `148/148`; Stage031-039 `254/254`; Stage026-030 `75/75`; full IDS v0.1 discovery `699/699`; changed-only governance `0` errors / `0` warnings; `190` events with no duplicate ID; owner render drift/reference issues `0/0`.
- Stage040 Phase 4 binds the exact Stage037 8-type/11-state/4-terminal/21-transition graph, seven pressure signals, and the reviewed actual Stage039 three-attempt/two-retry/dead-letter history into one fail-closed delivery report.
- The cleanup allowlist remains limited to temporary staging and incomplete derivative outputs; fact sources, manifests, evidence ledgers, report snapshots, and audit logs are protected. No delete or cleanup runtime runs.
- Automatic recovery eligibility and observed success are both empty. Healthy new admission is not recovery; eight unknown, terminal, resource, worker, conflict, calibration, contract, and crash cases require manual handling or a downstream gate.
- Safe shutdown replays reviewed isolated transport closure and records fresh-observation recovery plus P4-only rollback. There is no persistent pressure state, automatic resume, process recovery, production runtime, or production-readiness claim.
- Final Phase 4 validation: checker `14/14` contract and `8/8` delivery checks; focused `10/10`; Stage040 `46/46`; Stage005 `149/149`; Stage031-039 `254/254`; Stage026-030 `75/75`; full IDS v0.1 discovery `710/710`; changed-only governance `0` errors / `0` warnings; `191` events with no duplicate ID; owner render drift/reference issues `0/0`.
- STAGE-038 retains queue/worker transport; STAGE-039 retry/dead-letter; STAGE-041 locks/leases/fencing; STAGE-042 automatic resume; STAGE-043 crash recovery; STAGE-044 cleanup execution. Phase 1 executed none of these runtimes.
- `BATCH031_040` remains immutable in its terminal uploaded state. `BATCH041_050` is the current lock and remains `push_allowed=false`; do not upload, merge, mutate issues, reinstall app entries, or enter Stage042 in this review run.
- Current Phase 4 evidence adds `STAGE041_PHASE4_CLOSEOUT.md`, `lock_registry/stage041_lock_registry_delivery_contract.json`, `scripts/check_lock_registry_delivery.py`, and `tests/test_stage041_lock_registry_delivery.py`.
- The real metadata root `/Users/linzezhang/Downloads/IDS_MetaData` is path-only governance context. Do not read, list, hash, open, copy, move, delete, modify, dump, scan, normalize, or commit its contents.
- Do not use fake IDS business data, fake database rows, placeholder corpus, fabricated profiles, dumps, execution logs, or evidence.

## Local Files Intentionally Not Tracked

- `.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `.pytest_cache/`
- `__pycache__/`
- runtime SQLite/log files under `data/`
- generated PDF/ZIP artifacts under `reports/` and `outputs/`

These are recoverable from source, scripts, and GitHub.

## Known Limits

- STAGE-039 review reconciled all `21` project-level semantic diagnostics from
  the Phase 2 policy registry by using `planned` / `PROPOSED` and linking
  production calibration to `TASK-OPME-B-001`. Stage040 added one planned model,
  one planned formula and nine planned parameters; Stage041 and Stage042 Phase 2
  add three more of each registry type plus seventeen planned parameters. Current
  totals are 12/12/81 while active counts remain 7/7/49. The remaining `29`
  project-wide diagnostics are expected sparse root or unrelated-project paths
  and must not trigger sparse expansion.
- Docker was not available on this Mac during validation, so Docker Compose syntax could not be executed locally.
- macOS may reject the ad-hoc `.app` bundle through Gatekeeper/LaunchServices. The `.command` launcher is the current reliable click path.
- Real MQTT/OPC-UA/Modbus device ingestion is not implemented in this version.
- Model providers are configurable, but no plaintext API keys should be committed.
- STAGE-039 is locally reviewed, not production-ready. Persistent retry/dead-letter state, measured backpressure/fairness, production lock/lease/fencing, automatic lifecycle, process crash recovery, cleanup execution, PostgreSQL actions, raw source reads, and IDS business job execution remain absent. The selected Phase 2 values remain uncalibrated proposals and production automatic retry remains disabled.
- STAGE-040 Phase 3 provides isolated scenario evidence, not production or physical fault proof. Its values remain uncalibrated proposals; production lock/lease/fencing, automatic resume, crash recovery, cleanup execution, database action, raw-source read, IDS business jobs, GitHub actions, and app reinstall remain absent.
