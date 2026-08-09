# KMFA HANDOFF

## ⛔ 先读这一段：Owner 硬覆写压过 sealed taskpack（2026-07-27）

任何接手 agent（含 Codex 交付线）**必须先读 `AGENTS.md` 第 0 节「Owner 硬覆写」**。
裁决顺序：**Owner 会话直接指令 > `AGENTS.md` 第 0 节 > v1.5.2 sealed taskpack > 其余文档**。

已发生的实际冲突，作为判例记录：

- **根路径被误改，Owner 三次投诉。** v1.5.2 写「`/` 是完整匿名 App Shell」，交付线据此删掉了
  `app/frontend/src/KmfaHome.jsx` 并把匿名壳挂到根。Owner 看到后原话：
  「这根本不是我的东西 你不要搞这些恶心人的东西来恶心我」「主页还是没有恢复 我看到这个主页就恶心」。
  **已于 #211 归位**：`/` = KMFA 经营驾驶舱；匿名 App Shell / Walking Skeleton / 匿名反滥用挑战全部迁 `/workspace`。
  合同该条**作废**，不得再以合同为由回退。
- **门禁**：`app/backend/tests/test_root_is_kmfa_home.py`（根必须是驾驶舱 / `/workspace` 必须保留匿名壳 / 两者必须不同）。
  该测试红了**只许改代码，不许改测试**。
- **随迁清单**（改根路径相关内容时必须同步，否则 CI 会在这些地方红）：
  `backend/tests/test_smoke.py`、`test_public_entry_contract.py`、
  `e2e/public_shell_flow.py`、`public_accessibility_index.py`、`walking_skeleton_flow.py`、`abuse_control_flow.py`，
  以及 `frontend/index.html` **和已提交的 `frontend/dist/index.html`**（pytest 服务的是 committed dist，两边必须一致）。

## 每日资金 v0.0.0.1（当前受控实现，2026-08-09 已重取）

### 当前真实状态（T12 后，以此小节为准）

- **2026-08-09 T10 生产复核（当前，优先于本节内较早的“UNKNOWN/未部署”表述）**：最新 `main=a337d8512fdf2b64037e65698eda196e35dfaee2` 已经完整 E2E、Golden verify 与 Coolify deploy 成功。平台部署 `bq93hzgxapmdb3wsniyq126t` 状态为 `finished`，完成于 `2026-08-09T07:12:47Z`；只读身份回执确认运行 source commit 精确为该 SHA、镜像摘要为 `sha256:0231e4b2013ac3c81fcfdba3da6615c87cb1a18c1363242cc710502605c84a5d`，应用读回 `running:healthy`。同一已部署版本的固定 Access history-probe 真正到达独立云端 DWS 身份，但返回 `DWS_PAGE_RECORDS_MISSING`（`FAILED/NOT_MET`、未开始 cursor）；这不是认证、Access 传输或临时资源清理失败——Access bridge transport 为 `OK` 且最终 run-tag 精确清理为 `OK`。按 DF-002，终页没有显式记录列表不能写成“群没有消息”、不能推进 opaque cursor，也不能以时间边界分页接口替代主链。因此本轮原始消息/附件新采集、整数分勾稽、D1、R2、OCI、空环境恢复和资金发布一律为 `NOT_RUN`，绝不写 PASS；只读日志通道是 `HTTP 200` 但未观察到可归类的每日资金事件，也不构成 scheduler 或业务成功。详见 `machine/runs/daily_funds/T10_PRODUCTION_RECONCILE_20260809.json`。

- **2026-08-09 T02 Cloudflare Access 能力审计候选（本地，未提交/未推送/未部署）**：在不打开、输出或复用 `云部署必读.tar.gz` 中 token/密码/私钥/环境文件内容的边界下，`coolify-ops` 新增仅 `main` 手动触发的 `daily-funds-access-audit`。它仅以四个 Cloudflare `GET` 检查 token、Access application、service-token 与 policy 的**读取**能力；任何 API body 均限于 runner 临时文件，公开日志只得到有限分类，退出时删除临时文件。该模式不创建 service token/策略、不调用 history-probe、不读取 DWS/raw，也不触发部署。读能力尚未在云端运行，写权限明确保持 `UNKNOWN_NOT_TESTED`；因此 real target-group probe、opaque cursor transcript 与 AC-002 继续 `NOT_RUN/NOT_MET`。每日资金回归 `130 passed`、后端/API 与安全回归 `30 passed`、无值哨兵、workflow YAML、TaskPack projection 与变异门禁均通过。详见 `machine/runs/daily_funds/T02_CLOUDFLARE_ACCESS_AUDIT_CANDIDATE_20260809.json`；不得将该本地候选误写为 Access 授权、DWS 历史、解析、勾稽、D1/R2/OCI、资金发布或 production identity PASS。

- **2026-08-09 T02 固定 history-probe Access 桥候选（本地，未提交/未推送/未部署）**：在重取 `origin/main=f85764d119e6e9623490edc033e6e73941ee8ecd` 后，确认当前候选 HEAD 是其祖先；主线新增的公开项目成本入口变更没有被反向覆盖。新增 `daily-funds-history-probe-bridge` 仅允许在 `main` 且 Owner GitHub 身份下手动运行：从 Coolify 当前 `KMFA_CLOUDFLARE_ACCESS_AUD` 和 Cloudflare Access apps 回复中严格解析唯一 HTTPS `/ops/*` self-hosted 应用，拒绝根路径通配、非 HTTPS、分页不完整和多匹配。它只创建一个 `60m` service token 与该应用专属的 `non_identity` Service Auth policy，固定同源、无 body 地调用 `/ops/api/daily-funds/history-probe` 一次，最多 15 次/两分钟只读轮询 values-free 回执；`EXIT` trap 精确删除本次 policy 后删除 token，任一创建回执不可精确追踪或删除即 `NEEDS_ATTENTION`。broker/session/API 现有 `cursor_transcript` 只可能为有限枚举，页二终态可证明 `OPAQUE_CURSOR_REUSED_SECOND_PAGE_*`，但 cursor 本体永不保存、返回或写日志。候选回归 `161 passed`、TaskPack projection/变异门禁、Python 编译、workflow YAML、compose profile 解析、秘密格式文件名扫描与 diff check 通过；5 场合成每日资金浏览器 Oracle 均 PASS，production identity 仍未评估。尚未实际 dispatch、未请求 Cloudflare 写权限、未触发 DWS、未读 raw、未部署或推送。因此 Access 写能力、真实目标群 probe、AC-002、来源全量、解析、双事实整数分勾稽、D1/R2/OCI 和资金 publication 均为 `NOT_RUN/NOT_MET`，不得升级为 PASS。详见 `machine/runs/daily_funds/T02_CLOUDFLARE_ACCESS_BRIDGE_CANDIDATE_20260809.json`。

- `machine/runs/daily_funds/semantic_reconcile_end.json` 是 2026-08-03 的历史 T12 证据：当时运行源码匹配 `b8ac56ce75712f9937a209d9ad456b05e91e80e5`，不能代替之后的现网身份。2026-08-09 当前独立容器为 `running/healthy`、镜像 ID `sha256:6925a82a96003e2b634bd2fea1844ade9d75260c7a2eb06c765b8a2554897f87`、启动于 `2026-08-08T20:56:28Z`；该镜像没有 source revision/source URL label。故**当前 production source commit 仍为 `UNKNOWN`**。本轮重取 `origin/main=f85764d119e6e9623490edc033e6e73941ee8ecd`；旧的 `f2b66b63e1991038cffa4aefbbcd52ca3ab02ca5` 仅为下条历史部署记录所对应的 Git 基线，二者都不能冒充运行源码。
- **2026-08-09 T00 生产身份闭环（fail-closed）**：`f2b66b63e1991038cffa4aefbbcd52ca3ab02ca5` 对应当时 GitHub 成功 deploy run `31175690593` 所触发的 Coolify deployment record，经只读查询 run `31277892486` 返回 source commit 同为该 SHA、镜像摘要为 `sha256:6582bd5dd311d06b0bba9984681ac51b05a4c82e7453c58b3f5d3357d7869782`、完成于 `2026-08-07T12:02:39Z`。该轮当时的容器镜像为 `sha256:d5ee75bb326f1a645ab6b156f002c62a5246de0b5e39de0fea3b2414455d0198`，已与 record digest 不同；随后该容器又被替换为上条的 `sha256:6925…` 实例，仍没有直接 deployment record。本轮当前 Git 基线已前进至 `f85764d119e6e9623490edc033e6e73941ee8ecd`，但同样没有 current container ↔ deployment record ↔ source commit 的证据链。因此当前部署 UUID 与运行源码都保持 `UNKNOWN`，不可将 GitHub run 成功或时间相近误写成 production identity PASS。
- **2026-08-09 T02 云端实证（当前）**：使用该容器自己的隔离 DWS 卷做一次无值 30 分钟群历史探针，返回 `AUTH_READY`、`PAGE_OK`、`hasMore=false`，页面消息/目标文档消息/目标附件计数均为 `0`。只读 journal 连续六次 `poll` 相隔 `898–901` 秒；以最新 receipt 为终点的 65 分钟窗口有 `66` 次 `AUTH_OK` 探针、`1` 次 `KEEPALIVE_OK`、`5` 次 `SOURCE_MATCH_ZERO` poll、`0` 个 lock-held、`0` 个 unfinished run、`0` 个 outbox incident、`0` 个窗口末活跃 lease。该证据证明 T02 的独立调度、认证和当前空窗口 fail-closed 行为；它不证明历史全量、目标附件、账户余额、解析、整数分勾稽或资金 publication。该窗口没有触发 R2/D1/OCI 业务写入；后续改动周期性对象操作前必须遵守最新 origin/main 的零付费与 Standard-only 规则。
- **2026-08-09 T03 云端 Sparse Writer 实证（当前 acquired raw 范围）**：当前容器以独立 deploy key 通过 `Private-Database` 的 `main` SSH 连通性检查；在无活跃 `git_writer_lock` 时，只读重新执行受限 sparse clone。先在固定 raw 路径内读取 occurrence/batch 元数据，再用仅包含精确消息信封、occurrence、blob/分块与 batch manifest 的 fresh sparse clone 重开全部当前 raw：`8` 个 occurrence、`7` 个 batch、`10` 个 batch occurrence reference 均完成信封、manifest、重组和 SHA-256 校验，私库 commit 已在容器内验证但未复制进公共记录。journal 有 `7` 条匹配 occurrence，私库有 `1` 条额外 occurrence、无 journal-only 条目；私库是权威，journal 是可重建的非权威优化缓存，故不手工伪造 journal 回执。T03 fixture 回归 `7 passed`（直存/超大分块、重复、同名异字节、篡改、精确 sparse、标准非快进重试与禁强推），任务包 verifier `PASS 24 requirements / 11 tasks / 17 acceptance`。此项证明当前**已取得** raw 的写入/回读完整性；深历史仍受 `DWS_HISTORY_PERMISSION_DENIED` 边界约束，不能扩大为目标群历史全量或双事实/金额 publication PASS。详见 `machine/runs/daily_funds/T03_RAW_SPARSE_READBACK_20260809.json`。
- 新版后的首个真实 `*/15` 历史轮询已在 `2026-08-03T05:45:03Z` 终态返回 `SOURCE_MATCH_ZERO`；它不是 `DWS_AUTH_REQUIRED`、下载失败或部署失败。该结果只证明历史查询完成后未形成可发布的确定性双事实组合，绝不等同于任何资金金额、账户、附件解析或已发布结果。
- **2026-08-09 T04 私库已取得范围复审（当前，只读、无值）**：通过 Private-Database 统一客户端递归普查并逐份临时回读，当前 acquired raw 范围有 `8/8` 结构有效、SHA-256 完整的 occurrence；全部为“资金明细”交易候选、PNG、直存对象，资金账户明细表候选为 `0`。因此该已取得范围内没有可用于整数分勾稽的同日账户余额＋流水事实对。该结果不扩大为全群历史缺失：深历史仍受 `DWS_HISTORY_PERMISSION_DENIED` 限制。本机没有 worker 所需的 `tesseract + chi_sim`，故这一次仅记录 `NOT_RUN_LOCAL_OCR_RUNTIME_UNAVAILABLE`，**不**把它误报为真实附件解析失败。详见 `machine/runs/daily_funds/T04_PRIVATE_RAW_CENSUS_20260809.json`；不得从单一流水图片、历史部署、授权状态或 HTTP 健康推导资金 publication PASS。
- **2026-08-09 T04 云端授权通道复审（当前，无值）**：最新 `origin/main` 上的只读 Coolify 资源清单工作流成功，但仍未给出“当前 daily-funds 容器 ← 镜像 ← 源提交”的证据链。本机现有有效交互式 DWS profile 不得复制为 daily-funds 的云端运行依赖；内嵌浏览器无 KMFA Access 会话，Chrome 在同一路径被客户端规则阻断；GitHub 仓库 Secret **名称**清单没有发现可识别的 Access service-token 成对键。DWS 的精确群授权 `chat chmod` 明确要求宿主 UI 每次确认，模型无法静默绕过；此前同一隔离身份的最小 `chat.message:list` 授权也未解除深历史 `DWS_HISTORY_PERMISSION_DENIED`。在 Owner 明确授权仅限指定群的 `chat.message:list` 后，本机只无值解析到唯一目标并发起一次永久最小授权：命令返回 error、没有成功回执，审计仅给出 API 类错误；宿主 `DINGTALK_DWS_AGENTCODE` bridge 在检查时不存在。后续 no-write dry run 正常返回，但不能证明授权。故授权实际效果为 `UNKNOWN`、没有**确认的**授权或群历史可见性变更；未尝试跨组织全量授权或把群历史可见性改为 `ALL`，未改配置、raw 或排程。对本机 `protected` 目录仅做键名存在性检查，未发现每日资金专用授权包或目标参数键；这不等同于证明其他格式/受控系统不存在资料。指定 Coolify 应用的只读“已设置/为空”回执显示 12 项每日资金必填项均非空，而可选 `DWS client-id` 和恢复授权包为空；公开技能健康的进程状态正常也不能替代 DWS 深历史、解析或资金事实。该结果仅说明当前受控 device-flow 入口尚无已验证的执行通道，不能据此断言任何真实数据、DWS 历史读取、解析、勾稽、部署身份或资金 publication 成功；详见 `machine/runs/daily_funds/T04_DWS_PERMISSION_CHANNEL_AUDIT_20260809.json`。
- **2026-08-09 T04 本机 DWS 来源合同诊断（只读、无值、非运行时来源）**：在 Owner 已授权的唯一逻辑群上，本机 DWS `message list --direction older` 实际返回 `5` 条、`hasMore=true`，但没有可用 `nextCursor`；它只能按 `createTime` 时间边界续页，故不能替代 DF-002 的 opaque-cursor 主链。相同群的 `search-advanced` 在 `7` 日、`360` 日及三类冻结文档族查询下均成功返回终页空结果，未给出消息或 opaque cursor。该不一致表明不得把 `search-advanced` 的空页写成“全历史为空”，也不得把本机时间边界读取接入云端运行。另只读审计了 `_protected`：`48` 份表格候选及一个归档内 `8` 份资金命名工作簿均未被证明为目标群 DWS 来源，扫描表头未得完整双事实 schema；外接盘未挂载。全程没有输出或持久化业务值、消息内容、附件、ID 或凭据，且没有把本机文件作为 runtime 输入。详见 `machine/runs/daily_funds/T04_DWS_PERMISSION_CHANNEL_AUDIT_20260809.json`；T04、来源全量性和资金 publication 继续为 `需处理/NOT_MET`。
- **2026-08-09 DF-002 record-less 终页修复（未提交、未推送、未部署）**：上述真实合同不一致已收敛为采集器缺陷：`search-advanced` 成功终页若只含 `hasMore=false` 而未显式提供记录数组，不能证明目标群历史为空。现在仅显式空数组（`messages/items/records/list/data`）可作为有效零结果；无数组终页稳定失败为 `DWS_PAGE_RECORDS_MISSING`，live poll 写入 `需处理`，既不推进 durable cursor，也不再写成 `SOURCE_MATCH_ZERO`。显式空数组、record-less 失败、运行时不误分类三条回归均通过；每日资金合约 `107 passed`，受影响合约组合 `160 passed`，编译与 diff check 通过。此为本地 fail-closed 合同修复，不构成云端真实历史、附件 parser-open、双事实、金额 publication 或 production identity 证据。详见 `machine/runs/daily_funds/T04_DWS_OPAQUE_CURSOR_RECONCILE_20260809.json`；DF-002 的真实云端验收与 T04/资金 publication 继续为 `需处理/NOT_MET`。
- **2026-08-09 T02 云端控制面实证（只读、无值、未提交/未推送/未部署）**：重取 `origin/main=f85764d…` 后，经仓库既有零秘密 Coolify 清单确认 KMFA 资源为 `running:healthy`，但最近部署查询为 `0`，仍无法绑定当前容器、镜像与源码。一次严格无值容器健康/能力诊断经现有 Coolify execute 路由返回 `HTTP 404`，命令未启动；公共根路由为 `HTTP 200`，而 fixed history-probe 私有路由为 Access 未认证重定向。允许读取的 GitHub Secret 元数据中未识别到 Access service-token 成对键；没有使用本机 DWS profile、浏览器会话、时间边界查询或任何原始消息/附件作为替代。故 real target-group probe、redacted cursor transcript 与 AC-002 仍为 `NOT_RUN/NOT_MET`，而非 `SOURCE_MATCH_ZERO` 或 PASS。详见 `machine/runs/daily_funds/T02_CLOUD_CONTROL_PLANE_AUDIT_20260809.json`；必须先取得受控云端 Access 身份或可验证的固定控制入口，才可运行一次 24 小时、最多两页的 opaque-cursor 探针。
- **2026-08-09 T02 云部署控制面复审（本地候选，未提交/未推送/未部署）**：Owner 提供的 `云部署必读.tar.gz` 只以文件清单和非秘密部署主题读取；其中 token、密码、私钥和环境文件均未打开、输出或复用。仓库既有只读 Coolify 动作确认目标应用健康、每日资金环境**键名**齐备且 `COMPOSE_PROFILES=full`；根页面保持公开 `HTTP 200`，固定 history-probe 路由仍为 Access 未认证重定向，故没有因排障而公开私有资金接口。Archive 同时证实 Coolify Bearer API 的应用列表端点可用，而既有 container-execute 路由的 `404` 是 API 能力边界，不能误写为容器故障。新增未发布的 `coolify-ops` `deployment-identity` 模式：只读取 Coolify Application GET 的四个白名单配置字段，且只有仓库、分支 `main`、应用 UUID 和 40 位 revision 同时匹配时才输出 `VERIFIED_CONFIGURATION_ONLY`；它明确不是运行中 image/container identity Oracle，无法取得真实运行回执时继续 `UNKNOWN`。本地 workflow YAML 与 diff 检查通过；在完整任务包统一上传前不得运行该新模式、不得把配置 revision 写成生产已部署。
- **2026-08-09 T02 无值日志证据通道候选（本地，未提交/未推送/未部署）**：每日资金 cron 现在只输出严格四字段事件（固定 job、三态 outcome、有限白名单机器码）；任何未收录机器码一律输出 `UNCLASSIFIED`，且 runtime 初始化、状态回执或业务执行异常均不再向 cron 输出异常文本/堆栈。Coolify `logs` 模式也不再回显或“脱敏后回显”容器原文，而是在 Actions 临时文件中上限读取后，仅输出 HTTP/传输状态、行数、固定 job/outcome/机器码计数，并删除临时响应。该通道可区分受控 `AUTH_OK` 等白名单状态与普通成功，但不会公开消息、附件、金额、ID、路径、token 或未知 provider 文本。新增泄露哨兵、异常哨兵和格式伪造回归；受影响每日资金/API 合约 `131 passed`，Python 编译、workflow YAML、diff check 与 TaskPack projection（49 requirements / 49 acceptance / 56 phases / 56 tasks）均通过。它只为最终部署后的 15 分钟调度观测准备安全回执，**不是**现网日志、DWS opaque cursor、历史全量、解析、勾稽、资金发布或生产身份的 PASS；详见 `machine/runs/daily_funds/T02_VALUES_FREE_LOG_EVIDENCE_20260809.json`。
- **2026-08-09 T02 构建来源指纹候选（本地，未提交/未推送/未部署）**：Coolify 的构建期 `SOURCE_COMMIT` 仅在严格 40 位小写 SHA 时被烧入 app 与 daily-funds 各自的不可变镜像层；worker 只向共享 projection 写 SHA-256 指纹，app 只比较两侧指纹，UI 永不输出原始 SHA 或指纹。匹配状态固定为 `SOURCE_COMMIT_MATCHED_IMAGE_DIGEST_UNKNOWN`，明确不代表 image digest 或 deployment record 已验证；任一标记缺失、格式错误或无法比较均为 `UNKNOWN`，不升格 PASS。Docker Compose 的三个构建服务均经 `docker compose config`（含 `full`/`lifecycle` profile）解析，受影响每日资金合约/API 共 `127 passed`、Python 编译和 diff 检查通过。现网 raw-compose 模式仍不透明、未部署该候选，故**当前 production source/image/deployment identity 继续为 `UNKNOWN`**；不得把本地机制或配置 SHA 当作运行身份回执。
- **2026-08-09 T04 当前受影响合约回归（本地）**：daily-funds 合约、DWS auth broker 与 history-probe broker 共 `116 passed`；私有 Access / daily-funds API 共 `42 passed`；TaskPack projection `PASS 49 requirements / 49 acceptance / 56 phases`。这些只证明受控实现和 fail-closed 边界未被本轮证据更新破坏，不替代云端 DWS、真实附件 parser-open、双事实整数分勾稽、D1/R2/OCI 或 production identity receipt。
- 私库路径尚无正式 publication；D1/R2/OCI 的真实业务写入、恢复演练和五工作日观察均为 `NOT_RUN`。系统保持“需处理”并保留 fail-closed，不覆盖任何可信结果。
- 本轮代码合约 `101 passed, 1 skipped`；任务包、GitHub 远程 E2E、独立每日资金容器、部署与治理门均通过。这些证明实现、隔离和发布，不替代来源双事实与零分差业务门。
- T04 本地候选（未提交、未推送、未部署）：将“已取得附件但双事实未成立”细分为缺少账户余额、缺少资金流水、或业务日期未成对三种无值状态；在只读 Python 3.12 隔离容器中每日资金合约为 `109 passed`，受影响后端 API 合约为 `17 passed`。该候选不读取或接入其他系统的数据，当前生产 T12 状态保持不变。
- **2026-08-09 T04 cursor 合同复审（未提交、未推送、未部署）**：任务包 DF-002 要求真实 opaque `nextCursor`，而 DWS `message list` 文档仅支持时间边界续页；候选改为 `search-advanced --conversation-ids <configured group>`，仍只查唯一目标群，并保留稳定发送人/文档族本地三重门禁、30 分钟重叠窗、页失败不推进与 stalled cursor fail-closed。离线合约 `105 passed`、后端每日资金 API `17 passed`、编译/diff check 均通过。Coolify UI 显示应用运行于 `f85764d…`，但 daily-funds 容器 image identity 仍为 `UNKNOWN`；应用与服务器两条终端 WebSocket 均在命令执行前失败，故没有实际 DWS 查询、历史可见性/凭据变更、raw 读取或资金写入。详见 `machine/runs/daily_funds/T04_DWS_OPAQUE_CURSOR_RECONCILE_20260809.json`；T04/真实来源链仍是 `需处理`，不得把本地契约通过升级成真实样本、解析或发布 PASS。
- **2026-08-09 T04 受控云端历史探针候选（未提交、未推送、未部署）**：为替代不存在的通用 Coolify 终端执行 API，daily-funds 增加与设备授权 broker 分离的固定 `history-probe` 控制链：仅 Access 私有 `/ops/api/daily-funds/history-probe` 可写入严格 schema；容器只查已配置唯一群的固定 24 小时窗口、最多两页，且只逐字复用 opaque cursor。请求/回执均不含命令、群/发送人 ID、时间范围、消息、附件或金额；探针只写 values-free 状态枚举，网络回执另标 `DWS_HISTORY_PROBE`，不会混作 15 分钟主轮询。它不下载附件、不写 raw、不变更 cron，UI 明示不代表解析、双事实、整数分勾稽、金额或 publication。当前本地合约 `115 passed, 1 skipped`、受影响后端/Access 合约 `42 passed`、5 场合成浏览器 Oracle `PASS`、TaskPack projection `PASS 49/49/56/56`、编译/shell/diff check 均通过；本机 Docker daemon 未启动，容器启动 Oracle 为 `NOT_RUN`。未实际触发 DWS 读取，真实附件、DF-008/DF-022、资金发布与 production identity 均保持 `需处理/UNKNOWN`，不得越级部署或写 PASS。
- T04 真实样本能力审计（只读本地复核，非生产证据）：在与 worker 一致、无网络、只读挂载的 OCR 容器中，当前 4 份私库 PNG 原件均返回 `OCR_HEADER_MAPPING_MISSING`，无一份通过确定性 parser-open；审计只保留总数和失败码，不输出 OCR 文本、金额、文件名、ID、哈希或附件。按 DF-022，该真实格式保持 `NEEDS_REVIEW`，不得通过猜测字段、降置信度或替代数据升级为可发布事实。
- **2026-08-03 T04 云端实证（较新，优先于上两条的“当前”措辞）**：在独立生产容器内，360 日来源普查可读取当前窗口，但深历史连续分页两次停于 `DWS_HISTORY_PERMISSION_DENIED`；最小永久读取授权 `chat.message:list` 已用同一隔离身份成功写入，却未消除该深历史拒绝。故不得把已扫描部分“未见账户余额”扩大为全历史缺失，也不得擅自把群历史可见范围改为 `ALL`。当前 30 分钟历史探针正常。
- 同一云端 T04 受控 archive-only 探针已从目标群取得并经私库 fresh sparse readback 重开 3 份当前来源附件；它们均为“资金明细”PNG，parser `v4` 的真实能力矩阵均为 `NEEDS_REVIEW / OCR_HEADER_MAPPING_MISSING`，且没有有效 publication、D1、R2 或 OCI 业务写入。仅在内存中进行的 OCR 结构检查得到 4 行文本、既有别名在 3 与 8 个分词窗口均识别到 0 个字段；不能据此猜测或硬编码表头模板。DF-008/DF-022 仍未通过；当前无值生产证据仅证明 fail-closed 行为与真实格式未支持。
- 2026-08-03 T04 固定 OCR 多版面实验已拒绝：对 fresh sparse readback 的同 3 份 PNG，PSM `6/11/12` 均为 `OCR_HEADER_MAPPING_MISSING`、parser-open 为 `0/3`。该回退既未改善当前真实格式，又会把单附件最坏处理时间扩大；因此未进入候选或生产 parser，仍保持 `v4` 与 `NEEDS_REVIEW`。本结论不扩大为全量历史缺失或全格式不支持。
- 经 Owner 明确许可执行的基础设施清理只涉及 Docker build cache / 未使用镜像；卷和网络均未选择或清理。
- 下方较早的 T08/T09/T10/T11 条目均为历史记录；凡与本小节或 `machine/runs/daily_funds/semantic_reconcile_end.json` 冲突者，一律失效，不得作为当前生产或真实资金 PASS 依据。

- 当前执行合同：`KMFA_每日资金_v0.0.0.1_FINAL_TASKPACK.zip`，SHA-256 `072ab87c8d48acbd1732f47ff2edc76cf819c4537e60637f6bd5bf39233252b1`。2026-08-02 T08 重取移动基线：`origin/main=2e3621ecf361aa98f2c1dbb5bc3fcdea6b0b2b72`，是当前本地受控候选的祖先，候选尚未上传。此前 Coolify `running:healthy`、deployments 返回 0 条与 container execute 返回 404 都只是历史只读观察；T08 未重取生产身份，故当前 production source/image/deployment identity 仍为 `UNKNOWN`。`f75a1dc6…` 仅是最后一条历史源码记录，不能冒充现网身份，更不得把平台状态写成业务链路 PASS。
- 实现位于 `skills/每日资金/`：独立 Docker/cron/SQLite cursor/inbox/outbox、独立 DWS config/keyring、每 15 分钟 `chat message list --direction older` 的群历史边界轮询、每分钟授权探测、每小时保活、受控回填/OCI 冷备/观察。来源发送人必须以 `senderOpenDingTalkId` 精确校验，禁止将显示名 `sender` 当作 ID；禁止让它调用既有 skills、复用 `kmfa-dws-auth`/`kmfa-dws-keyring`、读取本机或使用 Agent/模型。
- **唯一窄例外（Owner Directive）**：原始消息信封、附件字节、occurrence/batch manifest 与正式 publication 只能由该服务的 single writer 以 `--filter=blob:none --sparse --no-checkout` 写入私有仓 `Private-KMDatabase/KMFA/daily_funds`；不得扩展为其他业务或全库 clone，禁止 force push。其他 KMFA 私有库访问规则不变。
- 资金结果发布门固定为：私库原始字节回读 → R2 热镜像 → 两类事实解析 → 整数分零差勾稽 → D1 query Oracle → 私库 publication → UI pointer；OCI 失败仅标记冷备滞后，不能抹掉前一份 VALID publication。固定线为 600,000/1,200,000 元，旧 500,000/1,000,000 禁止回流。
- 2026-08-02 T01 受控实现：daily-funds 仅构造自己的 `HOME`、`DWS_CONFIG_DIR`、`DWS_KEYCHAIN_DIR` 和 `DWS_DISABLE_KEYCHAIN=1`，不继承 `KMFA_DWS_PROFILE`、`DWS_PROFILE` 或宿主 client 覆盖；DWS v1.0.52 的空隔离 profile 实测创建 `identity.json`，不创建 `app.json`，故删除了先前会使真实授权后仍失败的虚构 `app.json.clientId` 前提。专用 `DAILY_FUNDS_DWS_CLIENT_ID` 只由该受控环境传给 DWS，绝不注入 AppSecret；首次设备授权使用 `--device --no-browser --yes`，且永不由 cron 启动。
- 2026-08-02 配置门校正（本地待完整发布）：DWS 的 `--client-id` 是官方 CLI 的可选覆盖；未配置 `DAILY_FUNDS_DWS_CLIENT_ID` 时，daily-funds 现在会**省略**该环境变量并使用 DWS 官方默认客户端，仍不继承宿主或其他 Skill 的覆盖值。同步门从 16 项必填改为 15 项必填，显式 client ID 与灾备 auth bundle 均为可选项；bootstrap receipt 明示 `official-default`/`configured-override` 而不泄露值。每日资金合约回归为 `57 passed, 1 skipped`，任务包完整性及三类独立 Oracle 均通过；此为离线代码证据，真实来源/云端身份和生产链路仍不得写为 PASS。
- 2026-08-02 实时配置盘点（只读）：Coolify 应用仍报 `running:healthy`，但部署查询返回 `0` 条，故现网 source/image/deployment identity 仍为 `UNKNOWN`。21 个每日资金环境键名均存在，但 15 个运行必填值均为空（只有默认私库地址/分支和 OCI 区域为非空默认值）；GitHub Secret Store 另有 6 个已设置项，尚未能执行完整同步。Cloudflare 账号读取到 4 个 D1 数据库、其中 2 个名称匹配每日资金，R2 bucket 为 0；账号 token 管理 API 返回未授权，不能安全生成 R2 S3 访问密钥。未创建、删除或写入任何云资源。
- 2026-08-02 T02 代码门：按 DWS `search-advanced` 分页合同，仅 `hasMore=true` 时才逐字复用 opaque `nextCursor`；终页即使携带该字段也会清空 durable cursor，下一轮从 30 分钟重叠窗口的 cursor `0` 重查。完整历史扫描确认无候选附件的日窗仅在 `advance_pointer=false` 的受控回填中记为 `BACKFILL_EMPTY_WINDOW` 并推进历史计划；实时采集的零匹配仍返回 `SOURCE_MATCH_ZERO`。回填一次最多 7 日且绝不移动 live pointer；`poll`、`auth_probe`、`keepalive` 的独立锁与 360 分钟 incident 去重均有合成回归覆盖。T02 完成时合约测试为 32 passed；此为离线契约证据，未调用真实群、未形成生产采集 PASS。
- 2026-08-02 T03 代码门：raw writer 从 cone sparse checkout 改为**非 cone 精确路径**，并在 checkout 与暂存前双重断言只可见/只写 `Private-KMDatabase/KMFA/daily_funds`。Git/SSH 运行环境改为 deploy-key-only 的临时 `HOME`/`known_hosts`，显式排除宿主 SSH agent、全局 Git 配置和交互提示；HTTPS remote 不再是允许配置。精确重叠 duplicate 被 canonicalize，同一 occurrence 出现不同字节立即失败；batch ID 不再受输入顺序影响。推送后全新 sparse clone 除附件 SHA 外还逐项回读消息信封、occurrence、路径与分块 manifest；标准 `fetch first` 非快进会 fetch/rebase/retry 一次，force push 被拒绝。合成私库替身完成实际 clone→commit→push→fresh-clone readback，涵盖根目录不落地、重复、同名异字节、超大分块和 message/manifest/byte 篡改；当前合约测试 35 passed。未连接真实私库、未写入真实原始数据，故 AC-005 的生产 commit SHA/实物 manifest 仍为 `UNKNOWN`。
- 2026-08-02 T03 复审补强：`raw/batches/{batch_id}.json` 现以**单个精确 sparse 文件路径**随每个原始批次 clone，并在 fresh clone 中按生成阶段同一 canonical 字节串回读；batch manifest 篡改会 fail-closed。每日资金合约回归为 `75 passed, 1 skipped`，TaskPack projection 校验通过；仍未连接真实私库或写入真实原件，AC-005 所需生产 receipt 继续为 `UNKNOWN`。
- 2026-08-02 T04 代码门：CSV/TXT/XLSX/XLSM 现在只有“候选解析格式”身份。`parse_attachment` 在实际值建模前强制 source SHA=payload、source version、私库 occurrence 路径/消息 hash、后缀、声明 MIME、字节 magic、唯一列模板、文件名/表内业务日期、文本化账号/流水号与整数分金额；重复账户/流水、歧义列、公式缓存、截断/行宽异常都 fail-closed。账户余额与资金流水仍严格输出为两张事实表；只有 sparse readback 后 parser-open 成功的 SHA 才会写入受保护 SQLite `parser_evidence`（format/MIME/magic/parser version，无原始值）。合成回归现为 39 passed、1 skipped（本机默认 Python 无 `openpyxl`）；工作区 Python 3.12 的 `openpyxl 3.1.5` 手工同例已验证正常 XLSX 整数分、公式拒绝和数字账号拒绝。未取得目标群真实附件，故 AC-015/任何生产格式支持声明仍为 `UNKNOWN`，`.xls`、PDF、图片/OCR 保持 `needs-review`，未发布金额。
- 2026-08-02 T04 复审补强：parser 升级为 `v3`，在未有真实模板时拒绝所有多 sheet 工作簿（避免只读 active sheet）及“流入/流出”与“金额/方向”并存的流水（避免静默选择一套金额）。状态投影只显示当前 parser version 的 capability receipt，旧版本记录保留在受保护 journal 作审计，不能继续宣称支持。每日资金合约 `77 passed, 1 skipped`；工作区 Python 3.12 / `openpyxl 3.1.5` 合成 XLSX 单表通过、多表拒绝；受影响 API 合约 `10 passed`。真实目标群样本和生产格式能力仍为 `UNKNOWN`。
- 2026-08-02 T05 代码门：勾稽、余额窗口和 Owner 阈值配置均先验证数据粒度再计算。所有金额、上一有效余额与动态线输入必须为非布尔整数分；同一余额日期、同账户流水主键、混合事实业务日或来源版本均拒绝，内部转账的 adjustment 仍进入冻结算式。账户、公司、银行与全局差异必须同时为 `0`，所以跨账户正负差不能抵销成假零差；历史回填只能使用恰好前一日的 VALID 余额，禁止借用未来 `current` 指针。3/6 完整自然月严格要求 95% 覆盖及 45/90 个直接观测，自定义日期范围至少 7 日且 80% 覆盖；日粒度重复或未分类 carry/gap 会停止动态线。已生效阈值 revision 必须为不可变的 SHA-256 形十六进制版本，同 revision 改写业务含义、损坏 active 配置或错误余额质量均 fail-closed。合约回归为 48 passed、1 skipped（本机默认 Python 缺 `openpyxl`；T05 未改 XLSX 解析），独立任务包边界/阈值 Oracle 通过；这仍是离线代码证据，真实群字节、云端运行与发布链路一律未标 PASS。
- 2026-08-02 T05 复审收尾：`reconcile()` 对直接调用也强制唯一的账户/流水事实对，先保留重复账户/流水的精确诊断，再拒绝不同候选来源的静默混合；若清晰账户键与哈希键同时给出而余额不一致，则拒绝作为期初。`history.json` 的前一日余额必须是带 64 位 publication ID、`VALID`、直接观测且非承接/缺口的记录；`current.json` 回退还必须是恰前一日、零差、带有效 ID 的 canonical publication。`_record_history` 只会写入零差 report 的该类记录。每日资金合约回归为 `80 passed, 1 skipped`，任务包结构校验 `PASS`；这仍只证明本地合成代码门，真实群字节、云端运行与发布链路仍为 `UNKNOWN`。
- 2026-08-02 T06 代码门：D1、R2、OCI 和 `current.json` 的发布交接现在以同一份严格 canonical publication 为锚点；非 `VALID`、非零差、非整数分/布尔金额、错版本/错 hash/错日期或不完整双事实表均在 pointer 前拒绝。D1 只使用普通 `INSERT`（同一 publication ID 冲突即整体失败），REST 绑定把整数分序列化为精确十进制字符串，并把可空期初余额写为固定 SQL `NULL`；R2 每个附件与 manifest 都写后回读、hash/尺寸复核。D1 投影和 query Oracle 后还必须成功写入私库 publication 并生成可导入的 Git bundle，随后才可原子切 pointer。OCI 放在最后：恢复集的时间戳固定为 publication 创建时刻，使同一输入重试字节一致；对象/manifest 均逐件 hash/类型校验，冷备失败只保留 VALID pointer 并标 `LAG`。冷备重试与发布/恢复共用 `publisher_lock`，防止它备份陈旧 pointer 或与新发布并发。恢复会校验 OCI/R2/D1/Git 的严格结构与哈希、在空 bare Git 实际导入 bundle、重建 D1 并运行 Oracle；55 个合约测试通过、1 个明确因本机缺 `openpyxl` 跳过，任务包完整性、storage/reconciliation 两个独立 Oracle 均通过。这仍仅是离线代码和合成恢复证据；真实 D1/R2/OCI 凭据、空环境恢复 transcript、浏览器 Oracle 与生产 pointer 一律仍为 `UNKNOWN`，不得写成 PASS。
- 2026-08-02 T06 复审收尾：OCI restore manifest 现在还绑定私库正式 publication commit；冷备在写 manifest 前、恢复在写 D1 前均会在空 bare Git 中验证原始附件 commit、私库 publication commit 的祖先关系，以及 `Private-KMDatabase/KMFA/daily_funds/publications/<day>/<id>.json` 与 D1 canonical payload 逐字节一致。缺该文件、错误 commit 或旧 manifest 均 fail-closed；冷备重试也必须从 `current.runtime.git_publication_commit_sha` 取到此绑定，否则不备份。canonical publication 与 D1 投影强制恰好一对、彼此不同且完全覆盖账户/流水来源版本；D1 Query Oracle 对布尔/浮点计数或余额拒绝而不强制转换。每日资金合约 `82 passed, 1 skipped`、受影响 API `10 passed`、任务包结构校验 PASS、storage/reconciliation/threshold 三个独立 Oracle PASS（阈值 Oracle 使用 Python 3.12；系统 Python 3.9 不支持任务包的 `str | None` 注解）。本轮仅刷新 Git 基线至 `origin/main=2e3621ec…`，未重取生产运行身份、未写真实 D1/R2/OCI/私库，故这些 live receipt 继续未被本轮证明，保持 `UNKNOWN`。
- 2026-08-02 T07 本地 App/API：`/ops/api/daily-funds/*` 现在只投影结构完整的 canonical publication；业务日期锚定预设窗口，逐分整数、账户/公司/银行汇总、日余额、双事实表、固定 60/120 万与浮动阈值快照必须同时自洽。完整账号、消息/群/附件标识、source/message hash 与 machine code 不进浏览器；仅显示末尾脱敏账户/流水引用和证据版本。无 publication、部分写入、布尔金额或完整性失败会返回 `503`，Owner UI 的人类状态降为“需处理”，OCI 也显示 `UNKNOWN`，不会把旧 status 的“已更新”伪装成可信资金。页面复用既有“钱 → 每日资金”入口，已补齐数据日期/证据版本、当日流入/流出/净变动、断档与覆盖缺口、图例可切换的固定/浮动线、公司/银行/脱敏账户、主要流水、来源完整性及阈值变更的版本/操作者/旧新值/回退版本留痕。组合本地回归（每日资金、smoke、API、skill-health）为 107 passed；前端 `npm run build` 通过。尚未做 T09 的真实浏览器多端 Oracle，也未部署、上传或宣称生产页面/API/资金结果已通过。
- 2026-08-02 T07 复审收尾：App 对共享 `current.json` 现要求精确 snapshot schema、恰好两份不同的 canonical source version，且所有流水只能引用其中单一一份；第三来源、混合流水来源、未知顶层/runtime 字段或普通发布 `OK` 缺少 OCI restore manifest 都会在任何金额进入 API 前降为 `503`。允许的 writer runtime 仅为无 runtime 的 PENDING 原子窗口、带私库 publication commit 的 LAG、带私库 commit + restore manifest 的 OK，或经 restore Oracle 写出的 `restored_at` 形态。每日资金/API/私有 Access/secret-hygiene 回归 `44 passed`，完整每日资金合约 `82 passed, 1 skipped`，当前构建浏览器 Oracle 的四种合成状态/桌面移动端均 PASS，前端 build、任务包投影与 diff check 均 PASS。移动基线复核为 `origin/main=2e3621ec…` 且是本地候选祖先；本轮未重取生产身份、未访问 DWS、未写真实私库/D1/R2/OCI、未部署或推送，因此不新增任何生产 PASS；真实资金 publication/链也没有本轮新证据，保持 `UNKNOWN`。
- 2026-08-02 T08（本轮受控代码门）：`status.json` 现在必须是精确的 `kmfa.daily_funds.status.v1` 无值 schema，并且完整固定排程必须匹配 worker 合同；未知顶层字段、错误日期/时间/ID、非白名单状态或任一排程扩展都会在既有 `/api/排程健康` 中降为 `需处理 / STATUS_INVALID`，不反射共享卷的任意字符串，也没有新增第二健康看板。所有 `*_LOCK_HELD` 现在由 runner 保留为预先登记的 `RUNNING`/跳过回执，不能将 observer、冷备或认证维护的并发占用写成终态“成功”；observer 会将 `PUBLISHER_LOCK_HELD` / `OBSERVER_LOCK_HELD` 明确投影为等待锁。合成验证：每日资金全合约 `87 passed`；daily API、public-entry 与 secret-hygiene `45 passed`；前端 build、Python 编译、diff check 与 KMFA repository TaskPack projection (`49/49 requirements, 56/56 tasks, 49/49 acceptance`) 通过。仍未访问 DWS、真实私库、D1/R2/OCI 或生产，未部署/推送；这些真实证据及五个真实业务日观察继续为 `UNKNOWN`，下一阶段才是 T09 的确定性回归与浏览器 Oracle。
- 2026-08-03 T09（当前未上传本地候选）：浏览器 Oracle 的合成 `status.json` 已与 T08 严格 schema 和完整排程合同对齐；另加入 worker 恢复后精确 `runtime={oci_backup_state, restored_at}` 指针场景。正常、处理中、需处理、恢复后、归档待复核共 5 个浏览器场景均 PASS，且仅请求四个每日资金投影 API、未泄露原始标记。复跑：每日资金全合约 `87 passed`、后端 daily/public-entry/secret-hygiene `45 passed`、前端 build、Python 编译、diff check 与 TaskPack projection (`49/49 requirements, 56/56 tasks, 49/49 acceptance`) 均 PASS。全部是本地合成证据：实际 DWS 群读取、真实附件能力、Git/R2/OCI/D1 空环境恢复、生产身份和五日观察仍为 `UNKNOWN`；本轮未访问/写入真实来源或云资源，未推送、未部署。
- 2026-08-02 T08 代码门：worker 在受保护 publication 卷写入 values-free `flow_state.json`，由既有 `/api/排程健康` 汇总运行审计、排程、业务流、自愈、恢复演练和上线后观察；没有新增健康页面或第二权威。首份经 `D1 Oracle + current pointer + history` 三方一致的 VALID publication 只建立当前 container deployment 的基准，之后仅新的源侧业务日期才会计入 5 日影子对照；同日 cron 重试、回填和重复运行不加计，D1/pointer/history 不一致则 `需处理 / D1_FAILED`。状态接口只投影零差、覆盖、阈值、取数、重复、备份、恢复和延迟等无值状态码，container marker 仅单向摘要，现网 source/image/deployment identity 明确仍为 `UNKNOWN`。合成回归：每日资金合约 `58 passed`，受影响 KMFA API/smoke/contract/skill-health `108 passed`，TaskPack 完整性 `PASS requirements=24 tasks=11 acceptance=17`；未执行真实 DWS、未部署，五个真实业务日观察尚未开始，不能写生产 PASS。
- 2026-08-02 T09 确定性回归与浏览器 Oracle：新增 `app/e2e/daily_funds_page_flow.py`，只生成临时合成 projection 并启动当前构建的 App；三个人类状态（已更新/处理中/需处理）、30 天默认、键盘 7 天切换、自定义区间、SVG 图例/tooltip、深链隐私边界和暗色移动端无横向溢出均 PASS。该 Oracle 还断言每日资金深链只请求四个 `/ops/api/daily-funds/*` 投影，不会先排队请求无关经营接口；为满足此独立性，通用 App 数据改为离开每日资金页后首次按需加载。真实 Chrome 独立检查亦看到已更新状态、脱敏金额、趋势图与 7 天切换。回归：技能合约 `58 passed`，后端 daily/access/secret/abuse/smoke/API/health `134 passed`，根入口/私有边界/daily API `36 passed`，TaskPack `PASS requirements=24 tasks=11 acceptance=17`；前端 build、Python 编译、diff check 均通过。所有证据仅本地合成，生产 source/image/deployment identity、DWS、D1/R2/OCI、空环境恢复和五日观察仍为 `UNKNOWN`/未开始；未推送、未部署，T10 才能进入最新 `origin/main` 的部署与真实环境证据门。
- DWS v1.0.52 合同校正（T02）：`chat message list` 的 `--group`、`--user`、`--open-dingtalk-id` 是互斥会话选择器；daily-funds 正确地只用唯一群作服务端历史读取，再逐条以群 ID、稳定发送人 ID 与文档族完成本地三重门禁。恢复演练专用 D1 现已纳入正常 runtime 配置的必填项，且必须与正式 D1 不同；空值/同值均 fail-closed，普通 preflight/runtime-audit 报 `CONFIG_INVALID`，恢复演练保留 `RESTORE_DRILL_CONFIG_INVALID` 的可操作状态。runtime-audit 仅写脱敏卷/进程/网络计数证据；T01 时 27 项合约测试、Python 编译、shell 语法、Compose 配置、workflow YAML 与 diff 检查均通过，T03 收尾计数为 35（T04 当前计数见上）。Docker daemon 未运行，故本地容器启动/挂载 Oracle 为 `UNKNOWN`，不是 PASS。
- 2026-08-02 通过受控 Cloudflare API 连接器盘点后，已实际创建 `kmfa-daily-funds-primary` 与 `kmfa-daily-funds-restore` 两个独立 APAC D1，以及 `kmfa-daily-funds` APAC Standard R2 桶；两库均为 0 table/8192 bytes 初始状态。R2 回读为 0 个 custom domain 且 managed `r2.dev` disabled。此操作未读取、显示或存储 runtime token/数据库 ID；D1 schema、R2 runtime credential、OCI 冷备以及真实发布仍全部待后续阶段验证。
- 真实控制面复核：`Private-KMDatabase/KMFA/daily_funds` 当前尚不存在（目标写入路径未被此切片使用，**不是**财务源数据缺失）；新建的 `kmfa-daily-funds-sparse-writer-20260802` 私库 deploy key 仍为唯一、可写，且 KMOS 仓库级 `DAILY_FUNDS_GIT_SSH_KEY_B64` Secret 已存在。其余 15 个 T01/T06 必填运行配置在 KMOS **仓库级** Secret 中尚未出现；组织级 Secret/Variable 仍因 token 无 `admin:org` 不可判定。最新只读 Coolify `flags` Action `30718054596`（2026-08-01T20:56Z）对两份应用环境上下文均观察到 9 个现存 daily-funds 项为空：`CLOUDFLARE_API_TOKEN`、`GIT_SSH_KEY_B64`、R2 的 endpoint/access/secret、OCI 的 endpoint/access/secret，以及旧的 `DWS_CLIENT_SECRET`；群、发送人、DWS client、Cloudflare account、D1/restore-D1、R2 bucket、OCI bucket 和可选 auth bundle 没有出现在该 Action 返回的当前环境条目中。该 Action 对所有 `DAILY_FUNDS_*` 条目只显示“已设置/空”而不回显值，因此可确认当时配置不满足 T01，但不能从它推导任何标识或之后同步后的可用性。当前终端的 DWS v1.0.52 `auth status` 也为未认证，且没有本机 `wrangler`/`oci` provisioning CLI；这些只说明本次不能借本机身份绕过独立云端授权，**不是**财务源数据缺失。候选同步流程会在 16 项齐全且回读成功时删除旧 `DWS_CLIENT_SECRET`，绝不重新注入它。
- 2026-08-02 只读 Coolify Action `30717536566` 再次对现网 application execute 返回 HTTP 404，未返回任何进程或挂载数据；因此 `running:healthy` 仍不是 daily-funds worker/cron/卷的生产证据。当前无法闭合的不是“全量业务数据”，而是更新后切片的合法云端 DWS 授权、目标群/发送人实际 source-gate 与 D1/R2/OCI 运行身份的端到端证据；它们不能从本地财务文件、外接盘或公开/私库文件名安全推导，也不得复制既有 DWS profile。尚未上传、部署或声称抓取/解析/备份完成；`BL-DAILY-FUNDS` 六段继续 `blocked_by_input`，页面/status 必须保持“需处理”。

- 2026-08-02 T10 发布前重取证：最新 `origin/main` 与本地 HEAD 仍为 `507fa187…`。Coolify 应用只读清单显示目标应用 `running:healthy`，但最新 deployments 查询返回 `0` 条、受控 container execute 仍返回 HTTP `404`，故当前 source/image/deployment identity 继续是 `UNKNOWN`。两份专用 D1 与一份专用 R2 bucket 已由控制面确认存在且为空；私库 `Private-KMDatabase/KMFA/daily_funds` 目标路径未创建，专用 sparse writer deploy key 元数据存在。已将五项由控制面验证的非秘密 Cloudflare 资源定位值写入 GitHub Secret Store（只记录键名，绝不回显值）。运行所必需的独立 DWS 群/发送人/client、Cloudflare runtime token/R2 access pair 与 OCI endpoint/bucket/access pair 仍未配置；它们不得由既有 Skill、本机登录态或财务文件推导。全量本地发布前门通过：每日资金合约 `58 passed`、受影响 backend `164 passed`、前端 build、合成浏览器 Oracle、TaskPack `24/24 requirements + 11/11 tasks + 17/17 acceptance` 与 diff check 均通过。`machine/runs/daily_funds/semantic_reconcile_end.json` 已撤销历史过期的生产 PASS 叙述，重写为本次 `T10_PRE_DEPLOY` 证据；尚未推送、部署或宣称真实资金链/恢复/五日观察通过。

- 2026-08-02 T10 部署与生产复核：已直接推送 `main`（无分支、无 PR），运行代码提交为 `ea96a2b9eeb0bf8bade0a63e37494636eda262fd`；远程 app E2E、Golden deploy 均成功，Coolify 部署日志确认 source commit 精确匹配该提交。生产根路径和 `/healthz` 为 HTTP 200，受保护 `/ops` 与每日资金 API 正确返回 Cloudflare Access 302。受控 Chrome 的原生桥、扩展和本机浏览器均健康，但对生产域请求被浏览器规则拦截，未获得已认证 UI receipt；不要将边缘健康或本地合成 UI Oracle 写成真实数据 UI PASS。部署后再次调用 Coolify 只读 execute 仍为 HTTP 404，故 worker/cron/卷的实时 receipt 继续为 UNKNOWN。每日资金专用 secret 同步 Action 在写入 Coolify 前 fail-closed：独立群/发送人/DWS client、Cloudflare runtime token、R2 access pair 与 OCI endpoint/bucket/access pair 均缺；未发生 Coolify 配置变更。它们是云端执行身份与目标参数，不是全量历史财务源数据，严禁用本机历史归档、既有 Skill 或其他 DWS profile 补造。status 继续为“需处理 / CONFIG_INVALID”，私库 raw、D1/R2/OCI、真实金额、恢复演练和五业务日观察均未开始。详见 `machine/runs/daily_funds/semantic_reconcile_end.json`。

- 2026-08-02 T11 受控来源与异地备份补齐（未推送、未部署）：移动基线已刷新为 `origin/main=bb51b9f0f54b3e78ce9c0b6b267f15565761342c`，当前本地候选仅基于该基线。通过私有历史归档的完整 SHA-256 校验与不回显结构扫描，发现唯一一组同时满足“资金账户明细/资金流水明细/资金明细”关键词、实际附件、单一群 ID、单一发送人 ID 的候选（48 份附件、39 个消息日期）；两个 ID 仅写入 KMOS 仓库级 `DAILY_FUNDS_GROUP_ID`、`DAILY_FUNDS_SENDER_ID` Secret，未进入代码、日志或本文件。每日资金 12 项运行必填 Secret 的**键名**现齐全。归档无 DWS profile、keyring、token 或可迁移认证包，且旧 Skill/profile 仍禁止复用。
- T11 OCI：用已验证的正式 OCI 身份新建专用、无公网、版本控制开启的冷备 bucket；创建仅限该 bucket 的 HTTPS `AnyObjectReadWrite` PAR，直接写入 `DAILY_FUNDS_OCI_PAR_URL` Secret。运行代码新增 PAR ObjectStore（旧 S3/HMAC 仅保留显式兼容，二者混用失败关闭）；真实合成 Git bundle/D1 export/R2 inventory 经 PAR 写入、逐件回读、restore manifest 验证和逻辑清理均成功，旧 PAR 已撤销。此为 OCI transport/restore 证据，不是目标群或真实金额恢复 PASS。
- T11 回归：每日资金契约 `60 passed, 1 skipped`（跳过项为无 XLSX runtime 的明确环境跳过）、Python 编译、Compose 渲染、workflow YAML、diff check，以及封存 TaskPack `24 requirements / 11 tasks / 17 acceptance` 和 threshold/reconciliation/storage 三个 Oracle 全部通过。仍不可把此写成生产数据 PASS：当前唯一未闭合的硬门是**新建 daily-funds 独立云端 DWS 身份的一次官方授权**。本机 DWS 为未认证，归档无可用授权，Coolify execute 仍为 404；在独立云端容器中完成授权并得到真实 `auth status`/目标群历史回执前，不推送候选、不同步 Coolify、不部署，也不声明原始写入、D1/R2/OCI 真实业务链、恢复演练或五日观察已通过。

## v1.5.2 公开软件交付线（2026-07-26）

- 当前唯一执行基线：用户提供的 `KMFA_Product_Design_Taskpack_v1.5.2.zip`，SHA-256 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`；产品/runtime 版本仍为 `0.1.4-one-time-github-main-upload`，两者禁止混用。
- 最近完成的唯一执行单元：**S05 whole-stage review + publication repair（P5.1-P5.4）**，见 `machine/runs/S05_STAGE_REVIEW.md`。本地 phase chain `c2c0b889 → 4c3d5ae0 → 34eac93f → e2409eec` 已与 reviewed `origin/main=3f7cfd61…` 整合；10 个跨 phase/origin/runner/edge findings 全部修复，open/waived risk 均为 `0`。首个 publication SHA `56ea0935…` 在 Ubuntu P5.4 暴露 `0700/root` bind-state 权限差异且未部署；容器 helper 修复后的 `afbd6cb6…` 全门禁和部署成功，但生产只读浏览器 Oracle 又发现 Cloudflare 自动注入 Insights beacon，CSP 正确阻断却产生 console error。第二修复保留严格 CSP，并只给 HTML 增加 `no-transform`，hold/private 仍为 `private, no-store`，JSON cache 语义不变，Browser Oracle 同时拒绝 beacon markup。second corrective local image `sha256:2a071ceb…0ec4cc9d` 上 focused public-entry `28/28`、full backend `225/225`、公共 Shell 与 Chromium/Firefox/WebKit a11y/index 全 PASS；前一 corrective image 上 P5.1 `14`、P5.2 `19`、P5.3 `28 crash + 2 timeout`、P5.4、恢复/secret/abuse 全 PASS。该结果是 second corrective guarded candidate，不是生产 PostgreSQL/S3/backup/lifecycle cutover 或生产 RPO/RTO 证明。
- P4.3 secret hygiene 继续有效且由 Stage Review 加固：浏览器 API 不返回 access token 明文，改用 host-only `__Secure-kmfa_session`（Secure/HttpOnly/SameSite=Strict/API Path/1h）；仅 Cookie 写操作强制 scheme/host 同源，legacy bearer 在自身到期前兼容读写；服务端显式撤销与恢复 secret 轮换原子撤销旧 session。全局边界拒绝 raw/percent/double-encoded capability URL path/query/Referer，Walking API validation error 只返回静态 code；session/device Cookie、服务端与浏览器 console 均脱敏，raw access log 关闭、CSP `connect-src 'self'` 且无第三方分析/错误 SDK。最终镜像复跑 request URL `43`、performance URL `38`、error sample `8`、walking no-store response `18`、日志/状态/cache/screenshot，全部 canary 命中 `0`、foreign request `0`；轮换与显式撤销旧 session 重放均 `404`。
- P3.3 可访问与索引边界继续有效：canonical 根页有 share metadata、键盘/屏幕阅读标签和 fail-closed 搜索边界；生产 `KMFA_PUBLIC_INDEXING_ENABLED=0` 保持 hold，根页 `200` 且 header+meta noindex、robots 全拒绝、sitemap 为空。S03 rollout 后匿名根页/Access 私有路径 Oracle 已通过，未把 hold 状态伪报为搜索引擎收录；显式索引晋级仍须另走隐私 Oracle，见 `machine/runs/S03_P33_ACCESSIBILITY_INDEX.md`。
- P3.2 App Shell 继续有效：根路径只加载公共 bundle，项目/上传/搜索/进度/报告/帮助 `6/6` 可操作且按真实接线状态呈现；公共搜索只查本页说明，不读用户数据。JavaScript disabled 与 `/healthz` degraded 均有明确状态；`KMFA_PUBLIC_SHELL_ENABLED=0` 可回退到六入口稳定静态壳。完整旧经营 App 位于受守卫的 `/ops/app`。P3.4 只贯通一个项目/文件/恢复切片，AC-PUB-002 的浏览→创建→处理→保存→恢复→搜索→下载→导出完整匿名产品旅程仍未完成。
- P3.1 根域/私有边界继续有效：`/` GET/HEAD 直接 `200`；`/ui*` 单跳 `308 → /`；公共浅健康不泄露 facts；OpenAPI、Swagger、深健康和既有 `/api*` 均进入 `/ops*`/私有运维面，生产 compose 默认启用 Cloudflare Access JWT 源站验签且缺配置 fail-closed。见 `machine/runs/S03_P31_EDGE_ROUTING.md`。
- P2.4 validator 现在封存 Canonical、AC、DAG、Release、Trace 五个 source，正向输出 `49 Requirements / 49 AC / 14 Stages / 56 Phases / 56 Tasks / 49 trace rows / 6 promotion gates`、0 errors/warnings；缺 AC、闭合循环、第八治理文件、`EVIDENCE/` 四类变异仍 `4/4` 非零且 source unchanged `5/5`。`machine/VALIDATION_REPORT.md`、renderer、authority/navigation 与 CI 已同步修正。
- P2.3 的 sealed `acceptance_contract.yaml`、`task_graph.yaml`、`traceability.csv` 继续与任务包原字节一致（SHA-256 分别为 `1f07bd14…bc1`、`a9753e7c…306`、`ca369627…727`）；focused gate 保持 49 需求↔49 唯一主 AC、AC 必填字段 `735/735`、断链 `0`，`05_执行与验收.md` 继续机械投影 AC/Oracle/Task/Test/Artifact/Owner。见 `machine/runs/S02_P23_TRACEABILITY.md`。
- P2.2 的七文件渲染继续有效：14 决策、49 需求、49 指标及 49 个 Task/Owner seed 全覆盖；无 `human/` 副本、无第八权威文档。连续两次渲染哈希一致；受控手改 `00` 与临时第八文件均被精确拒绝并恢复/移除；术语排序漂移和 shared-checker 跨项目误约束均已修复，见 `machine/runs/S02_P22_HUMAN_PLANE.md`。
- P2.1 的 sealed `machine/canonical_facts.yaml` 继续保持任务包原字节，SHA-256 `5ae070cb4105e83eec0c05b3771759e550a67f1241708810f0b4430300198552`；唯一 writer 仍为 `WR-TASKPACK-PUBLISHER`，P2.2 只读渲染。
- S05 whole-stage review 已闭合；包含本 HANDOFF 的合并提交是唯一 guarded upload 单元。只有该提交成为 `origin/main`、远端 CI 与自动部署/source-image identity 全部闭合后，published Stage 才从 `5/14` 变为 `6/14`；任一失败都仍停留 S05 publication repair。S03/S04 rollout 的根域 Everyone Bypass、`/api*`/`/ops*` owner-only Access、源站 403 fail-closed、Walking Skeleton 与 abuse Gate 继续是前置条件；完整匿名旅程、生产 DB/object/backup 切换、明确删除启用、G2 与 GA 仍未标绿。
- P1.1 的 12 FAQ/12 反证、P1.2 的 5 类用户/JTBD、10 步匿名旅程、P0 `12/12` + P1 `7/7`、`4 Objectives / 12 KRs`，以及 P1.3 的重大能力 `8/8`、低/基/高情景、敏感性、机会成本和 Kill 继续作为 P1.4 的冻结输入。工程总量沿用 task-level `58.5–106 engineer-days`，运行成本只作可重算公式；真实采用率、收益、账户账单、流量、容量与单点 ROI 均未伪造。2026-07-23 已只读刷新官方 R2 pricing/limits，实施和预算 Gate 仍须按当日账户与官方资料重取。
- 整个 S00 已完成复审、修复并上传：P0.1-P0.4、`AC-GOV-001/002/004`、S00 Stage Gate 与 `G0 Authority` 整体复验，4 个 findings 全部修复、open finding `0`，见 `machine/runs/S00_STAGE_REVIEW.md`；发布后的 `main` 为 `6a9f2163d00adc000e965bf6bffbc0ed59283d7a`。S01 中间 phase 只作本地 commit，不上传 GitHub。
- S01 发布已闭合：远端 `main=283a24080bce6590e902c77bb1fea20b19b990a7`，Dual-Plane run `29931423572` PASS，且该 SHA 没有 deploy run。published main 必须从 GitHub ref 实时读取，deployment source 必须从 Coolify manifest 实时读取，二者不得混用。
- S04 发布时已闭合的生产身份：source `031bf9923b92d8d2ac4a690a39476825940ba587`、image `sha256:cef4592801cafa05b152a06638d7c0ce105c6b9fb4ebac6aba5700d62acf2a9c`、Coolify deployment `r8pvdppp781azpor35cu8ol2`、completed `2026-07-23T13:39:32.000000Z`；deploy run `30011560083`、governance `30011559631`、当时 read-only query `30045297714` 均 SUCCESS，root/index/Walking/private-boundary Oracle PASS。本 P5.4 run 未查询或改变现网 current identity，因此该 tuple 只作最近闭合发布记录，不冒充 2026-07-26 当前现网；P5.4 local image `sha256:f85a90f…74fb13` 不是生产 digest。
- Owner 提供的 `fb31e8e... / sha256:0b09ca... / qcq1q8m... / 2026-07-20T21:50:47Z` 已由 query run `29916243207` 原样复核，作为上一部署的回滚/溯源记录保留。收口前发现 `main` 已前进并自动产生新部署，因此没有把旧 tuple 冒充当前身份。
- v1.5 恢复 bundle `1ee7fb111` 仍是不可变兜底，SHA-256 `2d0b516f...` 且 verify PASS；另发现并核验历史仓公开 recovery ref 已前进至 `268acce792`，仍为 PARTIAL 且 S24 路径为 0。受保护 full-sweep 的 1060 路径已互斥分类为 `Adopt 239 / Redo 750 / Discard 71 / Conflict 0 / 未分类 0`；`Redo` 只表示按当前 v1.5.2 Task/AC 重做所需行为，不重建旧文件。未 replay、merge、force-push 或复制私有元数据。
- 旧业务 `machine/facts` 的 S05/A0/Q4/BLK-001 与 v1.5.2 delivery Canonical Facts 分属不同 namespace：前者继续约束正式财务结论，后者由 sealed taskpack 的 `WR-TASKPACK-PUBLISHER` 唯一写入；14 个旧 facts 未改写，七文件只由 `WR-RENDER-HUMAN` 全量生成。旧运维快照中的 Access/私有入口步骤已明确标为历史取证，不得当作 v1.5.2 发布指令。
- P0.4/S00 的失败边界已局部刷新：生产当前仍以 `kmfa-app-state` 的 SQLite+私有文件 adapter 服务；S05 候选已在合成隔离环境证明共享 PostgreSQL、私有 S3-compatible 对象层、DB/object/outbox 可恢复一致性、full/incremental/tombstone、精确 provider version 清除、空环境恢复和明确删除生命周期，但未做生产 cutover。不得把 synthetic RPO/RTO、MinIO native versioning、same-host backup 或 named volume replacement 伪报为生产长期持久化/DR PASS。快速回滚使用 schema `4` 当前 binary，同时置 `KMFA_LIFECYCLE_MODE=paused` 与 `KMFA_CONSISTENCY_STATE_MODE=paused`，保留 S04/P4.1 dual reader、DB/对象/备份配置和所有卷并 forward-fix；禁止旧 binary/schema downgrade、删卷/对象/备份、撤既有 reader 凭据、改 verifier 或 recovery replay。
- 当前总进度：Task `24/56`；S05 phase `4/4` + whole-stage review/publication repair 已完成；发布状态在 second corrective SHA 远端闭合前仍为 Stage `5/14`，闭合后为 `6/14`。Stage findings `10/10` resolved、open/accepted risk `0/0`；full backend `225/225`；durability 与 S03/S04 public/recovery/secret/abuse 回归全 PASS。G2 仍需 S06/S07，GA 未通过。
- 远端 S05 CI、自动部署与 source/image/deployment identity 闭合后，下一个新 run 只可执行 **S06 / P6.1 / T-S06-01**；若远端任一门禁失败，只可留在 S05 publication repair。不得提前切生产 PostgreSQL/S3/backup/lifecycle、启用生产删除，或删除 `kmfa-app-state`、`kmfa-postgres-data`、`kmfa-object-data`、任何 backup、既有 verifier/session/object 或 v1.5 恢复资产。

下列既有交接主体更新时间：2026-07-17（Australia/Sydney）

## 接管入口

- 唯一 GitHub 源码：`git@github.com:LinzeColin/KMOS.git`，branch `main`，项目目录 `KMFA/`。
- 推荐稳定 checkout：`/Users/linzezhang/Documents/Codex/KMOS`；其他机器可放在任意路径，脚本应从 `git rev-parse --show-toplevel` 发现仓库根。
- 旧 `/Users/linzezhang/CodexProject` 是事故隔离中的历史 checkout，push URL 已禁用；不要解锁、不要从其他旧 clone 绕过。
- 迁移前 736 行 handoff 保存在 `machine/legacy/HANDOFF_PRE_KMOS_20260717.md`，仅供历史取证，不是当前执行合同。

## 当前项目状态（2026-07-17 深夜刷新：打通线执行态）

- 机器事实源：`machine/facts/`；人类入口：`文档/`（渲染产物，勿手写）。
- **打通线（DT1-DT9）**：canonical roadmap 见 `docs/governance/roadmap.yaml`；DT1 收官、DT4 吸收、DT5 主体实弹运转、DT8 门禁引擎试点、DT9 前置与基座齐备、DT6 App 可部署。
- **真实数据**：53 原始文件入 `KMOS/KMDatabase/data`（内容寻址）；私有派生层十一表 215,109 行（`KMFA/tools/` 全链零重建可复现，实证过；板表族首件税负率明细已入 `_staging.tax_composition`）。
- **证据档导航**：`stage_artifacts/索引.md`（打通线 76 档一表可查，断言表 `evidence_ref` 直跳）。
- **下批数据**：需求单已定稿 `docs/governance/下批数据需求单.md`（12 项，具体到导出选项；拉齐任一项即可机械复跑对应断言）。
- **对账**：《一致性证明与差异分析报告》第 1-7 号已交付（`stage_artifacts/DT5_DATA0019_report_no*`）；断言表 `metadata/quality/assertions.jsonl` 30 条（closed 族 19，证据链 30/30 零悬空）；**八切面零候选**（回款/开票/凭证/费用/税费/借款/材料/个人借支——每项闭案或挂单一数据依赖）——回款 7/11 月 0 分差、开票集团口径差 3 分、五账套凭证 0 不平、费用轴两大账套全窗口收口（湖北开明 2025-01..10 全解释含 07..10 段 8/8 根码 0 分差、武汉开明 01..10 十根码差额逐分归因零残留）、税费轴 36/39 格 0 分差、借款轴流量级闭合（窗口内新贷 0 分差+存量反推期初自洽，期初系统性缺失具名）、材料轴 117/190 凭证匹配（映射表 `metadata/quality/material_subject_map.json` 定稿）；对账基础设施 `tools/recon_common.py`（凭证号/科目双写法归一）；声明式门禁 `tools/gate_runner.py` 三门全绿。
- 旧口径提示：`4/18 / S05-P3-T1 / Q4 / D / NO_GO` 为 v1.5 业务线（S 系）状态，受 BLK-001 门控，与 DT 线并行存在；当前数据质量按 Q3（机器候选结构化）执行。
- Owner blocker `BLK-001`：8 份 PDF + 1 份电子表格约 273 行字段尚未逐条确认——**A 级报告的唯一人门**。未解决前，不得把结构校验解释为业务完成。
- **云端**：skills 运行基座与 App 部署件在 `KMFA/deploy/skills-runtime/` 与 `KMFA/app/`；等 Oracle ARM 实例 + `dws auth login --device` 一次 + Codex 应用停用 6 条旧排程（路线 B 已拍板）。实例日 runbook 见 deploy README。

## Repo 内 Skills（10 个，统一位于 `KMFA/skills/`）

1. `skills/每日工作检查/`（id `daily_routine_check_skill`）：钉钉工作检查，OneDrive `DWS_Outputs.zip` 只读输入。
2. `skills/资金周报/`（id `fund-weekly-analysis-skill`）：资金与税费周报，真实证据、OCR 复核和 no-simulation 门禁。
3. `skills/钉钉考勤/`（id `kmfa-dingtalk-attendance-skill`）：考勤晨晚提醒与官方报表 final reconciliation。
4. `skills/经营月报/`（id `mgmt-monthly-report-skill`）：七输入槽位到 Excel/PDF 的月报流程。
5. `skills/上游归档/`（id `dingtalk-dws-archive-skill`）：DWS 全文件归档 public-safe 源码、模板和验证器。
6. `skills/工资发放标准/`（id `gongzi-fafang-biaozhun`）：工资发放表模板复用与金额分校验。
7. `skills/红圈主合同/`（id `hongquan-main-contract-dws`）：红圈主合同导出、下载与归档。
8. `skills/信息费更新/`（id `info-fee-update`）：信息费申请表与历史明细更新。
9. `skills/项目成本表/`（id `project-cost-table-skill`）：项目成本输入门禁、双口径计算与工作簿生成。
10. `skills/每日资金/`（id `daily-funds-skill`）：独立 DWS 历史轮询、私有 Git 原件、D1/R2/OCI 与私有资金界面。

## 私有恢复点

agent 的私有恢复入口也在 GitHub：

```text
PRIVATE repo: LinzeColin/KMFA-Private-Runtime
Release:      cleanup-handoff-20260717
Manifest:     manifests/release_manifest.json
```

Release 包含 3 个经 SHA-256 校验的资产：旧 KMFA 开发/运行现场、DWS 全文件归档项目、6 张 Codex automation 的本机状态与旧 DWS skill 备份。PRIVATE 仓库的 `HANDOFF.md` 是恢复合同；任何 agent 都必须先确认仓库仍为 PRIVATE，再按 manifest 校验 size/hash。凭证、token、cookie、browser session、Keychain 导出和 `.env*` 明确不上传，恢复后重新认证。

OneDrive 同时保留冗余副本，但不是 agent 通信或唯一恢复入口：

```text
/Users/linzezhang/Library/CloudStorage/OneDrive-Personal/KMFA/cleanup_handoff_20260717/
├── dws_archive_project/
└── private_runtime/
    ├── daily_routine_check/
    ├── dingtalk_attendance/
    └── fund_weekly_analysis/
```

该目录包含真实运行状态；DWS SQLite 已在源端和备份端执行 `PRAGMA quick_check`。OneDrive 位置、文件数和校验结果已同步写入 public KMOS 与 private runtime repo，不能只依赖本机路径沟通。

旧脏工作区未直接合并到当前主线；其完整 KMFA 覆盖层已私有保存并通过 checksum 零差异验证：

```text
cleanup_handoff_20260717/legacy_worktrees/CodexProject_KMFA_overlay/
cleanup_handoff_20260717/legacy_worktrees/CodexProject-KMFA-S19_overlay/
```

考勤自然 automation 使用 immutable runtime：

```text
$HOME/Library/Application Support/Codex/KMFA/attendance-production/current
```

仓库状态只作诊断，不得替代 immutable release fingerprint 门禁。

## 本机接管结果

- 首轮公开接管提交：`64a4d7083be08ed6ef9169e585306464c2d06ec5`，已推送至 `origin/main`。
- Codex 已登记稳定项目 `/Users/linzezhang/Documents/Codex/KMOS`；6 张既有 automation 均已原位迁移到该项目，未创建重复任务。
- `kmfa` 10:35、`kmfa-3` 20:05、`kmfa-4` 13:35/19:05、`kmfa-dws` 每日 11:00、DWS auth 每 4 小时 20 分的计划保持不变；`kmfa-5` 已恢复技能合同规定的周一和周六 11:00。
- attendance immutable release 已原子切换至 fingerprint `eeb36084adcd39507597f5df6b273de4e8f1b18212234e2226eb3edb9d71255a`，source commit 为上述首轮接管提交；晨晚 live prompt 均通过只读一致性校验。
- 6 个本机 skill 名称均指向稳定 KMOS checkout；历史独立 DWS skill 已私有备份后由兼容别名接管。
- 未运行 live DWS、未发送钉钉消息；真实业务数据只进入 PRIVATE GitHub Release，public KMOS 无原始业务数据。

## 清理保护清单

public/private GitHub、OneDrive 冗余快照和本机 automation cwd 已完成校验。大清理时仍不得删除或改为 public：

- 推荐稳定 checkout `/Users/linzezhang/Documents/Codex/KMOS`；
- 上述 OneDrive `cleanup_handoff_20260717/`；
- OneDrive `DWS_Outputs.zip`、`DWS_Archive/` 与既有 `KMFA/` 私有目录；
- attendance immutable runtime；
- `~/.codex/automations/`、`~/.codex/skills/`、DWS 认证 profile 与自动化 memory/state；
- PRIVATE `LinzeColin/KMFA-Private-Runtime` 及 Release `cleanup-handoff-20260717`；
- `~/Downloads/KMFA_MetaData` 若后续重新出现则先只读核对；本次盘点该路径不存在。

旧 checkout 的 KMFA 内容已有私有覆盖层恢复点；删除旧 checkout 前仍应再次确认上述保护项存在且稳定 checkout 与 `origin/main` parity。本文不授权删除保护项。

## 验证与停止条件

最小接管验证：

```bash
git status --short --branch
git fetch origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
python3 KMFA/machine/tools/check_dual_plane_ci.py --root . --projects KMFA --require-projects
python3 KMFA/skills/每日工作检查/tools/validate_skill_package.py
python3 KMFA/skills/资金周报/tools/validate_taskpack.py
python3 KMFA/skills/钉钉考勤/tools/validate_skill_package.py
python3 KMFA/skills/经营月报/tools/validate_skill_package.py
python3 KMFA/skills/上游归档/tools/validate_skill_package.py
python3 KMFA/skills/项目成本表/scripts/validate_skill_package.py
```

遇到 secret/private 命中、远端非预期提交、非 `main`、SQLite 损坏、OneDrive 快照不完整或 automation 指向已删除路径时立即停止，不得伪造接管完成。
