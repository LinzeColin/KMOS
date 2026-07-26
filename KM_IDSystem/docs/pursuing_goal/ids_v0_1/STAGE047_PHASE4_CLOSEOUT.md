# STAGE-047 Phase 4：解析器输出合同交付收口

## 执行结论

- Task：`IDS-V0_1-STAGE047-P4`
- Acceptance：`ACC-STAGE-047`
- 执行模式：`ISOLATED_NON_PRODUCTION_PARSER_OUTPUT_CLOSEOUT`
- 结果：`PASS_ISOLATED_PARSER_OUTPUT_CLOSEOUT_RUNTIME_DISABLED`
- 下一门：`IDS-STAGE047-REVIEW-GATE`
- 本轮只完成 Phase 4；Stage047 整阶段复审、Stage048、批次复审、GitHub 上传与 App 重装均未执行。

## 冻结输入

Phase 4 绑定并重放已提交的 Phase 3：

- commit：`595a507519b443faa49fca9fa0a6e8bd21cb9dde`
- root tree：`65a4db060a67ffbb4e7007b25d0dd453fbdbfc88`
- `KM_IDSystem` tree：`d0e7058864e6669abcf213cf8c9defe4d57c6fa5`
- parent：`65b81389e24d9ae371f464dcd6321784b9078d8b`

Phase 3 的证据、合同、检查器、测试与 machine run 同时从该提交、Git 索引和工作树按 SHA-256 复核；任一平面漂移都会在重放前失败关闭。批准任务包归档、Unicode NFC 唯一 Stage047 成员、roadmap 与 instructions 也实时重验。

这些检查只读取已授权任务包与仓库治理工件。没有读取、列举、扫描、stat、哈希、复制或修改 IDS 原始元数据目录，也没有打开任何 IDS 业务源文件。

## 交付内容

### 脱敏 parser 输出样例

Phase 4 从 Phase 3 重新计算 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG 与 TIFF 八个已接受控制输出，并只保留：

- route、parser family 与 fixture-only parser version；
- canonical control `output_id`、状态和初始质量处置；
- `text`、`tables`、`pages`、`sections`、`confidence`、`errors` 六个字段的结构投影；
- 内容是否存在、嵌套项数量和安全错误码，不保留文本、表格单元格、页/节文本或公式值。

样例状态固定为 `RECOMPUTED_SANITIZED_CONTROL_OUTPUT_NOT_RUNTIME`。它们来自合成、格式标签化、预解析控制，不是业务 parser 输出，也不证明来源文件有效、OCR 可用或运行时 parser 已部署。

### fallback 控制日志

Phase 3 的 16 个场景各派生一条 `DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME` 记录。每条记录保留结果类别、输出状态、初始质量状态、规范化结果码、显式处置和 Stage048 所属的未来 fallback 状态，同时固定：

- `attempted=false`
- `attempt_count=0`
- `silent_drop=false`
- `parser_switch_performed=false`
- `runtime_owner=STAGE-048`

这些是非运行时控制记录，不是 fallback runtime log；Stage048 没有开始。

## 解析质量指标与失败分类

质量指标由 Phase 3 结果重新计算，而非从合同直接回显：

- 场景：`16/16`，通过率 `1.0`
- 格式标签覆盖：`8/8`，覆盖率 `1.0`
- accepted / rejected / route-no-output：`11 / 3 / 2`
- candidate / partial / failed：`6 / 4 / 1`
- unique output id：`11`
- explicit disposition：`16`
- silent drop、parser execution、fallback execution、persistent write：均为 `0`

七类失败关闭分类无重叠覆盖全部 10 个非候选或失败场景：

1. `QUALITY_REVIEW_REQUIRED`
2. `PARSER_OUTPUT_FAILED_EXPLICIT`
3. `ROUTE_OWNER_REVIEW_REQUIRED`
4. `ROUTE_INPUT_BLOCKED`
5. `INVALID_LINEAGE_REJECTED`
6. `MALFORMED_REFERENCES_REJECTED`
7. `EMPTY_WITHOUT_ERROR_REJECTED`

其余六个 candidate 仍是 `OUTPUT_CANDIDATE_NOT_VALIDATED`，没有被质量门批准或提升为高可信证据。

## 支持边界与版本证据

八个格式仅是控制合同覆盖范围；`runtime_supported_formats=[]`，真实 parser 与 fallback runtime 均不可用。`UNKNOWN` 与 `CORRUPT_OR_UNREADABLE` 只允许人工复核或显式阻断。legacy binary office、generic archive、audio、video、executable 与 unrecognized binary 不在本 Stage 的支持声明内。

版本证据：

- output contract / schema：`ids.parser_output.v0_1.stage047.p1`
- normalizer：`ids.parser.output_normalizer.v0_1.stage047.p2`
- format adapter：`ids.parser.output.format_fixture_adapter.v0_1.stage047.p3`
- 各格式 parser version：只证明 control fixture lineage，不是 deployable runtime version
- Stage048 / 049 / 050 分别保留 fallback、差异化评估与提示注入 runtime 所有权

本 Phase 没有创建或修改 parser 配置。

## 回滚与停止条件

回滚只撤销本 Phase 4 的 delivery contract、checker、tests、evidence、machine run 与必要治理投影，恢复到 P3 commit `595a507519b443faa49fca9fa0a6e8bd21cb9dde`。必须保留 P1–P3、批准来源、原始资料、manifest、evidence ledger、audit、index、report、database、GitHub 与 App 状态。

任何来源、P3 commit/tree/parent/工件、八个脱敏样例、十六条控制日志、质量指标、失败分类、版本/回滚、治理路线或无副作用声明失配，checker 都会返回 `FAIL_CLOSED` 并停在 `IDS-STAGE047-P4-GATE`。

## TDD 与验证证据

- TDD RED：13 项测试得到 16 项预期 assertion failures 与 1 项预期缺失 checker 命令错误；原因仅为 P4 contract/checker/evidence/machine run 与治理路线尚不存在。
- 核心 checker：9 项合同校验与 7 项交付校验全部通过。
- 最终 GREEN：P4 focused `13/13`，Phase1–4 `58/58`，Stage005 `178/178`，Stage041–047 aggregate `471/471`（`1192.255s`），full IDS v0.1 discovery `1227/1227`（`1590.578s`），9 个 Stage038–046 review checker，`229` 条唯一事件语义、七文档幂等渲染与项目双平面全部通过。
- 首次 aggregate 的 20 个失败由 6 个精确历史前向路由缺口与预期未暂存索引绑定组成；首次 full discovery 的 4 个失败是 Stage038/039 仍止于 P3 的前向路由。修复仅加入 `IDS-STAGE047-P4 -> IDS-STAGE047-REVIEW-GATE`，没有放宽旧阶段结论或运行时安全边界。失败尝试保留在 machine run，不计为 PASS。
- 根 `scripts/lean_governance.py` 因 sparse worktree 缺失，记录 `SPARSE_CONFLICT`；未展开任何其他项目。

核心工件：

- contract：`KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_output/stage047_parser_output_delivery_contract.json`
- checker：`KM_IDSystem/scripts/check_parser_output_delivery.py`
- tests：`KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/test_stage047_parser_output_delivery.py`
- machine run：`KM_IDSystem/machine/runs/2026-07-23-stage047-p4-local.json`

## 下一步

本 run 在 `IDS-STAGE047-REVIEW-GATE` 停止。下一次独立 run 才可执行 `IDS-V0_1-STAGE047-REVIEW`，从 Stage 全局复审 Phase 1–4 并修复发现。复审通过前不得进入 Stage048，也不得把 Phase 4 closeout 宣称为整 Stage 或生产就绪。批量上传门禁继续按 Stage041–050 十阶段策略锁定。
