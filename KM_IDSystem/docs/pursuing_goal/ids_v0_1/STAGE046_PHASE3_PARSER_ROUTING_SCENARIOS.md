# STAGE-046 Phase 3：解析器路由场景验证

## 执行结论

- Task ID：`IDS-V0_1-STAGE046-P3`
- Acceptance ID：`ACC-STAGE-046`
- 执行模式：`ISOLATED_NON_PRODUCTION_METADATA_ONLY_PARSER_ROUTING_SCENARIOS`
- 结果：`PASS_ISOLATED_PARSER_ROUTING_SCENARIOS_PARSER_DISABLED`
- 下一门：`IDS-STAGE046-P4-GATE`
- 本轮只完成 Phase 3；Phase 4、整 Stage 复审、批次复审、GitHub 上传与 App 重装均未执行。

## 冻结输入

Phase 3 绑定并重放 Phase 2 提交 `18c45ee39522891abe4ef65ed609eb5482f2f148`，根树为 `ae7b08d3bc0bab21c2523dfd9a5e756b7d6a840d`，`KM_IDSystem` 子树为 `0e549aaf1c476fa6d926c12ad444db66921164b5`，父提交为 `c82e4e928b167c718d462dc8cef3eed5b5dbb3ea`。Phase 2 证据、合同、检查器、测试和 machine run 均按 SHA-256 固定并在当前 worktree 中复核。

任务包来源仍绑定：

- archive SHA-256：`55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`
- 唯一 member：`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-046_解析器路由合同.md`
- member SHA-256：`955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39`
- roadmap SHA-256：`a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6`
- instructions SHA-256：`ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8`

这些检查只读取已授权任务包与仓库治理工件；没有读取、列举、扫描、stat、哈希、复制或修改 IDS 原始元数据目录。

## 场景覆盖与结果

检查器通过 P2 的 `build_routing_request()` 与 `evaluate_parser_route()` 重放 14 个确定性合成元数据场景，不实现第二套路由器：

1. PDF、DOCX、XLSX、PNG、JPEG、TIFF 的 `TYPE_CONFIRMED/HIGH` 均选出静态候选 route，但明确返回 `ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE`，解析器版本为 `UNASSIGNED_NOT_IMPLEMENTED`，不分派、不执行。
2. CSV、TXT 的 `TYPE_PROVISIONAL/MEDIUM` 均返回 `ROUTE_REVIEW_REQUIRED` 和 `QUALITY_REVIEW_REQUIRED`；治理 route 可定位，但没有候选选择或 fallback。
3. unknown 与信号冲突均进入 `OWNER_REVIEW_REQUIRED`，没有静默丢弃。
4. corrupt/unreadable 返回 `ROUTE_BLOCKED`、`DETECTION_INPUT_BLOCKED` 和 `EXPLICIT_ERROR_NO_FALLBACK`。
5. extension-only low confidence 进入 owner review；unsupported 返回 `ROUTE_UNSUPPORTED` 和 `UNSUPPORTED_EXPLICIT_NO_FALLBACK`。
6. instruction-like 文本仅以布尔 marker 表示。带 marker 与不带 marker 的路由结果一致；其标签为 `UNTRUSTED_EVIDENCE_TEXT`，解释为 `EVIDENCE_ONLY`，不能覆盖系统规则或授权工具。Stage 50 的 prompt-injection scanner 未实现、未调用。
7. 额外 caller parser override 与伪造 `routing_request_id` 均由 P2 严格请求合同失败关闭；两次都没有解析器分派。

汇总预期与检查结果为 14/14 场景具备显式 disposition、0 silent drop、0 parser dispatch、0 parser execution、0 fallback execution、0 parser output 和 0 persistent write。场景报告不保留 payload、source text、绝对业务源路径或 output refs。

## TDD 与边界

实现前测试先以 18 项运行，得到 `FAILED (failures=2, errors=16)`；失败均由 Phase 3 合同、检查器和证据尚不存在导致，没有将缺失实现误记为通过。随后仅新增 P3 工件并对必要的治理投影作前向门禁更新。

最终验证通过 checker 14/14 场景、focused 18/18、Phase1-3 compatibility 43/43、Stage005 173/173（45.246s）、Stage041-046 aggregate 386/386（1169.916s）与完整 IDS v0.1 discovery 1137/1137（1607.288s）；八个 Stage038-045 历史 review checker、223 条唯一事件语义、幂等 owner render 和项目级双平面也全部通过。

实现后的首次 focused run 暴露测试 helper `_outcome` 与 `unittest.TestCase._outcome` 同名，改名为 `_route_outcome_tuple` 后恢复正常。历史兼容 focused run 随后准确失败关闭九个停在 Stage046 P2→P3 的当前门断言；修复只增加精确的 `IDS-STAGE046-P3 -> IDS-STAGE046-P4-GATE` 路线。未暂存时 Stage039 review checker 继续因 Git-index 绑定失败关闭，完整暂存当前 KMIDS 变更后通过。双平面初检发现新机器事实中的未登记英文术语，修复机器事实源并重新渲染后通过；所有失败运行均未记为 PASS。

强制边界：

- `ISOLATED_NON_PRODUCTION_METADATA_ONLY_PARSER_ROUTING_SCENARIOS`
- `NO_REAL_SOURCE_FILE_READ`
- `NO_PARSER_DISPATCH`
- `NO_FALLBACK_EXECUTION`
- `NO_PROMPT_RULE_OVERRIDE`
- `NO_PHASE4_THIS_RUN`
- `NO_STAGE_REVIEW_THIS_RUN`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

这里的 `NO_REAL_SOURCE_FILE_READ` 指没有读取任何 IDS 业务源文件；任务包和冻结治理工件的完整性读取单独如实记录。Phase 3 不声称 parser、fallback、差分评估、prompt-injection scanner 或高置信度 evidence write 已存在。

## 工件

- 合同：`KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/stage046_parser_routing_scenarios_contract.json`
- 检查器：`KM_IDSystem/scripts/check_parser_routing_scenarios.py`
- 测试：`KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/test_stage046_parser_routing_scenarios.py`
- machine run：`KM_IDSystem/machine/runs/2026-07-22-stage046-p3-local.json`

## 停止条件与下一步

本 run 在 `IDS-STAGE046-P4-GATE` 停止。下一次独立 run 才可执行 `IDS-V0_1-STAGE046-P4`，完成全 Stage 独立复审并修复其暴露问题；Stage 046 在 P4 通过前仍不得宣称整 Stage 完成。批量上传门禁仍按 Stage 041–050 十阶段策略锁定。
