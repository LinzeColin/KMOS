# KMFA v1.5.2 S03 STAGE REVIEW

> Stage `S03 公开根主页与 Walking Skeleton`
> Reviewed: `2026-07-22T19:58:46Z`
> Phase candidate parent: `1a4941608a813254972ae333cdc66b5c32f4b142`
> Status: **REVIEW PASS — S03 guarded release candidate；production edge Oracle WAIT；G2 NOT PASS**

本文是不超过 64 KiB 的 public-safe compact receipt。它把 P3.1–P3.4、S03 objective/deliverable/gate、
相关 Acceptance、恢复边界、部署阻断与回滚作为一个整体重放，并记录复审发现及修复。它不保存用户文件、
恢复码、Access URL、凭据、平台原始响应或私有业务内容，也不把本地单节点骨架冒充长期持久化、完整匿名产品
旅程、生产公开状态或 `G2 Walking Skeleton`。

## 1. Frozen review subject

| Subject | Verified value / boundary |
|---|---|
| Authorized taskpack | v1.5.2 ZIP SHA-256 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`；43 files；self-excluding manifest `42/42` |
| Canonical S03 contract | Objective：匿名用户先在根域看到并走通真实软件；Deliverable：根入口、旧路径兼容、完整 App Shell、早期纵向骨架；Gate：生产等价匿名根入口 Oracle + 核心骨架 Flag 回滚 |
| Published baseline before review | `LinzeColin/KMOS:main@a991e1b8eade5e852cc750095ffe466bce1d1bb9`；fresh fetch 后未漂移 |
| Local phase chain | `df885354` P3.1 → `516bd99c` P3.2 → `2e6a0e9e` P3.3 → `1a494160` P3.4；连续、无 merge、相对 baseline `0 behind / 4 ahead` |
| Review boundary | 只复审、修复并授权一次 S03 guarded upload；未启动 P4.1；未写 Cloudflare、Coolify、生产数据或恢复资产 |
| Review-time production | 匿名根路径和 `/ui/` 仍命中既有 host Access `302`；因此 production Oracle 不是 PASS |

Receipt 所在最终 commit 不能自引用自己的 SHA，镜像又包含仓库内 receipt，因此最终 commit/image/deployment
身份必须在 commit 后由 Git object、CI artifact 和 Coolify 只读查询分别记录，禁止用预构建镜像 ID冒充线上摘要。

## 2. Task / Acceptance replay

| Task / Phase | Replayed evidence | Honest result |
|---|---|---|
| `T-S03-01 / P3.1` | 最终镜像 GET/HEAD `/ = 200`；`/ui`、`/ui/` 单跳 `308 → /`；canonical 仅根；生产 guard 缺配置时 `/api*`、`/ops*` 为 `503`，有效/伪造/错 Audience JWT 单测覆盖 | **PRODUCTION-EQUIVALENT PASS；LIVE EDGE WAIT** |
| `T-S03-02 / P3.2` | 桌面、390 px、无 JS、浅健康降级 `4/4`；项目/上传/搜索/进度/报告/帮助 `6/6` 可操作；无账号/邮箱/OAuth 前置；公共根不请求私有 API/bundle | **AC-PUB-004 CANDIDATE PASS；AC-PUB-002 PARTIAL/OPEN** |
| `T-S03-03 / P3.3` | Chromium/Firefox/WebKit 共 22 次 axe，critical/serious/incomplete 均 `0`；键盘流与 320/390 px 通过；未发布 canary sitemap/robots/HTTP/header/cache 五重 fail closed、index hit `0` | **AC-PUB-005 CANDIDATE PASS；EXTERNAL INDEX WAIT** |
| `T-S03-04 / P3.4` | 合成 workspace → 保存项目/进度 → 任意二进制上传 → 容器重启 → 新浏览器恢复 → 下载 hash 等值 → Flag `1→0→1` 且状态/对象不变 | **AC-QA-001 EARLY-SKELETON CANDIDATE PASS** |

`AC-PUB-002` 要求匿名浏览、创建工作区、建项目、上传、处理、保存、恢复、搜索、下载和导出完整旅程。
S03 只交付导航和一个可恢复文件切片，没有处理、工作区搜索、完整下载/导出、多文件或明确删除，所以该 AC
继续 open。`G2` 又要求 S03–S07 的根主页、匿名恢复、耐久存储、任意上传、下载/导出 P0 AC 全部通过；
当前既未完成 S04–S07，也没有 DB/object backup/restore，故 **G2 NOT PASS**，不得称“可用产品”或 GA。

## 3. Whole-stage Gate

| Gate dimension | Whole-stage assertion | Result |
|---|---|---|
| Production-equivalent root | 同一最终候选镜像在全新浏览器直接落 `/`，无登录控件/权限响应；旧路径、错误路径与私有 canary 行为确定 | **PASS** |
| App Shell / degraded modes | 六入口桌面与移动可操作；无 JS、依赖降级、React 错误与静态 Flag 回退都不空白、不写数据 | **PASS** |
| Privacy / index boundary | 默认 hold；只允许显式 true；错误根页和资产错误也统一 noindex/no-store；公开 artifacts 只含合成数据与聚合结果 | **PASS** |
| Early recoverable slice | capability 只存 SHA-256；对象不在公开静态树；attachment-only、nosniff、服务端/浏览器双 hash；重启与 Flag 回滚保持状态 | **PASS（单节点早期 adapter）** |
| Flag rollback | Shell、Index、Walking Skeleton 三 Flag 独立；全部回退时根页仍 `200`、稳定静态入口 `6/6`、robots 全拒绝、骨架读写关闭、私有面守卫不放松 | **PASS** |
| Deployment promotion safety | 同一 deploy workflow/SHA 先跑后端、治理、Docker、四类浏览器/E2E；失败不触发 Coolify；并发 main caller 取消旧 run，发布后仍强制核对实际 source commit | **PASS（source query mandatory）** |
| Live production edge | 当前 host Application 仍为 Access login boundary，匿名根为 `302`；仓库没有 Cloudflare 写凭据，面板变更必须按 runbook 的 guarded order 由授权控制面执行 | **WAIT / NOT CLAIMED** |

结论是 **S03 implementation + whole-stage review candidate PASS**，允许一次 guarded GitHub upload 和自动部署
验证；但只有绑定部署通过、路径 Access/源站 JWT canary 全绿且 host 公开后，live production Oracle 才能从
WAIT 晋级。这个边界不是用“本地测试通过”掩盖生产失败。

## 4. Whole-stage findings and fixes

| Finding | Severity | Evidence / impact | Minimal fix | Closure |
|---|---|---|---|---|
| `F-S03-001` promoted root error became indexable | High | indexing Flag 开启且前端缺失时 `/` 返回 `503`，却无 noindex/no-store；资产错误也可继承公开缓存语义 | 只有 2xx 根页/控制文件可进入成功分支；所有错误含资产错误统一 `noindex,nofollow,noarchive` + `private,no-store`；补负测 | **RESOLVED** |
| `F-S03-002` deploy raced independent E2E | High | `deploy.yml` 与 `app-e2e.yml` 原为两个独立 main push workflow，Coolify 可在应用/治理 E2E 完成前晋级同一 SHA | App E2E 改为 reusable workflow；deploy 的 golden path `needs` 同 SHA gate；gate 增加 full backend、validator、mutation、dual-plane | **RESOLVED** |
| `F-S03-003` UI promised unavailable deletion | Medium | 信任条原文“删除由用户明确触发”会让用户误以为显式删除已实现，实际由后续 Stage 交付 | 改为“不自动到期；显式删除待后续阶段接入”，保留诚实的当前能力边界 | **RESOLVED** |
| `F-S03-004` stale main caller could promote late | High | 多个 main push 的旧 caller 可能在新 SHA 后继续晋级 | deploy 增加单组 concurrency + cancel-in-progress；Coolify 已接收任务仍以 post-deploy `source_commit` 查询为最终判据 | **RESOLVED** |
| `F-S03-005` workflow lint defect | Low | readiness loop 声明但不使用变量，actionlint 报警，削弱工作流静态门禁信噪比 | 换为不绑定变量的有限重试；两份改动 workflow actionlint clean | **RESOLVED** |
| `F-S03-006` CI runtime drift | Medium | workflow 依赖 runner 默认 Python/Node，而生产构建固定 Python 3.12 / Node 20；未来 runner 漂移可制造不一致结果 | `setup-python@v5` 固定 3.12、`setup-node@v4` 固定 20，并缓存各自 lock/input；合同测试锁定版本 | **RESOLVED** |
| `F-S03-007` machine navigation stopped at P3.1 | Low | `machine/README.md` 已存在 P3.2–P3.4 receipts 却只导航到 P3.1，后续接管易遗漏三项证据 | 精确更新 runs 导航到 P3.1–P3.4 与本 whole-stage receipt | **RESOLVED** |
| `F-S03-008` Python caches polluted review/image state | Medium | 历史仓跟踪 4 个 `.pyc`，本次新测试又生成 2 个 bytecode，且 Docker context 会带入 pytest/ruff cache；复验会改脏 worktree，并可能夹带本机解释器/路径元数据 | 删除 4 个可再生 tracked bytecode；`.gitignore` 拒绝 bytecode/test/lint cache，`.dockerignore` 同步排除；源码与数据不删 | **RESOLVED** |

Final finding count：`total=8 / resolved=8 / accepted-risk=0 / open=0`。存储、备份、反滥用、扫描、
恢复轮换、多文件、删除、生产 edge 与外部 index 是已排期的后续合同/Oracle，不被伪装成 S03 review finding
已解决。

## 5. Identity, recovery and production boundary

| Namespace | Review-time VERIFIED snapshot | Meaning |
|---|---|---|
| `taskpack.version / sha256` | `1.5.2 / 310885168...cffb` | 产品设计执行 seal；不等于 runtime version |
| `product.version` | `0.1.4-one-time-github-main-upload` | `KMFA/VERSION` 当前值 |
| `source.published_main_sha` | pre-upload `a991e1b8eade5e852cc750095ffe466bce1d1bb9` | GitHub published ref，不是本地候选/部署源码 |
| `deployment.source_git_sha` | `68306e850fa66ffe6b53622915ca81ff8ba98bf8` | review 前最近成功平台查询的生产源码 |
| `artifact.image_digest` | `sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841` | review 前生产镜像，不是 S03 候选 |
| `deployment.id / completed_at` | `boh5fsnxe82umwcpqzooam1p / 2026-07-22T11:39:29.000000Z` | query run `29931489638` 的 finished 部署 |

- v1.5 recovery ZIP / bundle SHA-256 保持 `8066b65d...ef2c1 / 2d0b516f...077ed`；bundle head
  `1ee7fb111075225dc39039263d2681a0c0acd155`、prerequisite `97edb1b8750d49409a4f9372a784d4772fea258e`。
- 当前 split KMOS object store 没有 prerequisite，故不能把这里的直接 verify 失败误称资产损坏。复审在隔离 bare
  临时仓只 fetch 公共 `recovery/kmfa-v15-fuzzy@268acce7924d13dd6481b50af7f57d2d2ede81ed`；prerequisite
  object 存在、`git bundle verify` PASS、bundle head 是该公开 tip ancestor。没有把 ref/object 导入 KMOS。
- 受保护 S24 五路径在 current candidate 命中 `0`；无 recovery replay、merge、cherry-pick、force-push、
  schema/data rollback、私有 Release copy 或恢复资产写入。
- Owner 早先提供并已独立复核的 `fb31e8e... / sha256:0b09ca... / qcq1q8m...` 只保留为历史
  rollback/provenance tuple，不冒充当前生产身份。

## 6. Validation record

| Gate | Result |
|---|---|
| Taskpack seal | outer ZIP SHA PASS；ZIP test PASS；manifest `42/42`；official validator `49 R / 49 AC / 14 Stages / 56 Tasks`, 0 errors/warnings |
| Sealed authorities | byte-equal/hash PASS：Canonical `5ae070cb...552`、AC `1f07bd14...bc1`、DAG `a9753e7c...306`、Release `f47de7a...3c7`、Trace `ca369627...727` |
| Backend | Python 3.12 full regression `119 passed`；focused public/deploy/index contract `17 passed`；仅 inherited TestClient deprecation warning |
| Browser / image | public shell desktop/mobile/no-JS/degraded `4/4`；a11y 22 runs violations/incomplete `0`；unpublished index hits `0`；legacy private flow `11/11` |
| TEST-QA-001 | download #1/#2 SHA-256 均 `501b484cc19f114fdfed29a9f3f31ec5b0cdc3d12a0a8f75a2d21595998af011`；Flag rollback recovery `404`、root `200`、secret state/log/URL hits `0` |
| Error/guard/rollback | promoted root `503` 与 missing asset `404` 均 noindex/no-store；guard-on missing config 的四个私有 canary `503`；三 Flag 全回退 root/static/index/state 边界 PASS |
| Repository governance | validator PASS；required mutation `1 positive + 4 negative`，source unchanged `5/5`；auto-discovered five-project dual-plane PASS |
| Dependency / build | `npm audit --omit=dev` vulnerabilities `0`；resolved Python requirements known vulnerabilities `0`；两套 Compose parse；Vite/Docker build PASS |
| Workflow | reusable-call/needs/concurrency/runtime-pin contract PASS；actionlint PASS；deployment promotion remains bound to same SHA gate |
| Public safety | tracked Python bytecode `0`；final diff high-confidence credential/private key/new absolute path/forbidden payload/runtime DB/archive 命中 `0`；receipts `<64 KiB`；`git diff --check` PASS |

本地完整浏览器与恢复制品只放在一次性临时目录，使用合成项目/文件；不提交截图、状态库、对象字节或
`EVIDENCE/` 树。review-time runtime-frozen image 曾以 `sha256:b56eb7e7...c6b8` 完成上述浏览器/恢复回归；
最终 receipt commit 的精确 image ID 和实际部署 digest 必须在 commit/build/deploy 后另行核对，不能自引用。

## 7. Publication, rollout, rollback and next boundary

1. 上传前 fresh fetch；只有 remote main 仍为 `a991e1b8...`、候选为其直接后代、worktree clean、open
   finding `0`、安全与完整门禁全绿，才允许一次 `git push origin HEAD:main`；禁止 force。
2. 同 SHA deploy workflow 必须先通过 reusable app-e2e gate 再触发 Coolify。上传后核对 remote main、
   workflow conclusion、Coolify deployment UUID、actual `source_commit`、image digest 和 completed_at；任一不一致 STOP。
3. host 登录墙保持时，先建 `/api`、`/api/*`、`/ops`、`/ops/*` 更具体 Access apps；再配置 Audience 和
   源站 guard；确认 named volume、私有 canary、合成恢复/hash/Flag rollback 后，最后才把 host 改为 public
   Bypass。当前凭据边界不允许在 receipt 中代替授权控制面操作或泄露配置值。
4. 快速边缘回滚恢复 host Owner Allow；Index/Walking Skeleton Flag 均置 `0`，必要时 Shell Flag 置 `0`；
   路径 app 与源站 JWT guard 保持，`kmfa-app-state` 不删除，禁止 `docker compose down -v`。
5. 代码回滚只用普通 revert，按相反顺序撤销 review 与四个 phase commits；不得改写 ref、force-push、
   回退 schema/volume 或触碰 recovery assets。
6. 只有 upload/deploy/production Oracle 都闭合，下一新 run 才能进入 `S04 / P4.1 / T-S04-01`。本 receipt
   不启动 P4.1，也不允许把 `AC-PUB-002`、长期持久化、G2 或 GA 提前标绿。
