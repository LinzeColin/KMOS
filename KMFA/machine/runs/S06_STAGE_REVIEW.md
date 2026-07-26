# S06 whole-stage review — 安全上传、隔离扫描与版本血缘

状态：**LOCAL STAGE PASS — findings 全部解决；未上传 GitHub、未部署、未灰度**

日期：`2026-07-26`

范围：`S06 / P6.1-P6.4 / T-S06-01..04`

## 1. Authority 与发布边界

- 唯一基线：`KMFA_Product_Design_Taskpack_v1.5.2.zip`
- ZIP SHA-256：
  `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`
- task graph SHA-256：
  `a9753e7c76dea6041b7386fd31735db869a6e371bcbce57c2fc794256a4d1306`
- acceptance SHA-256：
  `1f07bd14a382a4bad552f43e7ba281064c06bae7ab52c5e0d75139c305c43bc1`
- 本地 phase chain：
  `59c65933 → e30963ce → 9c782ede → 3540d2ef`
- 运行时复审 merge：
  `4454aa6bba2e5dd1cb43a4421f368aed27ad0796`
  （父提交 `3540d2ef… + origin/main c00a90f5…`）
- restore oracle 修复：
  `8637c2e67d8bb869ee8e06aa6ecfe9f6a7bf393f`
- reviewed runtime image：
  `sha256:ed2175dc2d42c2e0e54274cee3b0cd0aabd2d175f56dde91887cbfe1133d3812`

上述 image 用于 S06 行为与恢复证明，不是发布候选：Owner 已改为**完成整个 v1.5.2
Taskpack 后一次性上传 GitHub**。本 Stage 不 push、不部署、不启用生产 Flag；后续源码还会继续
变化，因此不为中间 Stage 制造伪 release identity。

## 2. Owner 执行方法覆盖

2026-07-26 Owner 明确禁止把真实时间 soak、观察期、等待窗口、后台空转、重复审批、形式化
Gate、无限重试、连续运行 N 小时或全量测试作为开发、部署、上线或下一阶段前置；时间状态应使用
Fake Clock、历史回放、Fixture、模拟消息与即时故障注入。

本次已把该约束落实为代码而非口头豁免：

- P6.4 从 `120s/24` 定步 soak 改为 `12` 个固定 seed、三档大小的即时 Fixture replay；
- 删除 elapsed/P95/P99/RSS/FD 晋级阈值，输出
  `real_time_soak_used=false`、`wall_clock_promotion_threshold_used=false`；
- scanner backlog 不再等待新的 10 秒 rate window，也不以 drain/P99 判定；
- scanner timeout 由 fake-client focused test 即时注入，移除 scanner service 的 test sleep
  后门；
- object store 从 20 秒 pause 改为立即 unavailable：`503 → 同幂等键 replay 200`；
- P5.3 去掉 `recovery <= 30s` wall-clock Gate，仅验证 28 个故障点回放后状态收敛；
- CI backend 从全目录改为 10 个明确的核心/高风险 focused 文件；移除 P4.4 实时时窗 E2E、
  三浏览器公共全流、P5.1 全链和旧私有经营 App 全流作为前置。

旧 P6.4 receipt 的 120 秒数据只保留为“已废止方法”的审计记录，禁止重跑或用于晋级。

## 3. Acceptance closure

| Acceptance | 结果 | 关键证据 |
|---|---|---|
| `AC-UP-001` 任意合法样本安全存储；未知/高风险只作附件；执行成功 `0` | **PASS** | P6.1 `7/7` 类型均 attachment-only，执行 `0`；P6.2 风险附件 `4/4`、恶意拒绝 `4/4` |
| `AC-UP-002` 恢复 `100%`、篡改/泄露/超限写入/重复增长均 `0` | **PASS** | 半分片接受 `0`、篡改接受 `0`、超限写入 `0`、并发 durable copy `1`；12 Fixture upload/download/restart hash 全通过 |
| `AC-UP-003` 恶意/畸形 escape `0`，parser 不在 Web，合法误拒 `<1%` | **PASS** | escape `0`、final-image 合法误拒 `0/12`、focused policy corpus 零误拒；scanner 无 DB/object env、无 state mount/host port |
| `AC-UP-004` 版本唯一可追踪、不可覆盖、血缘缺口 `0` | **PASS** | 版本/血缘/派生物 `6/6/6`，original overwrite、parent gap、lineage gap 均 `0`；浏览器校验 preview SHA |

P6.4 v2 确定性聚合结果：

```text
component Oracles:              resumable / file-security / object-storage / lineage PASS
fixed Fixture replay:           12 uploads / 12 downloads / 2 restart hash checks
failed uploads / hash mismatch: 0 / 0
negative matrix:                10/10 PASS
data invariant failures:        0
isolation failures:             0
unexplained failures:           0
real-time soak used:            false
wall-clock promotion gate:      false
```

对象层即时故障注入为 `status 503 / first mutation 503 / replay 200`；最终 PostgreSQL
artifact version、MinIO native version、duplicate 为 `1 / 1 / 0`，download hash match。
Scanner backlog 为 `8 queued / 8 drained / 0 remaining / 0 preview-or-processing escape`，
且 `real_time_window_wait_used=false`。

## 4. Whole-stage findings

| Finding | 风险 | 修复 | 状态 |
|---|---|---|---|
| `F-S06-001` 删除请求可与 active scanner claim 竞态 | 删除一致性与可恢复性 | 删除前拒绝 active scan；scanner 只领取 retention=`active`；跨生命周期回归覆盖 | **RESOLVED** |
| `F-S06-002` flags=`0` 时 worker 在 `restart: always` 下退出循环 | rollback 可能重启风暴 | `--once` 才退出；service mode flags-off 有界 idle，配置先校验 | **RESOLVED** |
| `F-S06-003` UI/运维说明仍声称无预览或只到 P6.1/P6.2 | 用户与操作员被误导 | README、Public Shell、Walking Skeleton、Coolify 示例统一到 P6.1-P6.4 与 flags-off 边界 | **RESOLVED** |
| `F-S06-004` 本次 E2E 改动含 E501 | changed-scope lint 不绿 | 仅格式化 4 处本次变更，不扩张清理 231 条历史 Ruff debt | **RESOLVED** |
| `F-S06-005` P5.4 restore oracle 仍断言 schema `4` | schema `6` 真恢复被假红 | 单一 `EXPECTED_DATABASE_SCHEMA_VERSION=6` 同时驱动断言与报告 | **RESOLVED** |
| `F-S06-006` P6.4 使用真实 120 秒 soak 与 wall-clock 阈值 | 违反 Owner 方法与低 ROI | 固定 12 Fixture 即时回放；移除所有时间晋级阈值 | **RESOLVED** |
| `F-S06-007` scanner backlog 等待新限流窗口并测 drain/P99 | 真实等待与 flake | 去掉窗口等待、延迟指标，只判状态收敛/零逃逸；timeout 用 fake client | **RESOLVED** |
| `F-S06-008` 对象超时靠 pause 20 秒制造 | 真实等待且重复 outage 场景 | 合并为 unavailable `503 → replay` 即时故障，保留版本/幂等/恢复证明 | **RESOLVED** |
| `F-S06-009` deploy Gate 跑 full backend、P4.4 实时时窗与非 MVP 全流 | 全量测试成为晋级前置 | CI 改为明确 focused 核心/高风险集合；删除相关前置步骤 | **RESOLVED** |
| `F-S06-010` HANDOFF 把 partial recovery bundle 写成 verify PASS | 恢复证据过度声明 | 改为只声明 hash/ref；当前仓缺 prerequisite，verify 被明确阻断，禁止盲导入 | **RESOLVED** |

Open finding：`0`。Waived / accepted failure：`0`。

## 5. Targeted verification

```text
focused owner-method regression:     62 passed, 1 inherited warning
  abuse Fake Clock / scanner fault / public deploy wiring / consistency state
changed Python Ruff E,F / py_compile: PASS / PASS
workflow YAML / git diff --check:     PASS / PASS
taskpack validator:                   49 req / 49 AC / 14 stages / 56 tasks PASS
validator mutation suite:             1 positive + 4 negative PASS; sources 5/5 unchanged
repository dual-plane:                PASS (5 projects)
frontend production build:            PASS (622 modules; existing >500 KiB warning only)
Compose render:                       local + Coolify profiles PASS
P6.1 exact-image resumable:           PASS
P6.2 no-window scanner/browser:       PASS
P6.3 exact-image lineage/preview:     PASS
P5.2 immediate object fault:          PASS (20 checks)
P5.4 schema-6 backup/restore/delete:  PASS
P6.4 deterministic aggregate v2:      PASS (10/10)
```

在 Owner 覆盖前曾运行全 backend `276 passed` 与真实时间 P6.4；它们仅是历史诊断，不是当前或
未来前置，也不用于宣称长周期稳定性、生产容量或生产 RPO/RTO。

## 6. Recovery、rollback 与下一边界

v1.5 partial recovery bundle：

- SHA-256：
  `2d0b516fe7d578061e97dfca874745bcf3a0bf504b0f80976ad3aa21e01077ed`
- bundle ref：
  `1ee7fb111075225dc39039263d2681a0c0acd155 refs/heads/recovery/kmfa-v15-fuzzy`
- 当前仓缺 prerequisite commit
  `97edb1b8750d49409a4f9372a784d4772fea258e`，受保护 dryrun repo 也不存在；
  因此只能确认 hash/ref 保留，不能声明 `git bundle verify PASS`。
- 未 import、replay、merge 或 force-push；恢复资产未删除。

生产边界继续保持：

```text
KMFA_RESUMABLE_UPLOAD_ENABLED=0
KMFA_FILE_SECURITY_ENABLED=0
KMFA_ARTIFACT_DERIVATION_ENABLED=0
```

回滚保留 schema `6`、DB、原件、所有 immutable versions、lineage、assessment/event、
intent/chunk、derivatives、对象版本、备份、reader 配置、named volumes 与 v1.5 recovery
asset；禁止 binary/schema downgrade、`down -v`、删表/对象/卷/备份或 recovery replay 覆盖
live state。

本地 Task 进度为 `28/56`，S06 为 `4/4` 且 whole-stage review 本地通过；远端 published
Stage 仍为 `6/14`。根据最新 Owner 合同，**中间 Stage 一律不上传**；完成全部 `56/56`
Task 与最终整包复审后才一次性上传 GitHub。

下一个新 run 最多执行一个 phase：`S07 / P7.1 / T-S07-01`。不得在本 run 进入 S07、push、
部署、灰度、启用生产上传/扫描/预览，或切生产 PostgreSQL/S3/backup/lifecycle/delete。
