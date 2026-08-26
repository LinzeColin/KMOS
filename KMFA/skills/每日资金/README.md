# KMFA 每日资金

本目录实现 TaskPack `KMFA_每日资金_v0.0.0.1_FINAL_TASKPACK` 的独立云端纵向切片。它在 `KMFA/deploy/coolify/docker-compose.yml` 以 `daily-funds` 服务运行，拥有自己的 DWS 配置、SQLite、命名卷和 cron；不挂载 `skills` 服务的 volume。

## 运行状态

代码可离线验证，但任何生产身份、专用 DWS 群、真实附件类型、D1/R2/OCI 凭据或恢复结果没有证据时都不是 PASS。启动时 `preflight` 会把状态写成 `需处理 / CONFIG_INVALID`，而不是伪造健康。

启动和每日 `runtime-audit` 会在受保护 publication 卷写入脱敏隔离回执：仅包含固定卷挂载、是否发现其他 Skill 进程、配置指纹和 DWS 操作计数；不包含命令参数、挂载来源、群/发送人 ID、URL、附件或凭据。该回执不能替代真实采集/发布验收。

同一卷还会写入 `flow_state.json`，由既有 KMFA `/api/排程健康` 汇总，而不建立第二套健康页面。它只登记运行审计、排程、业务流、自愈和恢复演练状态；公开 `/public-api/技能健康` 仅额外投影最近一次历史轮询和历史回填的脱敏回执（状态、时间、退出码），不投影业务日期、金额、来源、附件或标识。worker 不具备现网 source SHA/image digest 证据时会明确保留 `identity_state=UNKNOWN`。

首次历史回填在云端原生 cron 的 `05,20,35,50` 分钟错峰运行，每批最多处理 7 个自然日，按从当前日向前 360 天的持久 planner 推进。它使用独立于实时 `poll_lock` 的长租约，因此慢速历史读取只会让下一批回填等待，不会阻塞 15 分钟当前日采集；原始 Git 写仍严格复用单一 `git_writer_lock`。

每日 `05:20` 的 `raw-archive-audit` 只在该云端容器中读取已取得范围内的私库原件：先按 Git tree 名称受限枚举，再以精确 sparse 路径重新打开消息信封、occurrence、批次 manifest 和字节 SHA，最后才运行现有离线解析器。它不请求 DWS、不写 Git/R2/D1/OCI、不变更 `current.json`，也不把原件、ID、金额或文件名写入日志和页面。其结果仅更新 values-free 附件能力回执；即使全部 parser-open，也不能代表全量群历史、同日双事实、整数分勾稽或资金发布已通过。

当旧版本的历史 planner 已完成、但新一次精确群历史重放发现私库缺少 occurrence 时，可在同一云端容器运行受控 `raw-coverage-repair`。它只比较 360 天内的脱敏 occurrence identity，下载并写入缺失项，随后从 fresh sparse clone 回读全量覆盖；不移动 `current.json`，不写 D1/R2/OCI，也不将文件名、消息、标识或金额送往日志。它是归档完整性修复，不是金额发布或绕过双事实勾稽。

只有 `raw-coverage-repair` 留下与当前私库提交一致的 360 天覆盖回执后，受控 `raw-fact-replay` 才能运行。它重新从该私库提交打开每个候选的账户余额和资金流水事实；每个业务日必须恰好一对、重新解析、逐分勾稽及 R2/D1/OCI 发布链全部通过。历史日按日期顺序写入，只有最后一个已验证业务日可以切换 `current.json`；缺失、歧义或无法解析的日期保持需处理并在 values-free 回执中计数，绝不补造金额。

每 6 小时 `r2-guard` 使用 Cloudflare 控制面只读接口核验全账户 bucket 默认均为 Standard、无 IA 生命周期且 IA 指标为零；同时以 31 天、每 15 分钟全部为新对象的最坏情况验证 Class A/Class B/存储均低于 Standard 免费额度 40%。只写入不含 bucket、对象或金额的回执。任何一项为未知、过期或失败时，R2 镜像、冷备前的 R2 readback 与 publication 都会保持 fail-closed；新对象也显式写入 `STANDARD`，同 SHA 键绝不覆盖旧镜像字节。

每日 `observer` 会在同一 container deployment 的首份经 D1 Oracle、pointer 与 history 三方比对的 VALID publication 上建立基准。只有此后每个**新的、源侧已确认的业务日期**才计入五日影子对照；重复 cron、重试、回填或同日版本刷新都不会加计。每个对照仅记录零差/覆盖/阈值/取数/重复/备份/恢复的状态码与延迟，不记录金额、账户或原始标识。D1/pointer/history 任一不一致时保持 `需处理`，不虚报观察完成。

## 专用 DWS 云端身份

首次授权只在 daily-funds 容器自己的云端 DWS 卷中完成。首选从 Cloudflare Access 保护的 KMFA “每日资金”页发起一次固定设备授权：页面只能开始或取消一次 DWS device flow，不能传入命令、群 ID、profile、token 或原始输入；同容器 broker 只把短时确认链接和确认码回传给该私有页，撤销、完成或过期即清除，绝不写入 cron、状态、日志、Git 或公开面。若该私有入口临时不可用，才在同一容器的受保护云端终端运行 `run_daily_funds.py bootstrap-dws-auth`；禁止在本机或其他 Skill 中授权。授权成功后 15 分钟采集完全无人值守。`DAILY_FUNDS_DWS_AUTH_BUNDLE_B64` 是可选灾备恢复包（由专用身份执行 `dws auth export --base64` 生成的单行 base64），而非上线前置条件。未配置 `DAILY_FUNDS_DWS_CLIENT_ID` 时，受控 DWS 进程使用其官方默认客户端；如需覆盖，该值只由此切片构造的进程环境注入，不继承宿主或其他 Skill 的覆盖值。固定 DWS v1.0.58-beta.1 先用唯一群、`group` 会话类型和部署时固定的 `DAILY_FUNDS_SENDER_IDS` 允许列表读取历史；允许列表最多 12 个，不从群成员动态发现，`DAILY_FUNDS_SENDER_ID` 必须是其中主发送人。若该接口终页缺少显式记录列表，才用官方 `+chat-messages --group <同一唯一群> --start ... --end ... --order asc --page-all` 读取完整窗口。后者的 provider 毫秒 cursor 仅由 DWS 内部延续，只有无失败、无截断、`complete=true`、`hasMore=false` 才允许进入后续原始附件流程；它不是按投影时间自行分页。两条路径的回包都逐条以群 ID、配置的稳定发送人 ID 和文档族执行本地三重门禁。`auth status` 或任一门禁失败即关闭。运行容器不接收 AppSecret；AppKey/AppSecret 不能单独建立该登录态，禁止把本机、既有 KMFA 服务或其他 Skill 的 DWS profile 复制进来。

当没有通用容器终端时，Access 私有页还可向同一容器发起一次严格固定的“云端历史读取验证”：先查配置好的唯一群、固定最近 24 小时窗口、最多两页，并逐字复用第一次返回的 opaque cursor。若该页缺失显式记录列表，才以官方 `+chat-messages` 对同一群、同一窗口和两页上限验证；其 provider 毫秒 cursor 由 DWS 内部延续，绝不从投影消息时间重建。控制请求不包含命令、群/发送人 ID、cursor、时间范围、消息、附件或金额；回应只显示状态与 continuation 枚举，不能下载附件或写 raw。它只是云端 DWS 读取路径的诊断，不替代 15 分钟主采集，也不表示附件解析、双事实、勾稽、金额或 publication 已通过。

若该私有入口的 Cloudflare Access 身份尚未证明可用，`coolify-ops` 的手动 `daily-funds-access-audit` 只执行四个 Cloudflare `GET`（token 验证、Access application、service-token、policy 列表）。各 API 响应只在 Actions 临时文件内解析，日志只得到有限分类；它不会创建 service token 或 policy，不会调用 DWS/历史探针，也不会输出账户、应用、策略、令牌、消息或金额。该预检即使全部为 `OK`，也只说明读能力已验证；创建受控服务身份所需的写权限仍必须保持 `UNKNOWN_NOT_TESTED`，不能据此宣称任何真实历史或资金结果。

在代码完成统一主线发布后，`coolify-ops` 的历史探针与恢复 bridge 都使用各自的**精确控制子路径**。若该子路径的 self-hosted Access 应用尚不存在，bridge 只会创建对应的固定声明；随后必须重新解析唯一、精确 KMFA 主机与精确控制路径的应用。根路径、`/ops/*`、混合主机、分页不完整或多匹配都会拒绝运行。公开仪表盘的 Bypass 选择器明确排除两个控制子路径，因此公开 `/ops` 页面不会把恢复或探针接口公开。bridge 在创建短时身份前要求子应用的 policy 列表为空，拒绝任何持久 Allow、Bypass 或未知策略；随后 runner 创建一个 `60m` service token 与只绑定该子应用的 `non_identity` Service Auth policy，以固定同源、无 body 的 `POST` 启动历史探针或完整恢复链。退出时只删除本次创建的 policy 和 token；任一资源无法精确追踪或删除即 `NEEDS_ATTENTION`，绝不写 PASS。历史探针回执会枚举 `OPAQUE_CURSOR_REUSED_SECOND_PAGE_*` 或 `GROUP_HISTORY_V2_PROVIDER_MILLISECOND_CURSOR_REUSED_SECOND_PAGE_*`，只证明相应的页间控制流，**不保存或展示 cursor 本体**。恢复 bridge 只有在 `RECOVERY_PUBLISHED` 或 `RECOVERY_PUBLISHED_NEEDS_REVIEW` 时才视为 publication 已完成；它和探针均不展示账户、应用、策略、令牌、消息、金额或原始文件。

## 原始证据写入边界

唯一 writer 对 `Private-KMDatabase/KMFA/daily_funds` 使用精确非 cone sparse checkout，不落地仓库根或其他业务路径。Git/SSH 仅使用 daily-funds deploy key、临时 `HOME` 和临时 `known_hosts`，拒绝宿主 SSH agent、全局 Git 配置、交互式凭据提示与 force push。每次写入后均从全新 sparse clone 回读原始附件、消息信封、occurrence 和分块重组 manifest；任何 SHA、消息、manifest、路径范围或回读不一致均停止后续 R2/解析/发布。

## 附件能力门

`.csv`、`.txt`、`.xls`、`.xlsx`、`.xlsm` 是**候选解析格式**，不是在代码合成测试通过后就可对生产宣称“已支持”。每份候选附件都必须先由唯一来源链下载、写入并从私有 Git sparse readback 回读；随后同时校验 source SHA、occurrence lineage、后缀、声明 MIME、字节 magic、列模板、业务日期和 parser-open。旧版 `.xls` 额外要求完整 OLE 容器、唯一普通工作表、无宏流、无 BIFF 公式及未加密；任一条件不成立即拒绝，不读取缓存公式值。成功后，受保护 SQLite 才按附件 SHA 写入 values-free `parser_evidence` 回执；该回执与私有 raw manifest 一起构成真实能力证据。

当前已取得私库原件的范围与目标群完整历史仍须分别证明；在云端 `raw-archive-audit` 对真实字节完成 parser-open 前，没有任何附件类型可被标记为已实证支持。图片与扫描 PDF 只有在显式启用的离线确定性 Tesseract 回退路径中才会尝试打开；它不是模型/API，也不会猜测金额。该路径同时要求来源谱系、MIME/magic、关键字段至少 0.98 置信度、两个不同业务日的同版式校准，以及后续同版式私有 Git readback 成功；任一条件未满足即保持 `needs-review`，不能进入 publication。

在真实样本冻结多工作表模板前，任何多 sheet 工作簿都会以 `XLSX_WORKSHEET_AMBIGUOUS` 停止；同一流水同时携带“流入/流出”与“金额/方向”两套金额编码时以 `TRANSACTION_AMOUNT_MAPPING_AMBIGUOUS` 停止。解析规则升级会更换 parser version，旧版本的 capability receipt 仅保留审计用途，不再投影为当前支持能力，直到原始字节在新版本下重新 parser-open。

## 已采集收支流水观察（非可用资金）

当真实 `资金明细` 图片具备完整的日期、转出、收入和银行表头，或能唯一确认日期与收支类别锚点、两列重复右对齐金额边界时，`raw-archive-audit` 才会以离线确定性 OCR 逐行重算转出/收入。若表头文字本身不可读，只有显式 `资金明细` 来源可进入更窄的固定表格回退：至少两行同日日期、唯一可见“合计”行、**恰好两列**稳定右对齐金额边界和独立 OCR 结果完全一致必须同时成立；出现第三个金额列时，几何关系不足以辨认流入/流出，必须保持需复核。若原图只在表头/版式/OCR 门失败，且可证明存在长网格线，才会以固定阈值删除该网格线并固定倍率放大；预处理后的两个独立 OCR 模式仍须给出完全相同的日期与收支合计，且继续执行未放宽的字段、逐行、0.98 置信度、单一业务日和唯一“合计”逐分勾稽。任何金额、日期、字段身份、逐行或合计失败都不得触发该图像修复。只有当前范围内**每一份**候选图片都通过、业务日不重复、且至少覆盖两个业务日，才写入只含日期、流入、流出、净流动和脱敏覆盖计数的 `cashflow_observation.json`。

它是为页面提供的“已采集收支流水”图层，不是账户余额、不是可用资金、不能进入阈值、风险判断、D1/R2/OCI formal publication 或 `current.json`。任一图片解析失败、合计不一致、重复业务日或覆盖不足都会原子清空该图层金额并保持 `NEEDS_REVIEW`；系统不会用它补造余额或部分拼接图表。

## 待付款请示观察（非账户余额）

财务群内的日度待付款请示截图通过同一条精确归档链进入独立观察器。固定标题、业务日期、总合计标签与总额必须由三种离线 OCR 分割一致识别；任何已确认标题但后续字段不一致的图片都会使本次观察保持 `NEEDS_REVIEW`，不显示金额。同一业务日存在多份完整日表时，只有更晚收到的那份可以覆盖；时间相同的重复日表会保持待复核。

页面只显示业务日期、待付款请示总额和脱敏覆盖计数，并明确将它与“账户余额”“已完成付款”“可用资金”和“风险阈值”分离。它提供每日待付款趋势，不能成为正式余额 publication 的替代品。

## 金额勾稽与阈值质量门

所有金额在解析后只能以整数分进入勾稽；浮点、布尔值、重复账户日期、重复流水主键、非整数上一有效余额和混合业务日期都会 fail-closed。每次勾稽只接受唯一的一对账户/流水事实，不能混合多个候选来源。账户、公司、银行及全局差额必须同时为 `0` 分，不能用一个账户的正差抵销另一个账户的负差；历史回填也只能读取**恰好前一业务日**、带有效 publication ID、零差且直接观测的 VALID 余额，不能借用未来的 `current` 指针或承接/缺口记录。

固定线不可由 Owner UI 修改：`<= 600,000` 元为高风险、`(600,000, 1,200,000]` 元为关注、其余正常。浮动线使用最近 3/6 个完整自然月的日末可用余额；日粒度必须唯一，工作日缺口标 `coverage_gap`，承接日与直接观测分别计数。3/6 月须同时达到 95% 覆盖和 45/90 个直接观测；自定义日期范围至少 7 日并须达到 80% 覆盖。动态线只能增加关注，不得降低固定高风险/关注结论；自定义配置 revision 一旦生效，其业务含义不得在相同 revision 下被改写。

## 发布、镜像与恢复

publication 是严格的零差、**唯一一对不同来源版本**、整数分 canonical record。D1 仅是读模型：同一 publication ID 使用普通 `INSERT`，不能用 replace 覆盖；D1 REST 的绑定参数统一为字符串，整数分保持精确十进制，允许为空的期初余额只写固定 SQL `NULL`。R2 先写入原件和 manifest，再逐件回读 bytes/hash/尺寸；同 SHA 键先回读，完全一致才复用，不一致绝不覆盖。D1 projection 与 query Oracle 通过后，还必须成功写入私库 publication 并生成可导入 Git bundle，才会原子替换 `current.json`。

OCI 是最后一跳，故其失败只把 runtime 标为 `LAG`，不会撤销一份已验证的 VALID pointer。恢复 manifest 使用 publication 创建时刻而非每次重试的当前时间，以保证同一恢复输入的 bytes 稳定，并绑定私库 publication commit；冷备在写入该 manifest 前即会验证 OCI artifact、R2 inventory、D1 export 的严格结构和 hash，并在全新 bare Git 库实际导入 bundle、确认原始 commit 与其后私库 publication commit 的祖先关系及 canonical publication 文件逐字节一致。冷备重试、发布与恢复共用 `publisher_lock`，避免并发写入或备份陈旧 pointer；恢复会重复同一验证，且仅在 D1 重建与查询 Oracle 均成功后才允许切换 pointer。

生产 OCI 入口使用专用 bucket 的 HTTPS `AnyObjectReadWrite` PAR；运行容器只持有这一个 bucket 范围内的回读能力，不持有用户级 HMAC。旧 S3/HMAC 仅保留为显式迁移/恢复兼容路径，和 PAR 同时出现即失败关闭，避免凭据范围不明确。

这些都是离线合同实现；尚无真实 D1/R2/OCI 身份、空环境恢复 transcript 或浏览器 Oracle 时，运行状态仍必须是 `UNKNOWN`/`需处理`，不能宣称生产恢复已通过。

## 本地无数据验证

```bash
python3 -m pytest -q KMFA/skills/每日资金/tests/test_daily_funds_contract.py
python3 KMFA/tools/check_baseline_slices.py
```

页面的 T09 浏览器 Oracle 另以当前已构建前端和临时合成 projection 启动本地 App；它覆盖三态、默认/自定义范围、键盘切换、趋势图图例/tooltip、移动端布局与脱敏边界，**不**连接真实 DWS、D1、R2、OCI、Git 或生产身份：

```bash
uv run --with-requirements KMFA/app/backend/requirements.txt \
  --with 'playwright>=1.50' --with 'httpx2==2.9.1' \
  python KMFA/app/e2e/daily_funds_page_flow.py \
  --out-dir "$(mktemp -d /tmp/kmfa-daily-funds-page-e2e.XXXXXX)"
```

测试只使用合成数据，覆盖整数分边界、3/6 月覆盖门、双事实表、CSV/Excel 的 MIME+magic+lineage、重复/歧义列/公式/日期/标识符质量门、终页 cursor 清除与页二失败不推进高水位、回填空日窗、私有 Git 新 sparse-clone 回读后的不支持附件登记与实时零匹配失败关闭、精确 sparse checkout、重复/同名异字节/超大附件、消息与 manifest 篡改回读失败、唯一双来源投影、D1 故障不移动 pointer、OCI bundle 缺少私库 publication 时不生成 restore manifest，以及旧阈值回流扫描。它不替代目标群真实采集验证。

若宿主 Python 尚未安装锁定的 `openpyxl==3.1.5`，XLSX 专项 pytest 会明确跳过；发布前必须在 daily-funds 容器镜像或已安装 `requirements.txt` 的环境中重跑，跳过不构成 XLSX 生产能力证据。

## 回滚

- 应用：从 Coolify 回滚到前一已知 image/source；保留所有 `kmfa-daily-funds-*` named volumes。
- 发布：`current.json` 只在 D1 Oracle 后原子替换；失败时保留上一份 VALID snapshot。
- 数据：以 OCI 不可变 restore manifest 回读 Git bundle、D1 export 和 R2 inventory；逐件 hash 校验后，在空 bare Git 库实际导入 bundle 并确认 publication 所引原始 commit、私库 publication commit 及 canonical 文件字节一致。仅当 D1 重建和查询 Oracle 都成功，才原子替换 `current.json`。Git 私库仍是原始数据权威；禁止删除 Git/R2/OCI/SQLite 卷来“修复”。

恢复运行只接受不可变 publication ID：

```bash
python3 /opt/daily-funds/scripts/run_daily_funds.py restore --publication-id <64位publication_id>
```

每月恢复演练另需在 Coolify 配置与正式库不同的 `DAILY_FUNDS_RESTORE_DRILL_D1_DATABASE_ID`；空值或正式库 ID 会失败关闭。

生产变量键位在 `KMFA/deploy/coolify/.env.example`。值只可由 Coolify Secret 注入，不得放入本仓、命令参数或日志。
