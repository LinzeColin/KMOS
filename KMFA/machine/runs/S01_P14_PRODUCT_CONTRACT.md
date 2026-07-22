# KMFA v1.5.2 PRODUCT CONTRACT

> Task `T-S01-04` / Phase `P1.4 合同冻结`
> Dependencies `T-S01-02 @ 7b80ac5804e60e2120646aba8c3fd7f7269552a7` and
> `T-S01-03 @ 8d1bb6e769dcce4382a8d2c6496b380194bea78d`
> Acceptance `supporting task; must still satisfy S01 Stage Gate`
> Captured: `2026-07-22T14:32:50Z`
> Status: **DONE — product-contract freeze PASS；S01 Stage Review pending；runtime NOT READY**

本文是 sealed v1.5.2 产品合同的 public-safe compact receipt，必须小于 64 KiB。它把 P1.1–P1.3 的客户
问题、PRD/OKR 和经济判据冻结为实现期间不可口头漂移的范围，并提供 Baseline、观察窗口与变更 Gate；
不取代 taskpack 的 Canonical Facts/Acceptance/Task DAG，不创建第二事实 writer，也不把合同完成冒充
软件交付、Stage 通过、预算批准、部署或 GA。

## 1. Authority, freeze key and pursuing goal

| Subject | VERIFIED value / frozen boundary |
| --- | --- |
| Authorized package | `KMFA_Product_Design_Taskpack_v1.5.2.zip` SHA-256 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`；manifest `42/42`、validator `49 R / 49 AC / 14 stages / 56 tasks` PASS |
| Contract authority | user authorization → sealed `machine/canonical_facts.yaml` + verified production facts → sealed AC/task graph/release policy → human seven files；本 receipt 只作投影 |
| Pursuing-goal fingerprint | sealed `PURSUING_GOAL.txt` SHA-256 `98403ae4473eb68f21b74eccbdeb4089d3c2efaebd391efd607ea71978d09e64`；下方文本逐字一致 |
| Frozen local input | P1.1 `250ce3aa...` → P1.2 `7b80ac58...` → P1.3/current parent `8d1bb6e7...`；三者均仅本地、尚未 S01 Stage upload |
| Published source | `origin/main = 6a9f2163d00adc000e965bf6bffbc0ed59283d7a`；local parent ahead `3` / behind `0` |
| Current product/runtime version | `0.1.4-one-time-github-main-upload`；不得由 taskpack `v1.5.2` 推断或覆盖 |
| Current deployment | source `68306e850fa66ffe6b53622915ca81ff8ba98bf8`；image `sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841`；deployment `boh5fsnxe82umwcpqzooam1p`；completed `2026-07-22T11:39:29Z` |
| Current entry failure | production anonymous `GET / = 302` to Cloudflare Access；因此 root、完整免账号旅程和 GA 均未通过 |
| Recovery protection | v1.5 immutable recovery bundle `1ee7fb111` 继续只读取证；不 replay、不 force-push、不夹带未完成 S24，不复制私有 runtime/data |
| Freeze key | `taskpack-sha256:31088516... + pursuing-goal-sha256:98403ae4... + P1.3-parent:8d1bb6e7...`；任一变化都必须重新走第 7 节 Gate |

冻结的 pursuing goal：

> 在不丢失 v1.5 恢复资产、不泄露未主动公开的数据且不引入无收益复杂度的前提下，将 KMFA 交付为根域名即主页、无需账号即可完整使用、支持任意文件安全上传与下载、项目/进度/分数及文件长期持久化直至用户明确删除、可恢复、可验证、可灰度发布并可快速回滚的公开软件。

这个目标是实现和取舍的主线，不是当前完成声明。低层资料若与它冲突，停止使用低层资料；实现者不得
自行把“public”改成登录后可见、把“任意文件”改成格式白名单、把“长期”改成自动过期，或把默认私密
改成上传即公开。

## 2. Six precise product definitions — mandatory Pass Gate

| Decision / contract | Frozen engineering definition | Explicit boundary | Completion Oracle |
| --- | --- | --- | --- |
| `D-001/D-002 根路径` | 匿名全新会话访问 `https://kmfa.linzezhang.com/`，根请求直接 HTTP `200`，最终 URL 和 canonical 均为 `/`，首屏是可操作完整 App Shell；`/ui`、`/ui/` 只允许单跳 `308 → /` | 登录/Access redirect、营销页后再登录、隐藏路径、redirect loop、两套 canonical 均不算主页 | `AC-PUB-001/003/004`；真实浏览器 + HTTP chain；根入口发布 Gate `100%`，上线 7 天 `>=99.9%` |
| `D-003/D-009 无需账号` | 浏览、创建匿名工作区、项目、步骤/进度/分数、上传、处理、保存、恢复、搜索、财务工作、下载和导出全程不要求账号、邮箱、Google/GitHub/ChatGPT OAuth | 把登录改名为激活/验证、只读匿名但写入或下载需登录、匿名 `401/403` 均失败；未来可选账号不得阻断核心旅程 | `AC-PUB-002`；完整旅程 `100%`，登录步骤 `0`，匿名权限错误 `0` |
| `D-004 匿名恢复` | 首次使用自动建立匿名 workspace；至少 256-bit 高熵 recovery secret 仅向用户展示/导出，服务端只保存不可逆 verifier；secret 不进 URL/Referer/log/analytics/error/cache，并换取短时、可撤销、仅限单 workspace 的 session | workspace ID 不是 secret；浏览器不能是唯一副本；无邮箱人工找回承诺；丢失唯一恢复材料的后果必须清楚说明，不能偷偷引入账号 | `AC-WS-001/002/003`；有效材料跨设备恢复一致率 `100%`、无效授权成功 `0`、secret canary 命中 `0` |
| `D-005/D-006 长期耐久` | 项目、步骤、进度、分数、备注、财务记录、文件 metadata/版本/任务/审计进入耐久事务数据库；原件和派生字节进入私有版本化对象存储。默认无自动到期，跨重启/部署存在，可从备份恢复，保留至用户明确删除或获批法律/安全处置 | browser storage、临时容器卷或 SQLite 单点不能是 SSOT；“长期”不承诺物理永恒、无限容量或无限免费；控费不得静默过期/删数据 | `AC-DATA-001..004`, `AC-PROD-001`, `AC-DL-001`；丢失/误删/不可解释孤儿 `0`，空环境标准恢复和原件 hash 一致 `100%` |
| `D-007 任意文件` | 在前置可见且按平台/预算核验的大小与 workspace 配额内，任何扩展名/媒体类型都有确定安全存储路径；先 quarantine，保留不可变原件、hash、版本和血缘；未知、高风险或扫描不确定内容默认 attachment-only | “任意”不等于无限大小、都能预览、执行、解压运行或内联渲染；明确恶意/违法/突破安全上限可拒绝或隔离，但合法格式不得因扩展名随意丢弃 | `AC-UP-001/003/004`, `AC-DL-001`；合法夹具可安全存储，危险执行/逃逸 `0`，原件可验证下载 |
| `D-008 默认隐私` | 站点入口是 PUBLIC，但所有新 workspace、文件、项目、分数、财务输入和结果默认 UNLISTED；仅用户显式操作后生成固定版本、字段白名单、可撤销的 public snapshot/capability；只有批准快照可进入公共索引 | public site 不等于 public data；private source 不能直接服务公共查询；recovery secret、文件内容、真实财务原文、员工/群聊/考勤和 OPERATIONAL_PRIVATE 不得被遥测或自动发布 | `AC-PROD-003`, `AC-ARCH-001`, `AC-SEC-001`；默认公开/越权/private canary 命中 `0`，撤销在批准 SLA 内全链路失效 |

六项定义共同生效，不能以一项补偿另一项：例如恢复失败不能用强制账号“修复”，成本压力不能用自动
删除“修复”，文件安全不能用只允许少数扩展名“修复”，拆登录墙不能以公开用户数据换取。

## 3. Cross-cutting contract and scope freeze

| Contract area | Frozen result |
| --- | --- |
| Customer job | 匿名用户从 `/` 进入，创建 workspace/project，记录步骤/进度/分数，上传与保存，执行可解释财务工作，跨设备恢复，搜索，并下载/导出原件与结果；10 步旅程不可用静态页面或 health check 替代 |
| Data ownership | 用户可取回原件、批准派生物和报告；download 以字节 hash/metadata 验证，不只看 HTTP 200；显式删除走可审计生命周期，包含公开链接/缓存/索引和对象版本处置 |
| HTTP semantics | 查看、搜索、状态、GET/HEAD 与下载不得写业务状态或启动无预算长任务；高成本导出使用显式 create-job → status → artifact 流程并支持幂等、取消、失败和重试 |
| Financial trust | 金额权威值使用 integer minor unit 或 Decimal；来源、口径、版本、人工拍板和重跑可追；未知/错误显示 blocked，不能生成伪完整数字 |
| Safety/release | public/workspace/ops 三平面隔离；高风险能力使用可审计 Flag；Canary/Blue-Green equivalent、post-deploy Oracle、previous artifact 和自动停止/回滚是 GA 必需，回滚不得删用户数据 |
| Governance/recovery | 当前 main、部署制品、v1.5 checkpoint 与历史包在变更前 reconciliation；双平面七文件和 compact receipt 足够，不增加平行 ledger/catalog/evidence tree |
| AI | v1.5.2 核心合同不要求概率模型；当前默认 `R-AI-001 = NOT_APPLICABLE`。只有实际用户结果依赖模型且经变更 Gate 后才启用模型评测/安全流水线 |

Scope 分层冻结如下；详细行和唯一 R/AC writer 仍是 sealed taskpack 与 P1.2，不在本文件复制 49 行：

| Layer | Frozen count | Rule |
| --- | ---: | --- |
| `P0 GA` | `12/12` scope groups；`41` Requirements | 全部主 AC 和对应 Stage/Release Gate 必须有可复现 PASS；UNKNOWN/FAIL 阻断 GA，真实泄露、数据损坏、财务不变量或回滚失败不可 waiver |
| `P1 enhancement` | `7/7` scope groups；`8` Requirements | 不得削弱 P0；可在无收益/高风险时保持 Flag off 或 `NOT_APPLICABLE`，但任何已启用能力必须满足自己的 AC |
| Sealed universe | `49/49 R` + `49/49 primary AC` | 额外 ID `0`、遗漏 `0`、重复 writer `0`；`R-GOV-005/AC-GOV-005` 的经济合同已由 P1.3 PASS，实际价值与账单仍待观察 |
| Triggered Backlog | `7` candidates | 独立搜索、主动-主动、多用户协作、组织账号、计费、通用 OAuth、完整 ERP/BI/元数据平台均非当前承诺；必须先有触发证据、明确授权、新/改 R+AC+DAG |
| Explicit non-goals | `NG-01..NG-07` | 不扩平台、不以登录阻塞、不承诺无限资源、不自动公开、不为名词迁基础设施、不建第二治理、不盲 replay/force-push/S24 |

## 4. Frozen Baseline, target and observation contract

`Baseline` 是当前失败/未知事实，不是降级目标。所有行都冻结日期/环境/制品身份、目标、测量方式、观察
窗口和 owner；后续只能用可复现证据替换 UNKNOWN，不能调低阈值把失败变绿。

| Subject | Baseline @ capture | Authorized target / hard Oracle | Measurement + environment | Observation window | Owner |
| --- | --- | --- | --- | --- | --- |
| Root and legacy paths | **FAIL/UNKNOWN**：production source `68306e85...` 匿名 `/ = 302`；`/ui` 精确链本 phase 未重测 | `/ = 200`、最终 `/`、Access/login `0`；`/ui`、`/ui/` 单跳 `308 → /` | 全新无 Cookie 浏览器 + HTTP trace，绑定 git/artifact/deployment | 每个 edge/app release；Canary；上线 7 天与 30 天 | Web+Edge+Security |
| Full anonymous journey and recovery | **UNPROVEN / blocked at entry**：302 阻止旅程；无 v1.5.2 跨设备恢复制品证据 | 10 步旅程 `100%`；登录/匿名权限错误 `0`；有效恢复 `100%`、无效授权/secret leak `0` | 生产等价两台隔离设备、安全 synthetic workspace、状态/hash diff | 每个 identity/recovery release；Canary；季度恢复 UX 复核 | Product+Backend+UX+Security |
| Durable DB/object and deletion | **FAIL/UNPROVEN**：当前 App SQLite `/var/lib/kmfa/state` 未挂耐久卷；无生产耐久 DB/object、空环境 restore 或有限 RPO/RTO 证明 | 记录/对象丢失、误删和不可解释孤儿 `0`；跨重启/部署/备份恢复 `100%`；默认无自动到期 | production-equivalent DB+object，重启/滚动部署、inventory/reconciliation、从空环境 restore、业务不变量 | 每次迁移；季度；重大平台变更前后 | Data+Storage+SRE+Privacy |
| Arbitrary upload and download | **UNPROVEN**：本产品尚无 v1.5.2 合法/恶意格式矩阵、原件 hash、Range/ZIP 或处理边界证据 | 合法范围内安全存储；危险执行/逃逸 `0`；原件/批准制品 hash 不一致 `0` | synthetic/malicious 文件矩阵、quarantine/processor sandbox、object metadata、下载 hash；不使用私密原文 | 每次 upload/processor/download 变更；S06/S07 benchmark；Canary | Backend+Security+Storage |
| Projects, progress, scores and finance | **UNPROVEN end-to-end**：历史业务流存在，但匿名耐久 CRUD/恢复、并发与完整 v1.5.2 financial Oracle 未完成 | project 恢复一致、冲突不静默丢失；金额/血缘/golden/black path 错误 `0` | synthetic business fixtures、DB snapshots、Decimal/integer golden/property tests、重跑与来源 trace | 每次 schema/calculation/report 变更；Canary；7/30 天任务观察 | Product+Backend+Finance+Data |
| Default privacy and abuse | **UNPROVEN after opening**：Access 当前遮挡 public 边界；拆墙后的页面/API/search/cache/object/telemetry canary 与匿名攻击尚未测 | private/secret canary、越权、默认公开和恶意绕过 `0`；攻击不无界增长；正常误伤 `<1%` | public/workspace/ops 三平面 probes、private canaries、normal+attack load、cache/index revoke | 每个边界/事件变更；Canary；持续监控与 7/30 天 | Privacy+Security+SRE |
| Economics and capacity | **CONTRACT PASS / RUNTIME UNKNOWN**：P1.3 覆盖 `8/8` 能力；无真实账户用量、账单、流量、容量或采用率 | 单位成本可归因、预算/配额/降级可执行；保守情景不可控且无护栏则 Stop；无单点伪 ROI | S06/S07 benchmark、S12 实际账户账单/资源/支持、低基高重算且不含秘密 | S05/S06/S07；S11；S12 周/月；Canary；7/30 天 | Product+Finance+SRE |
| Canary and rollback | **UNPROVEN**：部署身份可查询，但无 v1.5.2 渐进流量、阈值触发、自动回滚后核心旅程/数据不变量证据 | rollback 成功 `100%`；错误/泄露/成本阈值自动停止；previous artifact 核心 Oracle 恢复且数据不损坏 | production-equivalent + production canary，故障注入、flag/deploy events、前后状态/hash、唯一制品 | 每个 release；S11 chaos；S13 Canary/GA；季度演练 | Release+SRE+Security+Data |
| Governance and traceability | **STRUCTURE PASS / DELIVERY INCOMPLETE**：seal `49/49 R/AC`、`14×4` tasks PASS；仅 S00 Stage 已 review/upload | 端到端断链 `0`；S00–S13 Gate 逐项 PASS；所有 P0 和 rollback Oracle 后才 GA | sealed validator、双平面 Gate、CI/Release Artifact + compact receipt、remote/deploy identity | 每个 task/Stage/release；S01 独立 Stage Review 是下一 run | Product Owner+QA+Release |

## 5. Decision trace — D-001 through D-014

每项 APPROVED decision 都同时绑定需求/主 AC、scope/non-goal 边界和风险控制。以下是只读追踪视图；决策
原文 writer 仍是 sealed `canonical_facts.yaml`。

| Decision | Frozen result | Requirement / primary AC | Scope or non-goal boundary | Risk and enforced guard |
| --- | --- | --- | --- | --- |
| `D-001` | 根域名直接完整主页，200，地址 `/` | `R-PUB-001 / AC-PUB-001` | `P0-02`；不得用隐藏 `/ui` 或登录 landing 替代 | 当前 302 是 hard fail；root Oracle 未过就 Hold |
| `D-002` | `/ui`、`/ui/` 单跳 308 到 `/` | `R-PUB-003 / AC-PUB-003` | `P0-02`；不保留第二主页/canonical | loop、链式跳转或路径分叉即失败 |
| `D-003` | 核心完整旅程无账号/邮箱/OAuth | `R-PUB-002 / AC-PUB-002` | `P0-03`, `NG-02` | 登录需求不得借安全名义进入；变异由 `MUT-LOGIN` 拒绝 |
| `D-004` | 高熵匿名 workspace + recovery + scoped session | `R-WS-001, R-WS-002, R-WS-003 / AC-WS-001, AC-WS-002, AC-WS-003` | `P0-04`；账号不是恢复 fallback | secret 泄露/有效恢复非 100% 时 Hold GA，不动原数据 |
| `D-005` | 无自动到期、跨部署、备份恢复、明确删除 | `R-DATA-003, R-DATA-004 / AC-DATA-003, AC-DATA-004` | `P0-05`, `NG-03` | 自动过期、误删或 restore 失败阻断 durable claim |
| `D-006` | 关系 DB 管状态；对象存储管文件字节 | `R-DATA-001, R-DATA-002, R-DATA-004 / AC-DATA-001, AC-DATA-002, AC-DATA-004` | `P0-05`；browser/temp/SQLite 单点不是 SSOT | DB/object 不一致或无可恢复路径时不迁移、不扩容 |
| `D-007` | 任意扩展名安全存储；风险格式 attachment-only | `R-UP-001, R-UP-003, R-UP-004 / AC-UP-001, AC-UP-003, AC-UP-004` | `P0-06`；`P1-06` 预览深度可 off；不承诺无限 | 处理器逃逸立即 Flag off/rollback，原件仍可取回 |
| `D-008` | 上传默认 Unlisted；显式白名单快照才公开 | `R-PROD-003, R-ARCH-001, R-SEC-001 / AC-PROD-003, AC-ARCH-001, AC-SEC-001` | `P0-08`, `NG-04` | 任一 private canary/撤销失败关闭发布，不公开 source |
| `D-009` | 登录不进 v1.5.2 GA | `R-PUB-002 / AC-PUB-002` | `NG-02`；OAuth 仅 Triggered Backlog | 身份集成不能阻塞 anonymous GA，需新授权/版本 |
| `D-010` | main/production/recovery/history 先 reconciliation | `R-GOV-001, R-GOV-002, R-MIG-001 / AC-GOV-001, AC-GOV-002, AC-MIG-001` | `P0-01/P0-10`, `NG-07` | 禁止 blind replay/force-push/S24；恢复资产只读取证 |
| `D-011` | GET/HEAD 无业务写；昂贵导出显式 Job | `R-DL-003, R-DL-004, R-ARCH-002 / AC-DL-003, AC-DL-004, AC-ARCH-002` | `P0-07`；读取不隐藏计算/成本 | side effect、幽灵 job 或无界并发即阻断 |
| `D-012` | 复用七文件/最小 machine facts/compact receipt | `R-GOV-003, R-QA-004 / AC-GOV-003, AC-QA-004` | `P0-01/P0-11`, `NG-06` | 新 ledger/catalog/evidence tree 是第二 writer，Gate 拒绝 |
| `D-013` | Flag + Canary/Blue-Green equivalent + 自动回滚 | `R-REL-004, R-MIG-001, R-DATA-004 / AC-REL-004, AC-MIG-001, AC-DATA-004` | `P0-12`, `NG-05` | 无 previous artifact/rollback Oracle 不发布；回滚不删数据 |
| `D-014` | AI 仅在真实模型能力存在时触发 | `R-AI-001 / AC-AI-001` | `P1-07`, `NG-05`；当前 N/A | 不制造纸面 AI 或独立服务；引入模型必须重过 Gate |

Trace result：`D-001..D-014 = 14/14` 均为 APPROVED，需求/AC、scope/non-goal 与 risk guard 字段完整；
缺项 `0`、额外 decision `0`、与 P1.1–P1.3 冲突 `0`。

## 6. Change invariants and request fields

下列是 v1.5.2 protected invariants：根 `/`、完整免账号、匿名可恢复、DB+object 耐久、任意文件安全存储、
默认 Unlisted、用户可下载、恢复资产不覆盖、P0 Oracle 不降级、可逆发布/回滚。实现选择可以变化，结果合同
不能靠口头、issue 标题、供应商限制或测试降阈值变化。

任何语义变化必须提交一个最小 change request，`9/9` 字段齐全：

1. 建议和客户结果；2. 触发证据/反证；3. 受影响 D/R/AC/Task/非目标；4. public/privacy/data/security；
5. 成本/容量/on-call；6. schema/object/迁移与 v1.5 recovery；7. rollback/data-safe fallback；
8. 测试、Baseline、目标和观察窗口；9. Owner、审批人、版本与到期/复核日。

缺字段、只有技术偏好、没有客户/运营证据，或通过删除数据/强制登录/弱化阈值解决问题的请求一律不进入
实现。所有批准必须落在 versioned diff；会议、聊天或注释不是合同更新。

## 7. Range Change Gate

| Gate class | Example | Required review / evidence | Allowed outcome |
| --- | --- | --- | --- |
| `CG-0 Evidence refresh` | 用新 benchmark/账单/restore 结果替换 UNKNOWN，不改变目标语义 | 绑定环境、制品、日期、测量方法、owner；不得调低失败阈值 | APPROVE evidence update；进入对应 Canonical Facts writer，不改 scope |
| `CG-1 Reversible implementation` | tus vs multipart、合格 PostgreSQL/R2 equivalent、flag SDK、UI copy | 证明满足同一 AC、成本/安全可控、可回退；无新事实 writer | APPROVE within current task；不需要产品 rescope |
| `CG-2 P1 depth/threshold` | 预览深度、增强搜索、统计、可选分享或真实模型能力 | P0 不受损；P1 AC、价值/成本、Kill、Flag、观察窗口和 owner 完整 | APPROVE limited experiment、DEFER 或 REJECT；无证据默认 off |
| `CG-3 Protected P0/public/privacy` | 新强制登录、改变 root、自动过期、缩小任意文件、上传即公开、取消恢复/下载 | 明确的新 Owner/user authorization；版本升级；影响分析；更新 D/R/AC/task/release policy；迁移/回滚与通知 | 当前 v1.5.2 实现 **STOP/REJECT**；不得由工程 PR 静默批准 |
| `CG-4 New infrastructure/migration` | 独立 search、Kubernetes、主动-主动、身份/计费平台 | 现有方案在批准 baseline 下失败的量化 trigger；全生命周期成本；安全/恢复/退出计划；shadow/expand-contract；无不可逆迁移 | DEFER/REJECT until triggered；触发后也只允许可逆、分阶段批准 |
| `CG-5 Emergency safety` | 泄露、危险执行、数据损坏或成本失控 | incident 证据、最小 blast radius、previous artifact/data-safe fallback、复原和复审 owner | 可立即关闭 processor/P1/share/traffic 或 rollback；不得删已存数据或永久加登录 |

Gate 顺序：先判是否改变客户结果或 protected invariant；否则走 `CG-0/1`。若是，先查当前 D/R/AC 与
P1 Kill；P1 可逆深度走 `CG-2`，P0/public/privacy 走 `CG-3`，新平台走 `CG-4`。任何泄露/损坏优先
`CG-5`。审批前状态只能是 `PROPOSED/DEFERRED/REJECTED`，不能先实现再补合同。

## 8. Required negative mutation tests

以下测试是对变更 Gate 的合同级模拟，不是 runtime 测试；每个输入都必须得到确定结果：

| Mutation | Proposed change | Expected Gate result | Actual contract evaluation |
| --- | --- | --- | --- |
| `MUT-ROOT` | 把完整软件移回 `/ui`，根 `/` 只放营销或登录页 | `CG-3 REJECT/STOP`；违反 `D-001/002`, `R-PUB-001/003` | **PASS — rejected**；必须保持 `/` 直接完整 App Shell |
| `MUT-LOGIN` | 上传、保存、恢复或下载前要求 GitHub/Google 登录 | `CG-3 REJECT/STOP`；违反 `D-003/009`, `R-PUB-002`, `NG-02` | **PASS — rejected**；可选身份只有新授权且不得阻断 anonymous core |
| `MUT-RECOVERY` | 只靠 localStorage，或用邮箱账号替代 recovery secret | `CG-3 REJECT/STOP`；违反 `D-004`, `R-WS-001/002/003` | **PASS — rejected**；必须保持高熵能力与跨设备恢复 |
| `MUT-RETENTION` | 为控费把 workspace/file 设置 30 天自动到期 | `CG-3 REJECT/STOP`；违反 `D-005/006`, `R-DATA-003/004`, `NG-03` | **PASS — rejected**；用可见配额/降级，已存数据不静默删除 |
| `MUT-FILE` | 只允许 PDF/图片，未知扩展名一律丢弃 | `CG-3 REJECT`；违反 `D-007`, `R-UP-001` | **PASS — rejected**；未知/高风险改走 quarantine/attachment-only |
| `MUT-PUBLIC` | 上传后自动公开或让公共搜索直接查询 workspace | `CG-3 REJECT/STOP`；违反 `D-008`, `R-PROD-003`, `NG-04` | **PASS — rejected**；只有显式白名单固定快照可公开 |
| `MUT-INFRA` | 因“需要 Search/Canary”立即迁 Kubernetes 或引入独立搜索 | `CG-4 DEFER/REJECT`；违反 `D-012/013`, `NG-05`，且 P1.3 `K-05` 未触发 | **PASS — deferred/rejected**；先复用 DB FTS/平台等效机制，真实失败 trigger 后重审 |
| `MUT-THRESHOLD` | 把失败 Oracle 调低到当前实现以获得绿色状态 | `CG-3 REJECT`；违反 Baseline/target contract 和 P0 Gate | **PASS — rejected**；失败保持 FAIL/UNKNOWN，只有证据可更新 baseline |

Required task test result：新登录需求和新基础设施需求均没有绕过 Gate；`8/8` mutation 得到预期决定，
protected definition 未被弱化。

## 9. P1.4 Pass Gate and S01 boundary

| Gate | Result | Evidence |
| --- | --- | --- |
| Inputs | **PASS** | P1.1 PR/FAQ、P1.2 PRD/OKR、P1.3 economics、sealed goal 和 `D-001..014` 已读取；依赖 commits 唯一 |
| Required outputs | **PASS** | 本 `PRODUCT_CONTRACT` receipt、Range Change Gate（第 6–8 节）和逐字 pursuing goal（第 1 节）齐全 |
| Six definitions | **PASS** | 根路径、免账号、匿名恢复、耐久存储、任意文件、默认隐私 `6/6` 有精确定义、边界和 Oracle |
| Decision trace | **PASS** | `14/14` decision 均追到 requirement/AC、scope/non-goal 与 risk guard；缺项/额外项 `0/0` |
| Baseline contract | **PASS** | `9/9` 主题均含 current baseline、target、measurement/environment、window、owner；失败未改写为成功 |
| Scope freeze | **PASS** | P0 `41` + P1 `8` = sealed `49 R/49 AC`；P0/P1/backlog/non-goal 边界与 P1.2 一致 |
| Change test | **PASS** | `MUT-LOGIN` 与 `MUT-INFRA` 必测通过；完整 mutation `8/8` 被正确 reject/defer |
| Stop condition | **NOT TRIGGERED** | 当前用户授权与 sealed contract 一致；没有新的 public/privacy 冲突或不可逆迁移请求 |
| Runtime/GA | **NOT READY** | production `/ = 302`，产品 P0 runtime Oracles 未完成；合同 PASS 不能升级任何 runtime AC |
| Stage boundary | **PASS** | S01 phases 达 `4/4`，但本 run 未执行/宣称 S01 Stage Review、未进入 S02、未 deploy、未 GitHub upload |

Builder conclusion：`T-S01-04 product contract PASS`。这只冻结实现与变更规则；S01 Stage Gate 仍须在
下一个独立 run 对 P1.1–P1.4 整体复审，发现问题必须先修复并重新复验，全部关闭后才能一次性上传整个
S01。Stage Review 前 `Stage completed` 仍只计 S00，S02 不得提前开始。

## 10. Rollback, Stop and next boundary

- 若本 receipt 与 sealed authority 漂移，普通 revert 本文件、HANDOFF 和 machine navigation，回到
  `8d1bb6e7...`；不修改 taskpack、app、facts、七文件、恢复 bundle、production 或用户数据。
- 若未来新用户授权与当前合同直接冲突并改变 public/privacy 边界，触发 `T-S01-04` Stop：输出最小冲突
  决策、直接证据、默认保持当前合同和不决策后果；不得擅自折中或先实现。
- 低价值 P1 新需求默认进入 Triggered Backlog/Flag off；未达触发阈值的独立服务保持不存在。
- 下一新 run 只能执行 **S01 全 Stage Review**：重验问题、用户、价值、非目标、指标/观察期、经济判据、
  pursuing goal、范围和 change Gate；修复全部 findings 后才整体 Stage upload。本文件不启动 Review、
  不进入 S02，也不授权 phase 级 push。
