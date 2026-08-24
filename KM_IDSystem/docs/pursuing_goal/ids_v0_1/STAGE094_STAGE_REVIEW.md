# Stage094 · 证据撤回 · 整阶段机械复审

## 复审目标

本复审以冻结 `STAGE-094_证据撤回.md`、Stage094 P1--P4 控制合同与控制报告为唯一工程上下文，机械确认 Evidence Ledger、evidence gap、风险、可信等级、撤回、降级、恢复、报告影响与投毒防护的固定控制形状、失败关闭、业务线白箱人工处理与 P4→P3 回退保持一致。来源文档、真实证据账本与业务线白箱人工复核继续承担业务事实权威。

复审模块只读取本地控制工件并在进程内构造控制报告。控制标签保持 reference-only，不承载真实资料、业务事实、证据内容或业务结论。

## 固定复审形状

| 层级 | 固定形状 | 复审重点 |
| --- | --- | --- |
| P1 | `18/14/6/5`，`16` 类失败关闭 | 证据撤回字段、关联、六个控制定义、A/B/C/D/E 标签与关键结论 `evidence_id`／`evidence_gap` 约束 |
| P2 | `6×29` 输入、`11` 组投影、每条 `105`、合计 `630` | 固定 reference-only 输入、Evidence Ledger、关联、检索证据捕获、风险、可信等级、撤回、投毒、降级、报告影响与 future integration 引用 |
| P3 | `7×32=224`，`15` 类失败关闭 | 无内部证据、低 OCR、旧版本、冲突、撤回资料、恶意资料与低等级伪装高可信结论 |
| P4 | `7/7/7/7/7/4/2`、`517`、`4` 条中文反馈、`18` 类失败关闭 | 交付控制记录、不可作为结论依据类型、降级／撤回／恢复、回归与 P4→P3 回退 |

风险评分、可信等级分配或变更、撤回、降级、恢复、投毒处置、报告状态更新和业务判定继续保持业务线白箱 owner 前置；本 Review 只复审控制形状。无内部证据保持 evidence gap，低 OCR、旧版本、冲突与撤回保持降级说明，恶意资料保持隔离说明，低等级不得支撑高可信结论，撤回影响只声明未来报告状态复核。

## 失败关闭与运行边界

任一 P1--P4 合同、控制报告、固定形状、控制引用、单一权威、撤回规则 owner 前置、失败关闭、P4→P3 回退、业务线白箱人工处理或零运行时边界漂移，复审结果保持 `FAIL_REVIEWED_EVIDENCE_REVOCATION_RUNTIME_DISABLED`，下一门禁保持 `IDS-STAGE094-REVIEW-GATE`。

本复审保持真实资料、原始元数据、manifest、检索结果、证据账本、审计日志、回答、报告、数据库、物理索引、来源／OCR／版本／复核／冲突评估、风险计算、可信等级分配或变更、撤回、降级、恢复、投毒处置、报告状态更新、模型、模型 Token、Agent、OVH、生产与正式全局上传的后续授权边界。

## 验证与回滚

聚焦验证命令：

```bash
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage094_evidence_revocation_stage_review
```

复审通过只开放 `IDS-STAGE095-P1-GATE`；Stage095 保持未启动。本阶段回滚只撤回本说明、Review 合同、纯内存模块、聚焦用例、local receipt、治理投影与生成中文视图，恢复到 `PASS_EVIDENCE_REVOCATION_DELIVERY_EVIDENCE_RUNTIME_DISABLED`。Stage094 P1--P4、Stage093 Review、冻结任务包、受保护资料、真实证据账本、GitHub `main`／release、OVH 与应用状态保持原状。
