# KMFA v1.5.2 SOURCE IDENTITY

> Task `T-S00-01` / Phase `P0.1 只读取证`
> Acceptance `AC-GOV-002` / Test `TEST-GOV-002`
> Initial capture: `2026-07-22T11:12:07Z`; gate closure: `2026-07-22T11:40:26Z`
> Status: **DONE — AC-GOV-002 PASS**

本文是小于 64 KiB 的 public-safe compact receipt。它只记录身份、摘要、只读命令与缺口；不包含凭据、私有原始数据、完整 HTTP 查询串或私有 Release 元数据。

## 1. 身份结论

| 字段 | 状态 | 已核验值 | 证据/边界 |
| --- | --- | --- | --- |
| `taskpack_version` | VERIFIED | `1.5.2` | 外层 ZIP 与内部 manifest/validator 均通过 |
| `product_version` | VERIFIED | `0.1.4-one-time-github-main-upload` | `KMFA/VERSION`；不得由任务包版本推断 |
| `git_sha` | VERIFIED | `68306e850fa66ffe6b53622915ca81ff8ba98bf8` | 当前 `main` / `origin/main` / GitHub deploy run `29916233128` / Coolify deployment manifest 四者一致 |
| `artifact_digest` | VERIFIED | `sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841` | Coolify 只读部署查询经 GitHub Actions run `29916590384` 提取；不是 source/config/SBOM digest |
| `deployment_id` | VERIFIED | Coolify resource `gz5qao2k0zrx3polpbwgcg51`；deployment `boh5fsnxe82umwcpqzooam1p` | deploy run `29916233128` 入队并完成；只读查询回显同一 UUID 与 `finished` 状态 |

`AC-GOV-002` 要求的五字段已独立存在并可回溯，字段完整率 `5/5 = 100%`，部署身份歧义 `0`。`T-S00-01 / P0.1` 已完成；遵守“一次 run 最多一个 phase”，`P0.2` 只能从下一 run 启动。

## 2. Repository / source subject

| 项 | VERIFIED 值 |
| --- | --- |
| Canonical repository | `git@github.com:LinzeColin/KMOS.git` (`LinzeColin/KMOS`) |
| Target closure | `KMFA/` |
| Authoritative branch/upstream | `main` / `origin/main` |
| Execution checkout | 独立 Codex worktree；本 receipt 位于 detached 本地提交，权威源码从同步后的 `origin/main` 读取 |
| Current authoritative/deployed Git commit | `68306e850fa66ffe6b53622915ca81ff8ba98bf8` |
| Current authoritative Git tree | `8ee9c56f4d54fee812e7efc2a0164d064a290979` |
| Product version file SHA-256 | `bd74e3526bd19995b8a8e2d28a174b9f7fb352e2bda022a0bf9c7697957e6898` |
| Deployment workflow SHA-256 | `97228fc6003c9645576d9e34d43ce5177fd674380b154ef9d14436f41f30d888` |
| Selected runtime/config composite SHA-256 | `70736db6859299bae61f7c045d91ef7f823f18bf5c3d142e4b52403ff4030ebd` |

本 receipt 保存在 detached worktree 的本地未上传提交中，因此执行工作树 `HEAD` 会指向 receipt 提交；这不改变权威 `main`。复跑 source identity 必须比较 `refs/heads/main`、`refs/remotes/origin/main` 与远端 `refs/heads/main`，不得把本地 receipt commit 当作生产源码身份。本 run 已识别 `main` 从 `fb31e8e...` 前进到 `68306e8...`，并以新部署为当前对象，没有把 Owner 提供的上一部署身份误标为当前身份。

Composite 顺序固定为 `.github/workflows/deploy.yml`（从 Git object 读取）、`KMFA/VERSION`、`machine/facts/status.json`、`machine/facts/config.yaml`、App Dockerfile、App compose、Coolify compose、cloudflared compose。它只标识源码配置集合，不是部署镜像 digest。

## 3. Approved input identities

| 输入 | Bytes | SHA-256 | 验证 |
| --- | ---: | --- | --- |
| `KMFA_Product_Design_Taskpack_v1.5.2.zip` | 4,026,290 | `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb` | ZIP 共 43 个文件；manifest 排除自身，其余 42/42 hash PASS；validator `49 requirements / 49 AC / 14 stages / 56 tasks`, 0 error, 0 warning |
| Standalone `KMFA_Roadmap_v1.5.2.md` | 67,405 | `8e4e5086158ab5309f73c9cc1289b6ca3d783c90557342717950cc0677535485` | 与本轮本地输入唯一绑定；Roadmap 仍是 machine graph 派生视图 |
| `KMFA_acceptance_prod-entry-20260722_reference.zip` | 69,575 | `e0e31fc24d2712715b862939e51fd580fdcca1517721dc95eabf1aaadda6a714` | ZIP test PASS；内部 `SHA256SUMS.txt` 全 PASS |
| `KMFA_v1.5_recovery_reference.zip` | 2,366,432 | `8066b65dc96f4368b54e2a053e6726a2bf194806d67b1bdbcacb669a457ef2c1` | ZIP test PASS；只读核验，未 replay/merge |
| `KMFA_v1.4.2_reference.zip` | 118,652 | `e822c98bfe21445b4ddf7110ecf81d14c8fa8bd5f2cdeb00fab4a21e72df39f8` | ZIP test PASS；只作历史参考 |

### v1.5 recovery asset

- Bundle SHA-256: `2d0b516fe7d578061e97dfca874745bcf3a0bf504b0f80976ad3aa21e01077ed`。
- Bundle ref: `1ee7fb111075225dc39039263d2681a0c0acd155 refs/heads/recovery/kmfa-v15-fuzzy`。
- Prerequisite: `97edb1b8750d49409a4f9372a784d4772fea258e`。
- `git bundle verify` 在包含该 prerequisite 的只读历史基线仓中 PASS；bundle 自报 hash algorithm `sha1`。
- `_protected` 中的保护副本存在且 bundle SHA-256 相同；批准的 PRIVATE 冗余 Release 也已只读确认仍为 PRIVATE、server digests 与其私有 manifest 一致。私有资产名称、摘要与内容不复制到本公开 receipt。
- 当前 KMOS 不导入 recovery ref；未执行 fetch/replay/merge/cherry-pick/force-push，S24 未触碰。

## 4. Production subject at gate closure

### Current deployment — VERIFIED

- Target URL: `https://kmfa.linzezhang.com/`。
- GitHub deploy run `29916233128`: event `push`, branch `main`, head SHA `68306e850fa66ffe6b53622915ca81ff8ba98bf8`, conclusion `success`。
- Deploy log queued Coolify resource `gz5qao2k0zrx3polpbwgcg51` as deployment `boh5fsnxe82umwcpqzooam1p` and observed status `finished`。
- Public-safe read-only query run `29916590384` independently returned:
  - `source_commit=68306e850fa66ffe6b53622915ca81ff8ba98bf8`
  - `image_id_or_digest=sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841`
  - `deployment_uuid=boh5fsnxe82umwcpqzooam1p`
  - `completed_at=2026-07-22T11:39:29.000000Z`, `status=finished`
- The query workflow reads the Coolify deployment endpoint inside GitHub Actions with repository secrets, writes the multi-megabyte raw response only to runner temporary storage, and prints only the four approved non-secret fields. No token, raw response or build log was copied into this receipt.
- At `2026-07-22T11:41:13Z`, anonymous `GET /`, `/ui/` and `/healthz` still returned HTTP `302` to the `tiny-scene-b867.cloudflareaccess.com` login boundary. This is a verified baseline defect for later public-entry work, not an identity ambiguity and not a P0.1 Pass Gate assertion.

### Previous deployment — VERIFIED history, not current

The Owner-supplied fields for the deployment active at the start of this run were reproduced exactly by public-safe query run `29916243207`:

- `source_commit=fb31e8e5660ee2e9df00d0ff3b8294910b841078`
- `image_id_or_digest=sha256:0b09ca849c278d94b4981cacccea89e5f18ee5530f19dde690746f57d5658e6c`
- `deployment_uuid=qcq1q8m71d3tp12x0shzpzy0`
- `completed_at=2026-07-20T21:50:47.000000Z`, `status=finished`

While P0.1 was being resolved, `main` advanced by three commits that only added/fixed the deployment-info workflow. Because every `main` push triggers deploy, run `29916233128` produced the newer deployment above. The previous four fields remain a valid rollback/provenance record but are deliberately not labeled current.

The previous deploy run uploaded an SBOM artifact ZIP with SHA-256 `dc860ae9b03adfa3a99696921ccce2eb2cf185f6007a67e085f5ba90425dadc5`; this is **not** the application image and remains deliberately rejected as `artifact_digest`.

## 5. Public-safety checks

- Taskpack high-confidence secret-pattern hits: `0`。
- Tracked `KMFA/` high-confidence secret-pattern hits: `0`。
- Tracked forbidden data extensions (`sqlite/db/xls/xlsx/xlsm/zip/gz/7z/rar/.env*`): `0`。
- Four tracked `private_runtime/` paths are only two `.gitkeep` files and two boundary README files; no runtime payload is tracked。
- 本 phase 未执行 live DWS、DingTalk send、database/object-store write、Cloudflare mutation 或 production write。仅 workflow-dispatch 了 read-only `coolify-deployment-info` 查询；本 run 没有触发部署，所观察的新部署由外部 `main` push 自动触发。

## 6. Read-only audit log

| Check | Result |
| --- | --- |
| `unzip -t` outer taskpack and three approved input ZIPs | PASS |
| `python3 tools/validate_taskpack.py .` | PASS, 0 errors / 0 warnings |
| `shasum -a 256 -c manifest/SHA256SUMS.txt` | PASS, 42/42（ZIP 共 43 个文件，manifest 不校验自身） |
| Acceptance reference internal `SHA256SUMS.txt` | PASS |
| `git fetch origin main`, local/remote authoritative ref comparison | PASS, current `main` / `origin/main` = `68306e8...` |
| `git status --short --branch`; main mirror status | clean |
| `git submodule status --recursive` | no submodules |
| v1.5 `git bundle verify` against prerequisite-bearing historical repo | PASS |
| GitHub deploy run `29916233128` metadata/log read | PASS, source SHA / resource / deployment UUID / `finished` chain verified |
| Read-only Coolify query run `29916590384` | PASS, current source / image digest / deployment UUID / completed_at complete and unique |
| Sanitized anonymous HTTP headers, DNS and TLS read | Access `302` baseline reproduced |
| Secret/private boundary scans | PASS as listed above |

The following two rechecks are retained as timestamped blocker history. Their `BLOCKED` results describe the evidence available then and are superseded by the resolution recheck below.

### Second read-only recheck (`2026-07-22T11:19:14Z`)

- Remote `main` and the latest deploy subject remained `fb31e8e...` / run `29781494182`; no newer deployment existed.
- GitHub's run artifact inventory contained exactly one artifact, `sbom-kmfa-kmos`; its digest is the already rejected SBOM ZIP digest.
- All check-run output summaries were empty, commit statuses were empty, and a full deploy-log digest scan found only that SBOM ZIP digest.
- Current repository files and reachable Git history contained no production image ID/RepoDigest for this deployment.
- Coolify's official [API authorization documentation](https://coolify.io/docs/api-reference/authorization) requires a bearer token even for read-only resource access. Its official [Get deployment by UUID](https://next.coolify.io/docs/api-reference/api/deployments/get-deployment-by-uuid) response exposes `commit`, `status` and `logs`, but no dedicated image-digest field. Therefore the missing identity can only be recovered from Owner-authorized deployment logs and/or a read-only inspect of the running container/image; this agent did not request, reveal or bypass a credential.
- Anonymous `/`, `/ui/` and `/healthz` again returned `302` to the same Cloudflare Access host.

Result: the same `STOP-S00-001` condition is independently reproduced; no evidence permits promotion from `UNKNOWN` to `VERIFIED`.

### Third read-only recheck (`2026-07-22T11:21:21Z`)

- Remote/local `main` remained `fb31e8e...`; run `29781494182` remained the newest deploy and no external state change occurred.
- The artifact inventory remained exactly one SBOM ZIP, and the full deploy log still contained no other digest or image/container identity.
- Anonymous `/`, `/ui/` and `/healthz` remained `302` to the same Cloudflare Access host.
- No Owner-provided source/image/deployment identity fields were available in the authorized working set.

Result: `STOP-S00-001` has now reproduced in three consecutive goal turns. All safe in-scope, credential-free evidence paths are exhausted; further automatic retries cannot make meaningful progress. P0.1 remains `4/5` and must stay blocked until the Release Owner supplies the non-secret artifact identity.

### Resolution recheck (`2026-07-22T11:40:26Z`)

- Owner supplied four non-secret identity fields for deployment `qcq1q8m71d3tp12x0shzpzy0`; successful public-safe query run `29916243207` reproduced all four exactly from Coolify, replacing attestation-only evidence with platform-correlated evidence.
- Before closing the gate, authoritative `main` was re-fetched and found at `68306e8...`, three commits ahead. Those commits changed only `.github/workflows/coolify-deployment-info.yml`, but the repository's push trigger started a new deploy; the older identity was therefore not promoted as current.
- Deploy run `29916233128` completed successfully with new deployment UUID `boh5fsnxe82umwcpqzooam1p`.
- This agent dispatched the repository's constrained read-only query for that UUID. Run `29916590384` returned the current four-field tuple recorded in section 4, with `status=finished`; no credential or raw platform response left the runner.
- Current `main`, deploy run, Coolify manifest and artifact digest now form one unique chain. The five AC fields are `5/5`, and source/config/SBOM digests remain explicitly separated from the image digest.

Result: `AC-GOV-002` PASS; `T-S00-01 / P0.1` DONE.

## 7. STOP-S00-001 — RESOLVED

```text
STOP-ID: STOP-S00-001
Task / Acceptance: T-S00-01 / AC-GOV-002
Resolved at: 2026-07-22T11:40:26Z
Resolution evidence: Owner fields + query run 29916243207 verified the prior deployment; refreshed main/deploy evidence + query run 29916590384 verified the current deployment.
Current tuple: 68306e850fa66ffe6b53622915ca81ff8ba98bf8 / sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841 / boh5fsnxe82umwcpqzooam1p / 2026-07-22T11:39:29.000000Z.
Safety: no token/cookie/session or raw Coolify response was requested or retained; no recovery replay, merge, deploy, push or private-data copy was performed by this phase.
Disposition: inactive; do not reuse as a blocker unless a future identity refresh again loses an independent AC field.
```

## 8. Phase boundary

`T-S00-01 / P0.1` 已达到 `AC-GOV-002`：五字段完整率 `100%`、部署身份唯一、摘要边界明确。下一 run 可从任务包启动 `P0.2`；本文件不是 P0.2 已启动、S00 Stage Review 已完成或 GitHub upload 获准的证据。
