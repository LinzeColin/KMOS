# STAGE-052 Phase 3：中英文 OCR 质量受控场景

## 本轮结论

`IDS-V0_1-STAGE052-P3` 以
`ISOLATED_NON_PRODUCTION_CONTROLLED_BILINGUAL_OCR_QUALITY_SCENARIOS` 重放 P2 的纯内存四页控制队列，并为任务包要求的五类中英文 OCR 质量情形建立明确的候选、降级或失败处置。

场景只携带固定、非业务的标量类别和 P2 控制页号：扫描 PDF、模糊图片、表格图片、中英文混合和低质量。类别不是文件、文件检测结果、页面、图像、表格、OCR 文本或真实识别结果；本步骤不声称识别准确率、表格提取质量或真实 OCR 已验证。

这是一项可执行的质量处置场景合同验证：它确认低置信度只降级为待复核候选、中英文混合会明确隔离、失败页不会静默丢弃，并确认 P2 的仅内存缓存没有产生可清理或占用内置盘的临时产物。它不替代 `STAGE-053` 的实际按页 OCR 输出、`STAGE-054` 的实际复核路由或 `STAGE-056` 的缓存保留策略。

## 覆盖与处置

| 控制类别 | P2 控制页 | 处置 | 不作出的声明 |
| --- | ---: | --- | --- |
| 扫描 PDF control | 1 | `CANDIDATE_RETAINED_QUALITY_UNASSESSED` | 未打开 PDF，未评价识别准确率 |
| 模糊图片 control | 2 | `DEGRADED_EVIDENCE_REVIEW_REQUIRED_NOT_QUEUED` | 未打开图片，未创建复核任务 |
| 表格图片 control | 1 | `CANDIDATE_RETAINED_TABLE_STRUCTURE_UNASSESSED` | 未读取表格，未提取单元格或表结构 |
| 中英文混合 control | 3 | `DEGRADED_EVIDENCE_MIXED_LANGUAGE_REVIEW_REQUIRED_NOT_QUEUED` | 未执行语言识别或实际复核 |
| 低质量 control | 4 | `FAILED_PAGE_EXPLICIT_NO_EVIDENCE_PROMOTION` | 未读取样本，未提升证据 |

五个控制情形都有明确中文反馈和处置，`silent_drop_count` 为零。低置信和中英文混合只降级为待后续复核的候选，未写入实际人工复核队列；失败页保持显式失败。所有结果仍是 `CANDIDATE` 或 `UNASSESSED`，不能直接进入高可信证据层。

## 缓存与内置盘边界

P3 重放的 P2 结果固定为 `IN_MEMORY_REBUILDABLE_NOT_PERSISTED`，`cache_created=false`、`cache_write_performed=false` 且没有缓存路径。因此本轮的缓存清理结论是 `NO_TEMPORARY_ARTIFACT_CREATED`：没有临时产物可清理，也没有实际缓存占用内置盘。实际缓存保留期、容量控制、清理执行和重跑策略仍由 `STAGE-056` 独立承担。

## 明确未执行

- 未打开、读取、扫描、渲染、保留或提交任何真实扫描 PDF、图片、表格图片、页面、来源正文或 Owner fixture；
- 未选择、配置或调用 OCR 引擎，未执行文件检测、真实路由、parser、图像处理、表格提取或准确率评估；
- 未创建持久队列、缓存、按页输出、人工复核记录、质量门、证据提升、数据库、审计、证据账本、报告或运行时日志；
- 未启动 Agent、模型调用或模型 Token 消耗，未启动本地服务、OVH、生产运行、上传或推送；
- 未进入 P4、整阶段复审或批次复审。

## 回滚与下一门

回滚只撤销本 P3 场景说明、合同、纯内存场景模块、聚焦测试、machine run、事件、事实投影、治理状态和生成中文视图，恢复到 `PHASE2_BILINGUAL_CONTROLLED_QUEUE_SLICE_ENGINE_DISABLED`。不得改变真实资料、原始元数据、manifest、evidence ledger、audit log、已交付报告、持久运行状态、GitHub、OVH 或应用状态。

下一步只能在新的独立 run 进入 `IDS-STAGE052-P4-GATE`。
