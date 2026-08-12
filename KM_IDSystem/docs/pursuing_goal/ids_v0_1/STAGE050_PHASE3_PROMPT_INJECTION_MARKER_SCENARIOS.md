# STAGE-050 Phase 3：提示注入标记受控场景

## 本轮结论

`IDS-V0_1-STAGE050-P3` 以
`ISOLATED_NON_PRODUCTION_FORMAT_LABELLED_PROMPT_MARKER_SCENARIOS` 重放 P2 的仅内存
标记切片。场景只携带格式标签、reference-only control 元数据和固定非业务 control 文本；
格式标签不是文件、文件签名、路线结果、页面、图像、异常或解析正文。

这是一项可执行的场景合同验证：它确认各类受控输入都有明确的 evidence-only、未排队复核或
输入拒绝处置，确认没有静默丢弃、没有实际 fallback，也确认指令样 control 不能覆盖系统规则。
它不重做 Stage045 文件检测、Stage046 路由、Stage047 解析输出、Stage048 fallback 或 Stage049
差异评估。

## 覆盖与处置

11 个受控场景覆盖 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF、未知、坏输入和指令样文本：

| 控制类别 | 场景数 | 明确处置 |
|---|---:|---|
| PDF、DOCX、XLSX 与三类图片的普通 control | 6 | `CONTROL_CANDIDATE_MARKED_EVIDENCE_ONLY` |
| CSV 与 TXT 的低质量 control | 2 | `CONTROL_LOW_QUALITY_REVIEW_REQUIRED_NOT_QUEUED` |
| 指令样 TXT control | 1 | `CONTROL_INSTRUCTION_TEXT_MARKED_EVIDENCE_ONLY` |
| 未知格式与坏输入 control | 2 | `CONTROL_UNKNOWN_FORMAT_NOT_ELIGIBLE` 或 `CONTROL_BAD_INPUT_REJECTED` |

每个场景都有明确处置，`silent_drop_count` 为零。低质量 control 只返回“需要复核”的中文反馈，
没有创建复核队列；Stage048 仍是唯一 fallback 所有者，所有 P3 记录均为
`fallback_execution_performed=false`。

## 指令样文本边界

指令样 TXT control 被标记为 `CONTROL_INSTRUCTION_TEXT_MARKED_EVIDENCE_ONLY`，且只保留
`UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY` 解释。系统指令、工具授权和策略覆盖均为 `false`；
control 文本既不返回也不持久化。这不等于运行时提示注入标记或实际文档扫描。

## 明确未执行

- 未打开、读取、扫描、检测或保留任何真实 PDF、DOCX、XLSX、CSV、TXT、图片、未知或坏文件；
- 未重新评估路线，未选择、分派或执行 parser，未创建或比较实际解析产物，未执行 fallback；
- 未创建人工复核队列，未执行运行时标记、质量门、证据提升、持久化、数据库、审计、证据账本或运行时日志；
- 未启动 Agent、模型调用、本地服务、OVH、生产运行、上传或推送；
- 未进入 P4、整阶段复审或批次复审。

## 回滚与下一门

回滚只撤销 P3 受控场景模块、合同、聚焦测试、machine run 和治理投影，恢复到 P2 的仅内存标记
切片。它不改变真实资料、manifest、evidence ledger、audit log、已交付报告、持久运行状态、GitHub、
OVH 或应用状态。下一步只能在新的独立 run 进入 `IDS-STAGE050-P4-GATE`。
