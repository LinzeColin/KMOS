---
name: daily-funds-skill
description: 独立云端每日资金纵向切片；仅从指定钉钉群历史消息取数，原始证据进入 Private-Database，经过整数分勾稽后投影到 KMFA 私有页面。
---

# 每日资金

这是一个运行在 Coolify 的确定性服务，不是一个 Agent 提示词。运行时不得调用模型、其他 Skill、本机路径、事件触发或既有 DWS profile。

## 唯一输入与输出

- 输入：`dws chat message search-advanced --conversation-ids <唯一群ID>` 按固定时间窗与 opaque `nextCursor` 分页读取历史消息；消息须同时匹配唯一 `senderOpenDingTalkId` 与允许文档族（资金账户明细表、资金流水明细/资金明细）。显示名 `sender` 只能用于人工诊断，绝不能作为来源 ID。
- DWS 身份：首次只在 daily-funds 的独立云端卷中显式完成一次 `bootstrap-dws-auth`。当 Coolify 的 Bearer API 没有容器执行能力时，已通过 Cloudflare Access 的 KMFA 私有页面可经既有控制卷发出**唯一固定的**开始/取消请求；同容器 broker 只运行 DWS 设备流、只回传短时 `verificationUri`/`userCode` 给该私有页面，不能执行任意命令，不能读取原始数据，且设备码不进入 cron、日志、status、Git 或公开面。`DAILY_FUNDS_DWS_AUTH_BUNDLE_B64` 仅是可选灾备恢复导入。未配置 `DAILY_FUNDS_DWS_CLIENT_ID` 时，受控 DWS 进程使用其官方默认客户端；如配置，该值只在本切片构造的环境中作为覆盖值使用，绝不继承宿主或其他 Skill。`search-advanced` 只按唯一 `--conversation-ids` 远程读取；发送人、群 ID与文档族三重门禁仍逐条在本地执行。`auth status` 或任一门禁失败即关闭。运行时不得另行注入 AppSecret；AppKey/AppSecret 不能替代登录态，也不得读取宿主或其他服务的登录态。
- 受控历史验证：私有页面可发起**一次固定的**最近 24 小时、最多两页 `search-advanced` 探针。请求不含命令、群 ID、发送人、cursor、时间范围、消息、附件或金额；broker 仅返回 `REQUESTED/RUNNING/COMPLETED/FAILED/EXPIRED` 与固定 continuation 枚举。它不下载附件、不写 raw、不改变 15 分钟主采集链，也绝不构成 DF-008/DF-022、整数分勾稽、金额或 publication PASS。
- Access 控制面预检：若私有 history-probe 入口尚无可验证的云端身份，受控 `coolify-ops` 的 `daily-funds-access-audit` 只能对 Cloudflare 的 token、Access application、service-token 与 policy 列表发出四个 `GET`；每个响应仅在临时 runner 文件中分类为有限状态。它不得创建 token/策略、调用探针或公开任何 Access 标识；即使四项读取成功，写权限仍为 `UNKNOWN_NOT_TESTED`，不能把它写成授权、DWS 历史或资金结果 PASS。
- 受控 Access 探针桥：统一主线发布后，`daily-funds-history-probe-bridge` 才可手动运行。它只能选择当前 Coolify audience 对应的**唯一** HTTPS `/ops/*` self-hosted Access 应用，临时创建 `60m` service token 和该应用独占的 `non_identity` Service Auth policy，随后固定同源无 body 地调用一次 `/ops/api/daily-funds/history-probe`，最多两分钟轮询 values-free 回执。流程退出时精确删除本次 policy 与 token；任何识别、调用或清理失败均为 `NOT_MET`/`NEEDS_ATTENTION`。回执中的 `OPAQUE_CURSOR_REUSED_SECOND_PAGE_*` 仅证明 opaque cursor 控制流被复用，cursor 字符串、群 ID、消息和金额永不保存或输出。
- 原始权威：私有 GitHub `LinzeColin/Private-Database` 的 `Private-KMDatabase/KMFA/daily_funds`。仅本服务 single writer 获 Owner 窄例外使用 `--filter=blob:none --sparse --no-checkout` 的**非 cone 精确路径** clone；Git/SSH 进程只使用该服务 deploy key 与临时 known_hosts，不继承宿主 agent、全局配置或提示。禁止全库 clone 与 force push；推送后必须以全新 sparse clone 回读消息信封、occurrence、原始字节/分块 manifest 和 SHA-256。
- 附件能力：`.csv`、`.txt`、`.xlsx`、`.xlsm` 仅为候选格式。只有目标群真实字节经私有 Git readback、SHA/lineage、MIME/magic、模板和 parser-open 全部成功后，运行时才以 SHA 写入受保护 `parser_evidence` 回执；合成测试不能把任何格式标为生产已支持。`.xls` 继续为 `needs-review`。图片与扫描 PDF 仅可走显式启用的离线确定性 Tesseract 回退：来源校验、关键字段至少 0.98 置信度、两个不同业务日同版式校准和后续同版式 readback 缺一不可；它不是模型/API，任何缺口均保持 `needs-review`，不得发布金额。
- 解析模板：未有目标群真实样本冻结多表模板前，任何多 sheet 工作簿以 `XLSX_WORKSHEET_AMBIGUOUS` 停止；“流入/流出”与“金额/方向”两套金额编码并存时以 `TRANSACTION_AMOUNT_MAPPING_AMBIGUOUS` 停止。解析规则升级后的旧 capability receipt 仅留审计，不能投影为当前支持，必须以新 parser version 重新打开私有原始字节。
- 查询投影：Cloudflare D1；热镜像：Cloudflare R2；异地冷备：OCI Object Storage；本地 SQLite 仅含 cursor/inbox/idempotency/outbox/runtime journal。
- 页面：KMFA 私有 `/ops/app?tab=每日资金` 或 `/ops/daily-funds`，Cloudflare Access 保护；根页和公共 API 不暴露金额、附件、ID 或下载链接。

## 固定运行合同

- `*/15` 北京时间：历史轮询，只有包含显式记录列表的正常页 `hasMore=false` 才完成；缺少记录列表的终页必须以 `DWS_PAGE_RECORDS_MISSING` 失败关闭，不能写成零匹配或推进 cursor。仅在 `hasMore=true` 时逐字复用 opaque `nextCursor`，终页即使返回值也必须丢弃。任一页失败不得推进 durable high-water；增量重叠 30 分钟。
- `* * * * *`：授权探测，同一 incident 每 360 分钟最多一次 outbox 记录。
- `0 * * * *`：DWS 显式认证状态保活。
- `0 */6 * * *`：R2 零付费守卫。只读 Cloudflare 控制面，核验全账户 bucket 默认 Standard、无 IA 生命周期、IA 指标为零，并按最坏 31 天/15 分钟写入量确认 Class A/Class B/存储均低于免费额度 40%。回执过期、未知或失败时，R2、冷备前 R2 readback 与 publication 一律 fail-closed；不会把 bucket、对象、金额或凭据写入回执。
- `20 5 * * *`：只读 `raw-archive-audit`。它只从已取得范围的私库原件按精确 sparse 路径重新校验消息信封、occurrence、批次与 SHA，再运行离线确定性 parser；不请求 DWS、不写 Git/R2/D1/OCI、不切换 `current.json`。结果仅可更新 values-free 附件能力回执，不能代表群历史全量、双事实、勾稽或金额 publication PASS。
- 启动及每日 `05:45`：写入不含 argv、挂载来源或凭据的 runtime isolation audit；发现宿主挂载或其他 Skill 进程即失败关闭。
- 每日：最大 7 天的回填、OCI 冷备重试、自主观察；回填永不替换较新的 live pointer。观察以当前 container deployment 的首份 D1/pointer/history 三方一致的 VALID publication 为基准，之后仅新的**周一至周五**源侧业务日期计入五日影子对照；cron 重试、同日重跑、周末 publication 和历史回填不能虚增。该 values-free `flow_state` 只由既有 KMFA 状态中枢读取，生产 source/image 身份无真实 Oracle 时保持 `UNKNOWN`。完整历史扫描确认没有候选附件的日窗仅作为 `BACKFILL_EMPTY_WINDOW` 推进回填计划；经私有 Git 新 sparse-clone 回读、但未获确定性解析支持的附件登记为 `NEEDS_REVIEW` 后同样可推进历史计划，绝不构成勾稽或发布成功；来源谱系/哈希失败仍失败关闭。实时采集零匹配仍失败关闭。
- 金额：只用整数分/Decimal。固定高风险线 `60_000_000` 分，固定关注线 `120_000_000` 分；动态线为完整自然月 3/6 月平均日可用余额，或经过版本控制的自定义日期/数值线。
- 勾稽质量：账户、公司、银行、全局差异都必须为 `0` 分；禁止以跨账户抵销、静默去重、浮点/布尔金额、重复余额日或未来 `current` 余额形成假零差。3/6 月动态线须满足 95% 覆盖和 45/90 直接观测；自定义日期范围至少 7 日、覆盖至少 80%。
- 余额日：仅北京周六、周日可承接上一 VALID 余额并计为承接天；缺失工作日一律标 `coverage_gap` 并从动态线覆盖计算排除。未确认的法定假日不擅自承接，宁可停用动态线。
- 发布：Git 原始字节回读 → R2 → 解析 → 零分勾稽 → D1 事务/查询 Oracle → 私库 publication 与 Git bundle → atomic current pointer → OCI 异步冷备。publication 必须是严格 zero-fen canonical record；D1 只允许普通 `INSERT`，绑定参数只发送字符串（整数分为精确十进制），期初空值只使用固定 SQL `NULL`。R2/D1/Git 任一失败不切 pointer；OCI 失败只显示冷备滞后。
- 恢复：只接受 OCI 不可变 restore manifest（同一 publication 的重试复用创建时刻以保持 bytes 稳定）；manifest 必须绑定私库 publication commit。冷备在写 manifest 前、恢复在重建 D1 前，均逐件 hash/类型校验 Git bundle、D1 export、R2 inventory，再在空 bare Git 库实际导入 bundle，并确认 publication 引用的原始 commit、私库 publication commit 的祖先关系和 canonical 文件逐字节一致；重建 D1 并通过查询 Oracle 后才切换 pointer。发布、冷备重试和恢复共用 `publisher_lock`。
- 演练：每月 1 日 05:00 北京时间将最新 immutable publication 恢复至**独立非生产 D1**并运行同一 Query Oracle；配置为空或误指向正式 D1 必须失败关闭。

## 三态与停止条件

人类状态只有：`已更新`、`处理中`、`需处理`。风险标签（正常/关注/高风险/动态偏低/数据不足）不能替代运行状态。

以下任一条件立即保持上一份 VALID publication 并进入 `需处理`：授权、来源三重匹配、附件字节、解析模板、业务日期、勾稽、Git/R2/D1、恢复 Oracle 或配置身份不满足。`UNKNOWN` 永远不能写成 PASS。
