# STAGE-064 Phase 1：Chunk 身份、版本、输入输出与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE064-P1` 的静态 Chunk 身份与版本合同。唯一合同上下文是冻结
Stage064 任务包、Stage063 已完成本地复审工件和 Batch061-070 上传锁。合同只登记未来
`chunk_id`、`chunk_hash`、`document_id`、`page`、`section`、`version` 字段标签，以及对应的
引用式追溯、工程语义保护面、失败关闭和回滚边界；没有读取、打开、计算、生成、写入或删除
任何业务资料、原始元数据、parser 输出、文档、页面、章节、表格、来源片段、chunk、身份、哈希、
版本、索引或嵌入。

`chunk_id`、`chunk_hash`、`document_id`、`page`、`section` 和 `version` 在本步骤只是未来 schema
字段标签，不填入实际值，也不构成 document、page、section、版本记录、业务事实或另一权威来源。
`document_ref`、`page_ref`、`section_ref`、`parser_output_ref`、`table_context_ref` 和
`source_fragment_ref` 均为不透明受控引用，当前不得填入正文、物理路径、URL、页码值、章节名称、
表格内容或来源片段。

## 职责交界

| 事项 | 唯一职责阶段 | 本步骤处置 |
| --- | --- | --- |
| 章节感知切块边界 | Stage063 | 只复用已复审的引用边界，不重新检测或切分 |
| chunk 身份、哈希与版本合同 | Stage064 | 只定义未来字段、失败关闭、追溯和回滚边界 |
| 工程语义资产分类 | Stage065 | 只预留资产类型引用，不执行分类 |
| chunk 覆盖率 | Stage066 | 只预留覆盖率引用，不计算任何覆盖率 |
| 切块质量回归 | Stage067 | 不运行质量验证或回归 |
| 质量降级与人工复核 | Stage068 | 只声明未来关闭接口，不产生质量结论 |

## 输入、结果输出与追溯边界

未来身份与版本输入固定为十个仅引用字段，未来输出固定为十四个静态 schema 字段。其中
`chunk_id`、`chunk_hash`、`document_id`、`page`、`section`、`version` 是必须存在的未来字段标签；
当前没有请求、chunk、身份、哈希、document 绑定、版本、来源定位或追溯验证。

未来记录必须能回指 document、page、section、parser output、表格上下文和来源片段引用。工程步骤、
验收条款和参数表是三类保护语义面：身份、哈希和版本规则不得覆盖或导致它们按固定字符数任意切断。
该规则只定义边界，不执行识别、分类、切分、哈希、版本生成、重复检测、质量评估、索引或 embedding。

来源文档与经授权的业务线人工复核始终保持权威；chunk、身份、版本、模型输出或本合同不得替代来源
形成事实或决策结论。

## 失败、中文反馈与回滚

缺少 chapter-aware chunk、document、page、section、parser output、来源片段、身份或版本引用，无法确认
哈希/版本依据，或遇到跨页参数表与保护语义面可能被任意切断时，未来流程必须关闭并转人工处理；当前
没有任何实际失败、身份、哈希、版本或处置记录。不得自动写入事实库、证据账本、数据库、索引、报告、
生产状态或业务线结论。

回滚只允许移除本步骤的范围说明、静态合同、聚焦用例、machine run、事件、机器事实投影、治理路线和
生成中文视图，恢复到 `STAGE063_REVIEWED_LOCAL_CHAPTER_AWARE_CHUNKING_RUNTIME_DISABLED`。真实资料、
manifest、evidence ledger、audit log、已交付报告、事实库、数据库、索引、GitHub、OVH 与应用状态不在
回滚范围内。

一旦需要真实资料、授权 fixture、实际 parser 输出、实际切块、真实 `chunk_id`、`chunk_hash`、
`document_id`、`version`、语义资产分类、覆盖率、质量回归、质量降级、索引、embedding、Agent、模型、
OVH、生产、Phase2、整阶段复审、批次复审、上传或推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 `IDS-STAGE064-P2-GATE`，且必须由新的独立 run 进入。
