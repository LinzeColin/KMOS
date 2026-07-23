# KMFA v1.5.2 S04 STAGE REVIEW

> Stage `S04 匿名工作区、恢复与反滥用`
> Reviewed: `2026-07-23T13:00:36Z`
> Phase candidate parent: `12c7111d43daf12d325c1dd4bf4d50579f10dc3d`
> Status: **REVIEW CORRECTION PASS — FIRST GATE BLOCKED SAFELY；ONE CORRECTIVE UPLOAD AUTHORIZED**

本文是不超过 64 KiB 的 public-safe compact receipt。它把 P4.1–P4.4、`R/AC-WS-001..004`、
S04 objective/deliverable/gate、恢复资产、发布门禁和回滚作为一个整体重放，并记录复审发现与最小修复。
它不保存 workspace ID、恢复码、session/device Cookie、proof、真实 IP、用户文件、平台凭据或私有业务
内容，也不把单节点 named volume 冒充 S05 的长期持久化、备份恢复或 GA。

## 1. Frozen review subject

| Subject | Verified value / boundary |
|---|---|
| Authorized taskpack | v1.5.2 ZIP SHA-256 `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`；ZIP test PASS；official projection `49 R / 49 AC / 14 Stages / 56 Phases / 56 Tasks` |
| Canonical S04 contract | Objective：不登录仍可长期找回自己的数据并控制滥用；Deliverable：高熵匿名身份、恢复码/文件、短时会话、限额与挑战；Gate：跨设备恢复 `100%`、secret 泄露 `0`、攻击负载不拖垮正常用户 |
| Published baseline before review | fresh fetch `LinzeColin/KMOS:main@ce9c27da2c6518fec2c740897c788bd63069678f`；local candidate `0 behind / 4 ahead` |
| Local phase chain | `b7985d77` P4.1 → `8c9b9e10` P4.2 → `08641fb3` P4.3 → `12c7111d` P4.4；连续、无 merge |
| Review-time runtime image | `sha256:6a37c2cc3a8e72f9491183456d7c5ae590c6fc2bda8a927ce5ded107102763de`；由 corrective runtime source 构建 |
| Review boundary | 复审、修复并授权 S04 fast-forward；首次同 SHA Gate 若暴露新 finding，只允许一个窄范围 corrective commit，不 rerun 红 SHA；未进入 S05，未手工修改 Cloudflare/Coolify/WAF，未读写生产用户状态 |

Receipt 所在最终 Git commit 不能自引用自己的 SHA，Dockerfile 又会复制仓库文档，因此上表 image 是
review-time runtime-frozen image，不冒充 push 后 CI/Coolify 制品。最终 `source_commit / image digest /
deployment UUID / completed_at` 必须在发布后从 Git ref、同 SHA workflow 与部署 manifest 分别只读核对。

## 2. Task / Acceptance replay

| Task / AC | Final-source evidence | Result |
|---|---|---|
| `T-S04-01 / AC-WS-001` | 独立数据库分别完成 `10,000` sequential 与 `256` concurrent creates；ID/secret/token collision/error `0`；新 ID 128-bit，secret/token 256-bit；SQLite/WAL/SHM capability plaintext hit `0`；S03 16-char ID verifier 继续可读 | **PASS** |
| `T-S04-02 / AC-WS-002` | 新浏览器在重启后以 recovery file 恢复，再轮换 secret；随后用新 code 恢复；project/progress/object hash 一致率 `100%`；六类错误/截断/撤销材料授权成功 `0`；不可邮箱找回警示在全部入口可见 | **PASS** |
| `T-S04-03 / AC-WS-003` | Secure/HttpOnly/SameSite=Strict/host-only/API-path/1h session；显式撤销与轮换后旧 session replay 均 `404`；URL path/query、Referer、console、error、cache、log、state、audit、screenshot canary hit `0`；字段校验 `422` 固定错误码且不回显输入 | **PASS** |
| `T-S04-04 / AC-WS-004` | 正常 `20` actors / `100` requests 误伤 `0`；暴力恢复、proof replay/cross-actor、上传/导出洪泛、六路慢上传、`602` actor 低速分布式攻击绕过 `0`；global limit 后无 challenge bypass；资源行数/对象增长有界 | **PASS** |

S04 不要求、也没有证明 S05 的生产数据库、对象存储、默认不自动到期、明确删除或 backup/restore。
因此本 Stage 可通过自身 Gate，但 `AC-PUB-002` 完整匿名旅程、`AC-DATA-*`、`G2` 与 GA 继续 **OPEN /
NOT PASS**。

## 3. Whole-stage Gate

| Gate dimension | Whole-stage assertion | Result |
|---|---|---|
| Anonymous ownership boundary | workspace locator 与恢复 capability 分离；服务器只存 verifier；浏览器不用账号、邮箱、OAuth 或 localStorage 作为权威源 | **PASS** |
| Cross-device recovery | 重启、跨浏览器、file/code、rotation、revocation、negative matrix 与 object hash 在同一最终镜像闭环 | **PASS（early adapter）** |
| Secret hygiene | 正常旅程和负向错误面全部 canary `0`；session 可撤销；device/session/恢复材料不进入 compact evidence | **PASS** |
| Abuse / normal-user isolation | 六路慢上传仍在进行时，独立 actor 的 `/` 为 `200 / 5.14ms`，正常 workspace create 为 `201 / 24.60ms`；并发 admitted/blocked=`2/4`，释放后恢复 `200` | **PASS** |
| Bounded state | attack run 最终 `35` workspaces、`4` artifacts、control counters `430`、active leases `0`；合成敏感值与 capability state/log hits `0` | **PASS（bounded synthetic load）** |
| Rollback / compatibility | Flag `1→0→1` 时 row/object hash 不变；S03 16-char rows forward-compatible；新 22-char rows 明确禁止回滚到 pre-P4.1 reader | **PASS WITH EXPLICIT BINARY FLOOR** |
| CI promotion safety | deploy caller 同 SHA 先执行 full backend、governance、Docker、四类 E2E，再允许 Coolify；actionlint clean；发布后 source query mandatory | **PASS（post-upload execution pending）** |

结论：**S04 implementation + whole-stage review PASS**，允许当前 run non-force fast-forward upload，
并允许既有自动 workflow 在同 SHA Gate 全绿后部署。没有授权手工改 Cloudflare、Coolify 环境变量、WAF
或生产数据；live deployment identity 与 production Oracle 在实际发布前仍是 PENDING。

## 4. Whole-stage findings and fixes

| Finding | Severity | Evidence / impact | Minimal fix | Closure |
|---|---|---|---|---|
| `F-S04-001` phase receipt aggregated separate databases | Medium | P4.1 的 `10,000` sequential 与 `256` concurrent tests 使用独立 function-scoped stores，却把最终 rows 写成 `10,256` | receipt 改为两份独立 row/invariant 结果，不再制造不存在的聚合数据库 | **RESOLVED** |
| `F-S04-002` validation error echoed recovery input | High | FastAPI/Pydantic 默认 `422` body 含完整 overlong recovery canary，直接违反错误面 secret=0 | Walking API 增加静态 `request_validation_failed` handler；unit + final-image E2E 扫描回显 | **RESOLVED** |
| `F-S04-003` URL path was outside capability guard | High | middleware 只查 query/Referer；raw、percent 与 double-encoded path 未显式 fail closed | 同时检查 decoded `path` 与 `raw_path`；三类 path 负测均 `400` 静态错误 | **RESOLVED** |
| `F-S04-004` denied attempts did not consume rate budget | High | invalid/replayed proof、actor challenge 与 concurrency denial 在 increment 前返回，可无限写控制面并绕开 global attempt bound | 每个已评估 attempt 在任一 actor/proof/concurrency decision 前原子计入全部窗口；full global bucket 不再增长；确定性 64+1 测试锁定 | **RESOLVED** |
| `F-S04-005` attack isolation was only sampled after attack | Medium | 原 TEST-WS-004 在慢上传线程结束后才检查 root，不能证明攻击进行中正常写入可用 | barrier 保持六个连接活跃时，独立 actor 同步验证 root `200` 与 create `201`、各 `<1s` | **RESOLVED** |
| `F-S04-006` runtime contract/docs overstated or mislabeled | Medium | legacy bearer 实际在到期前兼容读写；同源约束只针对 Cookie mutation；invalid mode 实际阻断全部 guarded operations | 状态键、单测、前端与 runbook 改为真实语义；invalid-mode test 覆盖 create/read/mutation | **RESOLVED** |
| `F-S04-007` device cookie was absent from process redaction | Medium | process-wide regex 只覆盖 session Cookie，P4.4 `__Host-kmfa_device` 可能进入异常日志 | 统一 redaction 两个 Cookie 名；device canary log test 锁定 plaintext hit `0` | **RESOLVED** |
| `F-S04-008` rollback overclaimed pre-P4.1 compatibility | High | S03 reader 只接受 16-char ID；首次签发 22-char ID 后降到旧 binary 会保留数据但暂时使新 workspace 不可恢复 | receipt/app/runbook 明确 binary floor：保留 S04/P4.1 dual reader，先 Flag off/紧急策略，再 roll forward；禁止删卷/改 verifier/replay | **RESOLVED** |
| `F-S04-009` machine navigation stopped before Stage review | Low | `machine/README.md` 只导航到 P4.4，后续接管易遗漏 whole-stage correction | 精确加入 S04 Stage Review 导航，不新增权威文件 | **RESOLVED** |
| `F-S04-010` abuse Oracle scenarios shared one global rate window | High | first upload run `30009779537` 在 deploy 前阻断：fast Linux runner 让前序 upload flood 的 `7` 次上传与 concurrency flood 的 `6` 次尝试落入同一 `10s` global upload bucket；F-S04-004 要求所有拒绝也计费，因此恢复请求合法命中 burst=`12`，不是 limiter/lease 故障 | 不放宽生产策略；concurrency 场景先对齐到全新 policy window，断言 `2` admitted、`4` blocked 且拒绝原因只能是 `concurrency`；另以独立 control DB 轮询 persistent lease 必须在 `5s` 内归零后再验证恢复 | **RESOLVED** |
| `F-S04-011` cold-start connections raced persistent schema/WAL initialization | High | corrective full regression 的 32 线程/256 workspace test 在 `_open_store()` 报 `database is locked`：每个冷启动连接都重复执行 `PRAGMA journal_mode=WAL` 与 schema DDL，可能把合法匿名创建转成 `503` | 进程内按 resolved DB path 加锁并只初始化一次 WAL/schema，先设置 `busy_timeout`；FK/FULL sync 仍逐连接启用，配置失败必关连接。首批 32 请求增加 barrier，独立冷启动 `10/10`、full suite `157/157` | **RESOLVED** |

Final finding count：`total=11 / resolved=11 / accepted-risk=0 / open=0`。S05 durability、S06 malware/
resumable upload、S07 download/export 与真实生产流量观察是已排期合同，不伪装成本 Stage finding 已解决。

## 5. Identity, recovery and data boundary

| Namespace | Review-time verified value | Meaning |
|---|---|---|
| `taskpack.version / sha256` | `1.5.2 / 310885168...cffb` | 产品设计执行 seal；不等于 runtime version |
| `product.version` | `0.1.4-one-time-github-main-upload` | 当前 `KMFA/VERSION` |
| `source.published_main_sha` | pre-upload `ce9c27da2c6518fec2c740897c788bd63069678f` | GitHub baseline，不是本地 candidate |
| `review.runtime_image` | `sha256:6a37c2cc...763de` | 本地 corrective 运行代码 Oracle；不是生产 digest |
| `deployment.review_time` | source `ce9c27da...` / image `sha256:bafa6a96...4e60c` / deployment `amffqczj7p2o22yz3en1or13` / completed `2026-07-23T09:42:56Z` | review 前最近只读生产身份；S04 发布后必须重新查询 |

- v1.5 recovery ZIP SHA-256 `8066b65dc96f4368b54e2a053e6726a2bf194806d67b1bdbcacb669a457ef2c1`，
  内嵌 bundle SHA-256 `2d0b516fe7d578061e97dfca874745bcf3a0bf504b0f80976ad3aa21e01077ed`。
  ZIP test PASS；隔离 bare repo fetch 公开 recovery ref 后 `git bundle verify` PASS，bundle head
  `1ee7fb111075225dc39039263d2681a0c0acd155`、prerequisite
  `97edb1b8750d49409a4f9372a784d4772fea258e`。
- 未把 recovery ref/object 导入 KMOS；未 replay、merge、cherry-pick、迁移、重写或删除旧 rows、
  verifier、session、object、named volume 或恢复包。
- Owner 早先提供的 `fb31e8e... / sha256:0b09ca... / qcq1q8m...` 继续只作历史 rollback/provenance
  tuple，不冒充 review-time 或 S04 发布身份。

## 6. Validation record

| Gate | Result |
|---|---|
| Backend | Python 3.12 full regression `157 passed`；secret/abuse focused `18 passed`；强化的 32-thread cold-start test 独立进程 `10/10`；仅 inherited TestClient deprecation warning |
| Build / exact image | Vite `622` modules PASS；Dockerfile PASS；corrective runtime-frozen image `sha256:6a37c2cc...763de` |
| TEST-WS-002/003 | restart + file/code recovery + rotation + revocation + Flag rollback PASS；valid consistency `100%`；invalid authorization success `0`；validation echo `0`；total canary hit `0` |
| TEST-WS-004 | fresh-window Oracle 连续 `3/3` 后 corrective exact-image 再 PASS；normal false positives `0/100`；all attack bypasses `0`；concurrency `2 admitted / 4 blocked` 且原因仅 `concurrency`；lease `0` 后 recovery `200`；active-attack root/create `200/201`；global sustained `600` then block/recover |
| Public/private regression | shell desktop/mobile/no-JS/degraded `4/4`；Chromium/Firefox/WebKit critical/serious/incomplete `0`、unpublished index hit `0`；private flow `11/11` |
| Taskpack/governance | validator `49/49, 14/56/56`, 0 errors/warnings；mutation `1 positive + 4 negative`, source unchanged `5/5`；five-project dual-plane PASS |
| Sealed authorities | Canonical `5ae070cb...552`、AC `1f07bd14...bc1`、DAG `a9753e7c...306`、Release `f47de7a...3c7`、Trace `ca369627...727` |
| Dependency | production `npm audit --omit=dev` vulnerabilities `0`；resolved Python requirements known vulnerabilities `0` |
| Workflow/config | actionlint `v1.7.7` clean；four Compose parsers exit `0`（cloudflared fallback 仅提示本机未配置的外置 secret env） |
| Static/public safety | changed Python Ruff clean with inherited `main.py:E741` excluded；compile PASS；KMFA runtime DB/archive/bytecode `0`；high-confidence new-secret/absolute-path scan `0`；`git diff --check` PASS |

首次 GitHub deploy run `30009779537` 的 backend/governance、image、public shell、三浏览器 a11y/index、
recovery/secret Gate 全 PASS；`F-S04-010` 在 abuse E2E 阻断，`golden-path` skipped，Coolify 未触发。
修复只隔离 E2E 场景的 policy window，并增加对拒绝原因和 persistent lease 归零的确定性观察；不改变
limiter、预算或业务状态，禁止 rerun 红 SHA。
corrective 本地 full regression 随后暴露并修复 `F-S04-011`；最终 image 上 recovery/secret、abuse、
public shell、三浏览器 a11y/index、private `11/11` 均重新 PASS。

Full npm audit 另报告两个只影响 Vite/esbuild development server 的 devDependency advisories；生产镜像只
保留已构建静态资产与 Python runtime，不启动或复制 Vite dev server，CI 构建在 Linux。它们不构成
S04 runtime exposure；若未来远程暴露 dev server、引入 Windows build runner 或 advisories 影响 build
artifact integrity，则必须先升级并重新过 Gate。为避免无收益的 Vite major jump，本 Stage 不顺带重构。

浏览器 trace、截图、SQLite、对象字节、proof 与合成 capability 只在 `/tmp` 一次性目录中；仓库只提交
compact receipt 和源代码。所有运行证据绑定同一 runtime-frozen image，未复用 P4.4 的旧镜像摘要。

## 7. Guarded publication, rollout and rollback

1. 初始 S04 chain 已从 `ce9c27da...` fast-forward 到 `e1b983e8...`；run `30009779537` 暴露
   `F-S04-010` 并在 deploy 前阻断，本地 corrective Gate 又暴露 `F-S04-011`。只有 remote 仍为该 SHA、
   corrective diff 仅含两个 finding 的最小 runtime/test/Oracle/receipt/HANDOFF、finding `open=0`
   且本地完整复验全绿，才允许再 fast-forward 一个 corrective commit；
   禁止 amend 已公开 commit、rerun 红 SHA、force-push 或绕过 CI。
2. 同 SHA deploy workflow 必须先通过 reusable `app-e2e`，再触发 Coolify。自动部署若发生，仅监控并
   只读核对；本 run 不手工更改 Cloudflare/Coolify/WAF/生产数据。
3. 发布后必须核对 GitHub `main`、workflow conclusion、实际 deployment UUID、`source_commit`、
   image digest、completed_at。任一不一致、Gate failure、secret hit、恢复/hash failure 或 normal-user
   isolation regression 均 STOP，不进入 S05。
4. S04 runtime 保持 `KMFA_ABUSE_POLICY_MODE=enforced`；策略故障时可切
   `emergency-expensive-only`，只放宽低成本 read/mutation，仍限制 identity/recovery/upload/export；
   没有生产 `off`。
5. 首个 22-char workspace ID 创建后，**禁止**在 Walking Skeleton 开启状态下降到 pre-P4.1/S03
   binary。最快安全回滚是保留 S04/P4.1 dual reader 与 named volume，先置
   `KMFA_WALKING_SKELETON_ENABLED=0`（必要时同时保持 indexing hold），再前滚兼容修复。ordinary
   revert 只能撤销上层行为并保留双 ID reader；禁止 `down -v`、删对象/数据库、改 verifier、恢复包
   replay、强制登录墙或 force-push。
6. 只有 upload、同 SHA Gate、部署身份与 post-deploy Oracle 全部闭合，下一个新 run 才可执行
   `S05 / P5.1 / T-S05-01`。本 receipt 不启动 S05，也不把 published Stage、G2 或 GA 提前标绿。
