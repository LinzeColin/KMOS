# STAGE-042 Phase 4 关闭与交付

- Task：`IDS-V0_1-STAGE042-P4`
- Acceptance：`ACC-STAGE-042`
- 结果：`PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED`
- 合同：`automatic_lifecycle/stage042_automatic_lifecycle_delivery_contract.json`
- 检查器：`KM_IDSystem/scripts/check_automatic_lifecycle_delivery.py`
- 下一门：`IDS-STAGE042-REVIEW-GATE`
- 整阶段复审：本轮未执行，必须由下一个独立 run 完成

## 来源与前置绑定

P4 继续绑定唯一 Stage042 task-pack member：
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-042_自动运行、暂停、恢复与关闭.md`，
SHA-256 为
`78a4bed1f5348837699bd7dd227898e6d47cc4099ca268ee1600bae84605ec08`。
前置提交固定为 P3 `d8773ac03d10d877b0b9c439bfce91fe85f8fdfe`，其
`KM_IDSystem` tree 为 `51a990dbb6563197d7a16d97c7cf2af201a7224e`。
检查器还逐文件验证 Stage042 P3、已复审的 Stage040 backpressure 交付证据、
以及已复审的 Stage041 lock-registry 交付证据；任一 hash、祖先关系或合同漂移均
fail closed 回到 `IDS-STAGE042-P4-GATE`。

## 交付证据

本轮组合并复验以下控制面证据，不创建真实业务 job，也不写状态：

- job state graph：8 类 job、11 个状态、4 个终态、21 条允许转换；
- failure retry log：3 次 attempt、2 次 retry，最终 `DEAD_LETTERED`，未持久化；
- backpressure trigger proof：7 类压力信号全部具有受审决策证据；
- lifecycle scenario：P3 的 12/12 个隔离场景重新通过；
- same-source exclusion：4 类操作、16 个冲突矩阵项，operation invocation 与 retry budget consumption 均为 0；
- cleanup allowlist：只有 `TEMP_STAGING_OUTPUT` 与 `INCOMPLETE_DERIVATIVE_OUTPUT` 两类候选；
  `FACT_SOURCE`、`MANIFEST`、`EVIDENCE_LEDGER`、`REPORT_SNAPSHOT`、`AUDIT_LOG`
  五类工件始终受保护，未尝试删除。

## 自动恢复与人工处理

“具备自动恢复候选资格”不等于“已执行或已成功自动恢复”。本轮仅证明以下三类
暂停场景在全部 gate 满足后可以重新进入 `QUEUED` 候选：

1. external drive 恢复后受控重新排队；
2. disk space 恢复后受控重新排队；
3. external API budget 恢复后受控重新排队。

每一类都必须重新验证 owner、资源稳定性、无活动 claim/lock，并重新执行
admission → claim → lock 流程。`successful_automatic_recovery_cases_observed=[]`，
`automatic_resume_performed=false`。

以下情形必须人工处理：changed-input idempotency conflict、陈旧或不完整 start
观察、owner/稳定性复核缺失、活动 claim/lock、shutdown guard/timeout、worker
process crash、受保护 cleanup、终态历史重开请求、合同缺失或无效、未校准策略，
以及进程退出后缺少持久化 lifecycle state。进程崩溃恢复仍归 Stage043，cleanup
执行仍归 Stage044。

## 安全关闭

本轮只复验 P3 的有序关闭候选，未终止任何进程、未变更 job state：

1. 停止新的 lifecycle decisions；
2. 停止新的 admission 与 claims；
3. 对活动 job 请求安全暂停；
4. 等待 checkpoint 或 quarantine；
5. 冻结 retry 与 resume eligibility；
6. 由 owner runtime 释放匹配的 active locks，并验证 active lock 为 0；
7. 由 owner runtime 关闭已复审 transport；
8. 保留 audit、checkpoint 与 evidence refs；
9. 验证未发生 delete、persistence 或 runtime-output 写入。

guard 不满足或超过 60 秒时只能 `REQUIRE_MANUAL_REVIEW`，不得强制终止进程。

## 恢复与回滚

恢复必须从当前已授权 evidence 重建：重新校验 source/policy/upstream hash，重新观察
source identity、资源与 owner，拒绝 unknown/stale observation，确认无活动
claim/lock，再重新运行幂等 lifecycle decision。不得恢复丢失的 in-memory lifecycle
state，不得绕过新的 admission/claim/lock 周期，也不得重开终态历史。

回滚顺序：停止新 lifecycle decision → 活动或未知状态转人工复核 → 只撤销 P4
合同、检查器、测试、文档与对应治理同步 → 保留 Phase1–3、Stage037–041 已复审证据、
原始数据边界和所有 durable evidence。禁止 destructive rollback、cleanup/delete、
数据库或 schema 动作。

## 停止状态

生产自动 start/pause/resume/shutdown、queue/worker/retry/lock runtime、进程终止、
crash recovery、cleanup/delete、持久化、database/schema、raw metadata、真实或虚构
IDS 业务数据、GitHub upload、batch review 与 app reinstall 均未执行。
P4 只证明关闭合同可执行、可测试、可回滚；它不是生产运行或生产就绪证明。
