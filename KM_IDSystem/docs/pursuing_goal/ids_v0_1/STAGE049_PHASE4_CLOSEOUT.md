# Stage049 Phase 4：差异化解析器评估交付证据、回滚与中文反馈

## 本轮交付结论

`IDS-V0_1-STAGE049-P4` 只从已验证的 P3 格式标签化、reference-only control
场景派生交付证据。交付物是候选解析产物的结构样例、非运行时处置记录、质量指标、
失败分类、格式边界和回滚说明，状态为
`PHASE4_DIFFERENTIAL_EVALUATION_CLOSEOUT_EVIDENCE_ENABLED_REAL_PARSER_QUALITY_AND_PERSISTENCE_DISABLED`。

这不代表真实文件已经解析、两个 parser 的正文已经比较，或任何质量门、人工复核队列、
fallback、证据提升或持久化已经启用。

## 唯一合同上下文与交付物

唯一合同上下文仍为冻结 Stage049 任务包、Stage049 P1--P3 合同及 Stage048 已复审工件；
未建立第二权威事实源，未读取或保留业务正文、文件路径、来源引用、原始异常或原始元数据。

- `stage049_differential_parser_evaluation_delivery.py` 重放 P3 结果；
- 20 个 `SCHEMA_ONLY_CANDIDATE_PARSE_PRODUCT_SAMPLE_NOT_EXECUTED` 结构样例，覆盖 10 个非无效控制的两个候选版本；
- 11 条 `DERIVED_CONTROL_DISPOSITION_LOG_NOT_RUNTIME` 处置记录；
- 质量指标记录 11/11 场景通过、11/11 明确处置、静默丢弃为零；
- 五类互斥失败分类覆盖全部控制场景。

每个候选解析产物样例只含 `text`、`tables`、`pages`、`sections`、`confidence`、`errors`
的空结构或控制标签；不保留正文、表格单元、页面内容、章节内容、来源引用或运行时输出。

## 差异评估处置与质量指标

| 分类 | 场景数 | 处置边界 |
| --- | ---: | --- |
| `CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW` | 6 | 仅保留候选，未进入质量门或人工队列 |
| `CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED` | 2 | 仅记录低质量 control 的未排队复核边界 |
| `UNTRUSTED_INSTRUCTION_TEXT_EVIDENCE_ONLY` | 1 | 指令样 TXT 仍只是不可信证据文本，处置与普通 TXT 一致 |
| `CONTROL_CONTEXT_MISMATCH_NOT_ELIGIBLE` | 1 | 控制上下文不一致，未比较也未 fallback |
| `INVALID_CONTROL_REJECTED` | 1 | 坏文件 control 无效，未生成候选样例 |

格式标签仅说明受控场景覆盖，不是文件签名检测或运行时支持声明。控制格式标签为
PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF；运行时支持格式集合为空。`UNKNOWN`
与 `CORRUPT_OR_UNREADABLE` 维持显式异常处置，通用 parser 不允许。

候选 control-fixture parser 版本族为
`ids.parser.control_fixture.v0_1.stage049.p2`，仅用于交付证据；它们不是运行时
parser 版本。本轮没有创建或改写 parser 配置。Stage048 仍拥有 fallback，Stage050
仍拥有提示注入标记职责。

## 面向业务线的中文反馈

系统已生成可复核的受控差异评估交付证据：候选只保留为待质量核验对象，低质量、上下文
不一致、无效控制和指令样文本均有明确且克制的处置。此反馈不构成实际解析完成、质量通过、
高可信证据形成或自动化处理承诺。

## 回滚

回滚只撤回 Stage049 P4 的结构样例、非运行时处置记录、质量指标、失败分类、合同、测试和
治理投影，恢复到 `PHASE3_CONTROLLED_DIFFERENTIAL_SCENARIOS_RUNTIME_DISABLED`。必须保留
P1--P3 证据、原始资料、manifest、evidence ledger、audit 与已交付报告；不改变 GitHub、
OVH、应用或持久运行状态。

## 明确未执行与下一门

- 未打开、读取、扫描、检测或保留真实文件、页面、图像、来源正文或原始元数据；
- 未重新评估路线，未选择、分派或执行 parser，未比较候选解析正文，未执行 fallback、队列、质量门或证据提升；
- 未写入业务状态、数据库、审计、证据账本或运行时日志；
- 未启动 Agent、模型调用、模型 Token、本地服务、OVH、生产运行、上传或推送；
- 未进入整阶段复审、Stage050 或批次复审。

本 run 停在 `IDS-STAGE049-REVIEW-GATE`。下一次独立 run 才可执行
`IDS-V0_1-STAGE049-REVIEW`。
