# Stage088 整阶段机械复审

## 目标

只在内存中机械复审冻结 Stage088 的 P1--P4 合同、P2/P3/P4 控制报告与 P4→P3 回退边界，确认关键词与向量检索基线、六维元数据过滤、活动索引版本、candidate／selected、score／排序解释、检索轨迹／证据账本／结果有效性门禁引用链、八类受控场景、metadata-only 交付证据和业务线白箱人工处理保持一致。

## 复审范围与固定形状

- P1：query 9、filter 7、candidate 10、selected 10、score 7、active index version 7、retrieval trace 14、result validity gate 16 个字段，以及 28 类失败关闭；
- P2：6 条固定控制请求、9 组各 6 条控制投影，以及 528 次字段检查与 34 类失败关闭；
- P3：8 类关键词、材料牌号、设备型号、标准号、语义相似、六维过滤、Top-K／排序解释／结果有效性和旧索引服务版本轨迹场景，33 字段、264 次字段检查、8 条人工处理与 16 类失败关闭；
- P4：8 条检索样例、8 条 trace 日志、8 条过滤结果、8 条有效性测试报告、8 条证据缺口记录、4 条参数回滚说明、4 条中文反馈、572 次交付字段检查与 20 类失败关闭。

## 不可突破边界

- 只读取本仓冻结任务包和既有控制工件；不读取、打开、复制、写入、查询、删除、构建、过滤、排序、追踪、回滚或测量真实资料、来源正文、原始元数据、物理索引、实际检索样例、实际 trace、证据账本、审计日志、数据库、检索参数或业务事实。
- 不执行 PostgreSQL、FTS、BM25、pgvector、关键词或向量检索、材料牌号／设备型号／标准号匹配、语义计算、元数据过滤、混合排序、Top-K、provider／模型、模型 Token、Agent、OVH、生产、上传或推送。
- 来源文档、证据账本与业务线白箱人工复核仍是唯一权威；复审输出不得替代来源文档、成为业务事实或自动作出业务决策。

## 通过与失败关闭

复审仅在 P1--P4 合同和控制报告全部通过、固定形状完全一致、关键词与向量基线、vector-only 拒绝、六维过滤、活动索引版本／candidate／selected／score／trace／evidence ledger／结果有效性门禁引用链、显式证据缺口、业务线白箱人工处理和 P4→P3 回退链完整、所有运行时标志关闭时通过。任一合同、报告、记录形状、控制标签、回退路径、单一权威或零运行时标志不一致，都留在 IDS-STAGE088-REVIEW-GATE，不打开后续阶段。

通过后只开放 IDS-STAGE089-P1-GATE，但不启动 Stage089；Stage089 仍须在新的独立 run 中按其冻结任务包进入。Review 回滚仅撤回本说明、复审模块、聚焦测试、machine run、事件、机器事实、路线图、中文投影和交接，返回 PASS_RETRIEVAL_RESULT_VALIDITY_DELIVERY_EVIDENCE_RUNTIME_DISABLED，保留 P1--P4、冻结任务包、真实资料、fixture、manifest、evidence ledger、audit log、数据库、索引、GitHub、OVH 与应用状态。
