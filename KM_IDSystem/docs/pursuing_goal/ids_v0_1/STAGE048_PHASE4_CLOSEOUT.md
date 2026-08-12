# STAGE-048 Phase 4 解析失败降级链交付收口

## 本轮结论

- 任务：`IDS-V0_1-STAGE048-P4`
- 验收：`ACC-STAGE-048`
- 执行模式：`ISOLATED_NON_PRODUCTION_FALLBACK_CLOSEOUT`
- 结果：`PASS_ISOLATED_FALLBACK_CLOSEOUT_RUNTIME_DISABLED`
- 下一门：`IDS-STAGE048-REVIEW-GATE`

本轮只完成 P4 的非运行时交付证据；整阶段复审、Stage049、批次复审、GitHub 上传和
OVH 部署均未进入。

## 交付内容

P4 重放 P3 的 14 个格式标签化、仅引用控制场景，派生而非运行：

- 8 个 `SCHEMA_ONLY_PARSER_OUTPUT_SAMPLE_NOT_EXECUTED` 结构样例，覆盖 PDF、DOCX、
  XLSX、CSV、TXT、PNG、JPEG 和 TIFF；每个样例只包含 `text`、`tables`、`pages`、
  `sections`、`confidence`、`errors` 六字段的空结构和受控状态，不含正文、表格单元、
  页面文本、路径或原始异常；
- 14 条 `DERIVED_CONTROL_DISPOSITION_LOG_NOT_RUNTIME` 处置记录，逐一保留场景、格式标签、
  版本、置信度、明确处置与中文反馈码；`attempted=false`、`attempt_count=0`、
  `silent_drop=false`、`parser_switch_performed=false`；
- 由 P3 结果派生的质量指标、失败分类、支持边界和版本/配置回滚说明。

这些样例与记录不是 parser 输出或 fallback runtime 日志，也不证明真实格式、真实 parser、
人工复核队列、质量门、持久化或生产服务可用。

## 指标、失败分类与格式边界

场景 `14/14` 通过，明确处置 `14/14`，静默丢弃为 `0`。8 个控制格式样例覆盖率为 `1.0`，
运行时支持格式集合为空；parser 执行、fallback 执行和持久写入均为 `0`。

6 个互斥分类完整覆盖 14 个场景：

1. `PARSER_IMPLEMENTATION_UNAVAILABLE`：6 个 parser 不可用格式；
2. `QUALITY_REVIEW_REQUIRED`：CSV 与普通 TXT 的复核；
3. `OWNER_REVIEW_REQUIRED`：未知、冲突与低置信结果；
4. `EXPLICIT_INPUT_BLOCKED`：坏文件；
5. `UNSUPPORTED_FORMAT`：未支持格式；
6. `UNTRUSTED_INSTRUCTION_TEXT_REVIEW`：指令样 TXT。

最后一类仍与普通 TXT 保持同一复核处置，固定为 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`，
不能覆盖系统规则、工具授权或策略。Stage050 的提示注入职责没有被提前执行。

控制格式覆盖不等于运行时支持：`runtime_supported_formats=[]`，没有通用 parser，未知、
损坏、未支持或未列入的格式只保留复核或显式处置。

## 版本与回滚

交付仅记录 P2 control-fixture parser 版本
`ids.parser.control_fixture.v0_1.stage048.p2`；它不是运行时 parser 版本。本轮没有创建或
修改 parser 配置。

回滚只撤销 P4 的结构样例、非运行时处置记录、指标、分类、合同、测试和治理投影，恢复到
`PHASE3_CONTROLLED_FALLBACK_SCENARIOS_RUNTIME_DISABLED`。必须保留 P1-P3 证据、原始资料、
manifest、evidence ledger、audit 与已交付报告；不改变 GitHub、OVH 或应用运行状态。

## 明确未执行与下一门

- 未打开、读取、扫描、检测或保留真实文件、页面、图像或原始元数据；
- 未重新评估路线，未分派或执行 parser，未执行 fallback、队列、质量门或证据提升；
- 未写入业务状态、数据库、审计、证据账本或运行时日志；
- 未启动 Agent、模型调用、模型 Token、本地服务、OVH、生产运行、上传或推送；
- 未进入整阶段复审、Stage049 或批次复审。

本 run 停在 `IDS-STAGE048-REVIEW-GATE`。下一次独立 run 才可执行
`IDS-V0_1-STAGE048-REVIEW`。
