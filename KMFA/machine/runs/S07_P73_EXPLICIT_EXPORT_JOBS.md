# S07 / P7.3 / T-S07-03 — 显式导出 Job receipt

状态：**LOCAL PHASE PASS — 未做 S07 整体复审、未上传、未部署、未灰度**

Taskpack SHA-256：
`31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

Parent commit：
`9e8dcbea896f282aa3976a8ed1d8d66bece3eedf`

Requirement / acceptance：
`R-DL-003 / R-DL-004 / AC-DL-003 / AC-DL-004`

## 1. 范围与结论

本 receipt 只关闭 `S07 / P7.3 / T-S07-03`。旧
`GET|HEAD /api/报告中心/导出` 已永久改成不渲染、不排队、不登记、不审计写入的 `405` 弃用响应，
并用 `Link: </api/exports/jobs>; rel="successor-version"` 指向 canonical command。新合同为：

- `POST /api/exports/jobs`：必需 `Idempotency-Key`，只建立有界 durable job；
- `GET|HEAD /api/exports/jobs/{job_id}`：只读状态、事件和成本；
- `GET|HEAD /api/exports/jobs/{job_id}/artifact`：只读并重新验证 size/SHA-256 后 attachment 下载；
- `DELETE /api/exports/jobs/{job_id}`：确定性取消 queued/retry/running job；
- `GET|HEAD /api/exports/jobs/metrics`：只读队列、状态与成本指标；
- 独立 `python -m app.export_worker`：领取、渲染和原子完成；验收用 `--once`。

本 phase 延续旧私有报告中心的 Cloudflare Access 边界，不把历史经营报告接入匿名 workspace，
也不把报告正文、原始幂等键、私有路径、凭据或生成制品提交到公开仓。S08 published snapshot、
P7.4 ownership/authorization matrix、匿名工作区报告生成以及生产启用均不在本 phase。

默认关闭的 `KMFA_EXPORT_JOBS_ENABLED` 只控制新建和 worker 领取。Flag 关闭后既有 job 状态、
事件和未过期制品仍可读取，取消仍可用；源报告、`export_records`、`audit_events`、DB、卷、P7.1/
P7.2 资产、备份及 v1.5 恢复资产不删除、不覆盖、不降级。生成制品是可重建派生物，固定到期；
到期不影响源报告、用户文件、workspace、项目、进度、分数、备份或恢复材料。

任务包的 observation/timeout 文本按 Owner 明确合同全部改为 Fake Clock、Fixture、历史回放与故障
注入即时验证。本轮没有真实时间 Soak、观察期、业务等待窗口、后台空转式验收、重复审批、形式化
Gate、无限重试或全量测试前置。HTTP readiness 仅同步候选进程启动，不是业务观察证据。

## 2. Durable 状态机与资源边界

`export_jobs` 是有数据库约束的 mutable projection；`export_job_events` 是数据库 trigger 强制的
append-only ledger。既有 `export_records` 与 `audit_events` 继续由原 trigger 保护。worker 完成时
在同一 SQLite transaction 中提交：

```text
running job
  + artifact metadata/hash
  + succeeded event
  + export_records append
  + audit_events append
= 一个原子业务结果
```

缺任一 evidence table 的故障注入会整体 rollback，job 保持 `running`，不会出现“成功但无 hash/
审计”。制品先写同卷临时文件、`fsync`、原子 rename，再进入完成事务；取消、lease recovery、
worker 失败和 late commit 都清理未登记制品。进程在制品写入后崩溃时，过期 lease 的下一次领取会
先删除确定性 orphan path；不会把未登记字节冒充成功制品。

状态：

```text
queued -> running -> succeeded -> expired
                  -> retry -> running
                  -> failed
queued/retry/running -> cancelled
```

资源与成本固定上限：

| 边界 | 上限 |
|---|---:|
| 活跃 job | 64 |
| 同时 running | 2 |
| job metadata 记录 | 10,000 |
| 每 job 尝试 | 3 |
| 活跃 estimated cost | 256 units |
| 单 job estimated cost | 64 units |
| source snapshot | 2 MiB |
| artifact | 16 MiB |
| lease / retry delay | 60s / 5s（Fake Clock 直接推进） |
| 生成制品 TTL | 24h（Fake Clock 直接推进） |
| hash verification chunk | 64 KiB |

同一合法 `Idempotency-Key` 只存 SHA-256，不存原值。相同 key + 相同 source/request 并发重放只返回
同一 job；相同 key + 不同请求固定 `409 idempotency_key_conflict`。source snapshot 包含渲染真正
使用的标题、等级三元组、水印和正文或 dispositions，并在 2 MiB 内 canonical hash；worker 重新
取 snapshot 后必须与创建时 fingerprint 相同，并直接渲染已校验的内存 snapshot，避免 check/use
竞态。source 改变固定失败，不静默导出另一版本。

## 3. HTTP 语义、读取安全与兼容

POST 只持久化 command，不同步执行 HTML/CSV/PDF 渲染。创建返回 `202 + Location`；同 key replay
返回 `200 + Idempotency-Replayed: true`。状态、metrics 与 artifact 的 GET/HEAD 均用 SQLite
`mode=ro + query_only=ON`，构造 read repository 时不建目录、不建 DB、不跑 schema。HEAD 与 GET
分别注册独立 OpenAPI operation，不依赖隐式 HEAD。

制品读取固定 `private, no-store`、`attachment`、`nosniff`、content SHA-256 ETag，并返回实际
格式、报告等级、质量等级、delivery 和 watermark 状态。读取前从私有状态卷重新流式计算 size 与
SHA-256；缺失或篡改 `503`，未完成 `409`，到期 `410`，不返回替代字节。

旧副作用 GET 不再校验 query 后渲染，因此任意旧 query（含试图关闭水印的参数）都只得到静态
弃用信息。新 POST model `extra=forbid`；watermark、delivery、报告等级不能由请求控制。前端改为
“创建作业 → 显式刷新状态 → 下载/取消”，不做自动轮询。Flag 默认关闭时显示真实灰度状态，不把
不可用按钮伪装成已完成下载。

## 4. AC-DL-003 / AC-DL-004 确定性证据

最终本地 runtime image：
`sha256:502371f48f3d762b3618c789bd881fb698f1528912076930b3673e8bd2942c05`

exact-image 只挂载一份 synthetic report tree；报告正文、dispositions、故障、时间推进和浏览器
下载均为固定 Fixture。raw idempotency key、真实员工/财务/群聊/考勤/SQLite、恢复码、session、
storage key 和 IDS 原始元数据未进入 evidence。

| 验收项 | 最终观测 | 结果 |
|---|---:|---|
| 旧 GET/HEAD | `405/405`；business state delta `0` | **PASS** |
| 并发幂等 | `24` submissions / `1` created / `1` business result | **PASS** |
| GET/HEAD replay | `24` probes；DB/queue/audit/artifact delta `0` | **PASS** |
| 未授权长任务 | GET/HEAD renderer invocation `0`；生产 Access 在 handler 前拒绝 | **PASS** |
| job lifecycle | cancel/retry/timeout recovery/source-change fail/expiry 全部确定 | **PASS** |
| retry bound | 最多 `3` attempts；无无限 retry | **PASS** |
| 原子 evidence | evidence table 缺失时 success/export/audit 全 rollback | **PASS** |
| artifact | attachment + watermark；size/hash 再验证；SHA-256 `40c77d78…ca2f8` | **PASS** |
| 成本 | estimated/actual `1/2` bounded-render-unit-v1 | **PASS** |
| restart | job 状态与 artifact byte-identical | **PASS** |
| Flag rollback | 新建阻断、worker disabled；status/artifact 保留；re-enable 保留 | **PASS** |
| 浏览器 | 创建→worker→刷新→下载；hash match；console error `0` | **PASS** |
| 隐私 | raw key/private marker/report body log hit `0/0/0` | **PASS** |
| 时间纪律 | real-time acceptance waits `0`；soak/observation gate `false` | **PASS** |

Ignored local evidence：

```text
KMFA/.codex_private_runtime/s07-p73-e2e-reviewed/summary.json
  sha256 57ba6ab7da4423c581834b945e99f8d5c5ff733d37063d8fd4053c5381235e53
KMFA/.codex_private_runtime/s07-p73-e2e-reviewed/http-trace.json
  sha256 391a92577493a2297d887e509c00aa7eb9f78c694cfc75a3224bd0cab5b83be3
KMFA/.codex_private_runtime/s07-p73-e2e-reviewed/export-job-ui.png
  sha256 f93a4fc9b90322b0e170d1098893ea894ab0c75446cbcc2da519f598d222d2c5
```

## 5. Phase review findings

| Finding | 影响 | 最小修复 | 状态 |
|---|---|---|---|
| F-P73-001 旧 GET 同步渲染并写 export/audit，新 POST 为 404 | GET 不 replay-safe，成本与副作用不可控 | 永久 405 弃用 + canonical durable command API | **RESOLVED** |
| F-P73-002 combined GET/HEAD route 产生重复 OpenAPI operation id | route inventory 有歧义 | GET/HEAD 分别注册并共享只读 helper | **RESOLVED** |
| F-P73-003 初版取消或 lease crash 后可能留下未登记制品 | 私有卷 orphan 增长 | cancel + stale recovery 删除确定性 orphan path；late worker 同样清理 | **RESOLVED** |
| F-P73-004 初版报告中心仍回传过时本机 registry path | 暴露无用实现路径且与 SQLite 不符 | 改为 `app-state:export_records` 稳定引用 | **RESOLVED** |
| F-P73-005 source fingerprint 若校验后重新读文件存在 TOCTOU | hash 对不上实际渲染输入 | canonical bounded snapshot 校验后直接渲染同一 snapshot | **RESOLVED** |
| F-P73-006 E2E 对中文 legacy URL 未 percent-encode，预期业务失败被当基础设施失败 | Oracle 误报 | URL canonical quote；expected failed worker 显式验 rc=1 | **RESOLVED** |

Phase review open finding：`0`；waived/accepted risk：`0`。P7.4 ownership/authorization matrix、
S07 whole-stage review 和 S08 published snapshot 未被本 receipt 冒充为完成。

## 6. 验证

```text
pre-change baseline:
  GET /api/报告中心/导出:                       200 + export/audit 各 +1
  POST /api/exports/jobs:                       404

P7.3 + report/audit/public/access/abuse focused: 136 passed
Ruff changed Python（main 仅忽略既有 E741）:     PASS
frontend production build:                       PASS (622 modules)
  existing private App bundle warning:           >500 kB, non-blocking
host dist vs final exact-image dist:              6/6 byte-identical
local + Coolify Compose render:                   PASS / PASS
final Docker frontend+backend image build:        PASS
TEST-DL-003/004 exact-image API + Chromium:       PASS
  GET/HEAD state delta / long task:               0 / 0
  concurrent submissions / business results:     24 / 1
  cancel/retry/timeout/source-change/expiry:       true/true/true/true/true
  restart/rollback/re-enable:                      true/true/true
  browser console error / privacy log hit:         0 / 0

repository/taskpack closeout:
  validate_taskpack.py:                            PASS
    requirements/AC/stages/phases/tasks:           49/49/14/56/56
    receipts/errors/warnings:                      41/0/0
  check_dual_plane_ci.py --require-projects:       PASS (5 projects)
  sealed taskpack sources:                         5/5 byte-identical
    canonical_facts.yaml:                          5ae070cb…9552
    acceptance_contract.yaml:                     1f07bd14…bc1
    task_graph.yaml:                               a9753e7c…306
    release_policy.yaml:                           f47de7a0…3c7
    traceability.csv:                              ca369627…727
  compact receipt:                                 <64 KiB
  git diff --check:                                PASS
  staged public-safety shape scan:
    files / high-signal secret-private path hit:   19 / 0
    email-mobile-national-ID shape hit:            0
    forbidden runtime-credential-archive path:     0
  final pre-commit origin/main fetch:              c00a90f5…24a45
    local HEAD ahead/behind:                       9/0
```

验证没有把连续运行 N 小时、后台空转、真实等待、观察期、Soak、重复审批、全量测试或生产流量
作为前置。worker 的生产 poll loop 是可停止的队列消费者，不是验收计时器；Flag 为 0 时进程直接
退出。所有 retry/lease/expiry 测试直接推进 Fake Clock。

## 7. Rollback、停止条件与下一边界

整个 v1.5.2 Taskpack 完成前保持 `KMFA_EXPORT_JOBS_ENABLED=0`，不启动 `export-jobs` profile，
不部署、不灰度。快速回滚使用同一 binary/schema 把 Flag 置 `0` 并停止 worker；拒绝新建与领取，
继续提供既有 status/artifact/cancel。保留 job/event、export/audit、源报告、P7.1/P7.2、DB、
原件/派生物、备份、卷和 v1.5 recovery bundle。禁止旧 binary/schema downgrade、删卷、删源报告、
删备份、撤 reader 凭据或用 recovery replay 覆盖 live state。

立即停止条件：旧 GET/HEAD 仍改变业务状态；同 key 多业务结果；越预算领取；跨私有 Access 边界；
source/hash/metadata 错配仍下载；取消/失败/lease 后 orphan；成功状态缺 export/audit；无界 retry；
日志/evidence 出现 raw key、private bytes 或凭据；或回滚要求删除既有状态。

本地 Task 进度为 `31/56`；S07 为 `3/4` phases，S07 整体复审未开始；published Stage 仍为
`6/14`。下一次新 run 只可执行 `S07 / P7.4 / T-S07-04` ownership/authorization/负载总门禁，
不得提前进入 S07 整体复审、S08、上传 GitHub、部署或启用任何生产 Flag。
