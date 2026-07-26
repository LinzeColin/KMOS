# S06 / P6.2 / T-S06-02 — 隔离与扫描 receipt

状态：**LOCAL PHASE PASS — 未做 S06 整体复审、未上传、未部署**

Taskpack SHA-256：
`31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

Parent commit：
`59c659338854d54d138793deaaef5e12587bf705`

Requirement / acceptance / test：
`R-UP-003 / AC-UP-003 / TEST-UP-003`

## 1. 范围与结论

本 receipt 只关闭 `S06 / P6.2 / T-S06-02`。候选实现增加默认关闭的
`KMFA_FILE_SECURITY_ENABLED`、schema `5` 的 durable assessment 与 append-only transition
event、quarantine-first projection、HMAC 双向认证的私网 scanner protocol、无数据平面凭据的
scanner container、bounded retry worker、MIME/magic/文件名/archive 检查，以及
`clean / attachment_only / rejected / timed_out / scanner_error` 的真实用户提示。

最终候选镜像
`sha256:33f5325df96f549f149c662f57f3e264b8b3d4ce7cef62e2eb42f08eaf1c333f`
上的合成攻击/畸形语料 clean 或 preview 逃逸为 `0`；标准合法 policy 夹具误拒
`0/100`，最终镜像合法夹具误拒 `0/12`。解析只在独立 scanner 进程/容器发生，Web
进程不 import parser policy；scanner 无 DB DSN、对象凭据、app state mount 或 host port。
timeout 和 scanner unavailable 均持久化为非 clean，恢复后由 worker 重试收敛；任何状态都
不执行、不内联渲染、不生成预览。

本实现是针对 taskpack 语料与明确资源边界的
`kmfa-bounded-content-firewall/1.0`，不是 signature-complete 商业杀毒产品。`clean` 只表示
通过当前有界检查，UI 同时明确“仍仅附件下载”；本 phase 不把未测试恶意样本、生产流量、
第三方 AV 覆盖或未来 parser 安全伪报为已证明。

P6.2 没有进入 P6.3 immutable lineage/processor/preview，也没有执行 S06 whole-stage review、
GitHub upload、Coolify/Cloudflare 变更或生产 rollout。v1.5 recovery bundle、既有
SQLite/filesystem reader、恢复码/verifier、intent/chunk/object/outbox/backup 和所有 volume
均未删除或覆盖。

## 2. 已实现合同

### Quarantine-first durable state

- P6.1 immutable object 与 workspace projection 在同一 DB transaction 建立
  `quarantined` assessment；公开 payload 在 scan 前不提供下载，且始终
  `preview_allowed=false / processing_allowed=false`。
- assessment 保存 artifact version、受控文件名、reported/detected MIME、size、SHA-256、
  scanner/policy version、attempt、lease、row version 和完成时间；不保存 recovery/session
  capability。
- transition event 只保存 artifact version 的 20 位 SHA-256 opaque ref；SQLite/PostgreSQL
  均用 trigger 拒绝 UPDATE/DELETE。并发 claim 使用 state + row version + lease，两个 worker
  只能有一个获得同一 assessment。
- `rejected` 对象保持 `object_quarantine=isolated` 且下载 `409`；flag rollback 后仍阻断。
  `attachment_only / timed_out / scanner_error` 只允许固定 attachment 下载，绝不执行或预览。
- P6.2 前的历史 artifact 没有伪造 assessment，显式显示
  `unscanned_attachment_only`；可按既有私有路径下载，不冒充 clean。

### Scanner protocol 与最小权限

- App/worker 只 materialize 已按 size + SHA-256 验证的私有原件并流式发送；scanner 不读取
  database、object store 或 app volume。
- 请求 MAC 绑定 protocol、nonce、SHA-256、size、base64url filename 与 reported MIME；
  scanner 拒绝重放 nonce、错误 MAC、错误 length/hash 和压缩 content encoding。
- response MAC 绑定 verdict、reason、detected MIME、engine/version/policy、风险 flags 与
  archive bounds；client 校验 response size、schema、nonce、MAC 和固定 scanner identity。
- URL 只允许显式 `http://host:port/scan`；每次连接先解析并拒绝公网、multicast、
  unspecified、link-local 和 reserved 地址，再直接连接已验证私网 IP，避免把 scanner
  credential 发往公网。
- scanner container 固定 non-root `65532:65532`、read-only root、`/tmp` 80 MiB
  noexec/nosuid/nodev、cap-drop ALL、no-new-privileges、1 CPU、256 MiB、64 pids、internal
  network、无 host port、无 mount；唯一 KMFA 环境变量是随机 scanner shared secret。

### 有界分类与失败语义

- filename 再次执行 NFC、长度、控制字符、点路径、slash/backslash、双扩展和危险扩展检查。
- magic 覆盖 PDF/PNG/JPEG/GIF/ZIP/OLE/PE/ELF/WASM/MP3/WAV/MP4/gzip/7z/RAR/HTML/SVG/
  script/JSON/text/unknown，并与 reported MIME 和最终扩展名交叉检查。
- ZIP 不解压到文件系统；先检查 entry 数、单 entry/总展开大小、压缩比、绝对/父路径、
  Windows drive、backslash、symlink、encrypted、nested archive、macro 与 EICAR，再流式读取
  受限 entry。畸形 archive、path traversal、symlink、bomb 和 EICAR 为 rejected；encrypted、
  nested、macro 和普通 archive 仅 attachment。
- PNG CRC/chunk、JPEG/GIF trailer、PDF EOF、MP3/MP4/WAV bounds 和 JSON parse 失败为
  rejected；active/unknown/uninspected/high-risk/mismatch 为 attachment-only。
- 单次 scan 上限 `64 MiB`；archive entry `1024`、单 entry `64 MiB`、总展开
  `128 MiB`、压缩比 `100:1`，不递归扫描 nested archive。
- scanner timeout/config/error 永远不写 clean。worker 按 durable lease、retry delay 和
  max attempts 重试；完整备份在任何 assessment 为 `scanning` 时 fail closed，full restore
  保留 assessment、append-only events 与 rejected 下载阻断语义。

## 3. AC-UP-003 最终镜像 Oracle

所有输入均为 synthetic fixture；raw recovery/session capability、scanner shared secret、
用户文件名和 object key 不写入 CI artifact/compact receipt。

| Gate | 最终观测 | 结果 |
|---|---:|---|
| 直接 filename traversal | `../outside.txt` 在写入前 `422` | **PASS** |
| rejected corpus | EICAR、ZIP traversal、ZIP bomb、malformed PNG `4/4` | **PASS** |
| attachment-only corpus | MIME spoof、双扩展、macro、unknown `4/4` | **PASS** |
| unit 扩展语料 | HTML active、broken ZIP、ZIP EICAR 等 clean escape `0` | **PASS** |
| 合法误拒 | policy `0/100`；final-image `0/12` | **PASS** |
| timeout | 初始 `timed_out`，不是 clean；scanner 恢复后 retry → clean | **PASS** |
| unavailable | 初始 `scanner_error`，不是 clean；scanner 恢复后 retry → clean | **PASS** |
| parser/web 隔离 | Web 不 import policy；scanner 无 DB/object/state access | **PASS** |
| restart | assessment、events、rejected block 与可下载安全附件均保留 | **PASS** |
| flag rollback | persisted rejected 仍 `409`；旧/新未扫描文件 attachment-only | **PASS** |
| 浏览器 | 根页创建/上传、clean 提示、下载 enabled、preview control `0` | **PASS** |
| 隐私 | container/worker log capability/shared-secret 命中 `0` | **PASS** |

最终数据库摘要：

```text
assessment states: attachment_only=4, clean=15, rejected=4
append-only transition events: 73
isolated rejected objects: 4
observed initial states:
  attachment_only=4, clean=12, rejected=4, timed_out=1, scanner_error=1
malicious/malformed clean-or-preview escape: 0
```

## 4. Phase review findings

| Finding | 影响 | 最小修复 | 状态 |
|---|---|---|---|
| `F-P62-001` pre-change EICAR 可上传并 `200` 下载，无 security state | 不能满足 quarantine-first 与 escape=0 | 增加 schema 5 assessment/events、下载 Gate 和独立 scanner | **RESOLVED** |
| `F-P62-002` 若 scanner 直接获得 DB/object/state | scanner compromise 可跨越数据平面 | HMAC stream protocol；scanner env/mount/network/uid 强约束并由 unit+Docker inspect 固定 | **RESOLVED** |
| `F-P62-003` timeout/error 若当 clean 或直接 preview | 未判定文件可进入主动处理 | durable non-clean state；仅 attachment；preview/processing 永远 false；worker retry | **RESOLVED** |
| `F-P62-004` rejected 在 flag rollback 后若按 legacy 下载 | 回滚可重新暴露已知恶意文件 | `rejected` 下载 Gate 不依赖 flag；rollback exact-image Oracle | **RESOLVED** |
| `F-P62-005` active scan 若进入一致性 backup | restore 可得到悬空 scanning lease | backup 在 active scanning 时 fail closed；full restore 回归覆盖 events/state | **RESOLVED** |
| `F-P62-006` 首版 E2E 把 App 只接 internal network | Docker host port 无法发布，Oracle 误判 readiness | scanner 留在 internal scan-plane；App 另接普通 test network + scan-plane | **RESOLVED** |
| `F-P62-007` E2E 对 12 个合法样本逐个下载，10 秒内撞 export global 16 | 测试自身触发正确的 abuse capacity Gate | 保持 abuse enforced；12 个全扫描，仅 1 个代表下载，其余验证 download contract | **RESOLVED** |

Phase review open finding：`0`；waived/accepted risk：`0`。有界引擎覆盖范围和 production
rollout evidence 是明确未完成边界，不作为豁免，也不冒充 open Critical/High finding。

## 5. 验证

```text
new P6.2 backend suites:                              22 passed
all backend tests, Linux Python 3.12:                269 passed
  warning:                                            1 Starlette/httpx deprecation
Ruff all new P6.2 Python / compileall / diff check:   PASS / PASS / PASS
frontend production build:                           PASS (622 modules)
local + Coolify Compose render:                      PASS / PASS
final Dockerfile frontend+backend image build:       PASS
TEST-UP-003 final-image API+browser Oracle:           PASS
  malicious/malformed escape:                        0
  policy legal false rejection:                      0/100
  final-image legal false rejection:                 0/12
  preview success / secret log match:                0 / 0
taskpack validator:                                  49 req / 49 AC / 56 tasks PASS
validator mutation suite:                            1 positive + 4 negative PASS
  sealed sources unchanged:                          5/5
dual-plane governance:                               PASS
diff/untracked credential-shape + private-path scan: 0 / 0
```

Ruff 的 `EXE001` 按仓库既有 E2E 约定排除：同目录 tracked Python Oracle 均保留 shebang 且
Git mode 为 `100644`，本 phase 不为一个新文件单独制造执行位差异。Vite 仍报告既有私有
`App` bundle 大于 500 kB 的非阻断 warning；P6.2 公共 bundle约 `31 kB`，不为该既有私有
bundle 引入无收益拆分。

## 6. Rollout、rollback 与下一边界

P6.2 不做生产 rollout。S06 whole-stage review 前保持
`KMFA_FILE_SECURITY_ENABLED=0`，并由 CI 构建同一 source 的 image 后运行本 receipt Oracle。
guarded rollout 必须同时启用 `full,file-security` profiles、生成独立随机 shared secret，
并先验证 scanner health、无数据平面 env/mount、attack corpus、timeout、retry、浏览器状态和
回滚；任一失败立即停止晋级。

快速回滚先置 `KMFA_FILE_SECURITY_ENABLED=0` 并重部署同一 schema `5` binary，再停止
file-security worker/scanner；保留 assessments/events、DB、所有 object/chunk/backup/volume
和 v1.5 recovery asset。persisted rejected 继续阻断；未判定/旧文件仅 attachment-only。
禁止 schema/binary downgrade、`down -v`、删表/事件/对象/卷/备份、撤既有 reader 凭据、
改 verifier 或 replay recovery bundle 覆盖 live state。若需停全部新上传，再独立置
`KMFA_CONSISTENCY_STATE_MODE=paused`。

立即停止条件：scanner 需要超出最小权限的生产 DB/object access；任何 attack/malformed
fixture 成为 clean/preview；合法误拒达到 `1%`；timeout/error 成为 clean；rejected 在
rollback 后可下载；parser 进入 Web 主进程；证据泄露 capability/private bytes；或回滚需要
删除状态。

2026-07-26 收口前已自行 `fetch origin main`：远端
`c00a90f5b9fab87c880a7046ad3255b27ab24a45` 相对共同基线 `12d6fa9f…` 新增 `43`
个 KMIDS commits，但 `KMFA/` 与 `.github/workflows/` scoped diff 为 `0`。本地 P6.1/P6.2
chain 没有被远端删除；S06 whole-stage review/push 前仍须把当时最新 `origin/main` 纳入整合并
重跑完整门禁。

本地 Task 进度为 `26/56`；S06 为 `2/4` phases，published Stage 仍为 `6/14`。下一次新
run 只可执行 `S06 / P6.3 / T-S06-03`；不得提前进入 P6.4、做 S06 whole-stage review、
上传本中间 phase 到 GitHub，或启用生产 P6.1/P6.2。
