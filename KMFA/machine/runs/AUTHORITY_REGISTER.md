# KMFA v1.5.2 AUTHORITY REGISTER

> Task `T-S00-03` / Phase `P0.3 权威建立`
> Requirement `R-GOV-002` / Acceptance `AC-GOV-002` / Test `TEST-GOV-002`
> Captured: `2026-07-22T12:38:59Z`
> Closed: `2026-07-22T12:42:42Z`
> Stage-review correction: `2026-07-22T13:16:08Z`
> P2.3 projection update: `2026-07-22T15:53:03Z`
> Status: **DONE — AC-GOV-002 PASS**

本文是小于 64 KiB 的 public-safe compact receipt。它登记 namespace、唯一 writer、责任与冲突算法，但不复制产品/业务事实，不成为第八事实源。事实仍由下表指向的现有 machine 文件、Git object 或平台 manifest 写入；本 register 只回答“谁能写、从哪里读、冲突时怎么办”。

## 1. Authority order

固定优先级来自已授权 v1.5.2 Run Contract：

1. 用户本次最终授权；
2. taskpack `machine/canonical_facts.yaml` 与已核验生产事实；
3. taskpack `machine/acceptance_contract.yaml`、`task_graph.yaml`、`release_policy.yaml`；
4. 相应 machine facts 派生的人类七文件；
5. v1.5 recovery 与历史参考；
6. 外部项目/资料。

低优先级来源不得静默弱化 public、免登录、长期持久化、任意文件安全存储或默认私密合同。当前 taskpack ZIP SHA-256 为 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`；外层 43 个文件，manifest 排除自身后 `42/42` 通过。

## 2. Version namespaces

下表保存 P0.3 关闭时的 verified snapshot，不把 receipt 中的常量冒充永久 current。实时值必须从
对应 sole writer 重新解析；特别是治理-only Stage upload 后，published main 可以合法领先于仍在运行的
deployment source，二者必须分开显示。

| Namespace / field | Captured VERIFIED value | Sole authority / writer | Forbidden substitution |
| --- | --- | --- | --- |
| `taskpack.version` | `1.5.2` | sealed taskpack `manifest/PACKAGE_METADATA.json` / `WR-TASKPACK-PUBLISHER` | 不得当作产品版本、Git SHA 或 deployment ID |
| `taskpack.sha256` | `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb` | 下载输入字节 / `WR-TASKPACK-PUBLISHER` | 不得用内部 PDF、manifest 或目录摘要代替 |
| `product.version` | `0.1.4-one-time-github-main-upload` | `KMFA/VERSION` / `WR-RELEASE-VERSION` | `machine/facts/status.json.version` 与 changelog 条目只是域内快照，不得反向覆盖 |
| `source.published_main_sha` | `68306e850fa66ffe6b53622915ca81ff8ba98bf8` | GitHub `LinzeColin/KMOS` `refs/heads/main` / `WR-STAGE-PUBLISH` | detached phase receipt commit、tree SHA、旧 clone SHA 与部署源码均不得冒充 live published ref |
| `deployment.source_git_sha` | `68306e850fa66ffe6b53622915ca81ff8ba98bf8` | Coolify deployment manifest / `WR-DEPLOY-PLATFORM` | published main、receipt commit 或 workflow run SHA 均不得冒充当前 deployment 的构建源码 |
| `artifact.image_digest` | `sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841` | Coolify deployment manifest/build log / `WR-DEPLOY-PLATFORM` | 不得用 source/config/SBOM ZIP digest 代替 |
| `deployment.id` | `boh5fsnxe82umwcpqzooam1p` | Coolify deployment record / `WR-DEPLOY-PLATFORM` | resource ID、GitHub run ID 与旧 deployment UUID 均不是当前 deployment ID |
| `deployment.completed_at` | `2026-07-22T11:39:29.000000Z` | Coolify deployment record / `WR-DEPLOY-PLATFORM` | Git commit time、workflow start/end time不得代替 |
| `business.snapshot_version` | `0.1.4` | `machine/facts/status.json` / `WR-FACT-STATUS` | 仅标识旧业务状态快照，不得当作 `product.version` 或 taskpack version |
| `evidence.receipt_commit` | 运行时用 `git rev-parse HEAD` 取得 | Git object / `WR-PHASE-EXECUTOR` | receipt commit 只签证据，不自动成为 published main 或部署身份 |

字段名必须带 namespace。若两个值处于不同 namespace，它们不是冲突，必须并存且禁止互相推断。

## 3. Current deployment → source → taskpack binding

固定序列使用 UTF-8、每行 LF、末尾一个 LF：

```text
taskpack.version=1.5.2
taskpack.sha256=31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb
product.version=0.1.4-one-time-github-main-upload
source.repository=LinzeColin/KMOS
source.published_main_sha=68306e850fa66ffe6b53622915ca81ff8ba98bf8
deployment.source_git_sha=68306e850fa66ffe6b53622915ca81ff8ba98bf8
artifact.image_digest=sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841
deployment.resource_id=gz5qao2k0zrx3polpbwgcg51
deployment.id=boh5fsnxe82umwcpqzooam1p
deployment.completed_at=2026-07-22T11:39:29.000000Z
```

Binding SHA-256：`fca5e86879e083f69a772df00c02662f117cae5d0c4cf4866509b0b25fb2aad2`。

Reverse lookup is deterministic:

1. 用 `deployment.id` 在受约束的只读 query workflow 查到 `deployment.source_git_sha`、`artifact.image_digest` 与 `completed_at`；query run `29916590384` 已 PASS。
2. 用 `deployment.source_git_sha` 从 `LinzeColin/KMOS` Git object 读取 `KMFA/VERSION`，得到独立 `product.version`；不得从 taskpack 推断。
3. 独立读取 GitHub `refs/heads/main` 得到 live `source.published_main_sha`；它可以因治理-only upload 与 `deployment.source_git_sha` 不同，差异本身不是生产歧义。
4. 在 published main 上按 `deployment.id` 定位本 register，再用 binding 的 `taskpack.sha256` 定位唯一批准 ZIP，校验其 `PACKAGE_METADATA.json`、42-entry manifest 与 validator；不得声称旧 deployment source commit 内含后来才发布的 taskpack receipt。
5. P0.1 receipt `SOURCE_IDENTITY.md` 保存平台证据边界；本 register 只绑定其已核验字段，不取代 GitHub ref、平台 manifest 或 taskpack bytes。

## 4. One-writer-per-fact-domain map

下表是权威域全集。每行只有一个 `writer_id`；同一 writer 可以负责多个互不冲突的域，但同一域不得增加第二 writer。

| fact_domain | Authoritative source | writer_id | Accountable owner | Mutation rule |
| --- | --- | --- | --- | --- |
| `authorization.delivery_goal` | 当前 Owner 授权与 taskpack `PURSUING_GOAL.txt` | `WR-OWNER` | Owner | 只有 Owner 明确的新授权可改；不得由历史包推断 |
| `delivery.product_contract` | taskpack `machine/canonical_facts.yaml` | `WR-TASKPACK-PUBLISHER` | Product Owner | sealed input；变更需 Owner 授权的新包/勘误 |
| `delivery.acceptance_contract` | taskpack `machine/acceptance_contract.yaml` | `WR-TASKPACK-PUBLISHER` | QA+Product | 由 taskpack validator 维护引用闭合 |
| `delivery.task_graph` | taskpack `machine/task_graph.yaml` | `WR-TASKPACK-PUBLISHER` | Delivery Lead | DAG 为执行顺序；Roadmap 仅派生视图 |
| `delivery.traceability` | taskpack `machine/traceability.csv` | `WR-TASKPACK-PUBLISHER` | QA Architect | 只允许从 Canonical/AC/Task DAG 精确投影；断链或漂移即失败 |
| `delivery.release_policy` | taskpack `machine/release_policy.yaml` | `WR-TASKPACK-PUBLISHER` | Release Owner | Promotion/rollback gate 不由阶段 receipt 改写 |
| `product.runtime_version` | `KMFA/VERSION` | `WR-RELEASE-VERSION` | Release Owner | 版本升级必须经发布评审并与制品重绑 |
| `source.published_main` | GitHub `LinzeColin/KMOS:refs/heads/main` | `WR-STAGE-PUBLISH` | Tech Lead | 仅 Stage 全部 phase、复审及修复完成后非破坏性上传；禁止 force-push |
| `source.local_phase_candidate` | 当前隔离 worktree Git `HEAD` | `WR-PHASE-EXECUTOR` | 当前 Task owner | 每 run 最多一 phase；本地 commit 不得标为 published/production |
| `release.current_deployment` | Coolify current deployment manifest + CI query | `WR-DEPLOY-PLATFORM` | Release Owner | 仅部署流水线写；receipt 只读引用 |
| `recovery.v1_5_assets` | immutable bundle `1ee7fb111` + public recovery tip `268acce792` | `WR-RECOVERY-CUSTODIAN` | Recovery Lead | 只读保全；不得 replay/merge/force-push 或夹带 S24 |
| `business.current_status` | `machine/facts/status.json` | `WR-FACT-STATUS` | Product+Tech Lead | 只写旧业务状态；不写 v1.5.2 delivery phase |
| `business.blockers` | `machine/facts/blockers.json` | `WR-FACT-BLOCKERS` | Delivery Lead | Owner-only blocker 首次登记后不得重复审计 |
| `business.legacy_roadmap` | `machine/facts/roadmap.json` | `WR-FACT-ROADMAP` | Delivery Lead | 旧 S01-S18 业务路线；不得驱动 v1.5.2 DAG |
| `business.current_plan` | `machine/facts/plan.json` | `WR-FACT-PLAN` | Delivery Lead | 旧业务任务快照；当前 delivery task 只从 taskpack/HANDOFF 读取 |
| `business.acceptance` | `machine/facts/acceptance.json` | `WR-FACT-ACCEPTANCE` | QA+Product | 业务 A1-A6，不等于 v1.5.2 AC IDs |
| `business.product_scope_snapshot` | `machine/facts/product.json` | `WR-FACT-PRODUCT` | Product Owner | 旧业务草案保留；不得弱化新 product contract |
| `business.features` | `machine/facts/features.json` | `WR-FACT-FEATURES` | Architect | 由已核验实现更新，七文件只渲染 |
| `business.data_contract` | `machine/facts/data_contract.yaml` | `WR-FACT-DATA-CONTRACT` | Data+Backend | Schema/主键域唯一；跨项目仍经 KMDatabase schema |
| `business.data_pipeline` | `machine/facts/data_pipeline.json` | `WR-FACT-DATA-PIPELINE` | Data | 只登记 public-safe pipeline 状态 |
| `business.parameters` | `machine/facts/config.yaml` | `WR-FACT-CONFIG` | Tech Lead | 参数值/意图唯一；不得承载产品版本 |
| `business.glossary` | `machine/facts/glossary.json` | `WR-FACT-GLOSSARY` | Finance+Product | 数字口径唯一；金额继续 fail closed |
| `business.flows` | `machine/facts/flows.json` | `WR-FACT-FLOWS` | Product+Backend | 业务流程事实唯一 |
| `business.operations` | `machine/facts/ops.json` | `WR-FACT-OPS` | SRE | Runbook/故障处理唯一 |
| `business.changelog` | `machine/facts/changelog.json` | `WR-FACT-CHANGELOG` | Release Owner | 域内历史条目，不写当前产品版本权威 |
| `business.data_lineage` | `machine/lineage.yaml` | `WR-LINEAGE-GENERATOR` | Data | 仅由 `tools/lineage_graph.py` 机械生成，禁止手写 |
| `human.business_views` | `machine/canonical_facts.yaml` + `machine/acceptance_contract.yaml` + `machine/task_graph.yaml` + `machine/traceability.csv` + `machine/facts/*` → `文档/00_我在哪.md` … `06_运维手册.md` | `WR-RENDER-HUMAN` | Governance | 只能由 `machine/tools/render_human.py` 从已声明 machine sources 全量覆盖生成；禁止手写或复制 taskpack `human/*` |
| `continuity.active_delivery` | `HANDOFF.md` 顶部 v1.5.2 区块 | `WR-PHASE-EXECUTOR` | Delivery Lead | 只写最近已通过 phase 与下一最小 task；不得覆盖事实源 |
| `policy.agent_contract` | `AGENTS.md` | `WR-REPO-GOVERNANCE` | Tech Lead | 只写边界/路由并指向本 register/HANDOFF，不另存进度 |
| `evidence.phase_receipts` | `machine/runs/` compact receipts | `WR-PHASE-EXECUTOR` | 当前 Task owner | 每 phase 一份紧凑证据；完整日志外置；receipt 不能写回事实 |

30-row canonical writer map SHA-256：`c8e0cebb60d16039860f84b2b062df4aea73b48dda0c06828ee214a338dd7bcd`。规范化方式为跳过表头/分隔行，按表中顺序取 30 行五列、去掉 Markdown code ticks、用 `|` 连接列、LF 连接行并保留末尾 LF。

`metadata/**`、`docs/governance/**`、根目录历史文档、taskpack `human/*`/PDF/Roadmap、recovery/history 都只能提供 evidence/reference 或派生视图；它们不在本表中取得任何现行事实域的 writer 权限。

## 5. Executable conflict resolution

固定算法 `AUTH-RESOLVE-1`：

1. **Normalize**：给每个 claim 标注 `fact_domain`、namespace、source identity、captured_at 与 writer_id；缺任一项则不是可写 claim。
2. **Separate**：namespace 不同则并存，禁止互代。例如 `taskpack.version=1.5.2` 与 `product.version=0.1.4-...` 不冲突。
3. **Authorize**：同一 `fact_domain` 只接受本表 writer_id 写入；其他来源降为 evidence/reference。
4. **Order**：合法 writer 仍冲突时按第 1 节 authority order 选择；低优先级 claim 标记 `superseded`，不得折中。
5. **Production uniqueness**：生产 claim 必须绑定固定 resource、deployment UUID、`deployment.source_git_sha`、image digest、完成时间和 `finished` 状态。`source.published_main_sha` 只表示发布 ref，不自动声称已部署。若两个 deployment claim 都称 current，先只读查询平台 current deployment；仍无法唯一判定则触发本 Task Stop Condition，禁止发布。
6. **Candidate isolation**：本地 phase commit 只属 `source.local_phase_candidate`；完成全部 Stage Review/修复并上传前，不得改变 `source.published_main` 或 `release.current_deployment`。
7. **Private fail-closed**：任何解析需要 raw/private/secret 明文进入公开仓时，结果只能是 `Conflict/STOP`；不得为凑齐事实复制数据。
8. **Record**：输出 `Adopt / Redo / Discard / Conflict`、owner、default action 与 evidence；receipt 不反向修改原始事实。

已执行的代表性裁决：

| Claims | Domains | Result |
| --- | --- | --- |
| taskpack `1.5.2` vs `KMFA/VERSION=0.1.4-one-time-github-main-upload` | different | **Adopt both** under separate namespaces |
| taskpack S00/P0.3 vs `machine/facts/plan.json` S05-P3 | `delivery.task_graph` vs `business.current_plan` | **Adopt both**, current delivery only follows taskpack/HANDOFF |
| prior deployment `qcq1q8...` vs current `boh5fsnx...` | same production domain, different capture | **Adopt current platform query**, retain prior as history |
| declared machine source vs rendered `文档/*` | same delivery/business domain | **Adopt machine source**, regenerate view; never hand-edit view |
| recovery code vs current source | recovery vs published/candidate source | use P0.2 disposition; never wholesale replay |

Current production has one platform-verified current claim; the Stop Condition is **not triggered**.

## 6. Seven-file and legacy boundary

- `文档/` contains exactly seven files. They remain derived business-state views and are not modified in P0.3.
- Existing `machine/facts/` contains 14 populated files. They remain the writer set for the older business-state namespace until S02 performs its explicit canonical-facts task; P0.3 does not rewrite them.
- `machine/facts/status.json` and `plan.json` describe fail-closed S05/A0 business work. They do not select the active v1.5.2 delivery phase.
- `AGENTS.md` provides durable policy; `HANDOFF.md` provides current delivery continuity; neither may replace taskpack machine facts, `KMFA/VERSION`, Git refs or deployment manifest.
- `machine/README.md` is navigation only. Stale claims that facts/runs are empty are corrected in this phase without changing business data.

## 7. Validation record

Baseline before edits: `AUTHORITY_BASELINE_RECORDED status=FAIL checks=5 failed=3 facts_files=14 handoff_p03=true`。失败项为 register 缺失、AGENTS 仍将旧业务任务写成当前开发任务、machine README 错称 facts 为空。

| Gate | Result |
| --- | --- |
| Taskpack identity | Outer SHA PASS；ZIP 43 files；manifest `42/42`；validator `49 requirements / 49 AC / 14 stages / 56 tasks`, 0 errors/warnings |
| Namespace / writer structure | `AUTHORITY_FOCUSED_PASS namespaces=10 fact_domains=30 facts_covered=14 seven_views=7 binding=fca5e868`；P2.3 增加 sealed Traceability 域，published main 与 deployed source 各有唯一 writer |
| Conflict algorithm | `AUTH_RESOLVE_1_PASS cases=6 production_stop_negative=PASS`；different namespaces coexist, unauthorized writer rejected, ambiguous production stops |
| Reverse trace | `REVERSE_TRACE_PASS deployment->deployed-source + published-main->taskpack binding=fca5e868`；query run `29916590384`、Git ref/object 与 taskpack bytes independently matched |
| Production uniqueness | Latest deploy run `29916233128` and query run `29916590384` both bind `68306e8... / adfc849b... / boh5fsnx...`; current claims `1`, ambiguity `0` |
| Existing governance | 14 business facts preserved byte-for-byte；seven rendered files unchanged；dual-plane PASS；no eighth fact writer created |
| Public safety | Intended pre-HANDOFF delta 3 public-safe files；receipts <64 KiB；new absolute local paths `0`；secret/token/key hits `0`; forbidden payloads `0` |
| Mutation boundary | No push/deploy/database or object write/recovery replay/P0.4 work；`git diff --check` PASS |

P0.3 passing authorizes only the next new run to start P0.4. It does not complete S00, authorize Stage Review, or permit phase-level GitHub upload.
