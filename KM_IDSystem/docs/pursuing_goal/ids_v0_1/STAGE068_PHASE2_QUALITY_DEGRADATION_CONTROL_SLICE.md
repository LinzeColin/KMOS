# STAGE-068 Phase 2：质量降级最小可运行控制切片

## 当前结论

本步骤只实现 `IDS-V0_1-STAGE068-P2` 的纯内存、固定控制切片。它只接受四条固定、非业务、
`:control:` 的十三字段质量降级引用请求，并投影四条十九字段、非持久化的质量降级控制记录。
四条控制场景依次覆盖工程步骤、验收条款、参数表和重复 chunk 写入边界。

控制记录只保留不透明的质量降级请求、章节感知 chunk、身份与版本、工程语义资产目录、覆盖率、
质量回归、document、page、section、parser output、表格上下文、来源片段和重复写入边界引用。
它不会读取、打开、解析、切分、计算、检测、分类、生成、写入、删除或保留任何真实业务资料、
原始元数据、文档、页面、章节、表格、parser 输出、来源片段、chunk、身份、Hash、版本、覆盖率、
质量、降级结果、低可信证据、重复项、索引、数据库或业务结论。

## 最小切片与职责交界

| 控制场景 | 控制目的 | 固定人工处置 |
| --- | --- | --- |
| `procedure` | 工程步骤保护面 | `REQUIRES_BUSINESS_LINE_WHITEBOX_HUMAN_REVIEW` |
| `acceptance` | 验收条款保护面 | `REQUIRES_BUSINESS_LINE_WHITEBOX_HUMAN_REVIEW` |
| `parameter_table` | 参数表与跨页表格保护面 | `REQUIRES_BUSINESS_LINE_WHITEBOX_HUMAN_REVIEW` |
| `duplicate_chunk` | 重复 embedding/index 写入边界 | `LOW_CONFIDENCE_EVIDENCE_REQUIRES_HUMAN_REVIEW`，不检测或去重真实 chunk |

Stage063、Stage064、Stage065、Stage066 与 Stage067 分别保有章节感知切块、身份/版本、工程
语义资产分类、覆盖率和质量回归的唯一职责。本步骤只机械投影 Stage068 P1 已冻结的引用字段、
质量降级标签和人工状态；不重新检测章节、生成身份/Hash/版本、分类、计算覆盖率、执行质量回归
或形成真实质量降级。

## 质量、追溯与人工处理边界

每条控制输出严格保留 `document_ref/page_ref/section_ref/parser_output_ref/table_context_ref/
source_fragment_ref` 六维 `:control:` 引用。工程步骤、验收条款和参数表不得被任意切断、
合并或由质量降级状态覆盖。低质量不等于自动完全失败；四条输出仅声明未来需业务线白箱人工复核
或低可信证据需人工复核，不能替代来源文档、形成业务事实或自动业务建议。

重复 chunk 场景只验证固定控制标签“不得重复 embedding/index 写入”。这不证明真实重复检测、
去重、写入抑制、质量降级、来源反查或任何生产行为已经发生。

## 失败关闭、回滚与后续门

输入键、字段、顺序、场景或 `:control:` 引用任一不符合固定合同即拒绝，且不投影记录。
不得自动写入事实库、证据账本、数据库、索引、报告、生产状态或业务线结论。

回滚只撤回本 P2 范围说明、控制切片、切片合同、聚焦用例、machine run、事件、机器事实投影、
治理路线和生成中文视图，恢复到
`PHASE1_QUALITY_DEGRADATION_CONTRACT_RUNTIME_DISABLED`。真实资料、manifest、evidence ledger、
audit log、已交付报告、事实库、数据库、索引、GitHub、OVH 与应用状态不在回滚范围。

需要真实资料、授权 fixture、实际 parser 输出、实际切块、实际质量测量、真实重复检测/去重、
embedding/index、低可信证据创建、业务线实际复核、Agent、模型、OVH、生产、Phase3、整阶段复审、
批次复审、上传或推送时，立即停止本步骤。通过后的唯一后续门为
`IDS-STAGE068-P3-GATE`，且必须由新的独立 run 进入。
