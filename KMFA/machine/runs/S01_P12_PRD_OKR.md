# KMFA v1.5.2 PRD & OKR

> Task `T-S01-02` / Phase `P1.2 PRD 与 OKR`
> Dependency `T-S01-01` at commit `250ce3aa893e7329e0f1123d0e47b9bca3de8ea8`
> Primary Requirement / Acceptance `R-PUB-002 / AC-PUB-002`
> Captured: `2026-07-22T14:04:46Z`
> Status: **DONE — PRD contract PASS；AC-PUB-002 runtime remains FAIL/UNPROVEN**

本文是不超过 64 KiB 的 public-safe compact receipt。它把 P1.1 PR/FAQ 冻结为可验收 PRD、用户/JTBD、
战略目标、OKR、范围与非目标；不复制 taskpack 形成第二事实源，不把合同完成冒充软件上线，也不提前完成
P1.3 的成本收益/Kill Criteria 或 P1.4 的 Baseline/观察期冻结。

## 1. Authority、现状与状态语义

| Subject | VERIFIED value / boundary |
| --- | --- |
| Authorized taskpack | v1.5.2 ZIP SHA-256 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`；manifest `42/42`，validator `49 requirements / 49 AC / 14 stages / 56 tasks` PASS |
| Product input | `S01_P11_CUSTOMER_PRFAQ.md`：12 FAQ、9 条问题→结果链、12 个反证问题；无伪客户引语或采用量 |
| Published source | `origin/main = 6a9f2163d00adc000e965bf6bffbc0ed59283d7a`；P1.1 commit 仅本地领先 1，尚未 Stage upload |
| Production entry | 本 phase 匿名复核 `GET / = 302`；最新 repo-linked deploy run 仍为 `29916233128`，没有 P1.1/P1.2 deploy |
| Current product truth | 根入口、匿名完整旅程、耐久 DB/object、任意文件安全上传下载、恢复与回滚均不得宣称已交付 |
| Product authority | sealed `machine/canonical_facts.yaml`、`acceptance_contract.yaml`、`traceability.csv`、`task_graph.yaml`；本 receipt 只做 P1.2 可读投影与闭合检查 |

状态只使用以下语义：

- `VERIFIED CURRENT`：当前仓库、任务包或生产只读证据已直接证明。
- `AUTHORIZED TARGET`：Owner 已授权、但仍须由对应 Acceptance Oracle 证明的产品结果。
- `HYPOTHESIS`：来自 P1.1 的价值假设，必须允许被后续证据推翻。
- `OUT OF SCOPE`：没有当前 v1.5.2 交付承诺；不得因实现方便偷偷进入 GA。

`T-S01-02` 与未来 `T-S03-02` 共同引用 `AC-PUB-002`：本任务负责把完整免登录旅程定义到无歧义，
S03 才负责实现并取得 runtime 证据。因此本 phase 可判 **PRD contract PASS**，但当前 `302` 使
`AC-PUB-002` 必须继续是 **FAIL/UNPROVEN**。

## 2. Product definition

### 2.1 客户问题

KMFA 当前拥有财务核对、人工拍板、影响预览、重跑和报告下载等真实业务主线，但匿名用户打开根域名
即进入登录 dead end；即使未来拆除入口阻断，项目状态、文件字节、跨设备恢复、任意格式安全边界和
公开/私密隔离也仍缺少端到端证明。客户因此不能完成“立即开始—持续保存—可信处理—完整取回”的工作。

### 2.2 Strategic goal

把 KMFA 从受登录墙阻断的线上入口，收敛为**公开可达、匿名可完整使用、数据长期耐久、任意文件可安全
上传下载、财务结果可追溯且可安全发布**的软件；所有数据默认不公开，所有高风险变更可验证、可渐进、
可快速回滚。

### 2.3 Product principles

1. **先完成客户工作**：根域名进入产品，从项目和资料到结果、恢复与取回形成一条旅程。
2. **免账号不是降级版**：浏览、创建、上传、保存、恢复、搜索、下载和导出均不得要求账号、邮箱或 OAuth。
3. **公开站点不等于公开数据**：新工作区和内容默认 Unlisted；只有显式、白名单、可撤销快照可公开。
4. **长期保存必须可证明**：无自动到期不等于物理永恒；跨重启、部署与备份恢复均须通过 Oracle。
5. **任意格式不等于任意执行**：安全存储覆盖任意扩展名；高风险或未知格式可以 attachment-only。
6. **客户可带走数据**：原件、批准派生物和报告可验证下载；读取不得暗中写业务状态。
7. **未知就诚实阻断**：金额、来源、处理或恢复不确定时显示状态，不补造结果或静默覆盖。
8. **先最小骨架再增强**：先贯通匿名 walking skeleton；增强搜索、预览、统计或 AI 不能拖住 P0。

## 3. Users and Jobs-to-be-Done

| User | Situation / trigger | Job-to-be-Done | Desired outcome | Unacceptable result | Primary Acceptance |
| --- | --- | --- | --- | --- | --- |
| `U-01 临时访客` | 第一次从根域名进入，希望立刻判断产品是否有用 | 不注册地创建工作区和项目，上传一个资料并取回结果 | 首次有意义动作无账号前置，旅程可理解 | 登录墙、账号表单、隐藏 `/ui` 路径或 401/403 | `AC-PUB-001/002/004`, `AC-QA-001` |
| `U-02 长期个人用户` | 跨天、清浏览器、换设备或经历应用发布后继续项目 | 保存项目/进度/分数/资料，并凭恢复材料找回同一状态 | 数据未明确删除前持续存在，恢复后完整一致 | 浏览器是唯一副本、恢复丢项、误删或原件不可下载 | `AC-WS-002`, `AC-DATA-001..004`, `AC-PROD-001`, `AC-DL-001` |
| `U-03 经营/财务分析者` | 需要把来源资料转成可用于判断的经营结果 | 导入、校验、计算、解释、拍板、重跑并下载报告 | 金额精确、来源可追、重跑不重复、错误不丢已确认数据 | 浮点误差、虚构金额、来源断链、静默覆盖或静态演示 | `AC-FIN-001..004` |
| `U-04 公开分享者` | 只想选择性分享批准成果 | 从默认私密工作区显式发布并在需要时撤销 | 公开版本只含白名单字段，撤销后按 SLA 失效 | 上传即公开、私密内容被索引、撤销后仍可访问 | `AC-PROD-003`, `AC-SEC-001`, `AC-ARCH-001` |
| `U-05 维护与发布人员` | 需要上线、诊断故障、恢复或撤回版本 | 识别唯一制品，小批量发布，监控并自动停止/回滚 | 异常可定位，回滚恢复客户旅程且不损坏数据 | 只有文档证据、制品身份不明、回滚依赖删数据或泄露遥测 | `AC-REL-001..004`, `AC-DATA-004`, `AC-QA-004` |

P1.1 已将“账号摩擦、恢复理解度、格式分布、分享需求和项目/财务结合度”标为 `HYPOTHESIS`；本 PRD
不把它们提升为已验证采用率。P1.3 负责经济证伪，P1.4 冻结 Baseline 与观察期。

## 4. Core anonymous journey

下面 10 步共同构成 `AC-PUB-002` 的产品语义；不能挑选健康检查或静态页面替代完整旅程。

| Step | User-visible contract | Required result | Requirement → primary Acceptance |
| --- | --- | --- | --- |
| `J-01 进入` | 打开根域名，地址保持 `/` | 完整 App Shell 可操作，无 Access/登录跳转 | `R-PUB-001/003/004 → AC-PUB-001/003/004` |
| `J-02 建立工作区` | 首次访问自动获得匿名工作区 | 无账号/邮箱/OAuth；恢复责任清晰 | `R-PUB-002, R-WS-001 → AC-PUB-002, AC-WS-001` |
| `J-03 创建项目` | 创建项目并记录步骤、进度、分数、备注 | 保存后可重读，约束错误可理解 | `R-PROD-001 → AC-PROD-001` |
| `J-04 上传` | 选择任意类型资料，看到限制和真实处理状态 | 合法文件安全存储；危险内容不执行 | `R-UP-001/003/004 → AC-UP-001/003/004` |
| `J-05 处理与保存` | 需要处理时显示排队、成功、仅附件或失败状态 | 不假成功、不覆盖原件、失败可重试或降级 | `R-ARCH-002, R-REL-002 → AC-ARCH-002, AC-REL-002` |
| `J-06 业务工作` | 核对、解释、拍板、影响预览、重跑、生成报告 | 数值精确、来源清楚、重跑和错误路径不丢数据 | `R-FIN-001..004 → AC-FIN-001..004` |
| `J-07 恢复` | 导出恢复材料，在新设备找回同一工作区 | 有效恢复 100% 一致，无效材料不得授权，秘密不泄露 | `R-WS-002/003 → AC-WS-002/003` |
| `J-08 搜索` | 在自己的工作区查找项目、文件和可用结果 | 基础入口免登录；私密结果不进入公共索引 | `R-PUB-002, R-PROD-002 → AC-PUB-002, AC-PROD-002` |
| `J-09 下载` | 下载原件、批准派生物和报告 | 字节/元数据一致，高风险格式不内联 | `R-DL-001/004 → AC-DL-001/004` |
| `J-10 导出/离开` | 显式创建高成本导出并查看状态、取消或重试 | GET 无业务副作用，制品可验证，数据继续存在 | `R-DL-003, R-DATA-003 → AC-DL-003, AC-DATA-003` |

横切硬约束：任一步出现账号字段、登录弹窗、OAuth、`401/403` 匿名权限错误或秘密进入 URL/日志，
完整旅程即失败；任一步发生未解释数据丢失、私密泄露或无界资源增长，Release Gate 即失败。

## 5. Scope contract

### 5.1 分层语义

- `P0 GA`：全部对应主 Acceptance 必须通过；未证明或失败即不能 GA。
- `P1 enhancement`：可以在核心骨架后实现或保持 Flag off，但不得削弱 P0 的匿名、安全、持久化与取回。
- `Triggered Backlog`：不是当前承诺；只有触发证据、独立授权和新增 R/AC 后才能进入执行 DAG。
- P1.1 的“全部都可以”只表示核心客户旅程完整，不表示无限处理深度、无限资源或完整平台范围。

### 5.2 P0 GA — mandatory

| Scope ID | In-scope outcome | Requirements | Primary Acceptance | Exit rule |
| --- | --- | --- | --- | --- |
| `P0-01 Authority & recovery` | 身份、恢复差异、双平面和预授权保持唯一且可核验 | `R-GOV-001/002/003/004` | `AC-GOV-001/002/003/004` | 未分类差异、身份歧义、第八权威文件、普通依赖误阻塞均为 0 |
| `P0-02 Root & App Shell` | `/` 是唯一完整主页；旧路径单跳兼容；降级不白屏 | `R-PUB-001/003/004` | `AC-PUB-001/003/004` | 根入口 200、最终 `/`、关键入口 100% 可操作、路径分叉 0 |
| `P0-03 Full no-account use` | 浏览→工作区→项目→上传→保存→恢复→搜索→下载→导出全程免账号 | `R-PUB-002` | `AC-PUB-002` | 完整旅程通过；登录步骤和匿名权限错误均为 0 |
| `P0-04 Anonymous continuity` | 高熵匿名工作区、跨设备恢复、秘密不泄露、反滥用不靠登录 | `R-WS-001/002/003/004` | `AC-WS-001/002/003/004` | 标准恢复 100%；secret canary/越权/失控为 0；正常误伤低于阈值 |
| `P0-05 Durable ownership` | 项目状态和文件跨重启/发布/备份恢复存在，保留至明确删除 | `R-DATA-001/002/003/004` | `AC-DATA-001/002/003/004` | 数据丢失、不可解释孤儿、误删为 0；标准恢复演练 100% |
| `P0-06 Safe arbitrary upload` | 任意类型可安全存储；隔离检查、不可变版本和来源齐全 | `R-UP-001/003/004` | `AC-UP-001/003/004` | 危险执行/逃逸/无血缘版本为 0；合法夹具满足批准阈值 |
| `P0-07 Download & export` | 原件/批准派生物/报告可取回；昂贵导出显式且读取无副作用 | `R-DL-001/003/004` | `AC-DL-001/003/004` | 下载内容不一致、重复/失控任务、GET/HEAD 业务副作用为 0 |
| `P0-08 Project & privacy` | 项目/进度/分数恢复一致；内容默认 Unlisted，发布显式且可撤销 | `R-PROD-001/003` | `AC-PROD-001/003` | CRUD/恢复一致；未授权公开 0；撤销 Oracle 通过；分享功能可保持 off |
| `P0-09 Trustworthy finance` | 继承导入→核对→解释→拍板→重跑→报告，数值与来源可信 | `R-FIN-001/002/003/004` | `AC-FIN-001/002/003/004` | 精确/血缘/golden/black path 通过；静默覆盖和虚构结果为 0 |
| `P0-10 Safe architecture & migration` | 公共/工作区/运维隔离；部分写入可收敛；迁移可回退 | `R-ARCH-001/002, R-MIG-001` | `AC-ARCH-001/002, AC-MIG-001` | 越平面、幽灵状态、迁移差异为 0；每步回滚通过 |
| `P0-11 Security & quality proof` | 生命周期安全、walking skeleton、五类路径、全层测试和精简追踪 | `R-SEC-001/002, R-QA-001/002/003/004` | `AC-SEC-001/002, AC-QA-001/002/003/004` | 严重安全门/测试门/追踪断链为 0；不建 evidence tree |
| `P0-12 Operable release` | SLO、诊断降级、故障演练、Flag/Canary/自动回滚可执行 | `R-REL-001/002/003/004` | `AC-REL-001/002/003/004` | 告警可执行、降级不丢数据、故障/回滚 Oracle 全部通过 |

### 5.3 P1 enhancements — optional only when P0 remains intact

| Scope ID | Enhancement | Requirements | Primary Acceptance | Default / enable condition |
| --- | --- | --- | --- | --- |
| `P1-01 Accessible public UX` | WCAG 关键标准、主流移动端与批准公开内容索引 | `R-PUB-005` | `AC-PUB-005` | 核心旅程先可用；严重 a11y 和私密索引命中为 0 后启用索引 |
| `P1-02 Large/resumable transfer` | 上传断点续传、Range 和批量 ZIP | `R-UP-002, R-DL-002` | `AC-UP-002, AC-DL-002` | 限制可见；恢复/hash/ZIP 夹具通过，不把测试夹具大小冒充平台上限 |
| `P1-03 Enhanced search` | 全文、标签、可抽取文本、相关性和性能增强 | `R-PROD-002` | `AC-PROD-002` | 基础搜索仍在匿名旅程；独立引擎不默认进入范围 |
| `P1-04 Privacy analytics & capacity view` | 访问/产品事件与成本容量状态，不收集秘密或文件内容 | `R-PROD-004, R-OPS-001` | `AC-PROD-004, AC-OPS-001` | 无预算资源 0、敏感字段 0；单位成本待实测，不伪造 ROI |
| `P1-05 Economic validation` | 对重大能力补成本区间、敏感性、机会成本和 Kill | `R-GOV-005` | `AC-GOV-005` | 由 P1.3 完成；本 phase 只保留需求，不提前宣称经济 Gate PASS |
| `P1-06 Sharing/preview UX` | 可撤销分享体验和安全预览深度增强 | `R-PROD-003, R-UP-003, R-DL-001` | `AC-PROD-003, AC-UP-003, AC-DL-001` | P0 默认私密/附件取回始终成立；无法安全处理即 attachment-only/Flag off |
| `P1-07 Conditional AI assurance` | 只有真实用户可见模型能力存在时启用评测与安全流水线 | `R-AI-001` | `AC-AI-001` | 当前默认 `N/A`；不得为了“有 AI”制造功能或 GA 阻塞 |

### 5.4 Triggered Backlog — OUT OF SCOPE now

| Candidate | Trigger required before rescoping | Why excluded now |
| --- | --- | --- |
| 独立搜索引擎 | 数据库搜索在真实规模、相关性和延迟批准阈值下仍失败 | 当前无收益证据；增加同步、备份、权限和 on-call 面 |
| 跨区域主动-主动 | 单区域风险/法规/RTO 证据证明现有恢复不够 | 会显著增加一致性、成本和故障模式 |
| 多人协作编辑 | 高频协作任务、冲突模型和权限需求被真实用户证实 | 当前核心是匿名个人工作区；协作会改变身份与一致性合同 |
| 组织账号与角色体系 | 明确 B2B 管理任务另行授权，且不把登录强加给公共核心 | 现在会弱化免账号合同并增加隐私/支持成本 |
| 计费系统 | 真实使用和成本模型证明需要收费且获得授权 | 尚无用量/价格证据；不能让计费拖住数据安全 |
| 通用 OAuth / ChatGPT 登录 | 新授权说明其独立客户价值，且不阻塞 anonymous GA | 当前明确非目标；身份集成不是安全替代品 |
| 完整 ERP/BI/元数据平台 | 高频任务与量化收益证明必须扩张，而非复用现有业务流 | 范围、迁移、补丁和长期运维成本远超当前目标 |

这些候选没有当前交付 R/AC，不属于“已排期 scope item”。触发后必须先修改授权合同、Requirement、
Acceptance 与 Task DAG；禁止直接借某个实现 Phase 进入产品。

## 6. Explicit non-goals and avoided cost/risk

| ID | Non-goal | Avoided cost / risk | Safe default |
| --- | --- | --- | --- |
| `NG-01` | 不扩张为完整 ERP、网盘协作、通用 BI 或元数据治理平台 | 避免重复平台建设、迁移、复杂权限、补丁和长期 on-call，防止核心旅程延期 | 只继承能闭合 KMFA 客户工作的现有业务流 |
| `NG-02` | Google/GitHub/ChatGPT 登录不是 v1.5.2 核心能力或 GA 依赖 | 避免注册摩擦、OAuth 隐私/凭据/支持面和对 `R-PUB-002` 的直接冲突 | 公共核心始终匿名；缺 OAuth=`N/A` |
| `NG-03` | 不承诺物理永恒、无限容量或无限免费出网 | 避免不可兑现承诺、无界成本和通过悄悄删除控费 | 无自动到期 + 可恢复；限制在写入前可见且可核验 |
| `NG-04` | 不自动公开或索引全部上传内容 | 避免私密泄露、缓存/搜索残留和用户误解 | 默认 Unlisted；显式白名单快照，失败则发布 Flag off |
| `NG-05` | 不为 Canary/Search/AI 名词强制迁 Kubernetes 或增加独立服务 | 避免无收益迁移、更多故障域、补丁和回滚复杂度 | 先复用可验证能力；只有实测触发才升级 |
| `NG-06` | 不建立 `SCHEMAS/*.json`、state ledger、catalog builder 或逐 Stage evidence tree | 避免第二事实源、上下文膨胀、维护漂移和伪进度 | 复用双平面七文件、sealed machine graph 与 compact receipt |
| `NG-07` | 不盲目 replay v1.5、不 force-push、不夹带未完成 S24 | 避免覆盖当前有效代码、破坏唯一数据或丢失恢复资产 | 恢复资产只读取证；每次迁移先 reconciliation、可逆演练 |

非目标不是“永不讨论”，而是本轮默认不做；只有证据、授权和新的 R/AC/DAG 同时成立才能重新纳入。

## 7. OKR contract

所有 KR 都是 `AUTHORIZED TARGET`，不是当前结果。零泄露、零危险执行、精确恢复等数值来自安全/正确性
Acceptance，不是伪造商业收益；当前 Baseline、观察期和冻结版本由 P1.4 最终闭合。

| KR | Objective | Authorized measurable result | Requirement → primary Acceptance | Current evidence state |
| --- | --- | --- | --- | --- |
| `O1-KR1` | 公开入口真实可用 | 生产匿名 `GET /` 为 200，最终 URL `/`，无 Access/登录重定向 | `R-PUB-001 → AC-PUB-001` | `FAIL`：当前 302 |
| `O1-KR2` | 公开入口真实可用 | 主页→上传→保存→恢复→下载→导出匿名旅程 100% 通过 | `R-PUB-002 → AC-PUB-002` | `UNPROVEN/blocked at entry` |
| `O1-KR3` | 公开入口真实可用 | `/ui`、`/ui/` 单跳 308→`/`，无路由/canonical 分叉 | `R-PUB-003 → AC-PUB-003` | `UNPROVEN` |
| `O2-KR1` | 耐久保存与数据可取回 | 结构化数据和文件字节跨重启、滚动部署、备份恢复无丢失 | `R-DATA-001/002/004 → AC-DATA-001/002/004` | `UNPROVEN` |
| `O2-KR2` | 耐久保存与数据可取回 | 对象与数据库索引不可解释不一致为 0 | `R-DATA-002, R-ARCH-002 → AC-DATA-002, AC-ARCH-002` | `UNPROVEN` |
| `O2-KR3` | 耐久保存与数据可取回 | 原件/派生物/报告下载 hash 一致，标准恢复夹具 100% 通过 | `R-DL-001, R-DATA-004 → AC-DL-001, AC-DATA-004` | `UNPROVEN` |
| `O3-KR1` | 公开但不泄露、不失控 | 私密 canary 在页面/API/搜索/缓存/对象链接/遥测命中为 0 | `R-SEC-001, R-ARCH-001, R-PROD-003 → AC-SEC-001, AC-ARCH-001, AC-PROD-003` | `UNPROVEN` |
| `O3-KR2` | 公开但不泄露、不失控 | 恶意上传逃逸和危险文件执行均为 0 | `R-UP-001/003 → AC-UP-001/003` | `UNPROVEN` |
| `O3-KR3` | 公开但不泄露、不失控 | 匿名攻击不造成无界增长，正常用户误伤率低于 1% | `R-WS-004, R-OPS-001 → AC-WS-004, AC-OPS-001` | `UNPROVEN` |
| `O4-KR1` | 证据驱动的安全交付 | 49 条需求全部追到唯一主 Acceptance、任务、测试、证据和制品 | `R-QA-004, R-GOV-003 → AC-QA-004, AC-GOV-003` | taskpack structure `VERIFIED`；runtime evidence incomplete |
| `O4-KR2` | 证据驱动的安全交付 | Task DAG 无环；14 Stage 各 4 Phase/Task | `R-QA-004 → AC-QA-004` | sealed graph `VERIFIED` |
| `O4-KR3` | 证据驱动的安全交付 | 所有 P0 Gate 和回滚 Oracle 通过后才 GA | `R-QA-003/004, R-REL-004 → AC-QA-003/004, AC-REL-004` | `NOT READY` |

任何 Objective 不得用平均值遮蔽安全失败：私密泄露、危险执行、金额错误、数据丢失、恢复失败或回滚失败
均是独立 hard fail。P1 功能保持 off 不算 P0 失败，但已启用的功能必须满足它引用的 AC。

## 8. Full requirement universe consistency

此表不是新 registry；它只证明本 PRD 没有遗漏或新增 sealed 需求。每个 Requirement 与同编号主 AC
一一对应，任务与测试仍以 taskpack `traceability.csv` 为唯一 writer。

| Area | Count | Requirement IDs | Primary Acceptance IDs | Scope disposition |
| --- | ---: | --- | --- | --- |
| 治理 | 5 | `R-GOV-001, R-GOV-002, R-GOV-003, R-GOV-004, R-GOV-005` | `AC-GOV-001, AC-GOV-002, AC-GOV-003, AC-GOV-004, AC-GOV-005` | P0 4；P1 1 |
| 公开入口 | 5 | `R-PUB-001, R-PUB-002, R-PUB-003, R-PUB-004, R-PUB-005` | `AC-PUB-001, AC-PUB-002, AC-PUB-003, AC-PUB-004, AC-PUB-005` | P0 4；P1 1 |
| 匿名工作区 | 4 | `R-WS-001, R-WS-002, R-WS-003, R-WS-004` | `AC-WS-001, AC-WS-002, AC-WS-003, AC-WS-004` | P0 4 |
| 持久化 | 4 | `R-DATA-001, R-DATA-002, R-DATA-003, R-DATA-004` | `AC-DATA-001, AC-DATA-002, AC-DATA-003, AC-DATA-004` | P0 4 |
| 上传 | 4 | `R-UP-001, R-UP-002, R-UP-003, R-UP-004` | `AC-UP-001, AC-UP-002, AC-UP-003, AC-UP-004` | P0 3；P1 1 |
| 下载 | 4 | `R-DL-001, R-DL-002, R-DL-003, R-DL-004` | `AC-DL-001, AC-DL-002, AC-DL-003, AC-DL-004` | P0 3；P1 1 |
| 产品能力 | 4 | `R-PROD-001, R-PROD-002, R-PROD-003, R-PROD-004` | `AC-PROD-001, AC-PROD-002, AC-PROD-003, AC-PROD-004` | P0 2；P1 2 |
| 财务正确性 | 4 | `R-FIN-001, R-FIN-002, R-FIN-003, R-FIN-004` | `AC-FIN-001, AC-FIN-002, AC-FIN-003, AC-FIN-004` | P0 4 |
| 架构/迁移 | 3 | `R-ARCH-001, R-ARCH-002, R-MIG-001` | `AC-ARCH-001, AC-ARCH-002, AC-MIG-001` | P0 3 |
| 安全 | 2 | `R-SEC-001, R-SEC-002` | `AC-SEC-001, AC-SEC-002` | P0 2 |
| 质量 | 4 | `R-QA-001, R-QA-002, R-QA-003, R-QA-004` | `AC-QA-001, AC-QA-002, AC-QA-003, AC-QA-004` | P0 4 |
| 可靠性 | 4 | `R-REL-001, R-REL-002, R-REL-003, R-REL-004` | `AC-REL-001, AC-REL-002, AC-REL-003, AC-REL-004` | P0 4 |
| AI | 1 | `R-AI-001` | `AC-AI-001` | P1 conditional / default N/A |
| 运营 | 1 | `R-OPS-001` | `AC-OPS-001` | P1；不得削弱 P0 budget guard |

Coverage：`49/49 requirements`、`49/49 primary Acceptance`，额外 ID `0`，重复 writer `0`。P0 为 `41`，
P1 为 `8`；P0/P1 scope tables 的 requirement union 与 sealed universe 一致。

## 9. Primary Acceptance contract — AC-PUB-002

| Field | Frozen P1.2 contract |
| --- | --- |
| Environment | 生产等价环境；匿名全新会话；部署/制品身份唯一可追溯 |
| Safe input | 合成、匿名或 canary fixture；不使用真实员工、财务、群聊、考勤、SQLite、凭据或私密平台响应 |
| Journey | 浏览→创建工作区→项目→上传→处理/保存→恢复→搜索→下载→导出 |
| Negative observations | 账号、邮箱、OAuth、登录弹窗、Access redirect、401/403、秘密泄露、未解释数据损坏 |
| Threshold | 完整旅程通过；登录步骤 `0`；匿名权限错误 `0` |
| Evidence | E2E trace、网络日志、状态快照、唯一制品校验和；完整证据外置，仓内仅 compact receipt |
| Current verdict | **FAIL/UNPROVEN**：根入口当前 `302`，后续步骤没有生产证据；不得由 PRD 自审升级 |
| Implementation owner/task | Product+Web；`T-S03-02` 实现，相关 Stage/Release Gate 在 Oracle 全通过前保持阻断 |

“无需账号”禁止以下规避：先展示静态营销页再要求登录、把恢复页面藏在账号后、只允许浏览但写/下载需
OAuth、用匿名请求 `401/403` 当正常安全策略，或把登录改名为“激活/验证”继续阻断核心旅程。

## 10. Product self-review and Pass Gate

| Gate | Result | Evidence |
| --- | --- | --- |
| Inputs complete | **PASS** | P1.1、Owner authorization、historical flow、current `302` baseline 与 sealed graph 已读取；无私密原文复制 |
| Users/JTBD | **PASS** | `5/5` personas 各含 situation、job、outcome、unacceptable result 与 primary AC |
| Complete journey | **PASS** | `10/10` steps 覆盖 `AC-PUB-002` 输入顺序，登录与数据/安全横切失败条件明确 |
| Scope trace | **PASS** | P0 `12/12`、P1 `7/7` scope rows 均至少含一个 Requirement 和 primary Acceptance |
| Requirement universe | **PASS** | sealed `49/49 R` 与 `49/49 AC` 精确覆盖；P0 `41`、P1 `8`，未知 ID `0` |
| Non-goals | **PASS** | `7/7` 均说明避免的成本/风险与安全默认，不以口号代替边界 |
| OKR | **PASS** | `4` Objectives / `12` KRs；每个 KR 可判真伪并映射 R/AC；当前状态没有伪报成功 |
| No infinite scope | **PASS** | P0/P1/Triggered 三层分离；无当前 R/AC 的候选明确 OUT OF SCOPE |
| No fake precision | **PASS** | 只沿用 sealed 安全/正确性阈值；采用率、收益、单位成本和容量未编造 |
| Core no-login unchanged | **PASS** | `AC-PUB-002` 完整旅程无账号/邮箱/OAuth，未以安全或恢复为由弱化 |
| Phase boundary | **PASS** | 未做 P1.3 经济 Gate、P1.4 Baseline 冻结、实现/平台/数据变更或 GitHub upload |

Builder conclusion：`T-S01-02 PRD contract PASS`。这只说明范围、非目标、OKR 与 49 条需求无歧义，
不说明任何 runtime AC 已通过；`AC-PUB-002` 和 S01 Stage Gate 均保持未通过。

## 11. Rollback, Stop and next boundary

- 若某 P1 enhancement 拖慢或削弱 P0，默认 Flag off 或移回 Triggered Backlog；不得降低 P0 Oracle。
- 若新增范围需要无证据的不可逆平台迁移，触发 `T-S01-02` Stop：保留当前合同，停止新增范围并请求最小
  Owner 决策；当前未触发该条件。
- 若本 PRD 与 sealed taskpack 发生漂移，普通 revert 本 receipt/HANDOFF/navigation 即可；不触碰 app、facts、
  七文件、恢复资产、生产平台或用户数据。
- 下一新 run 只能进入 `S01 / P1.3 / T-S01-03`，补成本收益、敏感性、机会成本与 Kill Criteria；
  本文件不启动 P1.3、不完成 P1.4、不触发 S01 Stage Review，也不授权 phase 级 GitHub upload。
