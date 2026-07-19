# STAGE-044 Phase 3 Half-Product Cleanup Scenario Validation

## Decision

`IDS-V0_1-STAGE044-P3` 只执行隔离、非生产、reference-only 场景验证。它复跑
Phase 2 的内存候选判定，并复用已评审 Stage041/043 控制证据；不扫描或访问真实
候选路径，不运行后台清理，不移动、覆盖或删除文件。

结果只有在十四项场景全部通过时才是
`PASS_ISOLATED_CLEANUP_SCENARIOS_DELETE_DISABLED`。该结果不表示任何文件已清理、
不表示生产清理可用，也不授权自动恢复或 Phase 4。

## Source And Predecessor

- 唯一 Stage044 taskpack member、roadmap 与使用说明继续按精确 SHA-256 绑定。
- Phase 2 提交 `4867bb14f1ff87231d4dd6f4ebae7251d60be585` 及其
  `KM_IDSystem` tree `790114d3ce9e3e416d70c64da467ff148ceb848c` 必须保持
  当前 HEAD 的祖先。
- Phase 2 合同、检查器、测试和证据按提交时哈希绑定；治理前向变更只允许加入
  明确的新哈希并继续要求 Git tracked。
- Stage041 lock scenarios 与 Stage043 crash-recovery scenarios 作为已评审隔离控制
  证据复跑，不转移运行时职责。

## Fourteen Scenarios

1. 相同 cleanup request 精确 replay 只保留一条进程内 ledger 记录。
2. 同 request ID 的 changed payload 返回冲突且无副作用。
3. Stage043 的隔离控制子进程自退出证据只形成半成品复核候选，不执行恢复或删除。
4. 移动硬盘离线控制信号阻断清理，不物理拔盘。
5. 低磁盘控制边界阻断清理，不分配或填充磁盘。
6. API 预算不足阻断清理，不发起外部 API 请求。
7. `RUNNING` writer 阻断清理。
8. writer quiescence 或 producer/cleanup lease 证据未知时阻断清理。
9. `lstat` identity 不稳定时阻断清理，且不探测文件系统。
10. 同一相对路径缺少 exclusive namespace lock 时阻断清理。
11. Stage041 证明 processing、extraction、index、report 共用 source-pipeline 排他域。
12. fact source、manifest、evidence ledger、report snapshot、audit log 全部受保护。
13. Phase 2 声明的十四个 protected classes 全部拒绝删除。
14. 满足全部 reference-only gate 的两类半成品仍只返回人工复核候选，
    `delete_allowed=false`。

## Worker Loss Evidence Boundary

Phase 3 复用 Stage043 已评审的 ephemeral control child 自退出 `73` 证据。它不是
生产 worker 崩溃，不发送 signal、不 kill、不探测外部进程、不重启 worker、不执行
checkpoint resume 或 crash recovery。Stage044 只验证失败 attempt 的局部输出仍须
通过清理候选门，且候选结果不开放删除。

## Resource, Writer And Identity Boundary

drive、disk 与 API 仅作为受控 metadata 信号传入 Phase 2 evaluator。Phase 3 不对
候选文件所在设备或目录做 probe。活动 writer、未知 quiescence、未 fencing lease、
非 exclusive/非 managed lock、陈旧 identity、retention 不足或任一 evidence 缺失都
返回 `CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN` 或 `CLEANUP_BLOCKED_RESOURCE`。

## Same-Source Lock Evidence

四个任务族 `FILE_PROCESSING`、`ARCHIVE_EXTRACTION`、`INDEX_BUILD`、
`REPORT_GENERATION` 对同一 source 共用 `SOURCE_PIPELINE` 排他域。复用证据包含
完整矩阵 `25` 个冲突与所选四族 `16` 个冲突，operation、queue record 与 retry
budget effect 均为 `0`。本阶段不获取生产 lock/lease/fencing。

## Protected Artifact Evidence

核心五类和完整十四类都通过 Phase 2 evaluator 返回
`CLEANUP_BLOCKED_PROTECTED`。没有 delete attempt、没有 delete API、没有 override、
没有 background cleanup。事实源、manifest、证据账本、报告快照、审计日志、
已交付报告、索引、有效 checkpoint、held/succeeded output 均保持不可清理。

## Explicit Non-Actions

- no real cleanup scan, candidate discovery, stat/lstat, traversal or writer probe;
- no production lock acquisition, openat, unlinkat, move, overwrite or delete;
- no state/terminal/manifest/checkpoint/output mutation or audit/persistent write;
- no database/schema, queue/worker/retry/backpressure/lifecycle runtime;
- no raw metadata or IDS business source access and no fake IDS business data;
- no Phase 4, whole-stage review, Stage045, batch review, GitHub upload or app reinstall.

## Final Layered Validation

- Phase 3 checker: contract `18/18`, scenarios `14/14`.
- Focused tests: `19/19` in `14.295s`.
- Stage005 governance regression: `167/167` in `31.893s`.
- Stage041-044 aggregate: `246/246` in `1093.223s`.
- IDS v0.1 full discovery: `991/991` in `1436.808s`.
- Stage038-043 historical review checkers: `6/6`, all `review_valid=true`.
- Governance events: `213`, with zero parse, duplicate-ID or semantic errors.
- Machine-fact rendering is idempotent and KM_IDSystem project dual-plane is PASS.

首轮 aggregate `231/246` 与首轮 full discovery `990/991` 均按预期失败关闭。
修复只覆盖当前 P3→P4 前向路由、精确上游哈希兼容与
`persistent_recovery_state_available_after_exit=false`、
`automatic_recovery_performed=false` 的事实约束；没有改变历史复审结论、运行时能力、
删除授权或任何生产边界。

## Phase 4 Gate

十四项场景、Phase 2 复跑、Stage041 lock 证据和 Stage043 control-process 证据必须
同时通过，下一 gate 才可为 `IDS-STAGE044-P4-GATE`。Phase 4 必须在单独 run 中
执行；本轮 `push_allowed=false`。

## Rollback

只撤销 Phase 3 场景合同、检查器、测试、证据和最小治理投影。保留 Phase 1/2 与
Stage041/043 已评审证据。回滚不得扫描、读取或处理任何 runtime/source path，
不得删除 staging、cache、database、manifest、evidence、audit、report、checkpoint、
index 或原始资料。
