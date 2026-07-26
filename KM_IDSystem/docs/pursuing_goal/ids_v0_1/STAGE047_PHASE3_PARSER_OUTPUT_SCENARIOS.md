# STAGE-047 Phase 3：解析器输出场景验证

## 结论

`IDS-V0_1-STAGE047-P3` 在隔离、非生产、纯内存条件下通过 16 个确定性场景，覆盖 PDF、DOCX、XLSX、CSV、TXT、PNG、JPEG、TIFF、UNKNOWN 与 CORRUPT_OR_UNREADABLE。结果为：11 个控制输出被规范化、3 个不合规输出失败关闭、2 个上游路线明确不生成输出，静默丢弃为 0。

本阶段使用 `SYNTHETIC_FORMAT_LABELED_PREPARSED_CONTROL`，不是实际解析器测试：`NO_REAL_SOURCE_FILE_READ`、`NO_PARSER_EXECUTION`、`NO_FALLBACK_EXECUTION`。本轮停止在 `IDS-STAGE047-P4-GATE`：`NO_PHASE4_THIS_RUN`、`NO_STAGE_REVIEW_THIS_RUN`、`NO_GITHUB_UPLOAD`、`NO_APP_REINSTALL`。

## 身份与输入绑定

- task：`IDS-V0_1-STAGE047-P3`
- acceptance：`ACC-STAGE-047`
- contract：`ids.stage047.parser_output.phase3.scenarios.v1`
- execution mode：`ISOLATED_NON_PRODUCTION_FORMAT_LABELED_PREPARSED_OUTPUT_SCENARIOS`
- P2 predecessor：`65b81389e24d9ae371f464dcd6321784b9078d8b`
- P2 root tree：`a66f59a71bd8c41ba122e0415f126d7cea6d8375`
- P2 KMIDS tree：`eb2be74f3138221f39f4aab5e513c5fc8b03d984`
- P2 parent：`7d44f72c6a5d50e9042b8af1f588cd40e1caf4f3`
- approved archive SHA-256：`55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`
- Stage047 member SHA-256：`e1d5bdb219b6f16ca7fec4e4455e7acba1ecbae9803a7c13721b75895671d2f4`
- roadmap SHA-256：`a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6`
- instructions SHA-256：`ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8`

校验器从不可变 P2 commit 重新读取并哈希五项 P2 工件，避免把本轮对 P2 控制适配入口的向后兼容扩展冒充已提交 P2 证据。Stage046 P3 路由 checker、contract 与 machine run 同样从该快照重新哈希，并重放 14/14 路由场景。

## 控制适配边界

Phase3 仅扩展 P2 控制输入构造器，使已经解析好的合成映射可以声明以下格式元数据：

| 类型 | route | parser family | 控制版本 |
| --- | --- | --- | --- |
| PDF | `ROUTE_PDF` | `PDF_PARSER` | `ids.parser.control_fixture.pdf.v0_1.stage047.p3` |
| DOCX | `ROUTE_OOXML_WORD` | `OOXML_WORD_PARSER` | `ids.parser.control_fixture.docx.v0_1.stage047.p3` |
| XLSX | `ROUTE_OOXML_WORKBOOK` | `OOXML_WORKBOOK_PARSER` | `ids.parser.control_fixture.xlsx.v0_1.stage047.p3` |
| CSV | `ROUTE_DELIMITED_TEXT` | `DELIMITED_TEXT_PARSER` | `ids.parser.control_fixture.csv.v0_1.stage047.p3` |
| TXT | `ROUTE_PLAIN_TEXT` | `PLAIN_TEXT_PARSER` | `ids.parser.control_fixture.v0_1.stage047.p2` |
| PNG/JPEG/TIFF | `ROUTE_IMAGE` | `IMAGE_PARSER` | `ids.parser.control_fixture.image.v0_1.stage047.p3` |

这些值只是控制夹具的 lineage 元数据。适配器不打开文件、不检测类型、不选择 parser、不调用 parser，也不替换 Stage046 路由运行时。P2 的默认 TXT 调用与报告保持向后兼容。

## 场景矩阵

| 类别 | 场景 | 预期处置 |
| --- | --- | --- |
| 支持格式 | PDF pages、DOCX sections、XLSX table、CSV table、TXT text | 5 个 `OUTPUT_CANDIDATE_NOT_VALIDATED` |
| 图片格式 | PNG、JPEG、TIFF 低置信控制 | 3 个 `OUTPUT_PARTIAL_REVIEW_REQUIRED` |
| 路由无输出 | UNKNOWN、CORRUPT_OR_UNREADABLE | owner review / explicit block；Stage048 未运行 |
| 质量与失败 | low-quality TXT、explicit parser failure | review / blocked；不自动切换 parser |
| 指令文本 | instruction-like TXT 与中性基线 | 路由不变，文本仅为 evidence |
| 失败关闭 | forged lineage、malformed nested refs、empty without error | 3 个 `OUTPUT_REJECTED_FAIL_CLOSED`，不回显输入 |

精确汇总：

- scenario：16/16
- accepted control output：11
- rejected output：3
- route no output：2
- `OUTPUT_CANDIDATE_NOT_VALIDATED`：6
- `OUTPUT_PARTIAL_REVIEW_REQUIRED`：4
- `OUTPUT_FAILED_EXPLICIT`：1
- unique output identity：11
- silent drop：0
- parser execution：0
- fallback execution：0
- persistent write：0

XLSX 场景只验证公式字符串 `=1+1` 被原样保留；公式执行为 false。指令式文本只比较其 route 语义与无指令基线，保持 `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY`；本阶段未执行 Stage050 scanner，也不声称检测了 prompt injection。

## 失败关闭与回退口径

- UNKNOWN 路由结果为 `ROUTE_REVIEW_REQUIRED`，只记录 `OWNER_REVIEW_REQUIRED_STAGE048_NOT_RUN`。
- 损坏输入路由结果为 `ROUTE_BLOCKED`，只记录 `EXPLICIT_ROUTE_ERROR_STAGE048_NOT_RUN`。
- 低质量控制输出进入 `REVIEW_REQUIRED`，不静默提升为候选证据。
- 显式失败输出进入 `BLOCKED`，错误使用安全码与 message key，不回显原始异常。
- lineage、嵌套引用或空输出不合规时统一返回净化后的 `OUTPUT_REJECTED_FAIL_CLOSED`。
- Stage048 是 fallback runtime owner；本阶段只验证处置字段，不执行回退，也不生成虚假 fallback log。

## 验证证据

- TDD RED：19 项测试，3 failures、18 errors；缺失 P3 contract/checker/evidence 与治理转移，符合预期。
- 核心实现后：19 项中 17 项通过；余下 2 项仅因 P3 evidence 尚未写入。
- P3 checker：`KM_IDSystem/scripts/check_parser_output_scenarios.py`
- P3 contract：`KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_output/stage047_parser_output_scenarios_contract.json`
- focused tests：`KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/test_stage047_parser_output_scenarios.py`
- machine run：`KM_IDSystem/machine/runs/2026-07-23-stage047-p3-local.json`

最终分层测试结果写入 machine run、治理事件与 changelog；失败、命令错误或被修复的中间尝试不会计为 PASS。

## 风险、停止条件与回滚

主要风险是把格式标签夹具误称为真实 parser，把初始质量处置误称为质量门，或把 Stage046 metadata replay 误称为 Stage047 parser execution。合同、checker、tests 和治理事实均以 false flag 阻断这些扩大声明。

本轮只允许回滚 P3 contract/checker/tests/evidence、P2 控制适配扩展及对应治理投影。不得改动 P1/P2 已提交证据、批准来源、原始元数据、manifest/evidence ledger/audit/index/report、数据库、GitHub 或 app 状态。

通过后唯一下一任务是独立运行的 `IDS-V0_1-STAGE047-P4`。本轮不得进入 P4，不得执行 Stage047 整阶段复审，也不得上传本阶段结果。
