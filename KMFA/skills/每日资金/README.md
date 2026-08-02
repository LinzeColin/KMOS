# KMFA 每日资金

本目录实现 TaskPack `KMFA_每日资金_v0.0.0.1_FINAL_TASKPACK` 的独立云端纵向切片。它在 `KMFA/deploy/coolify/docker-compose.yml` 以 `daily-funds` 服务运行，拥有自己的 DWS 配置、SQLite、命名卷和 cron；不挂载 `skills` 服务的 volume。

## 运行状态

代码可离线验证，但任何生产身份、专用 DWS 群、真实附件类型、D1/R2/OCI 凭据或恢复结果没有证据时都不是 PASS。启动时 `preflight` 会把状态写成 `需处理 / CONFIG_INVALID`，而不是伪造健康。

启动和每日 `runtime-audit` 会在受保护 publication 卷写入脱敏隔离回执：仅包含固定卷挂载、是否发现其他 Skill 进程、配置指纹和 DWS 操作计数；不包含命令参数、挂载来源、群/发送人 ID、URL、附件或凭据。该回执不能替代真实采集/发布验收。

同一卷还会写入 `flow_state.json`，由既有 KMFA `/api/排程健康` 汇总，而不建立第二套健康页面。它只登记运行审计、排程、业务流、自愈和恢复演练状态；worker 不具备现网 source SHA/image digest 证据时会明确保留 `identity_state=UNKNOWN`。

每日 `observer` 会在同一 container deployment 的首份经 D1 Oracle、pointer 与 history 三方比对的 VALID publication 上建立基准。只有此后每个**新的、源侧已确认的业务日期**才计入五日影子对照；重复 cron、重试、回填或同日版本刷新都不会加计。每个对照仅记录零差/覆盖/阈值/取数/重复/备份/恢复的状态码与延迟，不记录金额、账户或原始标识。D1/pointer/history 任一不一致时保持 `需处理`，不虚报观察完成。

## 专用 DWS 云端身份

首次授权在 daily-funds 容器自己的云端 DWS 卷中执行一次 `run_daily_funds.py bootstrap-dws-auth`。该命令只可从受保护的云端交互终端运行，设备码只显示在该终端，绝不写入 cron、状态文件、日志或公开仓；授权成功后 15 分钟采集完全无人值守。`DAILY_FUNDS_DWS_AUTH_BUNDLE_B64` 是可选灾备恢复包（由专用身份执行 `dws auth export --base64` 生成的单行 base64），而非上线前置条件。未配置 `DAILY_FUNDS_DWS_CLIENT_ID` 时，受控 DWS 进程使用其官方默认客户端；如需覆盖，该值只由此切片构造的进程环境注入，不继承宿主或其他 Skill 的覆盖值。DWS v1.0.52 自己管理 profile 布局；群消息命令的 `--group`、`--user`、`--open-dingtalk-id` 互斥，因此运行时只向唯一群请求历史，再逐条以群 ID、稳定发送人 ID 和文档族执行本地三重门禁。`auth status` 或任一门禁失败即关闭。运行容器不接收 AppSecret；AppKey/AppSecret 不能单独建立该登录态，禁止把本机、既有 KMFA 服务或其他 Skill 的 DWS profile 复制进来。

## 原始证据写入边界

唯一 writer 对 `Private-KMDatabase/KMFA/daily_funds` 使用精确非 cone sparse checkout，不落地仓库根或其他业务路径。Git/SSH 仅使用 daily-funds deploy key、临时 `HOME` 和临时 `known_hosts`，拒绝宿主 SSH agent、全局 Git 配置、交互式凭据提示与 force push。每次写入后均从全新 sparse clone 回读原始附件、消息信封、occurrence 和分块重组 manifest；任何 SHA、消息、manifest、路径范围或回读不一致均停止后续 R2/解析/发布。

## 附件能力门

`.csv`、`.txt`、`.xlsx`、`.xlsm` 是**候选解析格式**，不是在代码合成测试通过后就可对生产宣称“已支持”。每份候选附件都必须先由唯一来源链下载、写入并从私有 Git sparse readback 回读；随后同时校验 source SHA、occurrence lineage、后缀、声明 MIME、字节 magic、列模板、业务日期和 parser-open。成功后，受保护 SQLite 才按附件 SHA 写入 values-free `parser_evidence` 回执；该回执与私有 raw manifest 一起构成真实能力证据。

当前执行基线尚未取得目标钉钉群的真实附件字节，因此没有任何生产附件类型可被标记为已实证支持。`.xls`、PDF、图片及 OCR 目前一律 `needs-review`：不会 OCR 猜金额，也不会进入 publication；若将来要启用确定性 OCR，必须先补充目标样本、固定引擎版本、hash/置信度门和回归语料。

## 金额勾稽与阈值质量门

所有金额在解析后只能以整数分进入勾稽；浮点、布尔值、重复账户日期、重复流水主键、非整数上一有效余额和混合业务日期都会 fail-closed。账户、公司、银行及全局差额必须同时为 `0` 分，不能用一个账户的正差抵销另一个账户的负差；历史回填也只能读取**恰好前一业务日**的 VALID 余额，不能借用未来的 `current` 指针。

固定线不可由 Owner UI 修改：`<= 600,000` 元为高风险、`(600,000, 1,200,000]` 元为关注、其余正常。浮动线使用最近 3/6 个完整自然月的日末可用余额；日粒度必须唯一，工作日缺口标 `coverage_gap`，承接日与直接观测分别计数。3/6 月须同时达到 95% 覆盖和 45/90 个直接观测；自定义日期范围至少 7 日并须达到 80% 覆盖。动态线只能增加关注，不得降低固定高风险/关注结论；自定义配置 revision 一旦生效，其业务含义不得在相同 revision 下被改写。

## 发布、镜像与恢复

publication 是严格的零差、双来源、整数分 canonical record。D1 仅是读模型：同一 publication ID 使用普通 `INSERT`，不能用 replace 覆盖；D1 REST 的绑定参数统一为字符串，整数分保持精确十进制，允许为空的期初余额只写固定 SQL `NULL`。R2 先写入原件和 manifest，再逐件回读 bytes/hash/尺寸；D1 projection 与 query Oracle 通过后，还必须成功写入私库 publication 并生成可导入 Git bundle，才会原子替换 `current.json`。

OCI 是最后一跳，故其失败只把 runtime 标为 `LAG`，不会撤销一份已验证的 VALID pointer。恢复 manifest 使用 publication 创建时刻而非每次重试的当前时间，以保证同一恢复输入的 bytes 稳定；冷备重试、发布与恢复共用 `publisher_lock`，避免并发写入或备份陈旧 pointer。恢复前会验证 OCI artifact、R2 inventory、D1 export 的严格结构和 hash，并在全新 bare Git 库实际导入 bundle、确认引用 commit，D1 重建与查询 Oracle 均成功后才允许切换 pointer。

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
  --with 'playwright>=1.50' --with 'httpx<0.28' \
  python KMFA/app/e2e/daily_funds_page_flow.py \
  --out-dir "$(mktemp -d /tmp/kmfa-daily-funds-page-e2e.XXXXXX)"
```

测试只使用合成数据，覆盖整数分边界、3/6 月覆盖门、双事实表、CSV/Excel 的 MIME+magic+lineage、重复/歧义列/公式/日期/标识符质量门、终页 cursor 清除与页二失败不推进高水位、回填空日窗、私有 Git 新 sparse-clone 回读后的不支持附件登记与实时零匹配失败关闭、精确 sparse checkout、重复/同名异字节/超大附件、消息与 manifest 篡改回读失败、D1 故障不移动 pointer 和旧阈值回流扫描。它不替代目标群真实采集验证。

若宿主 Python 尚未安装锁定的 `openpyxl==3.1.5`，XLSX 专项 pytest 会明确跳过；发布前必须在 daily-funds 容器镜像或已安装 `requirements.txt` 的环境中重跑，跳过不构成 XLSX 生产能力证据。

## 回滚

- 应用：从 Coolify 回滚到前一已知 image/source；保留所有 `kmfa-daily-funds-*` named volumes。
- 发布：`current.json` 只在 D1 Oracle 后原子替换；失败时保留上一份 VALID snapshot。
- 数据：以 OCI 不可变 restore manifest 回读 Git bundle、D1 export 和 R2 inventory；逐件 hash 校验后，在空 bare Git 库实际导入 bundle 并确认 publication 所引原始 commit。仅当 D1 重建和查询 Oracle 都成功，才原子替换 `current.json`。Git 私库仍是原始数据权威；禁止删除 Git/R2/OCI/SQLite 卷来“修复”。

恢复运行只接受不可变 publication ID：

```bash
python3 /opt/daily-funds/scripts/run_daily_funds.py restore --publication-id <64位publication_id>
```

每月恢复演练另需在 Coolify 配置与正式库不同的 `DAILY_FUNDS_RESTORE_DRILL_D1_DATABASE_ID`；空值或正式库 ID 会失败关闭。

生产变量键位在 `KMFA/deploy/coolify/.env.example`。值只可由 Coolify Secret 注入，不得放入本仓、命令参数或日志。
