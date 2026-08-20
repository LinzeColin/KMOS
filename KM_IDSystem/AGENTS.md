# KM_IDSystem Agent 规则

默认用户可见输出使用中文。

## S4 精简执行胶囊

普通任务先读本文件、`README.md` 和被任务直接点名的任务/证据文件；不得扫描无关项目。

- 不得读取完整 `模型参数文件.md`，除非变更涉及路由、优化规则、安全策略、评分、阈值、
  模型参数或发布验收。
- 治理验证：`python -B scripts/lean_governance.py validate --project KM_IDSystem --semantic`。
- owner 预览：`python -B scripts/lean_governance.py check-render --project KM_IDSystem`。
- 应用变更先补任务点名的窄后端/前端测试，再考虑 broad test discovery。

## 边界

- 不得编造 owner 决策或生产就绪结论。
- 数据、缓存、本地运行输出和 secrets 不得进入 Git，除非当前任务明确允许提交脱敏证据。

- **结论**：整阶段复审必须同时失败关闭 P1--P4 合同、控制报告、状态形状与零运行时边界。
  **为什么**：单独的 P4 交付通过不能证明 P1--P3 未漂移；Review 必须保留 P4→P3 回退，并把后继严格停在下一阶段 P1 门禁。
  **代价**：没量。

- **结论**：Stage074 P1 的本地 Embedding 兜底只能以未选模型、未执行的静态合同交付。
  **为什么**：在业务线白箱人工复核、单一权威和零 Token 生产边界下，模型选择、下载、Embedding、索引、队列或审计写入都属于后续受控门，不能被 P1 提前宣称或执行。
  **代价**：没量。
