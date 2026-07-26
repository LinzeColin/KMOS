# S06 / P6.3 / T-S06-03 — 版本、血缘与预览 receipt

状态：**LOCAL PHASE PASS — 未做 S06 整体复审、未上传、未部署**

Taskpack SHA-256：
`31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

Parent commit：
`e30963ce72cbec909a190e4a94e64db6074c23d5`

Requirement / acceptance / test：
`R-UP-004 / AC-UP-004 / TEST-UP-004`

## 1. 范围与结论

本 receipt 只关闭 `S06 / P6.3 / T-S06-03`。候选实现把同一匿名 workspace 的每次上传
保存为同一个 logical artifact 下的新 immutable version；同名、相同内容和修改内容都不会
覆盖历史。schema `6` 持久化版本号、parent、来源 upload operation、checksum、processor
registry、processing run、generation 和 derivative metadata，并把原件、衍生物、血缘一起
纳入备份恢复、对象对账、明确删除和容量预算。

默认关闭的 `KMFA_ARTIFACT_DERIVATION_ENABLED` 只允许独立 worker 处理 scanner 已判定
`clean` 的 `text/plain` 或 `application/json`。固定处理器
`kmfa-safe-text-extract/1.0.0` 最多读取经 size + SHA-256 复核的原件前缀 `256 KiB`，严格
UTF-8、NFC 归一和控制字符替换后只生成最多 `64 KiB` 的 `text/plain`；不执行用户代码或宏，
Web 进程不解析原件。浏览器下载预览后先复核 derivative SHA-256，再以 React text node
渲染；响应同时固定 `nosniff`、`no-store` 和 `default-src 'none'; sandbox`。高风险、
attachment-only、未扫描或不支持格式不进入处理器，也不提供内联预览。

最终候选镜像
`sha256:98c08e5873d311e7a49e19d82300b429dc2b3e9af31a9f832214aa55435c9bea`
上的 exact-image API + Chromium Oracle 证明：同名版本 `3`、其中相同内容 `2`、修改内容
`1`、原件覆盖 `0`、parent/lineage gap `0`；重新处理产生 generation `2`，同一幂等键重放
只产生一个 processing run 和一个 audit side effect；高风险预览/处理均为 `0`。重启和关闭
derivation Flag 后，原件、版本、血缘、派生物及最新下载 hash 均保持不变。

本 phase 交付的是满足当前 AC 的最小安全 text-preview derivative，不声称任意媒体都可预览，
也不引入通用 parser/thumbnail 平台。任意文件的安全存储与附件下载继续由 P6.1/P6.2 合同
保障；图片 thumbnail 等新处理器只有在独立安全边界、固定版本和新的验收语料具备后才能加入
registry。P6.3 没有进入 P6.4 load/soak、S07 Range/ZIP/download 扩展、S06 whole-stage
review、GitHub upload、Coolify/Cloudflare 变更或生产 rollout。

## 2. 已实现合同

### Immutable version 与完整 lineage

- 每次已授权 `PUT artifact` 都分配新的 `artifact_version_id`、单调 `version_number` 和独立
  object key；同一 workspace 保持一个 logical `artifact_id`，兼容 `artifacts` projection
  保留首版且不改写。
- `consistency_operations.artifact_version_number` 在 intent 阶段持久化；commit transaction
  同时写 `artifact_versions` 和 `artifact_version_lineage`。root 无 parent，后续 revision
  必须指向前一版本；SQLite/PostgreSQL 均用 FK、unique/check 和 update-reject trigger
  固定血缘。
- 单 logical artifact 最多 `32` 个 immutable versions；超限在新 object commit 前确定拒绝。
  上传 reservation、resumable reservation、原件、prepared derivative 和已收敛 derivative
  共用 `512 MiB` workspace artifact budget，避免派生物绕过已有容量门。
- workspace API 返回当前 version ID/number/count、parent/relation、checksum 和 preview
  metadata；独立 lineage API 返回 original/derivative nodes、revision/derived edges 和可机械
  检查的 `lineage_gaps`。

### Fixed processor 与可重跑 derivative

- `processor_registry` 的 name/version/output kind/media type/implementation SHA-256 不可更新或
  删除；历史 processing run 永远保留当时 processor identity，不把升级后的结果冒充旧结果。
- `artifact_processing_runs` 使用
  `pending → processing → prepared → converged`，或永久 `not_applicable`；lease、row version、
  retry 和 generation 均 durable。每个 source version/processor 最多 `16` 个 runs。
- derivative metadata 在 object write 前进入 `prepared`；重试若遇到同 key，只接受 size、
  SHA-256、artifact/derivative metadata 完全相同的 immutable object，随后原子收敛 projection。
- reprocess 强制 `Idempotency-Key`。同 key 重放返回同一 run，且只首次请求写
  `artifact_reprocess_requested` audit event；新 key 才产生下一 generation。
- preview endpoint 只返回最新已收敛 `text/plain` derivative；Flag 关闭后 endpoint fail
  closed，但原件下载与 lineage 查询仍可用，既有 derivative row/object 不删除。

### 生命周期、备份与恢复

- backup table dependency order 为 original version → lineage、processor registry →
  processing run → derivative；object index 同时封装原件、隔离对象和 derivative bytes。
- 任一 processing run 处于 `processing/prepared` 时 backup fail closed，避免 object/DB
  recovery point 不一致。含 derivative 的 full restore 会校验每个 object 的 size + SHA-256。
- inventory/reconciliation 同时枚举原件与 derivative；明确删除会先阻断 active processing，
  再把 derivative object versions 加入同一 lifecycle target，保留审计与恢复证明约束。
- legacy SQLite importer 对旧 artifact 只作确定的 root/revision backfill，不伪造 derivative；
  PostgreSQL/SQLite migrations 均保持既有 v1.5 reader 和恢复资产。

## 3. AC-UP-004 最终镜像 Oracle

所有输入均为 synthetic fixture；raw recovery/session capability、shared secret、用户文件名、
object key、DSN 和 provider credential 不写入 compact receipt 或 CI artifact。

| Gate | 最终观测 | 结果 |
|---|---:|---|
| 同名上传 | `v1 → v2 → v3`，logical artifact `1` | **PASS** |
| 相同内容 | 两个独立 version/object metadata；checksum 相同 | **PASS** |
| 修改内容 | 第三版独立 checksum；最新下载字节/hash 相同 | **PASS** |
| 历史覆盖 | 原件 overwrite `0` | **PASS** |
| version lineage | parent gap `0`；lineage gap `0` | **PASS** |
| processor lineage | 固定 `kmfa-safe-text-extract/1.0.0` + implementation hash | **PASS** |
| reprocess | generation `2`；同 key run/audit side effect 均 `1` | **PASS** |
| 高风险边界 | HTML attachment-only；preview/processing `0/0` | **PASS** |
| 浏览器 | 根页、同名第二版 `v2 / 2`、browser SHA 校验、React text render | **PASS** |
| restart | version/lineage/preview 均保留 | **PASS** |
| Flag rollback | 原件下载 hash 保持；DB/lineage/derivative 不变 | **PASS** |
| 隐私 | app/worker log capability/shared-secret 命中 `0` | **PASS** |

exact-image 最终数据库摘要：

```text
schema_version: 6
versions / lineage: 6 / 6
processor registry rows: 1
processing runs: converged=6
derivatives / distinct derivative object keys: 6 / 6
```

P6.3 exact functional Oracle 使用隔离 SQLite + private filesystem object adapter，并启动真实
scanner、worker、App 和 Chromium。相同最终 application image 还分别通过 PostgreSQL
schema/migration/恢复 gate `14/14`，以及私有 versioned S3-compatible gate `19/19`
（normal consistency `100%`、classified anomalies `3`、unexplained `0`）。后两项证明
schema `6` 和既有 provider adapters 没有回归；不把它们误报为 derivative 已在生产 S3 或
生产数据库上 rollout。

## 4. Phase review findings

| Finding | 影响 | 最小修复 | 状态 |
|---|---|---|---|
| `F-P63-001` pre-change 第二次 artifact upload 不能形成可追溯 revision | 同名/相同/修改内容无法满足历史不覆盖 | 一个 logical artifact 下新增 immutable versions、version cap 与最新 projection | **RESOLVED** |
| `F-P63-002` version 没有 durable parent/source operation | 无法反查来源且 lineage gap 不可机械识别 | schema 6 lineage table、FK/check/immutability trigger 与 graph Oracle | **RESOLVED** |
| `F-P63-003` 若 Web 直接解析原件或高风险格式进入 preview | 用户内容可在主动执行面逃逸 | 仅 scanner-clean text/JSON 的独立 worker；固定有界 text output；高风险 attachment-only | **RESOLVED** |
| `F-P63-004` derivative 若不进入 backup/delete/inventory | 恢复后悬空、删除不完整或对象账不平 | backup/restore、reconciliation 和 lifecycle 全部纳入 derivative | **RESOLVED** |
| `F-P63-005` derivative 未占用共享容量 reservation | reprocess 可绕过匿名 workspace 资源预算 | 原件、upload reservations、prepared/converged derivatives 统一 `512 MiB` 预算 | **RESOLVED** |
| `F-P63-006` 首版容量 SQL 在 psycopg 中含裸 `%` | PostgreSQL upload 返回 `503` | `LIKE` pattern 改为参数绑定；同镜像 PostgreSQL `14/14` | **RESOLVED** |
| `F-P63-007` 首版幂等 reprocess replay 重复写 audit | 一个业务请求产生多个可见副作用 | repository 返回 `created`，仅首次请求写 audit；exact Oracle 固定 side effect `1` | **RESOLVED** |

Phase review open finding：`0`；waived/accepted risk：`0`。不支持格式保持 attachment-only、
不声称通用 thumbnail/parser 能力是明确产品安全边界，不是把失败 Gate 豁免为 PASS。

## 5. 验证

```text
P6.3 focused backend tests:                         5 passed
capacity/resumable/abuse regression:               28 passed
all backend tests, Linux Python 3.12:              274 passed
  warning:                                          1 Starlette/httpx deprecation
Ruff new/changed P6.3 scope / py_compile:           PASS / PASS
git diff --check / workflow YAML parse:            PASS / PASS
frontend production build:                         PASS (622 modules)
  existing private App bundle warning:             >500 kB, non-blocking
local + Coolify Compose render:                    PASS / PASS
final Dockerfile frontend+backend image build:     PASS
TEST-UP-004 exact-image API+Chromium Oracle:        PASS
  same-name/same-content/modified versions:         3 / 2 / 1
  original overwrite / parent gap / lineage gap:   0 / 0 / 0
  high-risk preview / processing:                  0 / 0
  reprocess generation / idempotent audit effects: 2 / 1
same-image PostgreSQL schema gate:                 PASS (14 checks, schema 6)
same-image private S3 adapter gate:                PASS (19 checks)
  normal consistency / unexplained anomaly:        100% / 0
taskpack validator:                                49 req / 49 AC / 56 tasks PASS
validator mutation suite:                          1 positive + 4 negative PASS
  sealed sources unchanged:                        5/5
dual-plane governance:                             PASS (5 projects)
diff/untracked credential-shape + private-path:    0 / 0
```

Vite 的既有私有 `App` bundle 大于 500 kB warning 不影响公共 Shell 或本 phase 功能；为该既有
bundle 做范围外拆分没有本 phase 收益。Ruff 的 `EXE001` 按仓库现有 E2E 文件约定排除：同目录
Oracle 保持 shebang 与 Git mode `100644`。

## 6. Rollout、rollback 与下一边界

P6.3 不做生产 rollout。S06 whole-stage review 前保持
`KMFA_ARTIFACT_DERIVATION_ENABLED=0`；P6.1/P6.2 Flags 也不得因本 phase 自动晋级。
未来 guarded rollout 必须使用 reviewed 同一 source/image，先在非生产 workspace 启用
derivation worker，证明 processor registry、version graph、preview hash、高风险 attachment-only、
容量和 restart Oracle，再按灰度流量晋级。任一 gap、hash mismatch、越权 preview、异常容量或
隐私命中立即关闭 Flag。

快速回滚使用同一 schema `6` binary，把 `KMFA_ARTIFACT_DERIVATION_ENABLED=0` 后停止新
derivation worker；保留 DB、原件、全部 immutable versions、lineage、processing runs、
derivatives、object versions、backup、reader 配置、所有 volume 和 v1.5 recovery asset。
Flag 关闭后回到原件附件下载；派生物可在获批 lifecycle 中重建，但本 phase 回滚不删除它们。
禁止 binary/schema downgrade、`down -v`、删表/血缘/对象/卷/备份、撤既有 reader 凭据、
改 verifier 或 replay recovery bundle 覆盖 live state。

立即停止条件：处理器需要执行用户代码或宏；Web 进程需要解析原件；历史 object/version 被
覆盖；parent/derivative lineage gap 非 `0`；高风险文件可预览；preview checksum 不一致；
幂等重放产生多个业务结果；证据泄露 capability/private bytes；或回滚需要删除既有状态。

2026-07-26 收口时已重新 `fetch origin main`：远端
`c00a90f5b9fab87c880a7046ad3255b27ab24a45` 相对共同基线
`12d6fa9f46786387ee21d9bd3c682175464f3554` 新增 `43` 个 KMIDS commits；`KMFA/` 与
`.github/workflows/` scoped diff 为 `0`。本地 P6.1/P6.2/P6.3 chain 没有被远端删除或
覆盖；S06 whole-stage review/push 前仍须重新 fetch、整合当时最新远端并重跑完整门禁。

本地 Task 进度为 `27/56`；S06 为 `3/4` phases，published Stage 仍为 `6/14`。下一次新
run 只可执行 `S06 / P6.4 / T-S06-04` 上传质量门；不得提前做 S06 whole-stage review、
上传本中间 phase 到 GitHub、进入 S07，或启用生产 P6.1/P6.2/P6.3。
