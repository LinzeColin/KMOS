# S05 / P5.3 / T-S05-03 — consistency state receipt

Status: **LOCAL PHASE PASS — NOT STAGE-REVIEWED, NOT PUBLISHED, NOT DEPLOYED**

Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

Parent commit: `4c3d5ae0a7e13ef3e98cf3c5f0d6ad94d53f90ce`

Requirement / acceptance / test: `R-ARCH-002 / AC-ARCH-002 / TEST-ARCH-002`

## 1. Scope and conclusion

This receipt closes only `S05 / P5.3 / T-S05-03`. It adds an additive schema-v3
operation journal, fixed upload/process/index/export transition graph, hashed
idempotency keys, transactional outbox, consumer receipts, append-only traces,
retry/lease handling, reconciliation and persistent orphan quarantine. The
existing upload path now records intent before its object side effect, verifies
ambiguous outcomes, commits its database projection and process outbox together,
and resumes or explicitly isolates every durable partial state without deleting
the raw object.

`AC-ARCH-002` passes for the bounded synthetic PostgreSQL + private MinIO +
external durable-effect fixture. All `28` injected process crashes and `2`
timeout-after-apply cases converged or were explicitly isolated. The final
matrix contained `31` operations (`30` converged, `1` deliberately isolated)
and `30` outbox events (`30` delivered). Partial operations/outbox events,
unexplained terminal states, invalid traces, duplicate effect receipts,
duplicate external side effects, raw-object deletes and staged-file residue
were all `0`. Maximum measured recovery was `1.887s`, below the fixture's
bounded `30s` SLA.

This phase does **not** activate PostgreSQL/S3 in production, provide a real
business processor/search/export implementation, claim that pending process
events are already consumed in production, implement S05/P5.4 retention/
deletion/backup restore, or implement S06 resumable and malware-safe arbitrary
uploads. Generic process/index/export adapters and the outbox consumer contract
are executable and fault-tested, but later owner Stages must connect their real
business side effects. Long-term RPO/RTO and complete anonymous product-journey
claims therefore remain open.

## 2. Implemented contract

### Durable state and identity

- SQLite and PostgreSQL migrate additively to schema `3`; no v1.5 table, row,
  object or recovery asset is dropped. A v3 SQLite source can migrate operations,
  outbox rows, receipts, traces and quarantine in dependency order, while a v2
  source remains supported. Trace import follows the source's monotonic `seq`,
  not its random event ID, so same-second transitions retain their order.
- One idempotency key is unique within workspace + operation kind. Only its
  SHA-256 is persisted. Reuse with a different request fingerprint fails closed;
  replay with the same fingerprint resolves to the persisted operation/object/
  version identity.
- Upload states are fixed to
  `intent_recorded → effect_pending → effect_applied → commit_pending →
  outbox_committed → converged`, with `isolated` as the only exceptional
  terminal state. Invalid skips and stale concurrent transitions fail closed.
- Every initial state, retry and transition is appended to
  `consistency_trace`. SQLite and PostgreSQL triggers reject trace update/delete.
  Reconciliation independently replays trace order and reports a terminal
  operation as unexplained if its trace, receipt or outbox is incomplete.

### Upload, outbox and compensation

- The server privately streams and hashes the request, durably records intent,
  creates/verifies the immutable object, then commits compatibility metadata,
  normalized artifact version, one upload audit and one process outbox event in
  a single database transaction.
- Conditional-create conflict and unknown object-write timeout probe the
  existing bytes, SHA-256 and lineage. Matching identity resumes; mismatch is
  isolated. A database interruption after object success reuses the same object
  and projection identity.
- Browser uploads derive a stable retry key from workspace, filename, reported
  type, size and content hash. Selecting the same file after reload reconstructs
  the same key without persisting a raw key or file body in browser storage.
  Existing API clients may omit the header for backward-compatible one-shot
  uploads; clients that require replay guarantees send `Idempotency-Key`.
- Transactional outbox delivery uses due-time selection, expiring leases,
  attempt-fenced retry/isolation, bounded retries and a deterministic dedupe
  key. A stale worker cannot overwrite a newer lease. The consumer must
  atomically dedupe its external side effect and return a stable SHA-256
  receipt. A crash after effect apply or receipt commit is safe to replay.
- Compensation never deletes the only raw object. Identity mismatch, exhausted
  retry or orphan inventory becomes an explicit operation/outbox/quarantine
  state with an opaque report reference. Raw storage keys and idempotency keys
  are not emitted in compact reconciliation evidence.

### Recovery and rollback

- `python -m app.consistency_worker --limit 100 --isolate-after-attempts 5`
  resumes bounded upload intents and emits the compact reconciliation report.
  The generic engine supplies the same probe/apply-once/commit/outbox contract
  for later process/index/export adapters.
- Recovery selects the adapter recorded on each durable operation, not the
  current new-write mode. An in-flight S3 upload therefore still resumes after
  new writes roll back to legacy filesystem, provided the retained S3
  configuration remains available; the inverse mode switch is also bounded by
  the same rule.
- Missing source plus missing object is retried and then isolated after the
  configured attempt budget. Existing objects are retained. Inventory objects
  absent from both the DB index and durable intents are quarantined, not erased.
- Recovery removes a redundant tracked staging hardlink after object
  verification. The HTTP path removes and directory-fsyncs its random request
  name as soon as a durable intent owns the verified stage, so a later process
  crash cannot strand an untracked full-file copy.
- `KMFA_CONSISTENCY_STATE_MODE=paused` is the safe fast rollback: it blocks only
  new uploads while preserving reads, downloads, recovery and reconciliation.
  Unknown modes fail closed. Schema `3` is forward-fix only; rolling back to an
  older binary that rejects the newer schema is explicitly forbidden.

## 3. Final-image AC-ARCH-002 Oracle

Runtime-frozen application image:
`sha256:2fda6a3a7c83c0250883c53b4faea2ef8783e045b6092b8e61f3ffba6e385dd9`.

Database fixture:
`postgres:17.10-alpine3.23` /
`sha256:8189a1f6e40904781fc9e2612687877791d21679866db58b1de996b31fc312e4`.

Object fixture:
`minio/minio:RELEASE.2025-09-07T16-13-09Z` /
`sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e`.

All identities, object bytes, database rows and credentials were ephemeral
synthetic fixtures.

| Gate | Observation | Result |
|---|---|---|
| transition crashes | upload/process/index/export: `6` points each; outbox: `4` points; total `28` | **PASS** |
| ambiguous outcomes | primary-effect and outbox timeout after apply: `2`; both converged | **PASS** |
| operation terminals | `31`: converged `30`, explicit mismatch isolation `1`, partial `0` | **PASS** |
| outbox terminals | `30`: delivered `30`, partial `0`, missing receipt `0` | **PASS** |
| traces | `183` rows for `31/31` operations; invalid terminal traces `0` | **PASS** |
| idempotent effects | external effects `54`, attempts `56`, duplicate external effects `0` | **PASS** |
| duplicate persistence | duplicate effect-receipt groups `0`; converged-without-outbox `0` | **PASS** |
| quarantine | deliberate mismatch and orphan were explicitly isolated; orphan quarantine `1` | **PASS** |
| destructive compensation | raw-object deletes `0` | **PASS** |
| staging cleanup | final `.part` files `0` | **PASS** |
| recovery bound | maximum `1.887s` against synthetic `30s` SLA | **PASS** |
| evidence hygiene | fixture credentials and raw object-key prefix in compact JSON `0` | **PASS** |

The Oracle stores only compact JSON and a fault matrix. It does not convert the
synthetic recovery time into a production RTO claim.

## 4. Phase review findings and closures

| Finding | Impact | Minimal correction | Closure |
|---|---|---|---|
| `F-P53-001` baseline had no durable cross-system operation/outbox journal | object success plus DB/worker failure could become an unowned partial | add schema-v3 operations, outbox, receipts, traces and quarantine; wire the upload path | **RESOLVED** |
| `F-P53-002` an early isolation path could apply a stale observation after another worker advanced state | a healthy newer state could be overwritten as isolated | re-read in transaction and ignore stale isolation decisions | **RESOLVED** |
| `F-P53-003` initial reconciliation counted terminal labels without proving trace/outbox/receipt completeness | a corrupt terminal could be reported as explained | replay traces and detect delivered-without-receipt and converged-without-outbox | **RESOLVED** |
| `F-P53-004` the first browser retry key was random in memory | reload/reselection could not replay an ambiguous upload | derive the key deterministically from workspace + file identity/content | **RESOLVED** |
| `F-P53-005` an initial rollback note implied an old binary could read schema `3` | rollback could fail at startup and hide recoverable work | add `paused` mode and require forward-fix on the current schema | **RESOLVED** |
| `F-P53-006` a crash immediately after object verification could leave a tracked stage | redundant bytes could accumulate across repeated crashes | clean the stage whenever recovery sees `effect_applied` | **RESOLVED** |
| `F-P53-007` the random request hardlink remained until the whole request returned | a later process crash could strand an untracked full-file name | unlink and directory-fsync it after the durable stage/intent is verified | **RESOLVED** |
| `F-P53-008` the first Oracle recovery helper recreated a stage for already advanced operations | test-fixture behavior left three false orphan `.part` files and weakened evidence | create fixture stages only in pre-effect states and make final residue=`0` a hard Gate | **RESOLVED** |
| `F-P53-009` recovery initially reused the current write adapter after an adapter-mode rollback | an in-flight S3 intent could be handed to legacy filesystem and remain stuck | resolve every partial upload through its persisted `storage_backend`; add mode-switch replay regression | **RESOLVED** |
| `F-P53-010` v3 SQLite snapshot import ordered traces by random event ID | same-second transitions could be reordered after PostgreSQL migration | import in source `seq` order; add reverse-ID/same-timestamp regression | **RESOLVED** |
| `F-P53-011` the inherited P4.4 browser Oracle assumed seven creates stayed inside one fixed 10-second bucket | a boundary crossing produced an unexplained false red during final regression | continue within a bounded 20-create fixture until the first challenge; retain exactly-one challenge and automatic-retry assertions | **RESOLVED** |
| `F-P53-012` an expired outbox worker could retry/isolate after a newer worker reclaimed the event | stale completion could clobber the active lease | mirror due predicates in the claim update and fence retry/isolation by claim attempt | **RESOLVED** |

Phase-review open findings: `0` (`12/12` resolved; accepted risk=`0`).

## 5. Verification

```text
focused consistency/schema tests:                       35 passed
all backend tests:                                      199 passed
Ruff 0.12.12 on changed Python / git diff --check:       PASS / PASS
production Dockerfile frontend+backend build:            PASS
AC-ARCH-002 final-image Oracle:                          PASS
  crash / timeout injections:                           28 / 2
  unexplained terminals / duplicate external effects:   0 / 0
  partial operations / outbox / staged parts:            0 / 0 / 0
P5.1 exact-final-image structured regression:            PASS (14 checks, schema 3)
P5.2 exact-final-image object regression:                PASS (19 checks)
S03/P3.4 + S04/P4.2-P4.3 exact-image Oracle:             PASS
  invalid authorization / secret-canary hits:            0 / 0
S04/P4.4 exact-image abuse Oracle:                       PASS
  normal false positives / attack bypasses:              0/100 / 0
S03/P3.2 public shell desktop/mobile/no-JS/degraded:     PASS (4/4)
S03/P3.3 Chromium/Firefox/WebKit accessibility/index:   PASS (0 severe, 0 canary)
local default/PG/S3 + Coolify Compose renders:            PASS (4/4)
actionlint 1.7.7:                                        PASS
Python dependency audit / npm production audit:          0 / 0 known findings
repository validator / mutation suite / dual-plane:      PASS
```

The backend suite emits one Starlette/httpx deprecation warning; it does not
alter the result. Repository validators are rerun after this receipt and
HANDOFF are added.

## 6. Rollout, rollback and next boundary

P5.3 performs no production rollout. Production remains the verified S04
source/image/deployment tuple; no Cloudflare, Coolify, R2, PostgreSQL, WAF,
production database, object, volume, verifier or recovery material was changed.

A later S05-reviewed rollout must first finish P5.4, preserve and verify all
three volumes and provider objects, run schema expand against a recoverable
backup, deploy the same reviewed image to a canary, keep new processing paused,
run reconciliation and the same failure/duplicate/inventory Oracles, then
enable new uploads for a bounded cohort. Real process/index/export consumers
must implement the tested dedupe contract before their event kinds are enabled.

Fast rollback sets `KMFA_CONSISTENCY_STATE_MODE=paused`, retains schema `3`,
`kmfa-app-state`, `kmfa-postgres-data`, `kmfa-object-data`, the legacy reader,
all provider objects, operations, outbox rows, verifier/session state and the
v1.5 recovery bundle, then runs reconciliation and forward-fixes. It never uses
`docker compose down -v`, deletes a sole raw object, downgrades the schema,
revokes recovery material, force-pushes or replays a historical bundle over
live state.

Stop immediately if reconciliation finds an unexplained terminal, a duplicate
external/financial side effect, a raw-object delete, an identity mismatch
without quarantine, evidence containing credentials/private bytes, or a
production backup cannot be restored before migration.

This is Task `23/56` completed locally; S05 is `3/4` phases complete and the
published Stage remains `5/14`. The next new run may execute only
`S05 / P5.4 / T-S05-04` retention, deletion, backup and restore. It must not
perform whole-S05 review, activate production PostgreSQL/S3, upload this
intermediate phase to GitHub or delete any protected state/recovery asset.
