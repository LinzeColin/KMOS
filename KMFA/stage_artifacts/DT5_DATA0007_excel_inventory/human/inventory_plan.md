# DATA.0007 阶段一：40 Excel 盘点与适配器覆盖计划（2026-07-17）

- 盘点：40/40 成功，共 372 个 sheet；公开面零单元格值、零 sheet 名明文（全清单在 .codex_private_runtime）
- 归类：operating_analysis 11 ｜ collection 6 ｜ invoicing 4 ｜ loan 4 ｜ contract/journal/aging/tax 各 1 ｜ unknown 11
- 覆盖路线（阶段二执行序）：
  1. **24 个文件**匹配既有 v0.1.4 规格（finance_file_adapter 的 operating_analysis/journal + wps_file_adapter 的 collection/aging/invoicing/payment_approval/contract）→ 优先接抽取
  2. **5 个文件**需新建规格（kingdee_ledger/tax_filing/loan/performance/primary_data）→ 按 S07 规格表范式扩展
  3. **11 个 unknown_deferred** → 对照私有全量清单人工归类后回填关键词映射（显式 deferred，符合任务包"未映射列显式登记"）
- 幂等落库：抽取结果进 _staging（DATA.0006 基座），idempotency_key=源指纹+sheet+抽取器版本
