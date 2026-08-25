# Stage104 P2 · RAG 负向测试受控最小切片

## 目标与输入

本 phase 把 P1 的静态控制合同落为五条固定、非业务、`reference-only` 的纯内存控制请求。每条请求只保存不透明控制引用，覆盖回答结构、Prompt 版本、内部依据、外部增强、`evidence_gap`、文档 evidence、文档内潜在指令、IDS 规则、输出权限、人工确认，以及 `query`、`index_version`、`model_version` 和 `selected_evidence` 的可复现记录形状。

五条请求分别绑定 P1 固定的五个负向测试标签：文档指令与 IDS 规则优先、`evidence_gap` 真实性、高风险工程建议、合同承诺和生产写回。P2 只投影标签和控制状态；P3 才验证异常场景。

## 四组控制投影

- 回答合同与可复现记录：固定五段回答合同引用和五项版本/证据记录引用。
- 文档 evidence 与 IDS 规则防护：文档保持不可信、不可执行 evidence；文档内潜在指令无法覆盖 IDS 规则、输出权限或人工确认。
- 来源语义与外部增强：`internal_evidence`、`external_public_reference`、`model_reasoning` 和 `evidence_gap` 保留底层类型。`external_augmentation_opinion` 只作为展示标签，保留外部公开参考和模型推理的底层来源类型；它不替代内部依据。
- 输出权限与白箱门禁：高风险工程建议、合同承诺和生产写回保留业务线白箱人工确认前置；全部类别保持自动最终结论、发布和生产写回关闭。

## 运行时与业务边界

本切片不会读取任何资料、文档正文、Prompt、回答、查询或索引，不进行检索、模型调用、Token 消耗、来源绑定、实际输出分类、人工确认、回答发布、生产写回、数据库连接、审计写入、Agent、OVH 或正式上传，也不生成业务结论。控制投影是纯内存结构，不是业务事实、真实检索结果、审计记录或第二权威事实源。

## 验收、停止与回滚

- 固定五条控制请求、四组控制投影、`29` 个输入字段、每条 `57` 个投影字段，共 `285` 个纯内存控制检查点。
- 任何输入漂移返回 `CONTROL_INPUT_MISMATCH`，不产生投影或持久化记录。
- 本 run 止于 `IDS-STAGE104-P3-GATE`；P3、P4、Review 和 Stage105 保持未启动。
- 回滚只撤回 P2 的执行器、合同、范围说明、聚焦用例、machine run、治理投影与生成中文视图，返回 P1 的 `PASS_RAG_NEGATIVE_TEST_CONTRACT_RUNTIME_DISABLED`；保留 P1、Stage103 Review、冻结任务包、来源资料、业务白箱和主线状态。
