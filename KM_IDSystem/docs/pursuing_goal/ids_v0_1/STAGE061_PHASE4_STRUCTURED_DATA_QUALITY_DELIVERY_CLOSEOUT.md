# Stage061 Phase4 · 结构化数据质量交付证据与关闭说明

## 本 phase 已交付的范围

- 只从 Stage061 P3 的六类固定、非业务、reference-only control 场景派生六个 `metadata-only`
  结构化数据质量交付样例。
- 提供字段推断引用报告：仅记录六个 control 字段标签、P3 的六条质量结果候选引用与场景选择器；
  不是真实 XLSX/CSV 的字段推断、字段识别、字段映射或质量验证。
- 提供控制质量测试结果：空表、合并单元格、单位混乱、日期格式不一、异常值和重复行均有显式处置，
  静默丢弃为零，质量状态保持 `UNASSESSED`，统计结论保持关闭。
- 记录六条人工处理建议；其中合并单元格明确为
  `UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING`。这些条目是 control 类别，不是对真实
  表格结构或真实质量的观察。
- 提供只读的表格重解析和事实回滚说明：异常只允许回到
  `PHASE3_STRUCTURED_DATA_QUALITY_CONTROLLED_SCENARIOS_RUNTIME_DISABLED` 并撤回 P4 派生工件。

## 交付边界

- 六个样例均标记为
  `DELIVERY_METADATA_ONLY_STRUCTURED_DATA_QUALITY_SAMPLE_NOT_REAL_QUALITY_RESULT`；只保留控制场景、
  处置、字段标签、质量结果候选与来源定位控制引用，不含真实表格、工作表、表头、行列、单元格、
  公式、日期、数值、来源正文、文件路径或业务内容。
- 字段推断引用报告标记为
  `CONTROLLED_STRUCTURED_DATA_QUALITY_FIELD_INFERENCE_REPORT_NOT_REAL_FIELD_INFERENCE`；它不建立第二权威事实源，
  不能替代来源文档、字段映射、结构化事实、质量结果、证据绑定或数值统计。
- 质量结果标记为
  `CONTROLLED_STRUCTURED_DATA_QUALITY_TEST_RESULT_NOT_REAL_QUALITY_VALIDATION`；它不证明实际表格质量、
  真实来源追溯、真实字段完整性、真实单位/日期规范化、真实异常值判断、真实重复行判定或真实事实质量。
- 人工处理建议只向未来授权输入门说明责任边界：当前没有创建人工任务、队列、意见、质量结果、
  结构化事实或业务线结论。

## 表格重解析与事实回滚说明

1. 当前重跑只允许在内存中重放 P3 的固定 control 报告，不得打开、遍历、检测或解析真实 XLSX/CSV。
2. 若未来取得真实资料授权，必须先由业务线 owner 明确来源、授权 fixture、输入范围、质量规则、
   事实存储、证据绑定、回滚点和恢复责任。
3. 当前不存在真实质量结果库、事实库、typed value、数据库 migration 或持久化状态，因此本 phase 没有
   实际文件重解析、质量结果删除、事实删除、覆写、迁移或回滚动作。
4. P4 派生证据若不一致，只撤回 P4 说明、交付合同、纯内存模块、聚焦用例、machine run、事件、
   事实投影和治理路线；P1/P2/P3 前序证据保持不变。

## 人工确认提示

- 请业务线确认：本交付只包含结构化数据质量的 control 元数据样例，不可替代真实质量结果、
  来源证据、结构化事实或数值统计。
- 请业务线确认：六类异常均保留人工处理建议，当前没有自动解析、自动质量判定、自动质量结果写入或
  确定性模型结论。
- 请业务线确认：表格重解析和事实回滚说明只适用于未来授权输入门；当前没有真实文件、质量结果库、
  事实库或回滚动作。

## 本地验收与后续门

- P4 模块在内存中只重放 P3 control；返回
  `PASS_PHASE4_STRUCTURED_DATA_QUALITY_DELIVERY_RUNTIME_DISABLED` 时才允许记录本地交付证据。
- 本 phase 不读取真实表格或 fixture，不创建质量结果、事实、证据、数据库、人工任务、Agent、模型调用、
  模型 Token、本地服务、OVH 部署、生产运行、GitHub 上传或推送。
- 唯一后续门为新的独立 run：`IDS-STAGE061-REVIEW-GATE`。本 run 不进入整阶段复审、OVH 或上传。
