# STAGE-043 Phase 4 关闭与交付

- Task：`IDS-V0_1-STAGE043-P4`
- Acceptance：`ACC-STAGE-043`
- 结果：`PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED`
- 合同：`worker_crash_recovery/stage043_worker_crash_recovery_delivery_contract.json`
- 检查器：`KM_IDSystem/scripts/check_worker_crash_recovery_delivery.py`
- 下一门：`IDS-STAGE043-REVIEW-GATE`
- 整阶段复审：本轮未执行，必须由下一个独立 run 完成

## 来源与前置绑定

P4 继续绑定唯一 Stage043 task-pack member：
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-043_Worker崩溃恢复.md`，
SHA-256 为
`e1d5169cbc30515930a7224743b860d9b577ccfbf9e0f913ec254d2ea060317b`。
前置提交固定为 P3 `6af57993b35bde3c3a215b08ee7e1ab65c204747`，其
`KM_IDSystem` tree 为 `3461f0ac16efe01fb48e0eb589ac2a00b804e226`。
检查器逐文件验证 P3 合同、检查器、测试和证据，以及 Stage038–042 已复验交付
合同与检查器；任一来源、祖先、Git index 或 SHA-256 漂移均 fail closed 回到
`IDS-STAGE043-P4-GATE`。

## 交付证据

本轮组合并复验控制面证据，不创建 IDS 业务 job，也不写任务状态：

- job state graph：8 类 job、11 个状态、4 个终态、21 条允许转换；
- failure retry log：3 次 attempt、2 次 retry，最终 `DEAD_LETTERED`，未持久化；
- backpressure trigger proof：7 类压力信号均有已审失败关闭证据；
- Stage043 scenarios：P3 的 13/13 个隔离场景重新通过；
- isolated process loss：无输入输出的控制子进程自行退出码为 `73`，未 signal、
  kill、probe、restart 或 recovery；
- same-source exclusion：4 类操作、25 个完整冲突和 16 个选定矩阵冲突，operation
  invocation、queue record 和 retry budget consumption 均为 0；
- cleanup allowlist：只有 `TEMP_STAGING_OUTPUT` 与
  `INCOMPLETE_DERIVATIVE_OUTPUT` 两类 reference-only 隔离候选；
  `FACT_SOURCE`、`MANIFEST`、`EVIDENCE_LEDGER`、`REPORT_SNAPSHOT`、
  `AUDIT_LOG` 五类 Git 证据始终受保护且未尝试删除。

## 条件处理、自动恢复与人工处理

以下三条仅是所有门禁满足后的条件处理候选，不代表当前自动恢复资格：

1. 检查点完整、幂等、持久状态、版本、owner、资源、丢失代际栅栏和全新
   admission/claim/lock 周期全部有效后的 checkpoint continuation candidate；
2. Stage039 policy、预算、重放安全、资源和 backoff 全部有效后的 retry candidate；
3. 永久错误、合法 `RUNNING -> FAILED` 边和审计证据完整后的 safe-failure candidate。

当前没有持久化 job/recovery state，五个时间参数也未完成生产校准，因此
`automatic_recovery_eligible_cases=[]`、
`successful_automatic_recovery_cases_observed=[]` 且
`automatic_recovery_performed=false`。

下列情况必须人工处理：缺失或陈旧 crash evidence、检查点完整性未知、幂等冲突、
陈旧状态版本、丢失 worker 未栅栏、活动 claim/lock、资源或 owner 未复核、终态重开、
受保护清理、安全失败确认、合同无效、策略未校准，以及缺失持久 job/recovery state。

## 安全关闭

本轮只复验 Stage038 已审隔离 transport 的有序关闭证据；P4 未终止或重启任何进程，
未修改任务、重试、锁或检查点：

1. 停止新的 recovery evaluation；
2. 由各 owner runtime 停止新 admission、claim 与 retry；
3. 由 owner runtime 请求活动任务安全暂停并等待 checkpoint 或 quarantine；
4. 冻结 retry、resume 与 recovery eligibility；
5. 保留 crash、heartbeat、lease、checkpoint 与 audit evidence；
6. 由 Stage041 owner runtime 栅栏丢失代际并释放匹配的活动锁；
7. 由 Stage038 owner runtime 关闭已审 transport；
8. 验证未发生 delete、persistence 或 runtime-output 写入。

已复验证据只证明隔离 transport `queue_closed=true`、
`all_resource_locks_released=true` 且未取消活动工作，不证明生产 worker shutdown。

## 恢复与回滚

未来恢复必须重新校验 source/policy/upstream hash，重新观察 crash、heartbeat、lease、
state version 与 checkpoint，要求当前持久状态、owner/resource/checkpoint 复核和已栅栏
丢失代际，并确认无活动 claim/lock。候选只能通过
`ACTIVE -> RETRY_WAIT -> QUEUED` 后进入新的 admission/claim/lock 周期；Stage039 仍拥有
retry admission，Stage042 仍拥有 lifecycle transition，Stage044 仍拥有 cleanup。
不得复原丢失的 in-memory state，也不得重开终态历史。

回滚顺序：无效合同立即失败关闭 → 停止新的 recovery evaluation → 活动、未知或未栅栏
状态转人工复核 → 只撤销 P4 合同、检查器、测试、文档和对应治理同步 → 保留 P1–P3、
Stage037–042 已审证据、原始资料边界和所有 durable evidence。禁止 destructive
rollback、cleanup/delete、数据库或 schema 动作。

## 停止状态

真实 worker crash、进程探测、signal、kill、终止、重启、自动恢复、状态转换、
checkpoint continuation、queue/worker/retry/backpressure/production-lock/lifecycle runtime、
cleanup/delete、持久化、database/schema、raw metadata、真实或虚构 IDS 业务数据、
Stage043 整阶段复审、Stage044、GitHub upload、batch review 与 app reinstall 均未执行。
P4 只证明关闭合同可执行、可测试、可回滚；它不是生产运行或生产就绪证明。

## 验证结果

- TDD RED：11 个聚焦测试产生 13 个预期断言失败和 1 个预期缺失检查器错误；
- Phase4 checker：合同 `14/14`、交付 `14/14`；
- 聚焦测试：`11/11`，`98.108s`；
- Stage005 治理回归：`163/163`；
- Stage041–043 聚合：`185/185`，`660.796s`；
- 完整 IDS v0.1 discovery：`926/926`，`1024.295s`；
- Stage038–042 五个历史整阶段检查器、209 条事件语义、渲染幂等和项目双平面均通过。

首轮分层验证只暴露历史当前门枚举停在 P3，以及对应 P2 测试到 P3/P4 的精确哈希漂移；
修复仅新增 `IDS-STAGE043-P4 -> IDS-STAGE043-REVIEW-GATE` 前向兼容，不改变任何
历史复审结论、运行时所有权或安全边界。
