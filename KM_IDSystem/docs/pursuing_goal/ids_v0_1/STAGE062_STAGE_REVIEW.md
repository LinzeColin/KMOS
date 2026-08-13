# Stage062 Review · 表格证据绑定整阶段机械复审

状态：`completed_reviewed_local`  
任务：`IDS-V0_1-STAGE062-REVIEW`  
复审门：`IDS-STAGE062-REVIEW-GATE`

## 复审范围

本次只机械复审冻结的 Stage062 任务包与 P1--P4 已提交 control 工件：

- P1 的 `19` 字段 reference-only 绑定输入、`17` 字段未来输出、六维来源引用、八类字段语义与 `13` 个失败状态；
- P2 的 `2` 条固定非业务 control 请求、`2` 条未绑定候选和 `12` 个控制绑定维度引用；
- P3 的六类异常场景、`6` 条显式人工处置、`0` 条静默丢弃与未验证数值阻断；
- P4 的 `6` 个 metadata-only 交付样例、`6` 个字段引用标签、`6` 条控制质量结果、`6` 条人工建议、`3` 条中文确认及 P4→P3 回滚说明。

复审输出只包含上述固定 control 计数、合同边界和回滚结论。来源文档保持唯一权威；control 引用不代表真实表格、真实来源位置、真实证据、真实结构化事实、真实统计、真实重解析或真实回滚。

## 白箱与运行边界

- 不读取、打开、列举、复制、解析、验证、统计或写入真实 XLSX/CSV、生产记录、质检记录、fixture、来源正文、物理路径、实际 URI、事实库、证据账本或数据库。
- 六类异常均保留业务线人工处理；合并单元格保持 `UNRECOGNIZED_STRUCTURE_REQUIRES_HUMAN_HANDLING`。不自动确认、修正、绑定、写入、去重或静默丢弃。
- 未验证数值、RAG 摘要和模型文本均不能成为确定性统计或业务结论。
- 不运行 Agent、模型或模型 Token；不启动本地服务、OVH、生产运行、GitHub 上传或推送。

## 回滚

若复审合同或报告不一致，只撤回本 Review 的说明、纯内存复审模块、聚焦用例、machine run、事件、机器事实投影、治理路线和生成中文视图，返回 `PHASE4_TABLE_EVIDENCE_BINDING_DELIVERY_EVIDENCE_RUNTIME_DISABLED`。保留 P1--P4、冻结任务包、真实资料、manifest、evidence ledger、audit log、事实库、数据库、GitHub、OVH 和应用状态。

## 交接条件

仅在复审结果为本地通过后，下一独立 run 才可进入 `IDS-STAGE063-P1-GATE`。该门不授权真实资料访问、外部服务、OVH、生产运行或上传；全局上传仍须等待完整冻结任务包完成 `ACC-STAGE-168`。

## 验证记录

- 只读复审模块返回 `PASS_REVIEWED_LOCAL_TABLE_EVIDENCE_BINDING_RUNTIME_DISABLED`，P1--P4 结果均为通过，发现数为 `0`。
- 聚焦用例通过 `10/10`；含 P1--P4、Stage061 Review、两个批次与 Stage060 Review 的阶段链路回归通过 `129/129`。
- `check_batch051_060_review.py` 与 `check_batch041_050_review.py` 均返回 `PASS_BATCH_REVIEWED_LOCAL_GLOBAL_UPLOAD_LOCKED`；Stage005 治理回归为 `valid=true`。
- 机器事实已重渲染 `7` 个中文文件；Stage063 仍未启动，OVH、生产、上传与推送均未进入。
