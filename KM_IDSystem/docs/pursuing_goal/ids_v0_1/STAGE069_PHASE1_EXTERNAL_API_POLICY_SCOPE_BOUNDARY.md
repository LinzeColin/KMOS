# STAGE-069 Phase 1：外部 API 策略继承范围、输入输出与边界确认

## 当前结论

本步骤只定义 `IDS-V0_1-STAGE069-P1` 的静态外部 API 策略继承合同。唯一合同上下文是冻结
Stage069 任务包、Stage068 已完成本地整阶段机械复审、v0.1 根锁和既有普通人操作说明。合同只登记
data source/document 到 chunk 的自动策略继承、默认 `denied`、`denied` / `summary_only` /
`full_text_allowed` 三档策略、未来 Embedding 队列、成本控制、模型版本、审计字段、失败关闭、中文反馈和
回滚边界；没有读取、打开、解析、汇总、切分、外发、创建队列、缓存、审计、索引、数据库或业务结论。

所有 `data_source_ref`、`document_ref`、`chunk_ref`、授权、provider、model、版本、队列和审计字段均为
不透明受控引用或未来 schema 标签，当前不得填入原文、摘要正文、文本块、物理路径、URI、凭证、实际
provider、实际模型、实际 token、实际成本或任何真实业务资料。默认策略继续是 `denied`，本步骤没有
外部 API 请求、模型调用或模型 Token 消耗。

## 策略继承与白箱边界

| 层级 | 静态规则 | 本步骤状态 |
| --- | --- | --- |
| data source | 默认 `denied`；可声明三档允许值 | 未读取真实 source |
| document | 默认继承 source；只能请求更严格策略，不能放宽 source | 未解析或写入 document |
| chunk | 自动继承有效 document 策略；owner 不逐条标记 | 未创建或标记 chunk |

有效策略按 `MOST_RESTRICTIVE_AUTHORIZED_SOURCE_DOCUMENT_POLICY` 解析。未知值、缺少策略或 document
试图放宽 source 均失败关闭；例外只能在未来由业务线白箱人工复核处理。策略合同、审计标签、未来模型
输出和本步骤文档都不能替代来源文档，不能形成业务事实或自动决策。

## 三档未来操作流程

- `denied`：不创建外部 payload、不外发摘要或文本块、不创建未来 Embedding 队列。
- `summary_only`：只在未来本地已存在经授权摘要且预算/审计门均通过时处理摘要引用；原文和文本块仍不外发。
- `full_text_allowed`：只在未来继承策略、授权、预算和审计均通过时处理文本块；本步骤不选择 provider/model、
  不创建请求、也不发送任何内容。

未来审计必须能关联 source、document、chunk、有效策略、继承原因、谁授权、何时授权、授权原因、provider、
model、模型版本、token、成本、队列、预算状态和处理结果。未来预算未知或不足必须暂停任务。以上都是静态
字段合同，不代表已经形成审计记录、成本估算或实际调用。

## 失败、中文反馈与回滚

策略缺失/非法、source `denied`、document 放宽、chunk 人工改标、摘要/全文授权不完整、预算未知或不足、
provider/model/version 未选择、审计字段不完整，或试图在 P1 执行外部 API 时，未来流程必须关闭。中文反馈
明确说明禁止外发、摘要仅限未来授权处理、全文必须经过未来门禁，以及策略会自动继承到 chunk。

回滚只允许移除本步骤的范围说明、静态合同、聚焦用例、machine run、事件、机器事实投影、治理路线和生成
中文视图，恢复到 `STAGE068_REVIEWED_LOCAL_QUALITY_DEGRADATION_RUNTIME_DISABLED`。不改变真实资料、原始
元数据、manifest、evidence ledger、audit log、已交付报告、数据库、索引、GitHub、OVH 或应用状态。

一旦需要真实资料、授权 fixture、真实摘要、真实 chunk、provider 凭证、外部 API、模型、Token、Embedding
队列/缓存、数据库、索引、OVH、生产、Phase2、整阶段复审、批次复审、上传或推送，立即停止本步骤。

## 后续门

本步骤通过后的唯一后续门为 `IDS-STAGE069-P2-GATE`，且必须由新的独立 run 进入。
