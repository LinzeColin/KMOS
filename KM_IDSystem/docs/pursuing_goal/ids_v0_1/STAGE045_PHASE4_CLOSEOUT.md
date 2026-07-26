# STAGE-045 Phase 4 关闭与交付

- Task：`IDS-V0_1-STAGE045-P4`
- Acceptance：`ACC-STAGE-045`
- 结果：`PASS_ISOLATED_FILE_TYPE_DETECTION_CLOSEOUT_PARSER_DISABLED`
- 合同：`file_type_detection/stage045_file_type_detection_delivery_contract.json`
- 检查器：`KM_IDSystem/scripts/check_file_type_detection_delivery.py`
- 下一门：`IDS-STAGE045-REVIEW-GATE`
- 整阶段复审：本轮未执行，必须由下一个独立 run 完成

## 来源与前置绑定

P4 继续绑定唯一 Stage045 task-pack member：
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-045_文件类型检测.md`，SHA-256 为
`4eac237a7f63d764cf71789d4949a5168cbe8fe24e1fe7eb816baabe04bb4d27`。
前置提交固定为 P3 `dea3c486aceaaa34837aa4a6c9262a907e8dccba`，其 root tree 为
`ae1dfb9d1135cf578857fda9d6368ef0e2b4a4e7`，`KM_IDSystem` tree 为
`2a95d14bee023d2c1a3f4965a3206d0299c4b74d`，父提交为
`082565a958459fb4b9ad2b951a74982c30311a03`。检查器还逐项验证 P3 合同、检查器、测试、
证据与 machine run 的 Git index 哈希；来源、祖先或上游漂移均回到
`IDS-STAGE045-P4-GATE`。

## parser 输出样例

本轮为六类候选 route 交付统一结构样例：`PDF_PARSER`、`OOXML_WORD_PARSER`、
`OOXML_WORKBOOK_PARSER`、`DELIMITED_TEXT_PARSER`、`PLAIN_TEXT_PARSER` 与
`IMAGE_PARSER`。每项只包含以下六个合同字段：

- `text: null`
- `tables: []`
- `pages: []`
- `sections: []`
- `confidence: UNKNOWN`
- `errors: []`

所有样例均标记 `SCHEMA_ONLY_NOT_EXECUTED`、`UNASSIGNED_STAGE046` 和
`content_fields_are_untrusted_evidence=true`。空值表示没有运行 parser，而不是空解析成功；
没有业务文本、表格、页、章节、路径或输出引用，也没有生成 parser runtime output。

## fallback 日志

P4 从 P3 的七个非高质量结果派生结构化控制日志样例：三个中置信文本结果、未知二进制、
损坏 ZIP、信号冲突和仅扩展名低置信结果。日志保留场景 ID、检测类型/状态/置信度、候选
route、质量处置、受限错误码和未来 fallback state；每项均为
`DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME`，并固定：

- `attempted=false`
- `attempt_count=0`
- `silent_drop=false`
- `parser_switch_performed=false`
- `runtime_owner=STAGE-048`

这些是从已通过场景派生的交付结构，不是 Stage048 runtime 日志；没有执行 fallback，
也没有静默切换 parser。

## 解析质量指标

- 场景：`14/14`，通过率 `1.0`；
- task-pack 支持格式覆盖：`8/8`，覆盖率 `1.0`；
- 置信度：`HIGH=7`、`MEDIUM=3`、`LOW=1`、`UNKNOWN=3`；
- 质量处置：primary candidate `7`、质量复核 `3`、owner 复核 `3`、显式错误 `1`；
- 非高质量结果：`7/7` 均有明确复核或错误处置；
- 包含受限错误码的结果：`3`；
- 静默丢弃：`0`；parser output：`0`。

这些指标仅来自 P3 有界合成内存检测场景，不能代表真实资料的解析准确率、生产质量或
生产校准。

## 失败分类

| 分类 | 场景 | 错误码 | 处置 |
|---|---|---|---|
| `UNKNOWN_BINARY` | 未知二进制 | `NO_RELIABLE_TYPE_SIGNAL` | owner 复核，不执行 fallback |
| `CORRUPT_ZIP_CONTAINER` | 损坏 OOXML 容器 | `CORRUPT_ZIP_CONTAINER` | 显式错误，不执行 fallback |
| `SIGNAL_TYPE_CONFLICT` | 签名/MIME/扩展名冲突 | `SIGNAL_TYPE_CONFLICT` | owner 复核 |
| `EXTENSION_ONLY_LOW_CONFIDENCE` | 仅扩展名信号 | 无错误码 | owner 复核，不分派 parser |

四类均失败关闭。`errors=[]` 不等于成功：仅扩展名结果仍以低置信和 owner 复核显式处置。

## 支持与不支持边界

Stage045 只证明 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF 的检测候选与失败处置；
`UNKNOWN` 和 `CORRUPT_OR_UNREADABLE` 是失败哨兵类型。六类 parser route 全部仍是候选，
当前可用 parser route 为空。

旧式二进制 Office、通用压缩包、音频、视频、可执行文件和无法识别的二进制格式均未声明
支持。识别出候选格式不等于已具备 parser；未知、未列出或含糊输入必须 owner 复核或显式
报错。

## 版本与配置回滚

已实现的 detector 版本仍为 `ids.file_type_detector.v0_1.stage045.p2`。parser route 合同归
Stage046，parser 输出细化归 Stage047，fallback runtime 归 Stage048；六类 parser version
均如实记录为 `UNASSIGNED_NOT_IMPLEMENTED`。本轮没有创建或修改 parser 配置文件。

回滚目标是 P3 提交与
`PHASE3_SCENARIOS_ENABLED_PARSER_AND_FALLBACK_DISABLED` 状态：合同无效即停止，移除 P4
结构样例和派生日志，保留 P1–P3 与既有证据，并继续禁用 parser、fallback 和持久化。
回滚不得读取、扫描、哈希、解析、移动、覆盖或删除真实来源，不得破坏原始资料、manifest、
evidence ledger、audit log、index 或已交付报告。

## 中文反馈

Stage045 步骤四隔离交付证据已收口。十四个检测场景全部通过、八类格式均覆盖且没有静默
丢弃；七个非高质量结果都有明确复核或错误处置。当前未执行解析器或回退，parser 版本尚未
分配，样例和日志都不是 runtime 产物。下一步只能在独立 run 进行整阶段复审；本证据不是
生产就绪证明。

## 停止状态

`NO_REAL_SOURCE_FILE_READ`、`NO_FILESYSTEM_SCAN_OR_HASH`、`NO_PARSER_DISPATCH`、
`NO_PARSER_EXECUTION`、`NO_PARSER_OUTPUT`、`NO_FALLBACK_EXECUTION`、
`NO_RUNTIME_FALLBACK_LOG`、`NO_EVIDENCE_PROMOTION`、`NO_PERSISTENCE`、
`NO_STAGE_REVIEW_THIS_RUN`、`NO_STAGE046_THIS_RUN`、`NO_BATCH_REVIEW`、
`NO_GITHUB_UPLOAD`、`NO_APP_REINSTALL`、`NO_PRODUCTION_ACTIVATION` 均保持成立。

## 验证记录

- TDD RED：13 个测试产生 15 个预期断言失败和 1 个预期缺失检查器错误；
- 核心实现完成、治理尚停在 P3 时为 `12/13`，唯一失败是预期的当前路由红灯；
- 最终 checker：合同 `16/16`、交付 `9/9`；P4 聚焦 `13/13`，Phase1–4 兼容 `59/59`；
- Stage005 `172/172`，Stage041–045 聚合 `327/327`（`1138.506s`），IDS v0.1 全量发现
  `1077/1077`（`1566.023s`）；
- 首轮聚合 `323/327`，暴露四个 Stage041–044 历史 Phase4 前向路由止于 P3；首轮全量
  `1073/1077`，暴露三个 Stage038 gate allowlist 与一个 Stage039 review map 止于 P3。
  修复仅加入精确 `IDS-STAGE045-P4 -> IDS-STAGE045-REVIEW-GATE`，未弱化历史证据或安全断言；
- 七个 Stage038–044 历史整阶段 review checker、219 个无重复事件、30 个精确事件改动路径、
  双次负责人文档幂等渲染与 KM_IDSystem 双平面检查均通过；根治理脚本因 sparse checkout
  缺失仅记为 `SPARSE_CONFLICT`，未展开其他项目。
- 最终证据同步后，Stage042 review checker 曾因 Staged Development 的 current-task allowlist
  止于 P3 而失败关闭；只加入 P4 当前任务后，checker 恢复通过且 review 测试 `10/10`
  （`253.879s`）。
