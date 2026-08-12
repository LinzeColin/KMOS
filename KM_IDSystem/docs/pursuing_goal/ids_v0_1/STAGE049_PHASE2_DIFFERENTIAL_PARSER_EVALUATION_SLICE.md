# STAGE-049 Phase 2 差异化解析器评估最小切片

## 本轮结论

`IDS-V0_1-STAGE049-P2` 实现一个
`ISOLATED_NON_PRODUCTION_IN_MEMORY_DIFFERENTIAL_ELIGIBILITY_SLICE`。它只对两个
reference-only 的 control-fixture 候选记录执行资格与元数据一致性判断，记录候选的
parser 版本和解析置信度，并返回克制的中文处置。

它不是文件签名识别、parser route、真实 fallback、真实 parser 或解析正文比较。它不读取
文件、不创建实际解析产物、不计算质量分数，也不表明任何生产服务可用。

## 输入与实现

入口 `evaluate_controlled_differential_eligibility` 位于
`differential_parser_evaluation/stage049_differential_parser_evaluation_slice.py`。输入只有
`candidate_controls` 一个顶层字段，且固定为两个候选 control wrapper。每个 wrapper 只有：

1. `candidate_reference`：P1 固定的七字段 reference-only 元数据；
2. `parser_confidence`：`HIGH`、`MEDIUM`、`LOW` 或 `UNKNOWN`。

候选版本只允许 `ids.parser.control_fixture.v0_1.stage049.p2.*` 这一 control-fixture
命名空间；它们不是 Stage046 路由表中的实际 parser，也不会创建 parser 配置。输入只允许
`source:control:` 引用、既有 `ROUTE_CANDIDATE_READY_NOT_EXECUTED` 路线、Stage047 输出合同
版本及 `UNTRUSTED_EVIDENCE_TEXT` 标签。来源正文、路径、文件字节、原始异常和业务资料均不
能进入切片。

## 受控处置

| 控制结果 | 返回处置 | 中文反馈 |
|---|---|---|
| 同一控制上下文、两个不同版本、均为候选状态 | `CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW` | 两个候选版本已完成受控资格检查，仍需质量复核。 |
| 至少一个候选为部分结果 | `CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED` | 候选解析状态不一致，需要质量复核。 |
| 两个候选版本相同 | `COMPARISON_NOT_ELIGIBLE_INSUFFICIENT_DISTINCT_VERSIONS` | 候选版本数量不足，当前不具备差异化比较条件。 |
| 控制来源、路线、输出合同或证据标签不一致 | `COMPARISON_NOT_ELIGIBLE_CONTROL_CONTEXT_MISMATCH` | 候选控制上下文不一致，当前不具备比较条件。 |
| 非合同输入 | `COMPARISON_INVALID_CONTROL_REJECTED` | 候选控制输入无效，未执行差异化比较。 |

这里的“资格检查”只比较受控元数据，`semantic_parse_product_comparison_performed=false`。
它不会读取或比较 `text/tables/pages/sections/confidence/errors` 中的内容，也不会产出实际
解析产物或持久化比较结果。

## 证据文本、质量与降级边界

每个候选固定返回 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`；文档中的类似指令始终是证据
数据，不能覆盖系统规则、授权工具或改变策略。P2 不代替 Stage050 的运行时提示标记职责。

合格候选仍然只是 `CANDIDATE`，质量状态仍为 `UNASSESSED`。切片不执行质量门、不提升
高可信证据、不创建人工复核任务，也不改变 Stage048 的 fallback 责任；每个不具资格或需
复核结果都有明确处置，且 `fallback_execution_performed=false`。

## 明确未执行

- 未打开、扫描、识别或读取任何文件，未评估真实路线；
- 未选择、分派或执行 parser，未创建真实解析产物或比较正文；
- 未执行真实 fallback、质量门、提示注入标记、人工复核队列、持久写入或数据库连接；
- 未启动 Agent、模型调用或模型 Token 消耗，未启动本地服务、OVH 或生产运行；
- 未进入 P3、整阶段复审、批次复审、GitHub 上传或推送。

## 回滚与下一门

回滚只撤销本 P2 切片、合同、聚焦测试和治理投影，恢复到
`PHASE1_DIFFERENTIAL_PARSER_EVALUATION_BOUNDARY_RUNTIME_DISABLED`；不改变真实资料、
manifest、evidence ledger、audit log、已交付报告、持久运行状态、GitHub、OVH 或应用状态。
下一步只能在新的独立 run 进入 `IDS-STAGE049-P3-GATE`。
