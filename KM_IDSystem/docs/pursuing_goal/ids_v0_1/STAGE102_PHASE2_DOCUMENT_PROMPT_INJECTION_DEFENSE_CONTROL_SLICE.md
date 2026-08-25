# Stage102 P2 · 文档内提示注入防护纯内存受控最小切片

## 本 phase 的目标

依据冻结 `STAGE-102_文档内提示注入防护.md`、Stage102 P1 静态合同和 Stage101 Review 控制工件，交付可执行的纯内存 `reference-only` 控制切片。切片固定回答合同、Prompt 版本、来源类型分离、外部增强显示、文档内潜在指令防护、输出权限与业务线白箱人工确认的未来字段形状。

## 单一权威与输入边界

- 冻结 Stage102 任务包、Stage102 P1 合同和 Stage101 Review 控制工件构成唯一控制上下文。
- 来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威。
- 控制输入只含固定标签，不含业务事实、来源正文或路径、真实文档内指令、真实查询、Prompt、模型配置、evidence、引用、回答或业务结论。
- 本 phase 不读取、列举、提取、分类或处理业务资料、原始元数据、fixture、manifest、检索结果、文档正文、Prompt 正文、回答、报告、数据库、物理索引或审计日志。

## 受控最小切片

- 固定 `7` 条控制请求，逐条覆盖 P1 的七类潜在越权类别：IDS 规则覆盖、系统指令或角色重定义、工具或外部动作授权、Prompt 或模型配置覆盖、输出权限或人工门禁绕过、发布或生产写回绕过、来源或秘密访问请求。
- 每条请求固定 `28` 个控制字段，包含 P1 的文档 evidence、潜在指令、IDS 规则、Prompt 版本、提示注入防护、query、index_version、selected evidence、来源类型、输出权限、人工确认和审计边界，并增加 `model_version_ref`、外部公开参考和模型推理的控制标签以保持外部增强底层来源类型。
- `query_ref`、`index_version_ref`、`prompt_version_ref`、`model_version_ref` 和 `selected_evidence_ref` 只记录未来可复现字段形状，不创建真实记录。
- 四组纯内存投影分别覆盖回答合同与可复现记录、文档内提示注入防护、来源语义与外部增强显示、输出权限与业务线白箱门禁；每条 `50` 字段，共 `350` 个控制字段投影。

## 防护、来源语义与输出权限

- 文档内潜在指令固定为不可信、不可执行 evidence；IDS 规则保持优先级。控制切片不授权系统指令、工具或外部动作、Prompt 或模型覆盖、发布、生产写回、来源或秘密访问。
- `internal_evidence`、`external_public_reference`、`model_reasoning` 与 `evidence_gap` 保持四类底层来源类型。`external_augmentation_opinion` 仅是由外部公开参考和模型推理组成的未来显示标签，不能取代内部依据或关闭 `evidence_gap`。
- `safe_summary`、`draft_recommendation`、`high_risk_engineering_advice`、`contractual_commitment` 与 `production_writeback` 只作为未来输出分类标签。高风险工程建议、合同承诺和生产写回均保持业务线白箱人工确认前置，最终结论保持未发布。

## 本 phase 之外的运行时事项

真实文档读取、潜在指令识别或处理、查询、索引读取或切换、检索、Prompt 正文、provider 或模型选择和调用、模型 Token、来源类型绑定、外部增强显示、引用生成、输出分类、人工确认、回答发布、生产写回、数据库连接、审计、持久化、Agent、OVH、生产和正式上传均属于后续授权范围。

## 验收与停止条件

- 控制模块只接受唯一固定输入；任何变体返回拒绝状态、零投影和全零运行时计数。
- 聚焦白箱用例验证单一权威、`7×28` 输入形状、`4×50×7` 投影、五项可复现字段、提示注入拒绝、来源类型分离、输出权限、业务线白箱门禁、失败关闭、回退与零运行时边界。
- 本 run 止于 `IDS-STAGE102-P3-GATE`；P3、P4 和整阶段复审保持未启动。
- 任何真实资料或运行时动作、任何不可回滚 schema 变更、任何跨 Stage 改动或测试原因不明的失败都会停止本 phase。

## 回滚

回滚仅撤回本 P2 的范围说明、纯内存控制切片、合同、聚焦用例、机器事实投影、治理路线、生成中文视图和本地回执，返回 Stage102 P1 的本地零运行时状态。冻结任务包、Stage102 P1、Stage101 Review、真实资料、manifest、证据账本、审计日志、报告、数据库、索引、GitHub、OVH 与应用状态保持原状。
