# STAGE-049 Phase 3 差异化解析器评估受控场景

## 本轮结论

`IDS-V0_1-STAGE049-P3` 以
`ISOLATED_NON_PRODUCTION_FORMAT_LABELLED_DIFFERENTIAL_SCENARIOS` 重放 Stage049 P2 的
双候选资格处置。场景只携带格式标签和 reference-only control 元数据；格式标签不是文件、
文件签名、路线结果、页面、图像、异常或解析正文。

这是一项可执行的场景合同验证：它确认各类受控输入得到明确候选、复核或不具资格处置，
并确认这些处置没有静默丢弃、没有实际 fallback，也没有使证据文本改变系统规则。它不重做
Stage046 的真实路由，也不取代 Stage048 的 fallback 所有权。

## 覆盖与处置

11 个受控场景覆盖 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF、未知、坏文件和指令样
文本：

| 控制类别 | 场景数 | P2 返回处置 |
|---|---:|---|
| PDF、DOCX、XLSX 与三类图片的候选对 | 6 | `CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW` |
| CSV、TXT 与指令样 TXT 的低质量控制 | 3 | `CONTROL_METADATA_DIVERGENCE_REVIEW_REQUIRED_NOT_QUEUED` |
| 未知格式与坏文件控制 | 2 | `COMPARISON_NOT_ELIGIBLE_CONTROL_CONTEXT_MISMATCH` 或 `COMPARISON_INVALID_CONTROL_REJECTED` |

每个场景都有明确处置，`silent_drop_count` 为零。低质量控制只保留“需要质量复核”的中文
反馈，没有创建复核队列；未知与坏文件控制保留“不具资格”或“输入无效”的明确结果。Stage048
仍是唯一 fallback 所有者，所有 P3 记录均为 `fallback_execution_performed=false`。

## 指令样文本边界

指令样 TXT 场景与普通 TXT 低质量控制返回同一处置。报告只保留
`UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY` 标签，不保留文本本身；系统指令、工具授权和策略
覆盖均为 `false`。这不替代 Stage050 的提示注入标记或扫描职责。

## 明确未执行

- 未打开、读取、扫描、检测或保留任何真实 PDF、DOCX、XLSX、CSV、TXT、图片、未知或坏文件；
- 未重新评估路线，未选择、分派或执行 parser，未创建或比较实际解析产物，未执行 fallback；
- 未创建人工复核队列，未执行质量门、证据提升、持久化、数据库、审计、证据账本或运行时日志；
- 未启动 Agent、模型调用或模型 Token 消耗，未启动本地服务、OVH、生产运行、上传或推送；
- 未进入 P4、整阶段复审或批次复审。

## 回滚与下一门

回滚只撤销 P3 受控场景模块、合同、聚焦测试、machine run 和治理投影，恢复到 P2 的仅内存
资格切片。它不改变真实资料、manifest、evidence ledger、audit log、已交付报告、持久运行
状态、GitHub、OVH 或应用状态。下一步只能在新的独立 run 进入 `IDS-STAGE049-P4-GATE`。
