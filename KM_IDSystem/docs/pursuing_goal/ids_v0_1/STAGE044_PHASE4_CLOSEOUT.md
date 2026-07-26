# STAGE-044 Phase 4 关闭与交付

- Task：`IDS-V0_1-STAGE044-P4`
- Acceptance：`ACC-STAGE-044`
- 结果：`PASS_ISOLATED_CLEANUP_CLOSEOUT_DELETE_DISABLED`
- 合同：`half_product_cleanup/stage044_half_product_cleanup_delivery_contract.json`
- 检查器：`KM_IDSystem/scripts/check_half_product_cleanup_delivery.py`
- 下一门：`IDS-STAGE044-REVIEW-GATE`
- 整阶段复审：本轮未执行，必须由下一个独立 run 完成

## 来源与前置绑定

P4 继续绑定唯一 Stage044 task-pack member：
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-044_半成品输出清理.md`，
SHA-256 为
`e7e98eb5497aa33124b944dfc1d00e15588a672c0f9accc4cda4a66fe1f72a53`。
前置提交固定为 P3 `fd1d652bbe2e9edcbf4e7c9619b55db1873b365e`，其
`KM_IDSystem` tree 为 `809a7f6e32ecf57f10803f81abed964fa7cff160`。
检查器逐文件验证 P3 合同、检查器、测试和证据，以及 Stage043 已审交付合同、检查器
与证据；任一来源、祖先、Git index 或 SHA-256 漂移均 fail closed 回到
`IDS-STAGE044-P4-GATE`。

## 交付证据

本轮组合并复验控制面证据，不扫描真实候选、不创建 IDS 业务 job，也不删除文件：

- job state graph：8 类 job、11 个状态、4 个终态、21 条允许转换；
- failure retry log：3 次 attempt、2 次 retry，最终 `DEAD_LETTERED`，未持久化；
- backpressure trigger proof：7 类压力信号均有已审失败关闭证据；
- Stage044 scenarios：P3 的 14/14 个隔离场景重新通过；
- isolated process loss：已审无输入输出控制子进程自行退出码 `73` 只作为 partial-output
  决策证据，未 signal、kill、probe、restart 或 recovery；
- same-source exclusion：4 类操作、25 个完整冲突和 16 个选定矩阵冲突，operation
  invocation、queue record 和 retry budget consumption 均为 0；
- cleanup allowlist：只有 `TEMP_STAGING_OUTPUT` 与
  `INCOMPLETE_DERIVATIVE_OUTPUT` 两类 reference-only 候选；原始资料、事实源、数据库、
  manifest、证据、审计、报告、索引、有效检查点、owner 持有资料和成功输出共 14 类
  始终受保护，delete attempt 与 deleted ref 均为 0。

## 条件处理、自动清理与人工处理

上游 checkpoint resume、Stage039 retry 和 safe-failure 三条路径，仅是在来源、版本、
owner、资源、checkpoint、栅栏、幂等和生产校准全部满足后的恢复候选；两类半成品也仅在
manifest/provenance、可重建性、保留期/hold、durable reference、writer quiescence、
不可变 `lstat` identity、独占 namespace lock 与新鲜资源证据全部有效后的清理候选。

当前没有持久 cleanup candidate/audit state，也没有生产校准或生产 cleanup runtime，
因此 `automatic_recovery_eligible_cases=[]`、`automatic_cleanup_eligible_cases=[]`，
自动恢复成功、自动清理成功和实际清理成功均为空，且所有自动动作标志为 `false`。

下列 14 类情况必须人工处理：受保护资料或原始来源、manifest/provenance 缺失、不可重建、
保留期或 hold 未清、durable reference 存在或未知、writer 活动或未知、writer quiescence
未证明、`lstat` identity 陈旧或变化、未持有独占 namespace lock、同源操作冲突、资源
压力或观测陈旧、幂等冲突、策略未校准，以及缺失持久 cleanup/audit state。

## 安全关闭

本轮只复验 Stage038 已审隔离 transport 的有序关闭证据；P4 未终止或重启任何进程，
未修改任务、重试、锁、候选或审计状态：

1. 停止新的 cleanup evaluation 与未来 runtime 的 candidate discovery；
2. 冻结 cleanup candidate ledger，并等待 owner runtime writer/lock 静止；
3. 保留 source、manifest、evidence、report、audit 和 reference-only quarantine；
4. 仅由 Stage041 owner runtime 释放身份匹配的 cleanup lock；
5. 仅由 Stage038 owner runtime 关闭已审 transport；
6. 验证未发生 delete、persistence 或 runtime-output 写入；
7. unknown 或 in-progress 状态全部转人工复核。

已复验证据只证明隔离 transport `queue_closed=true`、
`all_resource_locks_released=true`，不证明生产 cleanup shutdown 或生产运行时可用。

## 恢复与回滚

未来恢复必须重新校验 source/policy/upstream hash，只加载 durable candidate/audit state，
重新观察资源、owner、writer 和 lock，重验 manifest、hold、reference、retention、identity
与 writer quiescence，并在未来 runtime 以新鲜 `lstat` identity 和独占 namespace lock
重跑幂等候选判断。未通过整阶段复审、生产校准和 runtime 门禁前必须保持 delete disabled；
不得复原丢失的 in-memory cleanup state，不得重开终态历史，也不得以删除作为回滚。

回滚顺序：无效合同立即失败关闭 → 停止新的 cleanup evaluation → 活动、未知或未栅栏
状态转人工复核 → 只撤销 P4 合同、检查器、测试、文档和对应治理同步 → 保留 P1–P3、
Stage037–043 已审证据、原始资料、manifest、evidence、audit 与已交付报告。禁止
destructive rollback、move、overwrite、cleanup/delete、数据库或 schema 动作。

## 停止状态

真实 worker crash、进程探测、signal、kill、终止、重启、自动恢复、自动清理、状态转换、
checkpoint continuation、queue/worker/retry/backpressure/production-lock/lifecycle runtime、
cleanup scan、filesystem probe/traversal、writer probe、dirfd/openat/unlinkat、move、overwrite、
delete、audit/persistence、database/schema、raw metadata、真实或虚构 IDS 业务数据、
Stage044 整阶段复审、Stage045、GitHub upload、batch review 与 app reinstall 均未执行。
P4 只证明关闭合同可执行、可测试、可回滚；它不是生产运行或生产就绪证明。

## 验证结果

- TDD RED：12 个聚焦测试产生 14 个预期断言失败和 1 个预期缺失检查器错误；
- Phase4 checker：合同 `15/15`、交付 `12/12`；
- 最终 GREEN：focused `12/12`；Stage005 `168/168`；Stage041-044 aggregate
  `258/258`（`1196.647s`）；IDS v0.1 full discovery `1004/1004`
  （`1749.795s`）；Stage038-043 六个历史复审检查器、214-event 语义、
  幂等渲染和 KM_IDSystem project dual-plane 均通过；
- 首轮 aggregate `257/258` 仅暴露 Stage044 Phase2 历史 handoff 断言停在 P4。
  修复只扩展精确的 P4-to-Review 路由并重绑定
  Phase2-test -> Phase3-checker -> Phase4-checker 哈希链；历史复审结论和
  runtime 安全边界未被削弱。
