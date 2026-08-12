# STAGE-048 Phase 3 解析失败降级受控场景

## 本轮结论

`IDS-V0_1-STAGE048-P3` 以
`ISOLATED_NON_PRODUCTION_CONTROLLED_FALLBACK_SCENARIOS` 验证既有 P2
纯内存降级处置。场景仅携带格式标签和已受控的七字段引用，不是文件、内容、页面、
图像、异常或真实路由结果。P3 复用 Stage046 已交付的仅元数据路线语义，但不重新
检测、评估或执行路线。

## 覆盖与处置

14 个受控场景覆盖 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF、未知、坏文件、
信号冲突、低置信、未支持格式和指令样文本：

| 类别 | 场景数 | P2 返回处置 |
|---|---:|---|
| 已治理高置信格式但 parser 不可用（含三类图片） | 6 | `BLOCKED_OR_UNSUPPORTED_NO_FALLBACK` |
| CSV、TXT、未知、冲突、低置信和指令样文本 | 6 | `HUMAN_REVIEW_REQUIRED_NOT_QUEUED` |
| 坏文件与未支持格式 | 2 | `BLOCKED_OR_UNSUPPORTED_NO_FALLBACK` |

每个场景都有明确处置；`silent_drop_count` 为零。低质量、未知、冲突和低置信结果
只要求人工复核，当前没有创建队列。坏文件与不支持格式保留显式阻断，不触发通用
parser、自动切换或真实 fallback。

## 指令样文本边界

指令样 TXT 场景与普通 TXT 复核场景返回相同处置。整个报告只保留
`UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY` 标签，不保留文本；系统指令、工具授权和
策略覆盖均为 `false`。这不替代 Stage050 的提示注入标记或扫描职责。

## 明确未执行

- 未打开、读取、扫描、检测或保留任何真实 PDF、DOCX、XLSX、CSV、TXT、图片或坏文件；
- 未重新评估路线，未分派或执行 parser，未执行 fallback、人工复核队列、质量门或证据提升；
- 未写入业务状态、数据库、审计、证据账本或运行时日志；
- 未启动 Agent、模型调用或模型 Token 消耗，未启动本地服务、OVH、生产运行、上传或推送；
- 未进入 P4、整阶段复审或批次复审。

## 回滚与下一门

回滚只撤销 P3 受控场景模块、合同、聚焦测试和治理投影，回到 P2 的纯内存降级处置
切片。它不改变真实资料、持久运行状态、GitHub、OVH 或应用状态。下一步只能在新的
独立 run 进入 `IDS-STAGE048-P4-GATE`。
