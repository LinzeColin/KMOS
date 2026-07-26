# S06 / P6.4 / T-S06-04 — 上传质量门 receipt

状态：**SUPERSEDED EXECUTION METHOD — phase 行为已由 S06 整体复审以确定性 Fixture/Fake Clock/即时故障注入重新验收**

> **2026-07-26 Owner override / S06 review amendment**：本文原始 phase receipt 中的
> `120 秒 soak`、真实限流窗口等待、scanner P99/drain wall-clock 门与 20 秒对象服务 pause
> 仅保留为已发生的历史审计，不再是开发、部署、上线或下一阶段前置，禁止重跑或据此晋级。
> 当前有效方法和结果见 `S06_STAGE_REVIEW.md`：12 个固定 Fixture 即时回放、Fake Clock
> abuse focused tests、scanner synchronous fault recovery、object unavailable `503 → replay`
> 故障注入；`real_time_soak_used=false`。完成整个 v1.5.2 Taskpack 前不上传 GitHub、不部署。

Taskpack SHA-256：
`31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

Parent commit：
`9c782edee6415db27c0a3c63f569eafb4fe0e6c9`

任务性质：
`T-S06-04` 是 S06 Stage Gate 的 supporting task；task graph 没有给它单独的 primary
Requirement / Acceptance ID。它复用 P6.1-P6.3 已封存合同和 Oracle，不伪造新的 AC 编号。

## 1. 范围与结论

本 receipt 只关闭 `S06 / P6.4 / T-S06-04`。最终候选镜像
`sha256:72bde00b55b0e84767467d9492387d18be5775ca1d958e64582da0d958272fb9`
上的同镜像证据包含：

- P6.1 任意文件/断点/断线/篡改/并发/回滚；
- P6.2 攻击与合法语料、scanner timeout/unavailable、8 项 retry backlog；
- P6.3 immutable version、parent/lineage、固定 processor、预览与回滚；
- P5.2 PostgreSQL + private versioned S3-compatible adapter、真实 20 秒对象服务 stall；
- P4.4 version-aware upload flood、6 路慢 body 并发、公共根页与正常 mutation 存活；
- P6.4 共享容量竞争、跨 workspace 零写入和 120 秒定步 upload/download soak。

最终 `12/12` negative matrix PASS；data invariant、isolation、unexplained failure 均为 `0`。
输出合同已进入 CI artifact：

```text
upload-quality-e2e/benchmark.json
upload-quality-e2e/negative-matrix.json
upload-quality-e2e/capacity-thresholds.json
upload-quality-e2e/summary.json
upload-quality-e2e/report.md
```

每个 compact artifact 均小于 `64 KiB`，只含 synthetic 计数、hash-independent 指标和 image
identity；raw recovery/session capability、workspace ID、文件原始字节、对象 key、DSN 和 provider
credential 不写入 evidence。

以下是当时的 phase 结论与数据，不是当前执行方法。当前只采用可重复的即时 Fixture/故障注入
验证，不声称生产容量、真实用户尾延迟或长周期稳定性；后续容量工作也不得以更长浸泡或真实
观察窗口作为前置。

## 2. 最终 benchmark 与阈值

### 120 秒 final-image soak

| 指标 | 观测 | Gate |
|---|---:|---:|
| 时长 / 上传样本 | `120.00s / 24` | `>=120s / >=24` |
| 上传成功 / 失败 | `24 / 0` | 失败 `0` |
| 下载 hash mismatch | `0` | `0` |
| synthetic 上传总字节 | `2,629,632` | 记录值，不作生产吞吐承诺 |
| upload latency p50 | `87.12 ms` | 记录值 |
| upload latency p95 | `96.94 ms` | `<=2,000 ms` |
| upload latency p99 / max | `104.38 / 104.38 ms` | p99 `<=3,000 ms` |
| RSS 增长 | `1,843,200 bytes` | `<=100,663,296 bytes` |
| FD 增长 | `-20` | `<=8` |
| restart 后首尾 hash | `2/2` | `2/2` |
| active reservation / request part / chunk part | `0 / 0 / 0` | 全部 `0` |
| version / distinct storage key / object | `24 / 24 / 24` | 全相等 |
| version lineage gap | `0` | `0` |

样本使用固定 seed、`1 KiB / 64 KiB / 256 KiB` 三档 synthetic payload，以 5 秒节奏运行。
报告保存完整分布而不是挑选最好的一次；没有 rerun-to-green 或丢弃失败样本。

### 共享配额竞争与隔离

- 镜像合同：单文件 `64 MiB`、chunk `4 MiB`、每 workspace 最多 `16` 个 session、共享 artifact
  容量 `512 MiB`。
- 7 个隔离 workspace 各声明保留 `64 MiB`，达到 `448 MiB`；另外两个 workspace 并发竞争最后
  一个 `64 MiB` 槽位，结果严格为 `1×201 + 1×429 artifact_capacity_reached`。
- reservation 阶段持久化文件字节 `0`；9 个 session 明确取消后，新 `64 MiB` reservation
  成功，证明容量释放。
- 使用另一个 workspace capability 对 winner session 发起 chunk 写入，响应
  `404 workspace_not_found`；owner offset 保持 `0`，跨 workspace 写入字节 `0`。

### scanner backlog

| 指标 | 观测 | Gate |
|---|---:|---:|
| retry backlog | `8` | 固定 synthetic corpus `8` |
| 初始状态 | `scanner_error` | 不得是 clean |
| attachment-only / preview-processing escape | `8 / 0` | escape `0` |
| drained / remaining | `8 / 0` | remaining `0` |
| 总排空时间 | `3,756.07 ms` | `<=60,000 ms` |
| worker item p50 / p95 / p99 | `465.10 / 498.08 / 498.08 ms` | p99 `<=10,000 ms` |
| 故障前后附件 hash 抽查 | `4/4` | `4/4` |

scanner 继续是 non-root、read-only、drop ALL capabilities、no-new-privileges、无 DB/object env、
无 state mount、无 host port、只接私网的独立服务。timeout/unavailable 不会被标 clean，恢复后
由 durable worker 收敛。

### object-store timeout 与幂等恢复

- application S3 read timeout 为 `15,000 ms`；Oracle 将 owned MinIO pause `20,000 ms`，强制
  stall 超过配置读超时，再恢复服务。
- 请求在 `20,177.66 ms` 内经有界 retry 返回 `200`，限定窗口为
  `18,000–45,000 ms`。
- 同一 idempotency key 重放返回同一个 `artifact_version_id`；PostgreSQL version `1`、
  MinIO native object version `1`、duplicate `0`，另一 App node 下载 SHA-256 相同。
- 完整 P5.2 Oracle 为 `20/20` checks、normal consistency `100%`、classified synthetic
  anomalies `3`、unexplained `0`；对象容器同 volume replacement、浏览器状态清除恢复和
  legacy-write rollback dual-read 继续 PASS。

### abuse / tail boundary

- 当前 image 内 policy probe 给出 upload 10 秒 workspace/global budget `24/128`、concurrency
  `2`；Oracle 不再复制过期常量。
- 同一 workspace 在单窗口产生 `24` 个 immutable versions/objects，第 25 次收到受控 challenge；
  immutable-version business rejection `0`。
- 全场 `27` 个 artifact versions = `27` 个 distinct storage keys = `27` 个 object files，
  version lineage gap `0`。
- 6 路 `512 KiB` 慢 body 并发：`2` admitted、`4` concurrency-blocked；攻击中公共根页
  `3.24 ms / 200`、正常 workspace mutation `24.42 ms / 201`；lease 归零后上传恢复 `200`。
- 正常 fixture `100` requests 的 false positive `0`，attack bypass `0`，结束后根页/status
  均 `200`。

## 3. Phase review 与 first-failure accounting

| Finding / 首次失败 | 影响 | 最小修复 | 状态 |
|---|---|---|---|
| `F-P64-001` P4.4 flood Oracle 仍要求第二至第六次上传 `409` | 与 P6.3“每次上传形成新 immutable version”冲突，基线真实失败 | 从 image 内 policy probe 读取阈值，验证 24 versions + 第 25 次受控拒绝，并核对 version/key/object/gap | **RESOLVED** |
| `F-P64-002` P6.1 Oracle 对 preview/execute 都用 `POST` 并要求 `404` | P6.3 新增 GET preview 后 POST 合理变为 `405`，旧 Oracle 误报回归 | 精确验证 GET preview 在 Flag off 时 `404 artifact_preview_disabled`，execute 路由仍不存在 | **RESOLVED** |
| `F-P64-003` 缺少 final-image 共享 quota race 与跨 workspace 写隔离 | 平均路径通过不能证明容量边界串行化或 capability 隔离 | 7×64 MiB reservations + 2 contender；取消释放；异 workspace chunk 写入与 owner offset Oracle | **RESOLVED** |
| `F-P64-004` 初版 quota 场景在同 workspace 建多个活跃 session | 正确触发 `artifact_upload_in_progress`，场景没有测到共享容量 | 改为 7+2 个隔离 workspace 竞争共享 512 MiB，总体合同不变 | **RESOLVED** |
| `F-P64-005` scanner backlog 初版逐项下载耗尽 export global-10s `16/16` | 安全状态正确，但 Oracle 混入另一个 rate-limit 场景而失败 | 在新 policy window 抽查首尾附件；8 项逐一检查状态、worker 收敛和 hash | **RESOLVED** |
| `F-P64-006` 既有 P5.2 只证明 object-store stop/status 503，没有真实 read timeout 中上传幂等性 | 尾部延迟与 retry 可能重复 DB/object version | pause 超过 read timeout，恢复后同 key replay，DB/native version 均严格为 1 | **RESOLVED** |
| `F-P64-007` 缺统一 benchmark / negative matrix / threshold artifact | 多个 Oracle 可各自绿但 image identity 或关键不变量可能未对齐 | P6.4 gate 强制五个 component image ID 相同并输出四个 compact artifacts | **RESOLVED** |

额外执行失败均已解释并保留：

- focused pytest 首次命令漏 `PYTHONPATH`，collection 阶段 5 个 `ModuleNotFoundError: app`；
  使用与 CI 相同环境后 `58/58`，全量为 `274/274`。
- scanner backlog 首版失败对应 abuse DB 的 `export global-10s`，不是 scanner state 或下载
  hash 错误；修复流量隔离后最终镜像通过。
- quota 初版失败为产品正确的 `artifact_upload_in_progress`；改正 traffic model 后才获得共享
  capacity race 证据。

Phase review open finding：`0`；waived/accepted risk：`0`。不把 synthetic 120 秒门提升为生产
容量，是明确的证据边界而非豁免失败。

## 4. 验证

```text
focused backend tests:                              58 passed
all backend tests, Python 3.12:                   274 passed
Ruff changed E2E scope / py_compile:              PASS / PASS
git diff --check / workflow YAML parse:           PASS / PASS
frontend production build:                        PASS (622 modules)
  existing private App bundle warning:            >500 kB, non-blocking
local + Coolify Compose render:                   PASS / PASS
final Dockerfile image build:                     PASS
P6.1 exact-image resumable Oracle:                PASS
P6.2 exact-image scanner/browser Oracle:          PASS
P6.3 exact-image lineage/preview Oracle:          PASS
P5.2 exact-image PostgreSQL/S3 Oracle:             PASS (20 checks)
P4.4 exact-image abuse/slow-body Oracle:           PASS
P6.4 exact-image quality aggregate:               PASS (12/12 rows)
taskpack validator:                               49 req / 49 AC / 56 tasks PASS
validator mutation suite:                         1 positive + 4 negative PASS
  sealed sources unchanged:                       5/5
dual-plane governance:                            PASS (5 projects)
diff/untracked credential-shape + private-path:   0 / 0
```

Vite 既有私有 App bundle 大于 `500 kB` warning 没有因本 phase 增长；为该既有 bundle 做范围外
拆分不增加 P6.4 收益。P6.4 没有写真实业务数据、调用生产 API、修改 Cloudflare/Coolify、上传
GitHub、删除 Docker volume、replay v1.5 recovery bundle 或触碰生产 state。

## 5. Rollout、rollback 与下一边界

P6.4 不做生产 rollout。S06 whole-stage review 前继续保持：

```text
KMFA_RESUMABLE_UPLOAD_ENABLED=0
KMFA_FILE_SECURITY_ENABLED=0
KMFA_ARTIFACT_DERIVATION_ENABLED=0
```

本节原有基于 P95/P99、真实 timeout 和观察窗口的 rollout 指令已废止。后续只允许在隔离
Fixture workspace 即时验证核心链路和高风险故障：scanner backlog 状态收敛、object unavailable
`503 → replay 200`、version/key/object 一一对应、恢复与下载 hash、跨 workspace 零写入、
临时分片归零及 capability/private byte 零命中。不得把 elapsed time、真实等待或人工审批层
作为晋级条件；当前也未授权 rollout。

快速回滚优先降低上传并发/文件上限、排队或降级 scanner，再关闭对应 Flag；已有下载必须继续。
若需停止全部新上传，置 `KMFA_CONSISTENCY_STATE_MODE=paused`。回滚保留 schema `6`、DB、原件、
immutable versions、lineage、assessment/events、intent/chunk、derivatives、对象版本、备份、
reader 配置、所有 named volumes 与 v1.5 recovery asset。禁止 binary/schema downgrade、
`down -v`、删表/对象/卷/备份、撤 reader 凭据、改 verifier 或 recovery replay 覆盖 live state。

本 receipt 的远端分叉与下一 run 说明也已被整体复审取代。当前真值见
`S06_STAGE_REVIEW.md` 与 `KMFA/HANDOFF.md`：本地已纳入
`origin/main=c00a90f5…`，S06 whole-stage review 本地通过；中间 phase/Stage 不上传。下一个新
run 最多执行 `S07 / P7.1 / T-S07-01` 一个 phase，整个 v1.5.2 Taskpack 与最终整包复审完成后
才一次性上传 GitHub。
