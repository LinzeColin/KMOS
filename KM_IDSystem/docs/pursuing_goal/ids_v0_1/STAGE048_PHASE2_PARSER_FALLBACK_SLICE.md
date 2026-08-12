# STAGE-048 Phase 2 解析器降级处置切片

## 本轮结论

`IDS-V0_1-STAGE048-P2` 实现一个
`ISOLATED_NON_PRODUCTION_IN_MEMORY_FALLBACK_DISPOSITION_SLICE`。它是冻结任务包
允许的 fallback chain 切片：只对 P1 已定义的 reference-only 控制记录返回明确
中文处置。它可以被直接调用和测试，但不表示真实 parser、真实 fallback、人工复核
队列或生产服务已经可用。

## 输入与实现

入口 `resolve_control_fallback` 位于
`parser_fallback/stage048_fallback_slice.py`。输入只有两个顶层字段：

1. `fallback_reference`：P1 的七字段仅引用结果；
2. `parser_confidence`：`HIGH`、`MEDIUM`、`LOW` 或 `UNKNOWN`。

该切片只接受 `source:control:` 前缀的内存控制引用与固定的 control-fixture
parser 族/版本。它不接收正文、路径、文件字节、原始异常或业务资料。版本和置信度
只记录在返回的内存记录中，不写入日志或任何持久状态。

P2 选择任务包中的 fallback chain 选项；文件签名识别和 parser route 仍分别属于
Stage045/046，差异化解析评估仍属于 Stage049。

## 明确处置

| 受控结果 | 返回处置 | 中文反馈 |
|---|---|---|
| 候选未验证 | `NO_FALLBACK_CANDIDATE_RETAINED` | 当前结果保持候选状态，不执行自动回退。 |
| 部分结果或需复核 | `HUMAN_REVIEW_REQUIRED_NOT_QUEUED` | 需要人工复核，当前未创建复核任务。 |
| 明确 parser 失败 | `EXPLICIT_FAILURE_RETAINED_NOT_DROPPED` | 解析失败已保留，不执行自动回退或丢弃。 |
| 路线受阻或不支持 | `BLOCKED_OR_UNSUPPORTED_NO_FALLBACK` | 不执行回退，请人工复核。 |
| 非合同输入 | `INVALID_OUTPUT_REJECTED_NO_FALLBACK` | 输入状态无效，不执行回退并请人工复核。 |

没有匹配的控制组合会进入最后一项，因而不会静默消失，也不会改选 parser。

## 文档文本与质量边界

所有输入和输出固定保留 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY` 标签；没有正文
被读取或解释。`system_instruction_allowed`、`tool_authorization_allowed` 和
`policy_override_allowed` 都是 `false`。这只是 Stage048 的标签执行，不替代
Stage050 的提示注入标记职责。

切片不运行质量门，也不提升任何证据。`parser_confidence` 仅是被记录的受控字段，
不构成质量通过、来源证明或高可信证据。

## 明确未执行

- 未打开、扫描、识别或读取任何文件；
- 未评估真实路由，未选择、分派或执行 parser；
- 未执行真实 fallback，未创建人工复核队列，未写日志、状态或数据库；
- 未启动 Agent、模型调用或模型 Token 消耗，未启动本地服务、OVH 或生产运行；
- 未进入 P3、整阶段复审、批次复审、GitHub 上传或推送。

## 回滚与下一门

回滚只撤销本 P2 切片、合同、聚焦测试和治理投影，恢复到 P1 的静态降级边界；不改变
真实资料、持久运行状态、GitHub、OVH 或应用状态。下一步只能在新的独立 run 进入
`IDS-STAGE048-P3-GATE`。
