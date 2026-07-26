# STAGE-046 Phase 4：解析器路由交付收口

## 执行结论

- Task ID：`IDS-V0_1-STAGE046-P4`
- Acceptance ID：`ACC-STAGE-046`
- 执行模式：`ISOLATED_NON_PRODUCTION_PARSER_ROUTING_CLOSEOUT`
- 结果：`PASS_ISOLATED_PARSER_ROUTING_CLOSEOUT_PARSER_DISABLED`
- 下一门：`IDS-STAGE046-REVIEW-GATE`
- 本轮只完成 Phase 4；整 Stage 独立复审、Stage047、批次复审、GitHub 上传与 App 重装均未执行。

## 冻结输入

Phase 4 绑定并重放已提交的 Phase 3：

- commit：`49b876ec68ec8f92f0b9df72d57cca7b2d1d3344`
- root tree：`974c9917128938f133c64f5752c26502704e90ae`
- `KM_IDSystem` tree：`d1eba5655e94697a2381c141a7c55b0e3892d1a6`
- parent：`18c45ee39522891abe4ef65ed609eb5482f2f148`

Phase 3 的证据、合同、检查器、测试与 machine run 均从 Git 索引读取并按 SHA-256 固定。批准来源继续绑定唯一 Stage046 任务包成员；归档、成员、roadmap 与 instructions 哈希全部实时通过。任务包成员名按 Unicode NFC 归一化后唯一匹配，避免文件系统组合字符差异造成误判。

这些完整性检查只读取已授权任务包与仓库治理工件。没有读取、列举、扫描、stat、哈希、复制或修改 IDS 原始元数据目录，也没有打开任何 IDS 业务源文件。

## 交付内容

### 解析器输出结构样例

对 `ROUTE_PDF`、`ROUTE_OOXML_WORD`、`ROUTE_OOXML_WORKBOOK`、`ROUTE_DELIMITED_TEXT`、`ROUTE_PLAIN_TEXT` 与 `ROUTE_IMAGE` 生成六个 `SCHEMA_ONLY_NOT_EXECUTED` 样例。每个样例仅包含：

- `text`
- `tables`
- `pages`
- `sections`
- `confidence`
- `errors`

所有内容字段为空，置信度为 `UNKNOWN`，解析器版本均为 `UNASSIGNED_NOT_IMPLEMENTED`。这些样例只说明 Stage047 应遵守的输出形状，不是解析结果，也不代表 parser 可用。

### fallback 控制日志

Phase 3 的十四个场景各派生一条 `DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME` 控制记录，完整保留检测状态、route action、候选 route、parser family/version、质量处置与错误码。全部记录满足：

- `attempted=false`
- `attempt_count=0`
- `silent_drop=false`
- `parser_switch_performed=false`
- runtime owner 为 `STAGE-048`

这些记录不是 runtime fallback log；Stage048 的 fallback 实现和运行时所有权没有被提前激活。

## 质量指标与失败分类

质量指标由 Phase 3 报告重新计算，而非手工写死：

- 场景：`14/14` 通过，显式处置 `14/14`，静默丢弃 `0`
- 治理格式：`8/8`，覆盖率 `1.0`
- 治理 route family：`6`；实际选出的唯一候选 route id：`4`
- 置信度：`HIGH=6`、`MEDIUM=3`、`LOW=1`、`UNKNOWN=4`
- 处置：parser unavailable `6`、quality review `3`、owner review `3`、blocked `1`、unsupported `1`
- 带显式错误码结果：`14`；parser output 与 fallback execution 均为 `0`

五类失败关闭分类无重叠覆盖全部十四个场景：

1. `PARSER_IMPLEMENTATION_UNAVAILABLE`
2. `QUALITY_REVIEW_REQUIRED`
3. `OWNER_REVIEW_REQUIRED`
4. `DETECTION_INPUT_BLOCKED`
5. `FILE_TYPE_UNSUPPORTED`

## 支持边界、版本与回滚

Stage046 只治理八类 detection result 到六个候选 route 的映射。`available_parser_routes=[]`、`parser_implementation_count=0`、`assigned_parser_version_count=0`；格式检测支持和 route 合同均不等于 parser runtime 支持。legacy binary office、generic archive、audio、video、executable 与 unrecognized binary 均不在支持声明内；未知、冲突、低置信、损坏与未支持输入只能复核或显式失败。

版本证据固定为：

- router：`ids.parser_router.v0_1.stage046.p2`
- registry：`ids.parser_route_registry.v0_1.stage046.p2`
- parser output owner：Stage047
- fallback runtime owner：Stage048
- differential evaluation owner：Stage049
- prompt-injection scan owner：Stage050

没有创建或修改 parser 配置。回滚只丢弃本 Phase 4 的结构样例、派生控制日志、指标与分类，并恢复到已提交的 Phase 3 scenario-only 状态；必须保留原始资料、manifest、evidence ledger、audit、report、index 与 Phase1-3 证据，禁止破坏性来源操作。

## TDD 与停止条件

实现前运行十三项聚焦测试，得到 `FAILED (failures=16, errors=1)`；失败只来自 P4 合同、检查器、证据、machine run 与治理路线尚不存在，没有把缺失实现误记为通过。核心合同和检查器随后通过九项合同校验与七项交付校验，并保持 parser、fallback、输出、持久化与外部副作用全部关闭。

最终分层验证全部通过：Phase4 聚焦测试 `13/13`（`1.563s`）、Phase1-4 兼容测试 `56/56`（`6.033s`）、Stage005 治理回归 `174/174`（`47.314s`）、Stage041-046 聚合测试 `399/399`（`1183.625s`）、IDS v0.1 全量发现 `1151/1151`（`1600.768s`），以及八个历史整阶段复审检查器（`220.172s`）。`224` 条治理事件无解析、重复 ID 或语义错误；owner view 连续两次渲染一致，项目级 dual-plane 通过。首次聚合中的 `18` 项失败与 `3` 项错误、定向复审中的单项失败均作为 fail-closed 修复证据保留，不计入 PASS。

任何来源、Phase3 snapshot、结构样例、派生控制日志、质量指标、失败分类、版本/回滚、治理或无副作用证据失配，检查器都会返回 `FAIL_CLOSED` 并停在 `IDS-STAGE046-P4-GATE`。

## 工件

- 合同：`KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/stage046_parser_routing_delivery_contract.json`
- 检查器：`KM_IDSystem/scripts/check_parser_routing_delivery.py`
- 测试：`KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/test_stage046_parser_routing_delivery.py`
- machine run：`KM_IDSystem/machine/runs/2026-07-22-stage046-p4-local.json`

## 下一步

本 run 在 `IDS-STAGE046-REVIEW-GATE` 停止。下一次独立 run 才可执行 `IDS-V0_1-STAGE046-REVIEW`，从全 Stage 视角复审 Phase1-4 并修复发现；Stage047 不在本轮授权范围。批量上传门禁继续按 Stage041–050 十阶段策略锁定。
