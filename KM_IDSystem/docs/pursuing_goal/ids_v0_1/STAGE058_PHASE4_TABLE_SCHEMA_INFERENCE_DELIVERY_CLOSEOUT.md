# Stage058 Phase4 · 表格 Schema 推断交付证据与关闭说明

## 本 phase 已交付的范围

- 只从 Stage058 P3 的六类固定、非业务、reference-only control 场景派生六个 `metadata-only` 表格 Schema 交付样例。
- 提供字段推断引用报告：仅记录 P3 control 涉及的六个候选字段标签和引用计数，不是实际 XLSX/CSV 的 schema 推断、字段识别或事实抽取。
- 提供控制质量结果：空表、合并单元格、单位混乱、日期格式不一、异常值和重复行均有显式处置，静默丢弃为零。
- 记录六条人工处理建议；其中合并单元格明确为 `UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING`。这些条目是 control 类别，不是对真实表格结构的观察。
- 提供只读的重解析和事实回滚说明：异常只允许回到 `PHASE3_TABLE_SCHEMA_INFERENCE_CONTROLLED_QUALITY_SCENARIOS_RUNTIME_DISABLED` 并撤回 P4 派生工件。

## 交付边界

- 六个样例均标记为 `DELIVERY_METADATA_ONLY_SCHEMA_PROFILE_SAMPLE_NOT_REAL_TABLE_FACT`；只保留控制场景、处置和来源定位引用，不含真实表格、工作表、表头、行列、单元格、公式、日期、数值、文件路径或业务内容。
- 字段引用报告标记为 `CONTROLLED_FIELD_INFERENCE_REPORT_NOT_REAL_SCHEMA_INFERENCE`；它不建立第二权威事实源，不能替代来源文档、结构化事实、证据绑定或数值统计。
- 质量结果标记为 `CONTROLLED_TABLE_SCHEMA_QUALITY_TEST_RESULT_NOT_REAL_TABLE_VALIDATION`；它不证明实际表格质量、真实来源追溯、真实单位/日期规范化、异常值判断或重复行判定。
- 人工处理建议只向未来授权输入门说明责任边界：当前没有创建人工任务、队列、意见、事实或业务线结论。

## 重解析与事实回滚说明

1. 当前重跑只允许在内存中重放 P3 的固定 control 报告，不得打开、遍历、检测或解析真实 XLSX/CSV。
2. 若未来取得真实资料授权，必须先由业务线 owner 明确来源、授权 fixture、输入范围、事实存储、证据绑定、回滚点和恢复责任。
3. 当前不存在真实事实库、typed value、数据库 migration 或持久化事实，因此本 phase 没有实际文件重解析、事实删除、覆写、迁移或回滚动作。
4. P4 派生证据若不一致，只撤回 P4 说明、交付合同、纯内存模块、聚焦用例、machine run、事件、事实投影和治理路线；P1/P2/P3 前序证据保持不变。

## 人工确认提示

- 请业务线确认：本交付只包含表格 Schema control 元数据样例，不可替代真实表格事实、来源证据或数值统计。
- 请业务线确认：六类异常均保留人工处理建议，当前没有自动解析、自动事实写入或确定性模型结论。
- 请业务线确认：重解析和事实回滚说明只适用于未来授权输入门；当前没有真实文件、事实库或回滚动作。

## 本地验收与后续门

- P4 模块在内存中只重放 P3 control；返回 `PASS_PHASE4_TABLE_SCHEMA_INFERENCE_DELIVERY_RUNTIME_DISABLED` 时才允许记录本地交付证据。
- 本 phase 不读取真实表格或 fixture，不创建事实、证据、数据库、RAG 摘要、人工任务、Agent、模型调用、模型 Token、本地服务、OVH 部署、生产运行、GitHub 上传或推送。
- 唯一后续门为新的独立 run：`IDS-STAGE058-REVIEW-GATE`。本 run 不进入整阶段复审、OVH 或上传。
