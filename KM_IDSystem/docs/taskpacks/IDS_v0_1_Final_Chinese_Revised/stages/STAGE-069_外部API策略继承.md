# STAGE-069 · 外部 API 策略继承

- 本地编号：D12-S001
- 当前版本：v0.1
- 能力域：D12 · Embedding 与外部 API 策略
- 入口：IDS 系统运营入口
- Acceptance ID：ACC-STAGE-069
- 建议并行度：否
- 并行说明：本 Stage 涉及共享契约、状态机、数据库、索引、证据、报告或执行规则，建议单独完成后再进入下游。
- 预计实际执行开发时间：8-16 小时

## 追求目标（Pursuing Goal）

让 data source/document 的 external_api_policy 自动继承到 chunk，不要求 owner 手动标 chunk。

## Codex 执行范围

### 允许

- 只处理本 Stage 明确相关文件。
- 可以新增本 Stage 所需的代码、schema、测试、配置、文档或 UI 切片。
- 必须输出修改文件列表、真实测试结果、验收证据和回滚说明。

### 禁止

- 不得提交真实原始资料。
- 不得提交 secrets、API key、数据库密码或云端凭证。
- 不得移动、删除、覆盖 `00_ORIGINAL_RAW_DATA`。
- 不得把旧产品名用于新 UI、报告、文档显示名。
- 不得声称测试通过但没有真实测试输出。
- 不得扩大到其他 Stage 的范围。

## Phase / Task

### Phase 1：范围、输入输出与边界确认
1. 定义外部 API 策略继承、Embedding 队列、成本控制、模型版本和审计。
2. 确认默认 external_api_policy=denied，owner 不需要逐条标记 chunk。
3. 定义 denied、summary_only、full_text_allowed 的操作流程和审计字段。

### Phase 2：实现、接入与最小可运行切片
1. 实现策略继承、Embedding 队列、缓存、成本估算或模型版本记录。
2. 禁止未授权 chunk 外发，允许授权 source/document 自动继承到 chunk。
3. 记录 provider、model、token、chunk_id、policy reason。

### Phase 3：外部 API 策略继承 专项验证与异常场景
1. 验证 denied 不外发、summary_only 只外发摘要、full_text_allowed 才外发文本块。
2. 验证预算不足时暂停外部 API 任务。
3. 验证每次外部 API 调用都有审计记录。

### Phase 4：外部 API 策略继承 交付证据、回滚与中文反馈
1. 交付外部 API 策略样例、审计日志、成本估算和失败处理结果。
2. 记录哪些数据没有外发及原因。
3. 提供策略回滚和外发记录查询说明。

## 验收标准

- 追求目标对应能力已经可运行，或已形成可执行、可测试、可回滚的工程合同。
- 本 Stage 的失败状态、停止条件、审计记录、回滚路径明确。
- 本 Stage 不破坏原始资料、manifest、证据账本、审计日志和已交付报告。
- 相关测试、场景验证或文档证据真实存在。
- 中文交互反馈清楚、克制、面向企业用户，不使用夸大或 AI 化承诺。

## 停止条件

- 需要真实资料但没有 fixture 或 owner 授权样本。
- 可能删除、移动、覆盖原始文件。
- schema migration 无法回滚。
- 测试失败且原因不明。
- 修改范围超出本 Stage。
- 并行开发导致共享文件冲突。

## 回滚方式

回滚本 Stage 的代码、schema、配置或 UI 变更；不得影响原始资料、manifest、evidence ledger、audit log 和已交付报告。若本 Stage 产生派生产物，应只清理明确允许清理的临时文件或可重建缓存。
