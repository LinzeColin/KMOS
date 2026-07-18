# STAGE-042 Phase 2 Automatic Lifecycle Decision Slice

## Identity

- Task: `IDS-V0_1-STAGE042-P2`
- Acceptance: `ACC-STAGE-042`
- Policy: `ids.automatic_lifecycle_policy.v0_1.stage042.p2`
- Mode: `ISOLATED_NON_PRODUCTION_REFERENCE_ONLY_LIFECYCLE_DECISION_SLICE`
- Next gate: `IDS-STAGE042-P3-GATE`

## Controlled Evidence

This Phase implements one deterministic, in-memory decision slice over the
real Git-tracked Phase 1 control boundary. It evaluates five candidate types:

1. `AUTO_START`: proposes `QUEUED -> CLAIMED -> RUNNING` only after fresh
   admission, claim, lease, lock and fencing evidence.
2. `AUTO_PAUSE`: proposes only legal queued/retry or
   `PAUSE_REQUESTED`-mediated active paths. Drive offline, insufficient disk
   and insufficient API budget remain mandatory pause signals.
3. `AUTO_RESUME`: proposes only `PAUSED -> QUEUED` after owner revalidation,
   fresh resource gates, a full stability window and zero active claim/lock.
4. `SAFE_SHUTDOWN`: proposes an ordered legal close path without terminating a
   process, releasing a lock or mutating a job.
5. `CLEANUP_CANDIDATE_SCAN`: emits only an eligible-class candidate for the
   separate Stage 44 gate and exposes no delete path.

Every result records Git-tracked control input references, empty output
references, a safe error reference when blocked, a control checkpoint digest
and a durable audit reference. IDs use the `control:stage042:` namespace and
are not IDS business jobs. The checker writes only its JSON report to stdout.

## Proposed Parameters

All five values are `PROPOSED`, registered as planned and linked to
`TASK-OPME-B-001`. They are logical control bounds; this Phase does not sleep,
schedule, wait, scan or calibrate production behavior.

| Parameter | Value | Derivation |
|---|---:|---|
| `lifecycle_tick_interval` | 1 s | reviewed Stage 41 acquisition timeout |
| `resume_stability_window` | 60 s | two reviewed Stage 40 observation TTL windows |
| `checkpoint_wait_timeout` | 30 s | one reviewed Stage 41 lease duration |
| `graceful_shutdown_timeout` | 60 s | two reviewed Stage 41 lease durations |
| `cleanup_scan_interval` | 300 s | five reviewed Stage 40 API control windows |

Invalid source, contract, parameter, request, evidence, state version, owner
revalidation, timing relationship or upstream hash returns a manual-review or
explicit rejection result. Rollback is `NO_AUTOMATIC_LIFECYCLE` plus removal of
Phase 2 files only.

## Explicit Non-Actions

- no state, queue, worker, retry, lock, lease or fencing mutation;
- no automatic start, pause, resume or shutdown execution;
- no process termination or crash recovery;
- no cleanup/delete or protected-artifact action;
- no database, schema, registry-state or runtime-output write;
- no external API, raw metadata or IDS business-source access;
- no fake business data or fabricated business job;
- no production activation, GitHub action or app reinstall.

## Validation

- TDD RED: 16 focused tests produced four expected failures and fifteen expected
  errors before the Phase 2 contract, checker, registries and governance route
  existed.
- GREEN: checker `20/20` contract and `13/13` decision checks, focused `16/16`,
  Stage004 `3/3`, Stage005 `159/159`, Stage037-039 `124/124`, Stage040-042
  `145/145`, full IDS v0.1 `827/827`, `202` clean events, idempotent rendering
  and project-scoped dual-plane PASS.
- The first full run reached `826/827` and exposed three exact
  `TASK-OPME-B-001` governance-ID occurrences as legacy display-name debt. The
  compatibility classifier now accepts only exact `TASK-/FEAT-OPME-*` IDs in
  checker and machine evidence; actual legacy display names still fail closed.

## Phase 3 Gate

Phase 3 must run separately. It may validate duplicate requests, resource
pause/resume, stale evidence, worker-crash ownership, duplicate-operation lock
proofs and protected cleanup boundaries. It must not reinterpret this Phase as
production runtime evidence.

Stop markers:

- `NO_PHASE3_THIS_RUN`
- `NO_ACTUAL_AUTOMATIC_LIFECYCLE`
- `NO_PERSISTENCE`
- `NO_PROCESS_TERMINATION`
- `NO_CLEANUP_DELETE`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

`push_allowed=false`; the only next task is `IDS-V0_1-STAGE042-P3`.
