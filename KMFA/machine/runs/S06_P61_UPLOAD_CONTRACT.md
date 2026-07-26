# S06 / P6.1 / T-S06-01 — 上传合同 receipt

状态：**LOCAL PHASE PASS — 未做 S06 整体复审、未发布、未部署**

Taskpack SHA-256：
`31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

Parent commit：
`12d6fa9f46786387ee21d9bd3c682175464f3554`

Requirement / acceptance / test：
`R-UP-001 + R-UP-002 / AC-UP-001 + AC-UP-002 / TEST-UP-001 + TEST-UP-002`

## 1. 范围与结论

本 receipt 只关闭 `S06 / P6.1 / T-S06-01`。候选实现增加默认关闭的
`KMFA_RESUMABLE_UPLOAD_ENABLED`、`kmfa-offset-v1` upload session API、固定分片、
服务端权威偏移、幂等重试、分片与完整文件 SHA-256、可见大小/配额/进度 UI，以及明确
取消清理。它复用 S05 `consistency_operations` 和既有 immutable object → DB+outbox
状态机，不创建第二套数据平面；v1.5 SQLite、filesystem reader、恢复码/verifier、对象、
备份与所有卷均未迁移、删除或重写。

`AC-UP-001` 在最终镜像的 7 类合成夹具（PDF、PNG、MP3、MP4、ZIP、未知二进制、
双扩展 `.exe`）上通过：`7/7` 私有存储、`7/7` 只按 attachment 下载，公开对象 URL
成功数 `0`，执行/内联预览成功数 `0`。`AC-UP-002` 在 4 个分片边界均恢复成功；
真实容器重启 `1` 次、真实 socket 半分片断线 `1` 次，恢复成功率 `100%`，不完整分片
接受数 `0`。分片 checksum 篡改、完整文件 checksum 篡改逃逸、超限预算后写入、重复
对象增长均为 `0`；两个并发相同分片响应均收敛为一个 durable chunk。

这不是 P6.2 malware clean、magic/MIME 验证、sandbox、解析器安全、派生预览、多文件
生命周期或生产大流量证明。生产仍保持 P6.1 Flag=`0`；本 phase 没有变更 Cloudflare、
Coolify、R2、PostgreSQL、生产 DB/object/volume、Access、WAF、恢复材料或发布身份。

## 2. 已实现合同

### API、配额与持久状态

- `POST /workspaces/{id}/upload-sessions` 以 `Idempotency-Key` 创建/重放 session；
  请求声明受控文件名、reported media type、精确字节数与完整 SHA-256。
- `GET/HEAD .../upload-sessions/{session}` 返回服务端 offset、length、state 和最大分片；
  `PATCH` 只接受 `application/offset+octet-stream`、identity content encoding、连续 offset
  与分片 SHA-256；`POST .../complete` 在完整 hash 通过后进入既有 S05 状态机；
  `DELETE` 只取消仍为 `intent_recorded` 的 session，并同步清除其完整暂存和分片。
- 单文件 `64 MiB`、固定非末片 `4 MiB`、workspace artifact `1`、全局 artifact
  `512 MiB`；每个 workspace 最多保留 `16` 个 resumable session，限制取消/失败造成的
  row、lock 与暂存增长。
- 创建 intent 前同时检查 artifact reservation、全局预算与文件系统余量；本地余量按
  “分片 + 完整组装文件”两份字节预留。超限测试确认 intent `0`、chunk `0`。
- 分片使用只含 operation ID + offset 的 `0600` 私有文件名，不含用户文件名；`flock`
  串行化同 session 并发写。同 offset/同 hash 是幂等 replay，不同字节、越序、短非末片、
  超界和非 identity encoding 均 fail closed。
- 未完成 session 是 durable reservation，reconciliation 不把它误推进为 whole-file
  failure；完成文件一旦出现，仍由原 S05 adapter 按 intent 记录的 storage backend 续跑。
  Flag 回滚不会删除分片，显式取消是本 phase 唯一自动清理入口。

### UI 与安全边界

- 根页读取服务器公开合同后才展示实际 `8 MiB standard` 或 `64 MiB resumable` 上限、
  `4 MiB` 分片、`512 MiB` 阶段总预算、session 上限和已确认字节进度；无“无限上传”文案。
- 浏览器先计算完整 SHA-256，并以 workspace + 文件名/type/size/hash 生成稳定 retry key；
  刷新/恢复工作区后重新选择同一文件会重建同一 key，从服务器 offset 继续，不使用
  `localStorage`、`sessionStorage` 或第三方遥测。
- 任意类型都只保存原始字节；下载固定
  `application/octet-stream + Content-Disposition: attachment + nosniff`，不返回 bucket URL
  或 presigned URL。P6.2 前不执行、不解析、不内联预览，也不伪报已扫描。
- upload session 的 POST/PATCH/DELETE 全部进入 P4.4 expensive upload policy。一次最大
  上传需要 session create + 16 chunks + complete，因此 10 秒 actor/workspace budget 调整为
  `24`，global 为 `128`；并发仍为 `2`，artifact byte/session lifetime ceiling 继续限制放大。

## 3. 最终镜像 Oracle

最终本地候选镜像：
`sha256:6ddb1800ad6d946664e20287e837f5eb9649d1eccf4a9dcb408e53bd21a9180e`

所有输入、身份和字节均为临时合成夹具；compact JSON 为 `1.9 KiB`，不保存 recovery/session
capability、原始私有数据或凭据。

| Gate | 观测 | 结果 |
|---|---|---|
| 类型矩阵 | 7 类安全存储，attachment-only `7/7`，执行成功 `0` | **PASS** |
| 分片边界 | unit process-view 中断位置 `0/1/2/3` chunks，恢复 `4/4` | **PASS** |
| 真实中断 | 容器重启 `1`；socket 半分片断线 `1`；partial accepted `0` | **PASS** |
| checksum | 分片篡改逃逸 `0`；完整 hash 篡改发布 `0` | **PASS** |
| 超限/空间 | `64 MiB + 1` 在 intent/chunk 前拒绝；两份 staging 余量 Gate | **PASS** |
| 幂等/重复 | 同 session/create/complete replay 对象总数不增长；重复 chunk extra copy `0` | **PASS** |
| 并发 | 相同 offset 的 2 个并发请求均 `204`，durable chunk `1` | **PASS** |
| 私有下载 | 字节/hash 相同；公开对象/assets GET 成功 `0` | **PASS** |
| Flag 回滚 | resumable disabled；既有 hash 保留；standard upload `200`；未完成 chunk 保留 `1` | **PASS** |
| 浏览器旅程 | quota 可见、真实 `/upload-sessions`、重启恢复/下载/撤销/泄露扫描 | **PASS** |
| 隐私 | capability evidence/log 命中 `0`；未解释失败 `0` | **PASS** |

## 4. 平台限制核验

- Cloudflare 当前官方请求体上限为 Free/Pro `100 MB`、Business `200 MB`、Enterprise
  `500+ MB`；zone `max_upload` API 的公开枚举最小值也是 `100`。P6.1 的单请求上限为
  `4 MiB`，保守低于该最小公开合同：
  <https://developers.cloudflare.com/support/troubleshooting/http-status-codes/4xx-client-error/error-413/>，
  <https://developers.cloudflare.com/api/resources/zones/subresources/settings/methods/list/>。
- R2 单次 PUT 上限为 `5 GiB`；KMFA 在 App 私有暂存中组装最多 `64 MiB` 后沿用 S05
  单次 immutable object PUT，因此没有把 4 MiB App chunk 冒充 R2 multipart part：
  <https://developers.cloudflare.com/r2/platform/limits/>。
- 对当前 zone 的只读 API 查询因现有 token 权限返回 `9109 Unauthorized`，故本 phase 不声称
  已读取账户实时设置或通过真实生产 edge。S06 整体复审/guarded rollout 前仍必须对同一发布
  image 做 4 MiB edge canary；任何 `413`、源站截断或 WAF/代理差异立即停止晋级。

## 5. Phase review findings

| Finding | 影响 | 最小修复 | 状态 |
|---|---|---|---|
| F-P61-001 只有 8 MiB whole-request PUT | 断线必须重传，无法证明 AC-UP-002 | 增加 flag-guarded offset session，复用 S05 intent | **RESOLVED** |
| F-P61-002 原 reconciliation 会把未完成 session 当失败 whole file | 分片尚未齐就进入 retry/isolation | 识别 resumable intent，无完整 stage 时保持 active reservation | **RESOLVED** |
| F-P61-003 旧 upload 10 秒 device/global `6/12` | 一次 16 分片上传必被自身限流 | 提升到 `24/128`，保留并发/字节/全局层；测试固定时钟消除跨窗假红 | **RESOLVED** |
| F-P61-004 取消可无限累积 durable rows/locks | 长期匿名成本无界 | 每 workspace lifetime resumable session 上限 `16` | **RESOLVED** |
| F-P61-005 创建只预留一份文件空间 | chunks 与 assembled 共存可跌破余量 | intent 前预留两份本地字节并加回归 | **RESOLVED** |
| F-P61-006 压缩正文与半分片断线未显式处理 | checksum/offset 语义可能含糊，临时文件可残留 | 只接受 identity；捕获 disconnect、删除 request part、保持 durable offset | **RESOLVED** |
| F-P61-007 公共说明最初无条件写 64 MiB | Flag off 时产生虚假能力声明 | 文案明确 resumable 64 MiB / rollback standard 8 MiB | **RESOLVED** |
| F-P61-008 最初并发只测重复 chunk，没有 completed replay | duplicate object 成本证据不足 | 增加 create/complete replay 和 exact object-count Gate | **RESOLVED** |
| F-P61-009 取消清理与已在途分片可在状态转换前交错 | 已取消 session 可能留下私有残片 | 状态确认/取消声明与 chunk/discard 共用跨进程 session lock；增加确定性竞态回归和重复取消 | **RESOLVED** |

Phase review open finding：`0`；waived/accepted risk：`0`。账户实时 edge identity 是 S06
Stage Review 的 promotion evidence，不被本地 phase receipt 冒充为已完成。

## 6. 验证

```text
focused P6.1 + abuse regression:                         34 passed
all backend tests:                                      247 passed
Ruff E/F on changed Python / git diff --check:           PASS / PASS
frontend production build:                              PASS
final Dockerfile frontend+backend image build:           PASS
TEST-UP-001/002 final-image Oracle:                      PASS
S03/P3.4 + S04/P4.2-P4.3 + P6.1 browser Oracle:         PASS
  invalid authorization / secret-hygiene canary hits:    0 / 0
workflow YAML / local + Coolify Compose render:          PASS / PASS
taskpack validator / 4 mutation cases / dual-plane:      PASS / PASS / PASS
diff credential-pattern scan:                           0 new hits
```

Vite 仍报告既有私有 `App` bundle 超过 500 kB 的非阻断 warning；P6.1 公共 bundle约 `30 kB`，
本 phase 未为该既有私有 bundle 引入无收益拆分。

## 7. Rollout、rollback 与下一边界

P6.1 不做生产 rollout。S06 整体复审前保持
`KMFA_RESUMABLE_UPLOAD_ENABLED=0`；候选 CI 必须运行本 receipt 对应 Oracle。快速回滚只把该
Flag 置 `0` 并重部署，标准 8 MiB upload、既有读取/恢复/下载继续可用；保留 schema `4`、
`kmfa-app-state`、PostgreSQL/S3 配置、所有 intent/chunk/object/outbox/backup、legacy reader 与
v1.5 recovery bundle。若需停全部新上传，再独立置
`KMFA_CONSISTENCY_STATE_MODE=paused`。禁止 `down -v`、删 chunk/object/volume、schema/binary
downgrade、撤 reader 凭据、改 verifier 或 replay 恢复包覆盖 live state。

立即停止条件：edge 4 MiB canary 失败、任何文件绕过私有对象策略、checksum 篡改逃逸、重复对象
增长、断线后 durable offset 倒退、证据出现 capability/private bytes，或回滚会删除既有状态。

本地 Task 进度为 `25/56`；S06 为 `1/4` phases，published Stage 仍为 `6/14`。下一次新 run
只可执行 `S06 / P6.2 / T-S06-02` 隔离与扫描；不得提前进入 P6.3/P6.4、做 S06 whole-stage review、
上传本中间 phase 到 GitHub，或启用生产 P6.1。
