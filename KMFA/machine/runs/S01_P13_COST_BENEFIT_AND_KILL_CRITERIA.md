# KMFA v1.5.2 COST, BENEFIT & KILL CRITERIA

> Task `T-S01-03` / Phase `P1.3 经济与证伪`
> Dependency `T-S01-02` at commit `7b80ac5804e60e2120646aba8c3fd7f7269552a7`
> Requirement / Acceptance `R-GOV-005 / AC-GOV-005`
> Captured: `2026-07-22T14:16:31Z`
> Status: **DONE — economic contract PASS；not a budget approval or runtime value proof**

本文是不超过 64 KiB 的 public-safe compact receipt。它覆盖 sealed Task Pack 定义的全部重大能力，记录
收益机制、工程量区间、运行成本公式、敏感变量、机会成本、置信度、复核窗口和 Kill；不制造采用率、
收入、节省金额、账户配额、供应商账单、单点 ROI 或日历工期，也不提前完成 P1.4 Baseline 冻结。

## 1. Authority and verified boundary

| Subject | VERIFIED value / boundary |
| --- | --- |
| Authorized taskpack | v1.5.2 ZIP SHA-256 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`；manifest `42/42`、validator `49 R / 49 AC / 14 stages / 56 tasks` PASS |
| Product scope | `S01_P12_PRD_OKR.md`：P0 `12/12`、P1 `7/7`、Triggered Backlog 分层；本文件不新增 scope |
| Customer hypotheses | `S01_P11_CUSTOMER_PRFAQ.md` 的 `FQ-01..12`；需求强度、恢复理解、格式分布、分享使用和运营成本尚未被伪装成事实 |
| Current source | local `HEAD=7b80ac58...`、`origin/main=6a9f2163...`，ahead `2` / behind `0`；S01 未上传 |
| Current production evidence | 匿名 `GET / = 302`；最新 repo-linked deploy 仍为 run `29916233128` / source `68306e85...` |
| Current infrastructure truth | 生产耐久 DB/object、备份恢复、最终配额、流量、单位运行成本均未实证；当前 SQLite 不能证明跨部署耐久 |
| Economic authority | taskpack `quality/COST_BENEFIT_AND_KILL_CRITERIA.md`、`task_graph.yaml` 与本日官方平台资料；本 receipt 是 P1.3 投影，不是采购或财务账单 writer |

收益使用“机制 + 可观察结果”表达，不折算货币；成本区分建设工程量与持续运行公式；置信度只沿用 taskpack
的 `中/中低`，缺数据时不擅自提高。`Kill` 是关闭 release、方案或低价值增强的风险控制，不授权删除已
保存数据，也不允许实现者静默弱化根域名、免账号、默认私密、耐久和数据可取回等 P0 合同。

## 2. Cost model and source refresh

### 2.1 Engineering investment — sealed ranges

| Workstream | Initial range | Interpretation |
| --- | ---: | --- |
| `W1 Authority/Recovery + Product Contract` | `9–19 engineer-days` | 身份/恢复保护、产品合同和治理基础；不能按生成文件数当进度 |
| `W2 Public root + anonymous workspace` | `9–16 engineer-days` | 根入口、完整免登录、匿名连续性；由 `M-01/M-02` 共享 |
| `W3 Durable DB/object + upload/download` | `15–24 engineer-days` | 结构化数据、对象、恢复、文件传输与安全；由 `M-03/M-04` 共享 |
| `W4 Product/search/analytics/finance` | `10–16 engineer-days` | 搜索、分享/统计、项目与财务主线；由 `M-05/M-06/M-07` 共享 |
| `W5 Security/testing/observability/release` | `17–31 engineer-days` | 安全验证、全层测试、观测、故障和回滚；主要对应 `M-08` 且横切全部能力 |

Task Graph 的 56 个 task-level 区间机械求和为 `58.5–106 engineer-days`；taskpack 报告将其写作约
`59–106`。五个已取整 workstream 的低端表面相加为 `60`，与 task-level `58.5` 存在 `1.5` 天取整差；
本 receipt 不隐藏或重写 sealed 输入，**总量判断使用 task-level `58.5–106`，workstream 仅作共享归因，
不得逐能力重复相加**。这些都是建设投入，不是日历承诺、运行费或收益。

### 2.2 Current official object-cost inputs — volatile, not a KMFA bill

2026-07-23（Australia/Sydney）只读刷新官方 Cloudflare R2 页面：

- Standard storage 页面显示 `$0.015 / GB-month`、Class A `$4.50 / million requests`、Class B
  `$0.36 / million requests`，直接 R2 Internet egress 显示 free；Standard 月度免费量显示
  `10 GB-month / 1M Class A / 10M Class B`。
- Infrequent Access 另有 retrieval 费和 30 天 minimum storage duration；本合同不默认选它。
- 平台限制页面显示单对象上限 `5 TiB`、single-part upload `5 GiB`、multipart `4.995 TiB`；Worker、
  账户、应用安全、预算和扫描能力可能给出更低边界，因此这些绝不是 KMFA 产品配额承诺。

Official sources：

- <https://developers.cloudflare.com/r2/pricing/>（页面标注 last updated 2026-05-28）
- <https://developers.cloudflare.com/r2/platform/limits/>（页面标注 last updated 2026-06-08）

价格、免费量和限制在 S05/S06 实施与 S12 预算 Gate 必须按当日官方页和实际账户重取。当前没有 R2 bucket、
账户用量或账单证据，故不得声称“月费为 0”或“支持 5 TiB 文件”。

### 2.3 Parameterized monthly operating formula

```text
C_total = C_object_storage + C_object_ops + C_retrieval
        + C_database + C_compute + C_scanning
        + C_backup_restore + C_observability + C_support_oncall

C_R2_standard ≈ billable_GB_month × 0.015
              + billable_ClassA_million × 4.50
              + billable_ClassB_million × 0.36
```

公式中的 billable unit 必须按官方 rounding/free-tier 规则和实际账单计算；它没有包含 DB、计算、扫描、
备份、观测、第三方服务、税/汇率或人力。即使 R2 direct egress 当前显示 free，高下载率仍会增加 Class B、
应用/连接服务、缓存、反滥用、支持和恢复验证成本，所以不能把“egress free”解释为“下载无成本”。

## 3. Major capability economic matrix

以下 `8/8` 能力与 sealed economic matrix 一一对应。工程区间按共享 workstream 引用，不可相加；持续成本
只列可观测 driver。P0 能力的 Kill 默认 Hold/rollback/重新设计，P1 增强可直接 Flag off。

| ID / capability | Benefit mechanism and proof signal | Shared build range | Ongoing cost drivers | Primary sensitivity | Opportunity cost | Confidence | Minimum Kill |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| `M-01 根入口/免登录` | 消除当前 302 dead end，让访客能完成首次有意义动作；看匿名完整旅程完成率而非 PV | `W2 9–16d` | Edge/路由、安全回归、滥用控制、支持 | 匿名流量、现有路由复杂度、正常误伤 | 先做 OAuth 会推迟核心合同并增加隐私/支持面 | `中` | 根入口仍需登录，或拆墙产生私密泄露：Hold release，恢复安全边界并重设计，不以登录作为永久修复 |
| `M-02 匿名恢复` | 无账号仍能跨设备继续同一项目；看恢复夹具一致率和用户保存/理解恢复材料证据 | `W2 9–16d` | 密码学/session、恢复 UX、密钥支持、演练 | 保存恢复材料比例、恢复频率、误操作 | 不做恢复会让耐久承诺只在当前浏览器成立；强制账号则破坏免登录 | `中低` | 标准有效恢复达不到 100% 或 secret 泄露：Hold GA；修 UX/协议，不偷偷引入账号 |
| `M-03 耐久 DB + object` | 避免项目/文件随重启或发布丢失，支持可验证取回；看丢失/孤儿/恢复不变量 | `W3 15–24d` | DB/对象、版本、备份、恢复、对账、下载、值班 | workspace 数、文件 GB-month、对象数、下载率 | 延后恢复演练会积累不可见数据风险；过早多区域会放大一致性成本 | `中` | 不能从空环境恢复，或保守情景无配额/降级/预算护栏：Hold durable claim/release；保留数据并停止扩容 |
| `M-04 任意文件` | 减少格式拒绝和多工具拆分；看合法夹具通过、attachment-only 比例和危险执行为 0 | `W3 15–24d` | 分片/操作请求、扫描、沙箱、预览、隔离、配额、误报支持 | 文件 P50/P95/P99、扫描/预览率、高风险格式比例 | “所有格式都预览”会增加解析器攻击面并挤压恢复/下载工作 | `中低` | 恶意逃逸/危险执行：立即关闭处理器并回滚；成本过高则 attachment-only，不删除原件 |
| `M-05 搜索` | 缩短找回项目/文件/结果的时间；看任务成功、相关性、权限和延迟，不用查询量冒充价值 | `W4 10–16d` | 索引、权限、评测、增量更新、维护 | 语料量、查询量、Top-k 相关性、P95 | 独立引擎会增加同步、备份、授权与 on-call，可能无收益 | `中` | DB FTS 已达批准目标：Kill 独立引擎；增强搜索在观察期无任务改善：Flag off，保留基础入口 |
| `M-06 公开发布` | 让用户选择性分享批准成果并获得公开发现；看显式发布/撤销任务成功与真实需求 | `W4 10–16d` | 快照、白名单、撤销、CDN/索引、隐私运营 | 真实发布比例、缓存命中、撤销频率 | 建公共内容平台会推迟默认私密、恢复和文件取回 | `中低` | 无法证明字段白名单、任一 private canary 泄露或需求无证据：关闭真实分享，保持默认 Unlisted |
| `M-07 财务分析` | 让结果可用于真实判断；看精确金额、来源血缘、重跑去重和完整业务任务 | `W4 10–16d` | 口径/映射维护、数据校验、血缘、回归、支持 | 现有实现复用率、输入质量、规则变化 | 完整 ERP/BI 会扩大迁移和维护，反而推迟可信核心流 | `中` | 关键结果不精确、不可追溯或错误路径丢数据：阻断正式结论/报告，保留来源和 blocked 状态 |
| `M-08 观测/安全发布` | 降低故障发现与恢复风险；看可执行告警、恢复演练、canary 与回滚后的核心 Oracle | `W5 17–31d` | traces/metrics/logs、保留、演练、值班、安全工具、补丁 | 流量、信号基数、保留期、故障复杂度、人力 | 只做功能不做恢复会把事故成本后移；全量高基数观测会吞噬预算并泄密 | `中` | 无自动回滚、回滚后核心流失败或观测含 secret/file content：Hold GA，关闭有害信号并回到 previous artifact |

Coverage result：major capabilities `8/8 = 100%`；每行都有收益机制、共享成本区间、持续成本 driver、
敏感变量、机会成本、置信度和至少一个可执行 Kill。

## 4. Low / Base / High scenario model

当前没有真实公开流量、文件分布或单位账单，故情景用**参数状态和方向**而非伪精确数量。`Base` 是待验证
比较情景，不是现状声明；P1.4 只冻结可核验 Baseline，S06/S07/S11/S12 再用 benchmark/账单替换 UNKNOWN。

| Dimension | Low scenario | Base comparison | High / conservative scenario | Decision movement |
| --- | --- | --- | --- | --- |
| Anonymous traffic/workspaces | 少量首次试用、低并发 | 稳定增长、重复访问开始出现 | 突发/攻击流量与高并发 | 先小规模；逐层 quota/rate/concurrency/challenge，正常误伤仍须低于 AC |
| File size/object count | 小文件为主、对象少 | 混合类型与大小、存在重复/版本 | 大文件、多版本、大量小对象并存 | 大小影响 GB-month/分片，数量影响 ops；限制前置可见，不能写后静默丢弃 |
| Download/retrieval | 偶发原件取回 | 周期下载与报告导出 | 高频下载、Range、批量 ZIP/公开访问 | 测 Class B、连接服务、缓存和支持；仅公开安全内容可缓存 |
| Scan/preview ratio | 多数 attachment-only | 常见格式受控扫描/预览 | 高风险格式多、深度处理请求高 | 优先安全存储；超预算/超时降为 attachment-only，处理器 Flag 可独立关闭 |
| Public publishing | 分享功能 off 或极少 | 少量显式白名单快照 | 公开比例高、撤销/索引复杂 | 没真实需求不建平台；泄露/撤销失败立即关闭分享，不影响私密工作区 |
| Search corpus/queries | DB FTS 轻载 | 语料与查询足以做相关性基线 | 大语料、高 QPS、复杂排序 | 只有 AC-PROD-002 真实规模失败才评估独立引擎 |
| Recovery/backup | 小夹具定期演练 | 按季度和重大迁移恢复 | 高频变更、严格 RPO/RTO、故障多 | 不能减少演练伪装省钱；先优化自动化，恢复失败 Hold durable claim |
| Observability | allowlist 关键旅程、短保留 | 采样 trace + 核心 SLI | 高基数、长保留、全量事件 | 先采样/聚合/retention；秘密或文件内容命中即 Kill 对应信号 |
| Human labor/on-call | 自动化高、低支持量 | 有日常 triage/补丁/恢复演练 | 高误报、复杂故障、频繁人工恢复 | 把支持/值班计入总成本；若靠持续人工兜底才可用，停止扩展并重设计 |

情景结论：低情景不授权提前引入独立服务；基准情景需要真实测量后才能晋级；高/保守情景优先使用透明
配额、排队、sampling、attachment-only、Flag off 和 previous artifact。若这些护栏都无法控制核心持续
成本，才触发 `T-S01-03` Stop，而不是删数据、强制登录或伪报收益。

## 5. Sensitivity register and formulas

| ID | Variable | Cost/benefit direction | Non-obvious risk | Required measurement / control |
| --- | --- | --- | --- | --- |
| `SEN-01` | 日活/并发 workspace | 增加 DB、事件、反滥用与支持；也增加潜在使用价值 | 低活跃时复杂基础设施 ROI 极低 | 匿名且不含秘密的 journey completion、并发、误伤；先小规模 |
| `SEN-02` | 文件平均值与 P50/P95/P99 | GB-month、分片、备份/恢复时间随大小上升 | 小文件请求费与大文件容量/续传是不同曲线 | S06 真实安全夹具分布；大小/配额前置显示 |
| `SEN-03` | 下载/出网频率 | R2 direct egress 当前 free，但 B ops、连接服务、计算和支持仍上升 | “免费出网”容易掩盖请求/其他服务和滥用成本 | S07 Range/ZIP benchmark、B ops、connected-service bill、预算告警 |
| `SEN-04` | 扫描/预览比例和深度 | 计算、内存、许可、延迟、误报支持随处理加深 | 能上传不要求能预览；深解析扩大攻击面 | 记录安全状态而非内容；超时/超预算 attachment-only |
| `SEN-05` | 公开发布比例 | CDN/索引/隐私运营和撤销工作上升 | 低需求时复杂公共平台没有回报 | 经同意的发布任务与撤销成功；默认 off/Unlisted |
| `SEN-06` | 搜索语料/查询/相关性 | 索引/查询负载上升；相关性改善才是收益 | QPS 高不代表找到结果；DB FTS 可能长期足够 | 真实安全评测集、Top-k/P95/权限；指标触发升级 |
| `SEN-07` | 恢复演练频率 | 演练有成本，但不演练使备份价值未知 | 为省成本降低演练会放大数据损失尾部风险 | 季度+重大迁移；RPO/RTO 与不变量实测 |
| `SEN-08` | 观测基数/采样/保留 | 信号量和保留直接影响存储/查询/值班 | 高基数既昂贵又可能夹带秘密 | allowlist、sampling、retention、敏感 canary scan |
| `SEN-09` | 人力、复用率与 on-call | 建设/维护/支持成本对复用与误报高度敏感 | 纸面自动化可能把工作转成人工排障 | 从 task/incident/恢复演练记录实测，不以忙碌时长当收益 |

敏感性重算必须至少改变：流量、文件大小、下载/出网、扫描率和人力五类假设；结论只允许输出范围及
Gate 变化。没有实际量时保持 `UNKNOWN`，不得为了计算完整而填零。

## 6. Opportunity-cost decisions

| Decision | Chosen priority | Work deliberately displaced |
| --- | --- | --- |
| 先 root/no-login walking skeleton | 先证明用户能进入并走完一个文件旅程 | 第三方登录、营销壳、隐藏 `/ui` 入口 |
| 先恢复与耐久 | 先证明数据不丢且可取回 | 低收益 UI 增强、未触发多区域架构 |
| 任意文件先 safe storage | attachment-only 也是完整的安全价值 | “所有格式都预览”的解析器长尾 |
| 搜索先 DB FTS | 先用真实语料证明相关性/延迟缺口 | 独立搜索集群、双写/同步/on-call |
| 分享默认 off/Unlisted | 先证明白名单和撤销 | 通用公开内容平台、自动 SEO 全量索引 |
| 财务先精确与血缘 | 保留核对/拍板/重跑真实业务价值 | 完整 ERP/BI/元数据平台扩张 |
| 观测先关键旅程 allowlist | 可关联且不泄密的最小信号 | 全量高基数日志和无期限保留 |
| compact evidence | 把时间投入代码、测试、恢复和演练 | 平行 schema/ledger/catalog/evidence tree |

机会成本不是把 P0 需求移出范围；它决定实现顺序、处理深度和 P1/Triggered Backlog 是否保持关闭。

## 7. Kill / Hold / Continue matrix

| Kill ID | Capability | Evidence trigger | Immediate action | Data-safe fallback | Review owner/window |
| --- | --- | --- | --- | --- | --- |
| `K-01` | `M-01` | `/` 仍需登录，或拆墙后 private canary/越权非 0 | Hold/rollback release；修边界 | previous artifact；不得公开工作区数据 | Web+Security / every deploy |
| `K-02` | `M-02` | 标准有效恢复不为 100%、无效材料授权成功或 secret 泄露 | Hold GA；关闭有缺陷恢复入口并修协议/UX | 原工作区保持不动；不以账号替代 | Backend+UX+Security / every release+quarterly |
| `K-03` | `M-03` | 空环境恢复失败、记录/对象不变量失败，或成本无 quota/degrade 路径 | Hold durable claim 和扩容；禁止破坏迁移 | 保留旧 schema/object/version，继续只读/可取回 | Data+SRE / migration+quarterly |
| `K-04` | `M-04` | 恶意逃逸/危险执行，或处理成本持续超保守预算 | 关闭对应 processor/preview；必要时 Hold upload release | attachment-only + 原件下载；已存数据不删 | Security+Backend / every security release |
| `K-05` | `M-05` | DB FTS 达批准目标，或增强搜索在观察期无任务改善 | Kill 独立引擎/关闭增强 Flag | 保留基础匿名搜索和私密隔离 | Search+Product / S08+7/30-day review |
| `K-06` | `M-06` | 无白名单、任一泄露、撤销失败或真实发布需求无证据 | 关闭真实发布/索引 | 工作区保持 Unlisted；仅安全 demo/聚合可见 | Product+Privacy / canary+7/30-day |
| `K-07` | `M-07` | 关键金额不精确、来源断链、重跑重复或错误路径丢数据 | 阻断正式结论、报告升级和业务决策 | 展示 blocked/来源/旧版本，不伪造金额 | Finance+Data / every calculation change |
| `K-08` | `M-08` | 无自动回滚、故障后核心 Oracle 失败，或 telemetry 含 secret/file content | Hold GA；关有害观测/Flag，回 previous artifact | 数据 schema/object 保持兼容，不靠删除回滚 | SRE+Security / every release+exercise |
| `K-X` | All P0 | 任一 P0 AC 为 FAIL/UNKNOWN 或证据不可复现 | Hold/Kill Release | previous verified artifact；不丢数据、不重写 ref | Release Owner / every Gate |

`K-01..K-08` 对重大能力覆盖 `8/8`，每项至少一个 Kill。P1 功能无收益证据时可直接 off；P0 失败时 Kill
的是版本/实现/不安全路径，核心授权结果仍需重新设计并由后续 AC 证明。

## 8. Review windows and evidence replacement

| Checkpoint | Evidence to replace UNKNOWN | Allowed decision |
| --- | --- | --- |
| `P1.4` | 当前事实 Baseline、目标、观察期与 owner | 冻结 measurement contract；不补造运行值 |
| `S05` | 实际 DB/object 产品、账户能力、备份/恢复和账单字段 | 确认 adapter/存储类；无恢复不迁移 |
| `S06/S07` | 文件 P50/P95/P99、分片、扫描/预览、下载/Range/ZIP benchmark | 更新单位成本、配额和 attachment-only 边界 |
| `S08/S09` | 搜索任务、分享需求、财务复用/质量 | 保持、Flag off 或 Kill P1 深度；不扩成平台 |
| `S11` | 压力、极限、soak、故障与尾延迟 | 调整容量/并发；硬失败阻断 release |
| `S12` | 实际周/月用量、账单、事件基数、告警和 on-call | 建预算/告警；删除无价值信号，不删用户数据 |
| `Canary` | 错误、成本、误伤、泄露和 rollback Oracle | 扩大、保持、停止或回滚 |
| `Post-launch 7/30 days` | 匿名任务完成、恢复/下载、P1 feature use 与 incident/cost | 保持 P0；扩展或 Kill 低价值 P1 Flag |

复核只使用 public-safe 聚合或经授权证据；恢复密钥、文件内容、真实财务原文、员工身份和私密平台响应
不得进入事件、日志或本 receipt。

## 9. AC-GOV-005 self-review

| Gate | Result | Evidence |
| --- | --- | --- |
| Major capability coverage | **PASS** | sealed `M-01..M-08 = 8/8 = 100%` |
| Benefit mechanism | **PASS** | `8/8` 有客户/运维结果与未来 proof signal；货币收益数字 `0` |
| Cost ranges | **PASS** | `5/5` sealed workstream 区间；task graph total `58.5–106` 与 rounded `~59–106` 差异透明 |
| Low/Base/High | **PASS** | `9` dimensions 均有三情景与决策移动；Base 明确不是已测 baseline |
| Sensitivity | **PASS** | `SEN-01..09`；覆盖流量、大小、下载/出网、扫描、发布、搜索、恢复、观测、人力 |
| Opportunity cost | **PASS** | `8/8` 决策说明被主动推迟的工作，不削弱 P0 |
| Confidence | **PASS** | `8/8` 沿用 taskpack `中/中低`；未知未升级 |
| Kill criteria | **PASS** | `K-01..08` 覆盖每项重大能力，另有全局 `K-X`；动作与 data-safe fallback 完整 |
| No fake precision | **PASS** | 无采用率、收入、节省、账户账单、容量或单点 ROI；官方单价只进入参数公式 |
| Runtime price refresh | **PASS** | 当日官方 R2 pricing/limits 已只读核验；实际账户与其他成本仍为 UNKNOWN |
| Stop condition | **NOT TRIGGERED** | 高情景已有 quota/queue/sampling/attachment-only/Flag/rollback 可逆护栏；尚无不可逆投入 |
| Phase boundary | **PASS** | 未做 P1.4 freeze、实现/平台/数据变更、采购、deploy 或 GitHub upload |

Builder conclusion：`T-S01-03 / AC-GOV-005 economic contract PASS`。这证明经济判据结构完整、可重算、
可 Kill，不证明客户采用、运行成本可接受、P0 runtime AC 或整个 S01 Stage Gate 已通过。

## 10. Rollback, Stop and next boundary

- 若官方价格、Task scope 或真实容量改变，只更新参数/区间和 Gate，不回填一个看似精确的 ROI。
- 若保守情景下核心持续成本不可控且 quota、定价、范围、降级均无效，触发 `T-S01-03` Stop：保持已有数据
  可取回、停止新增昂贵处理和不可逆投入，向 Owner 提交最小范围决策。
- 回滚本 phase 只需普通 revert 本 receipt/HANDOFF/navigation；不触碰 app、facts、七文件、恢复资产、
  production、bucket/database 或用户数据。
- 下一新 run 只能进入 `S01 / P1.4 / T-S01-04` 冻结 Baseline、目标、观察期与 Stage Gate 输入；
  本文件不启动 P1.4、不触发 S01 Stage Review，也不授权 phase 级 GitHub upload。
