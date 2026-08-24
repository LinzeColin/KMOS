# Stage091 · 证据缺口处理 · 整阶段机械复审

## 复审目标

本复审以冻结 `STAGE-091_证据缺口处理.md`、Stage091 P1--P4 控制合同与控制报告为唯一工程上下文，机械确认内部资料不足以 `evidence_gap` 表达、关键结论必须保留 `evidence_id` 或 `evidence_gap` 引用、证据等级与异常处理边界完整。来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威。

复审模块只读取本地控制工件并在进程内构造控制报告。控制标签不承载真实资料、业务事实、证据内容或业务结论，不建立第二权威事实源。

## 固定复审形状

| 层级 | 固定形状 | 复审重点 |
| --- | --- | --- |
| P1 | `12/7/5`，`12` 类失败关闭 | evidence gap 未来字段、关联字段、A/B/C/D/E 与关键结论引用约束 |
| P2 | `6×27` 输入、`10` 组投影、每条 `78`、合计 `468` | 固定 reference-only 输入、关联链、风险／撤回／投毒／报告状态引用 |
| P3 | `7×32=224` | 无内部证据、低 OCR、旧版本、冲突、撤回、恶意、低等级伪装高可信结论 |
| P4 | `7/7/7/7/7/4/2`、`517`、`4` 条中文反馈、`18` 类失败关闭 | 交付控制记录、不可作为结论依据类型、降级／撤回／恢复说明 |

P3 的无内部证据场景保持空 `evidence_id_ref` 与不透明 `evidence_gap_ref`；撤回场景只声明未来报告状态影响，不能更新报告状态；低等级伪装高可信结论保持拒绝。所有七条场景和 P4 交付记录均保留业务线白箱人工处理要求。

## 失败关闭与运行边界

任一 P1--P4 合同、控制报告、固定形状、控制引用、单一权威、回退路径、人工处理要求或零运行时边界漂移，复审结果保持 `FAIL_REVIEWED_EVIDENCE_GAP_HANDLING_RUNTIME_DISABLED`，下一门禁保持 `IDS-STAGE091-REVIEW-GATE`。

本复审不读取、复制、写入、查询或解析真实资料、原始元数据、manifest、检索结果、证据账本、审计日志、回答、报告、数据库或物理索引；不执行检索、证据缺口识别／关闭、证据捕获、OCR 或版本评估、风险计算、可信等级变更、撤回、恢复、投毒防护、报告状态更新、模型调用、模型 Token、Agent、OVH、生产或正式上传。

## 验证与回滚

聚焦验证命令：

```bash
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage091_evidence_gap_handling_stage_review
```

复审通过只开放 `IDS-STAGE092-P1-GATE`；Stage092 仍保持未启动。本阶段回滚只撤回本说明、Review 合同、纯内存模块、聚焦用例、local receipt、治理投影与生成中文视图，恢复到 `PASS_EVIDENCE_GAP_HANDLING_DELIVERY_EVIDENCE_RUNTIME_DISABLED`。Stage091 P1--P4、Stage090 Review、冻结任务包、受保护资料、真实证据账本、GitHub、OVH 与应用状态保持原状。
