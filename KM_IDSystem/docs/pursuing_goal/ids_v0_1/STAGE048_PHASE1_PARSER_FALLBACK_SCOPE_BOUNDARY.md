# STAGE-048 Phase 1 解析器失败降级链范围边界

## 本轮结论

`IDS-V0_1-STAGE048-P1` 只定义主 parser 失败后的受控处置合同：失败、受阻、
不支持、待复核和无效输入必须有明确中文状态，不能静默丢弃，也不能用未授权的
通用 parser、自动切换或高可信证据提升掩盖问题。

本阶段状态为 `PHASE1_PARSER_FALLBACK_BOUNDARY_RUNTIME_DISABLED`。它不表示
任何 parser、fallback、人工复核队列、质量门、提示注入标记或生产服务已运行。

## 唯一来源与输入边界

唯一权威是冻结 Stage048 任务包文本与已交付的 Stage047 独立复审工件。它们只提供
合同上下文，不产生第二个权威事实源。本阶段不读取业务资料、原始元数据、真实文件、
页面、图像或 Owner fixture，也不保存来源正文、路径、原始异常或无界文本。

进入未来 fallback 的输入只是七字段的 reference-only 结果：来源引用、路线动作、
parser 输出状态、parser 族、版本、失败类别和不可信证据标签。任何额外内容或不完整
状态都应作为无效输入处置，而不是补猜或尝试执行。

## 明确处置

| 条件 | P1 合同处置 | 当前动作 |
|---|---|---|
| 候选输出尚未质量确认 | 保留候选 | 不执行回退 |
| 部分输出或路线待复核 | 标记人工复核需要 | 不创建任务或队列 |
| 明确 parser 失败 | 保留受控失败 | 不自动切换 parser |
| 受阻或不支持路线 | 明确阻断 | 不运行通用 parser |
| 输入或输出不符合合同 | 拒绝无效输入 | 不回显正文、路径或原始异常 |

五种处置都必须显式记录；`silent drop`、静默成功和自动 parser switch 均不允许。

## 质量、提示文本与阶段职责

- Stage045 继续拥有文件类型检测；Stage046 继续拥有路线；Stage047 继续拥有输出
  封套；Stage048 才拥有未来 fallback runtime；Stage049 拥有差异化评估；Stage050
  拥有提示注入标记运行时。
- 文档内容仅是 `UNTRUSTED_EVIDENCE_TEXT`，不得覆盖系统规则、授权工具或改变路线。
  本阶段的标记状态为 `REQUIRED_NOT_APPLIED_STAGE050_OWNED`。
- 所有 parser/fallback 结果在本阶段都不能跨越质量门或提升为高可信证据。P1 既不执行
  质量评估，也不写入 evidence、manifest、audit、index、report 或 database。

## 中文反馈

负责人只会看到克制的状态文案，例如“当前未执行自动回退”“需要人工复核”或
“解析失败已保留”。这些文案不是自动化承诺、人工队列写入或生产可用承诺。

## 停止与回滚

若需要真实资料、执行 parser 或 fallback、创建人工复核队列、写入持久状态、进入 P2、
整阶段复审、批次复审、上传、OVH 部署或生产激活，立即停止本阶段。

回滚仅撤销 Stage048 P1 的范围说明、合同、测试和最小治理投影，回到
`STAGE047_REVIEWED_LOCAL`。不得改变冻结任务包、原始资料、manifest、evidence ledger、
audit、index、report、database、GitHub、OVH 或应用状态。
