# S05 / P5.4 / T-S05-04 — retention, backup and restore receipt

Status: **LOCAL PHASE PASS — NOT STAGE-REVIEWED, NOT PUBLISHED, NOT DEPLOYED**

Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

Parent commit: `34eac93fbc8fdb64ed3ad83dde7afdf84711ee39`

Requirement / acceptance / test:
`R-DATA-003 / AC-DATA-003 / TEST-DATA-003` and
`R-DATA-004 / AC-DATA-004 / TEST-DATA-004`

## 1. Scope and conclusion

This receipt closes only `S05 / P5.4 / T-S05-04`. It adds schema-v4 retention
and legal-hold projections, proof-gated explicit deletion, a separately
credentialed S3 lifecycle worker, portable full/logical-incremental database
plus object backups, empty-environment restore, tombstone replay and a
quarterly restore/deletion drill runbook.

The default contract has no time-based expiry and starts with
`KMFA_LIFECYCLE_MODE=paused`. A deletion request requires an active anonymous
session, the workspace recovery secret, exact confirmation text, an
`Idempotency-Key`, an unexpired restore proof for the current schema, no legal
hold and no unresolved consistency operation. The App cannot physically
delete S3 objects: a separate no-port worker receives prefix-scoped
list/get/delete-version credentials. Legacy filesystem lifecycle deletion now
fails closed by default because it cannot isolate App delete access; its
explicit override is test-only and absent from compose. Public cache/index
revocation is required before finalization, records the real completion time,
and fails closed when no real adapter is connected or the SLA is exceeded.

`AC-DATA-003/004` pass for the bounded synthetic PostgreSQL + versioned private
MinIO fixture. A full backup plus logical incremental restored one standard
fixture into an empty database and empty object prefix, then the real App
recovered the workspace and downloaded byte-identical content. Project progress
`73`, score `91`, one financial record, one task and one object were restored;
fixture count was `1/1`, invariant failures were `0`, measured synthetic RPO was
`4000ms` and RTO was `246ms`.

The lifecycle matrix proved default no-expiry, wrong-token/secret rejection,
legal-hold blocking without data loss, one failed object deletion followed by
safe retry, public purge within the fixture SLA and exact provider-version
removal from `4 → 0`, with accidental deletes `0`. A deletion-tombstone
incremental restored into a second empty environment without resurrecting the
workspace business rows, object, old recovery capability or imported restore
proof.

This phase does **not** enable deletion, PostgreSQL or S3 in production, create
an independent production backup destination, configure a production
publication/cache adapter, perform S05 whole-stage review, upload GitHub or
claim production RPO/RTO. The measurements below are synthetic release-candidate
evidence only. This run neither queries nor mutates current production; the
last phase-scoped S04 tuple remains a historical closed-rollout reference, not
a fresh 2026-07-26 production identity.

## 2. Implemented contract

### Retention, hold and deletion

- SQLite and PostgreSQL migrate additively to schema `4`. Existing workspaces
  backfill an `active` retention projection; no expiry timestamp or scheduled
  expiry job exists. Legacy SQLite import handles the lifecycle table set
  atomically and backfills old schema-v1-v3 workspaces.
- Restore proof includes backup/manifest identity, schema version, fixture
  counts, invariant count, measured RPO/RTO and artifact-identity hash. It is
  accepted only while both consistency and lifecycle writes are paused,
  expires after `93` days, and cannot be replayed after being marked failed.
  A restored environment invalidates imported proofs and must record a fresh
  isolated drill.
- Legal hold and irreversible object deletion are transactionally ordered. A
  hold imposed before a target enters `deleting` blocks the request and removes
  it from due polling; a hold arriving after irreversible work began returns an
  explicit conflict instead of claiming preservation. Release returns a blocked
  request to the durable queue.
- Deletion targets are durable and idempotent. A first-attempt missing object is
  an integrity failure, not evidence of a crash after delete. Only a target
  already durably marked `deleting` may accept an empty provider inventory as
  crash-replay completion.
- The deletion API stores a hash-only verifier bound to workspace, confirmation,
  idempotency key and recovery secret. An exact replay returns the same request
  after access revocation and after completion; a mismatched replay remains
  indistinguishable from an unknown workspace.
- Worker claims use a ten-minute lease and refresh request heartbeat after each
  publication and object boundary. A live lease cannot be retried by another
  worker; a stale lease remains recoverable. Public purge evidence uses the
  adapter completion time, and a late purge records
  `public_purge_sla_exceeded` before any object deletion and leaves the
  automatic due queue pending explicit operator review.
- S3 deletion enumerates the exact key's current and historical versions plus
  delete markers, verifies every available version before any delete, removes
  only the exact key, then re-lists and requires an empty inventory. A matching
  prefix-neighbour cannot be deleted.
- Finalization removes business rows, file access, recovery verifier and
  publication binding, retains a tombstoned workspace/retention record and
  append-only opaque lifecycle/audit evidence, and scrubs raw storage key,
  object hash, size and artifact identity from completed deletion targets.

### Backup and empty-environment restore

- `python -m app.backup_restore backup` writes a private `0700/0600`,
  checksum-closed directory with canonical manifest, table upserts/tombstones,
  object upserts/tombstones, deep-hashed object blobs and `COMPLETE`. Incremental
  chains bind parent backup ID and parent manifest hash.
- Restore validates every manifest, delta, blob, chain edge, object identity,
  size/hash/backend and final row/object count. It refuses a non-empty migrated
  database, legacy object directory or configured/chain-declared object backend.
  An empty final object set does not bypass the empty-target check. Direct
  destination/bundle/blob symlinks are rejected.
- Backup mechanically refuses any consistency operation outside
  `converged/isolated`, even when the mode flag says paused. Restore requires a
  timezone-aware incident at or after the final recovery point; negative RPO is
  rejected instead of clamped to zero.
- Logical row and object tombstones prevent deleted data from reappearing when
  replaying full plus incremental backups. PostgreSQL sequences are reset after
  insertion, and restore reports measured RPO/RTO and invariant failures.
- A database failure after object writes leaves only the isolated restore target
  dirty; the runbook requires discarding that target and recreating a new empty
  environment. Restore never overwrites a live production database or bucket.
- `record-proof` only records the measured result while both write planes are
  quiesced. Same-host backup directories are staging, not disaster recovery;
  the runbook requires hash-verified replication to an independent encrypted,
  access-audited, version-locked failure domain.

### Rollout and rollback controls

- App and lifecycle worker default to `paused`; the worker has no public port.
  App compose receives normal object credentials only. Lifecycle credentials
  exist solely on the worker and are prefix-scoped by
  `object-store-lifecycle-policy.json`. Production activation requires the
  S3-compatible backend; the legacy filesystem remains a reader/compatibility
  path, not a credential-separated deletion backend.
- S05 Stage Review must approve production use. Gray enablement starts with one
  synthetic workspace while App deletion remains paused, verifies current proof
  and worker isolation, then activates both modes for the bounded canary.
- Fast rollback scales the worker to zero and restores both lifecycle modes to
  `paused`. It retains DB/object/backup/trace/outbox/lifecycle state and all
  named volumes. It never uses `down -v`, schema downgrade or recovery replay.

## 3. Final-image AC-DATA-003/004 Oracle

Runtime-frozen application image:
`sha256:f85a90f1071350d67e17d4efd164a49df5065bcbcb3aab679e96c467fc74fb13`.

Parent source identity:
`34eac93fbc8fdb64ed3ad83dde7afdf84711ee39`.
The image was built after all runtime/test/config corrections and before adding
this receipt/HANDOFF, avoiding a self-referential image claim.

Database fixture:
`postgres:17.10-alpine3.23` /
`sha256:8189a1f6e40904781fc9e2612687877791d21679866db58b1de996b31fc312e4`.

Object fixture:
`minio/minio:RELEASE.2025-09-07T16-13-09Z` /
`sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e`.

All credentials, workspace capabilities, object keys, DB rows, backup bytes and
provider versions were synthetic and ephemeral. Public evidence contains only
the following bounded values:

| Gate | Observation | Result |
|---|---|---|
| default retention | automatic expiry `false`; due without request `0` | **PASS** |
| authorization | wrong token and wrong recovery secret both rejected | **PASS** |
| legal hold | deletion blocked before irreversible work; data loss `0` | **PASS** |
| retry | first provider delete failed; object and business rows remained; retry completed | **PASS** |
| provider inventory | exact object versions/delete markers `4 → 0`; neighbour deletes `0` | **PASS** |
| public effects | publication/cache/index purge completed within fixture SLA | **PASS** |
| purge SLA negative | late real completion preserved `public_purge_sla_exceeded`; object/business remained | **PASS** |
| worker concurrency | active ten-minute lease rejected overlap; stale claim recovered | **PASS** |
| deletion replay | exact request replayed after revocation/completion; wrong secret remained `404` | **PASS** |
| credential boundary | S3 reports separate worker credentials; legacy destructive adapter defaults denied | **PASS** |
| accidental deletion | `0` | **PASS** |
| backup chain | full + incremental + deletion tombstone; all checksum-closed | **PASS** |
| backup fail-closed | pending consistency, bundle/blob symlink, invalid/pre-recovery incident all rejected | **PASS** |
| full manifest | `f4206faa20c5cf95f707e11023b9a2cf20a9837e9a1997dba32c4fceed395865` | **PASS** |
| incremental manifest | `16f9282c7f55f14e67c56ce5e8942d52a6c234ff86c7cd130cd4b9a12c640948` | **PASS** |
| tombstone manifest | `405f1d282238d052007a9b950191870b2fb6c0915b35055074bd0b94ea7c97dc` | **PASS** |
| standard fixture | expected/restored `1/1`; object `1`; download hash equal | **PASS** |
| application state | progress `73`; score `91`; financial/task `1/1` | **PASS** |
| restore invariants | failures `0`; synthetic RPO/RTO `4000ms / 246ms` | **PASS** |
| non-resurrection | final objects/business rows/active imported proofs `0/0/0`; old recovery rejected | **PASS** |
| evidence hygiene | credentials, capability values and raw object prefix in compact report `0` | **PASS** |

## 4. Phase review findings and closures

| Finding | Impact | Minimal correction | Closure |
|---|---|---|---|
| `F-P54-001` baseline had no explicit retention/deletion or DB+object restore contract | “long-term” persistence could not be mechanically proved | add schema-v4 lifecycle projections, proof gate, worker, portable backup/restore and drill runbook | **RESOLVED** |
| `F-P54-002` an S3 key with missing current HEAD could still have historical versions/delete markers | old private bytes could survive an apparently successful delete | enumerate and verify exact-key versions even when current HEAD is absent; require empty post-delete inventory | **RESOLVED** |
| `F-P54-003` legal hold and worker claim were initially separate observations | a hold could race the irreversible delete boundary | transactionally block before `deleting`; reject a late hold as explicit conflict | **RESOLVED** |
| `F-P54-004` an empty final backup object set initially skipped target-backend emptiness checks | restore could mix with unknown pre-existing objects | inspect legacy/configured/every-chain backend regardless of final object count | **RESOLVED** |
| `F-P54-005` a missing object on the first delete attempt could be mistaken for crash replay | pre-existing loss could be hidden as successful user deletion | persist `object_missing_before_delete`; only a verified prior `deleting` state may accept replay absence | **RESOLVED** |
| `F-P54-006` completed deletion targets retained raw storage key/hash metadata | deletion evidence could preserve unnecessary private identifiers | scrub key/hash/size/artifact identity after physical deletion; retain only opaque append-only evidence | **RESOLVED** |
| `F-P54-007` a restored failed proof ID could be replayed with matching fields | deletion might rely on an invalid imported drill | failed proof IDs are permanently conflicting; restore marks imported proofs failed | **RESOLVED** |
| `F-P54-008` inherited P5.1/P5.3 Oracles hard-coded schema `3` or omitted the v4 retention projection | final-image regressions falsely failed instead of testing behavior | bind P5.1 to `SCHEMA_VERSION` and make synthetic P5.3 workspaces create the v4 projection | **RESOLVED** |
| `F-P54-009` delete replay authorized the already-revoked session before checking the prior idempotent request | the same safe retry returned `404` after the first accepted request | verify a hash-only request fingerprint first and return only the same request identity/state | **RESOLVED** |
| `F-P54-010` public purge reused the worker attempt-start timestamp | a slow adapter could appear within SLA after actually finishing late | persist each adapter completion time; record late SLA evidence and stop before object deletion | **RESOLVED** |
| `F-P54-011` `revoking/purge_pending` requests were immediately due and reclaimable | concurrent workers could overlap destructive effects | add ten-minute claim lease, boundary heartbeat, busy outcome and stale recovery | **RESOLVED** |
| `F-P54-012` legacy App and worker shared a writable filesystem volume while status claimed credential separation | production could overstate least privilege | deny legacy lifecycle deletion by default, expose honest status and require S3 for production-active deletion | **RESOLVED** |
| `F-P54-013` backup trusted paused flags, followed direct symlinks and clamped negative RPO | partial state or invalid evidence could be accepted as recoverable | block nonterminal operations, reject destination/bundle/blob symlinks and validate incident ordering/timezone | **RESOLVED** |
| `F-P54-014` current FastAPI/Starlette `TestClient` no longer accepts the workflow's pinned `httpx` harness | CI failed during test collection before product assertions | replace the test-only dependency with verified `httpx2==2.9.1` | **RESOLVED** |

Phase-review open findings: `0` (`14/14` resolved; accepted risk=`0`).

## 5. Verification

```text
all backend tests:                                      220 passed
Ruff E/F/I on new P5.4 Python / git diff --check:       PASS / PASS
production Dockerfile frontend+backend build:            PASS
AC-DATA-003/004 final-image Oracle:                       PASS
  default expiry / accidental deletes:                   false / 0
  provider exact versions:                               4 → 0
  fixture / invariants / RPO / RTO:                       1/1 / 0 / 4000ms / 246ms
  final object/business/proof resurrection:               0 / 0 / 0
P5.1 exact-final-image structured regression:             PASS (14 checks, schema 4)
P5.2 exact-final-image object regression:                 PASS (19 checks)
P5.3 exact-final-image fault regression:                  PASS
  crashes / timeout-after-apply / max recovery:           28 / 2 / 2.406s
  partial/unexplained/duplicate/raw-delete/staged:         0 / 0 / 0 / 0 / 0
S03/P3.4 + S04/P4.2-P4.3 exact-image Oracle:              PASS
  invalid authorization / secret-canary hits:             0 / 0
S04/P4.4 exact-image abuse Oracle:                        PASS
  normal false positives / attack bypasses:               0/100 / 0
local and Coolify Compose renders:                        PASS
workflow YAML parse:                                      PASS
repository validator / mutation suite / dual-plane:       PASS
  49 R / 49 AC / 14 stages / 56 phases/tasks; warnings 0
changed-file raw capability/private-key/cloud-key/absolute/
binary/sealed hits:                                       PASS (all 0)
generated ephemeral DSN template:                         1, manually SAFE
```

The first local backend invocation used system Python and stopped at collection
because runtime dependencies were absent. A requirements-isolated run then
exposed the real Starlette `httpx2` harness drift fixed above. The first local
S03/S04 browser invocations also stopped before assertions because the installed
browser revision did not match CI-pinned `playwright==1.60.0`; after installing
revision `1223`, fresh state/container runs passed. None of these pre-assertion
harness failures is counted as a product result. One parallelized full-suite
invocation crossed an inherited S04 ten-second abuse test bucket and observed
`409` instead of the expected seventh-request `429`; the isolated test passed
immediately, the final serial suite passed `220/220`, and the final-image abuse
Oracle independently passed `0/100` false positives and `0` bypasses.

Repository validators are rerun after this receipt and HANDOFF are added.

## 6. Rollout, rollback and next boundary

P5.4 performs no production rollout and does not claim a fresh current
production identity. The previously closed S04 source/image/deployment tuple is
retained only as historical rollback provenance; no Cloudflare, Coolify, R2,
PostgreSQL, WAF, production database, object, cache, index, volume, verifier,
session or recovery material was changed. No backup or synthetic Oracle
artifact is committed.

S05 now has four local phase candidates. The next run may perform only the
required whole-S05 review across P5.1-P5.4. It must replay schema/adapter
compatibility, backup/restore/deletion invariants, recovery assets, rollback
ordering, CI and public safety as one Stage; fix every finding before one
guarded S05 upload. It must not begin S06 first.

Even after Stage Review, production promotion must preserve and independently
back up all current state, keep the legacy reader and deletion mode paused,
expand schema forward, restore into an isolated environment, deploy the exact
reviewed image to a canary and prove the anonymous recovery/download and
lifecycle Oracles before any bounded cutover. Lack of an independent encrypted
backup, a current restore proof, a real cache/index adapter, legal-hold
conflict, identity mismatch, non-empty restore target or invariant failure is a
STOP.

Fast rollback scales the lifecycle worker to zero, sets
`KMFA_LIFECYCLE_MODE=paused` and
`KMFA_CONSISTENCY_STATE_MODE=paused`, preserves schema `4`,
`kmfa-app-state`, `kmfa-postgres-data`, `kmfa-object-data`, all provider
versions, backup chains, trace/outbox/lifecycle evidence, recovery/session state
and the v1.5 recovery bundle, then restores only into a new isolated target and
forward-fixes. It never uses `docker compose down -v`, destructive schema
downgrade, force-push or historical recovery replay.

This is Task `24/56` completed locally; S05 is `4/4` phases locally complete and
the published Stage remains `5/14`.
