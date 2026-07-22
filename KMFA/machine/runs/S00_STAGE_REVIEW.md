# KMFA v1.5.2 S00 STAGE REVIEW

> Stage `S00 权威、恢复与启动授权` / Promotion Gate `G0 Authority`
> Reviewed: `2026-07-22T13:20:47Z`
> Independent-review correction: `2026-07-22T13:37:56Z`
> Phase candidate parent: `3f274f398ade0352837c313dff9b8cbf706eb18a`
> Status: **PASS — G0 release candidate；仅授权一次非破坏性 S00 Stage upload**

本文是不超过 64 KiB 的 public-safe compact receipt。它复审 S00 四个 phase 的共同结果、记录 findings
及修复，并定义可机械核验的上传/回滚边界；不复制完整日志、不建立逐 Stage evidence tree、不写入
私密平台响应，也不把 builder 自审冒充独立 verifier 结论。

## 1. Frozen review subject

| Subject | Verified value / boundary |
| --- | --- |
| Authorized taskpack | v1.5.2 ZIP SHA-256 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`; 43 files，self-excluding manifest `42/42` |
| Canonical graph | `14 stages / 56 tasks`; S00 为 4 phases / 4 tasks，依赖为 `01 → 02`, `01 → 03`, `02+03 → 04` |
| Published baseline before review | `LinzeColin/KMOS:main@68306e850fa66ffe6b53622915ca81ff8ba98bf8` |
| Local phase chain | `6af7d629` P0.1 → `1633a65a` P0.2 → `dd23478b` P0.3 → `3f274f39` P0.4；连续、无 merge、相对 baseline `0 behind / 4 ahead` |
| Pre-review delta | 8 public-safe paths：`AGENTS/HANDOFF/machine README` 加 5 个 compact recovery/authority/preauthorization files；无 app、facts、人类七文件、数据库或对象写入 |
| Review boundary | 只复审/修复 S00 并上传整个 Stage；`S01/P1.1` 未启动 |

Receipt 所在最终 commit 不能把自己的 SHA 写进自身内容。`evidence.receipt_commit` 用
`git rev-parse HEAD` 解析；`source.published_main_sha` 用远端 ref 解析。只有两者在上传后相等，才算
本 Stage 已发布，禁止用 parent SHA 或 tree SHA 伪装 closure。

## 2. Task / Requirement / Acceptance / Test replay

| Task / Phase | Requirement → Acceptance → Test | Replayed evidence | Result |
| --- | --- | --- | --- |
| `T-S00-01 / P0.1` | `R-GOV-002 → AC-GOV-002 → TEST-GOV-002` | GitHub main/deploy run `29916233128`、受约束 query run `29916590384`、product version 与 taskpack bytes 独立回溯；五字段 `5/5`、deployment claim `1`、歧义 `0` | **PASS** |
| `T-S00-02 / P0.2` | `R-GOV-001 → AC-GOV-001 → TEST-GOV-001` | bundle verify、public recovery ref、1060-path partition、16-row disposition CSV、S24 exclusion 与禁止 replay/force-push 重跑 | **PASS** |
| `T-S00-03 / P0.3` | `R-GOV-002 → AC-GOV-002 → TEST-GOV-002` | 10 个 version/identity namespace、29 个唯一 fact-domain writer、部署源码与 published main 分离、冲突算法与反向查找重跑 | **PASS after F-S00-002 fix** |
| `T-S00-04 / P0.4` | `R-GOV-004 → AC-GOV-004 → TEST-GOV-004` | 20 项 inventory、14 defaults、8 Stage entries、普通依赖 `6/6 CONTINUE`、Stop `4/4 FAIL_CLOSED` / fields `12/12`、S00 unknown `5/5` | **PASS after F-S00-003 fix** |

S00 Stage Gate 三个断言均成立：进入实现的差异未分类数 `0`；taskpack/product/published-source/
deployed-source/artifact/deployment identity 不混用；普通依赖导致暂停 `0`。因此 `G0 Authority` 的
唯一前置 `S00 PASS` 已满足。

## 3. Whole-stage findings and fixes

| Finding | Severity | Evidence / impact | Minimal fix | Closure |
| --- | --- | --- | --- | --- |
| `F-S00-001` governance-only main push caused production rebuild | High | 原 `deploy.yml` 对每个 main push 触发 Coolify；初修使用 `machine/runs/**` 又被 fresh independent audit 证明会吞掉该目录的未知/runtime 文件 | 最终逐条列出本 Stage 10 个治理文件，不使用目录通配符；正例 10/10 skip，app、未知顶层与 `machine/runs/runtime_probe.py` 三类负例均 deploy-required | **RESOLVED after independent finding** |
| `F-S00-002` published main 与 deployed source 共用 `source.git_sha` | High | 治理-only upload 后两值合法分叉；共用字段会把未部署 commit 冒充生产源码 | 拆为 `source.published_main_sha` 与 `deployment.source_git_sha`，namespace `9 → 10`；重算 binding `fca5e868...` 并改写 reverse trace | **RESOLVED** |
| `F-S00-003` 五项 S00 startup unknown 没有逐项闭合表 | Medium | DB/object、负载及 RPO/RTO/预算的缺证容易被遗忘或被误报 Ready | 增加 `5/5` 矩阵；无 backup 的当前 RPO/RTO 明确为 unbounded/not recoverable，所有失败基线绑定 owner/default/硬 Gate | **RESOLVED** |
| `F-S00-004` machine navigation 漏列 P0.4 | Low | `machine/README.md` 的 runs 导航停在 P0.3，不能完整发现现有 receipt | 补齐 P0.4 与本 Stage Review 导航，不新增事实源 | **RESOLVED** |

Final finding count：`total=4 / resolved=4 / accepted-risk=0 / open=0`。修改均为治理、证据或触发边界；
没有借复审进入 S01、重构 app 或引入新服务。

## 4. Identity and production baseline

| Namespace | Review-time VERIFIED snapshot | Live writer |
| --- | --- | --- |
| `taskpack.version / sha256` | `1.5.2 / 310885168...cffb` | approved ZIP bytes / package metadata |
| `product.version` | `0.1.4-one-time-github-main-upload` | `KMFA/VERSION` at the relevant Git object |
| `source.published_main_sha` | pre-upload `68306e850fa66ffe6b53622915ca81ff8ba98bf8` | GitHub `refs/heads/main` |
| `deployment.source_git_sha` | `68306e850fa66ffe6b53622915ca81ff8ba98bf8` | Coolify deployment manifest |
| `artifact.image_digest` | `sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841` | Coolify deployment/build record |
| `deployment.id / completed_at` | `boh5fsnxe82umwcpqzooam1p / 2026-07-22T11:39:29.000000Z`, `finished` | Coolify deployment record |

Latest deploy run remained `29916233128` at the deployed source above; query run `29916590384` reproduced all
four non-secret deployment fields. Owner-supplied prior tuple beginning `fb31e8e... / 0b09ca... / qcq1q8...`
remains verified rollback/provenance history through query run `29916243207`, not current identity.

Public `/`, `/ui`, `/ui/` and `/healthz` still return Cloudflare Access `302`. This is a preserved S03 failure
baseline, not an S00 failure and not a claim that the public software goal is already delivered.

## 5. Recovery preservation replay

- Standalone and taskpack-embedded recovery ZIP remain byte-identical at
  `8066b65dc96f4368b54e2a053e6726a2bf194806d67b1bdbcacb669a457ef2c1`.
- Immutable bundle remains `2d0b516fe7d578061e97dfca874745bcf3a0bf504b0f80976ad3aa21e01077ed`;
  `git bundle verify` returns head `1ee7fb111...` with prerequisite `97edb1b875...`.
- Historical public recovery ref remains `268acce7924d13dd6481b50af7f57d2d2ede81ed`.
- 1060 paths remain exhaustive and mutually exclusive：`Adopt 239 / Redo 750 / Discard 71 / Conflict 0 /
  unclassified 0`；exact S24 set remains excluded and absent from the candidate.
- No recovery ref import、replay、merge、cherry-pick、force-push、private release copy or protected-asset mutation
  occurred during the review.

## 6. Validation record

| Gate | Result |
| --- | --- |
| Taskpack seal | Outer ZIP SHA PASS；manifest `42/42`；validator `49 requirements / 49 AC / 14 stages / 56 tasks`, `0 errors / 0 warnings` |
| S00 trace/DAG | 4 tasks / 4 phases；dependencies、R/AC/TEST/task reverse links closed；supporting Stage Gate assertions explicit |
| Source/deployment | remote main refresh stable at pre-upload `68306e8...`; latest deploy/query identity unique；published/deployed namespace split PASS |
| Recovery | ZIP/bundle/ref identities PASS；bundle topology PASS；1060 dispositions and S24 exclusion PASS |
| Authority/preauthorization | namespaces `10`、fact domains `29`、S00 unknown `5/5`、ordinary pauses `0`、Stop fields `100%` |
| Repository governance | Full repository dual-plane checked `5` projects，PASS；facts and seven rendered KMFA views unchanged |
| Upload trigger | Candidate 10-path set 与 10 个精确 ignore entries 一一相等；加入 app、未知顶层或 `machine/runs/` 未知路径均 flips to deploy-required |
| Public safety | compact receipts each <64 KiB；no newly added absolute local path、credential value、private/raw payload、SQLite/archive/workbook/PDF；`git diff --check` PASS |
| Mutation boundary | No app/facts/文档/database/object/Cloudflare/recovery data mutation；no deploy or push before review closure；S01 untouched |

通用 verifier 的自动 ingest 只识别包根 `MANIFEST.*`，而本授权 taskpack 的 sealed manifest 在
`manifest/PACKAGE_METADATA.json + FILE_CATALOG.csv + SHA256SUMS.txt`，因此未通过改名/复制来伪造兼容，
也未生成无收益的形式化 evidence ZIP。上传前应在 sealed candidate tree 上另做 fresh read-only audit；
该外部 verdict 不写回本文件，以免改变被审 tree。

## 7. Publication, rollback and stop boundary

1. 上传前重新 fetch；只有远端仍为 `68306e8...` 且候选为其直接后代时才允许
   `git push origin HEAD:main`，禁止 force-push。
2. 本 Stage 最终 10-path delta 必须与 `.github/workflows/deploy.yml` 中 10 个治理-only 精确 entries 一一相等；
   不允许目录通配符，任何额外或未知路径都改按 production release 处理。
   GitHub `dual-plane` 校验仍应运行；`deploy` 不应为最终 SHA 创建运行。
3. 上传后要求远端 main 等于 receipt commit、主镜像 fast-forward 且干净；生产 deployment 应继续绑定
   `68306e8... / adfc849b... / boh5fsnx...`。若出现新 deploy，立即停止晋级并重新查询身份/Oracle。
4. Git 发布回滚使用普通 revert；生产意外变更优先切回 previous verified deployment。不得回退 schema、
   删除用户数据、重写 ref 或触碰 recovery assets。
5. 远端非 fast-forward、secret/private 命中、恢复身份变化、production claim 歧义或 path filter 漏掉
   非治理文件均触发 STOP；不得为了完成 Stage 绕过。

Builder Stage Review result：`S00 PASS / G0 PASS / open findings 0`。完成本次非破坏性上传并验证上述
远端/部署后，下一新 run 只能从 `S01 / P1.1 / T-S01-01` 开始；本 receipt 不授权 P1.2，亦不宣称
根入口公开、loginless 全旅程、长期持久化、任意文件安全上传下载或最终 canary/rollback 已完成。
