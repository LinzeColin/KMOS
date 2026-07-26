# STAGE-041 Phase 4 Closeout

- Stage: `STAGE-041`
- Phase: `Phase 4`
- Task: `IDS-V0_1-STAGE041-P4`
- Acceptance: `ACC-STAGE-041`
- Result: `PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED`
- Stage review status: `pending_next_run`
- Next gate: `IDS-STAGE041-REVIEW-GATE`
- Execution ready: `false`

## Source and prerequisite binding

- Approved archive SHA-256: `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`
- Unique Stage041 member: `IDS_v0_1_Final_Chinese_Revised/stages/STAGE-041_锁注册与竞态控制.md`
- Member match count: `1`
- Member SHA-256: `2258a7b57c6c2881f208f43fbe2862c7815a2794c908d6fef108a1a4b5a2ad36`
- Source status: `SOURCE_VERIFIED`
- Phase 3 commit: `03677aaec2fe7dbe6780736bf802e6ef555f383d`
- Phase 3 `KM_IDSystem` tree: `ac363a93c711ac8bf41d9cb3894e37f3b3f1a405`
- Phase 3 prerequisite: committed ancestor of the current Phase 4 branch.

The machine contract rehashes the committed Stage041 Phase 3 contract, checker,
evidence and tests, plus the reviewed Stage040 delivery contract/checker/review
artifact and the Stage037 state index. A shape, hash, commit or tree mismatch
stops before any delivery replay.

## Delivered evidence

The stdout-only checker composes already authorized evidence without creating a
business job or persistent state:

1. Lock lifecycle: five operation families, five primary acquisitions, five
   exact replays and twenty-five same-source conflict decisions under the shared
   `SOURCE_PIPELINE` namespace.
2. Lifecycle safety: renewal advances every lock version once without advancing
   the fence; takeover advances fence and versions; stale CAS/fence evidence is
   rejected; release tombstones and reacquisition remain monotonic.
3. Job state and failure log: `ids.job_state.v1`, 8 job types, 11 states, 4
   terminal states and 21 legal transitions; reviewed failure evidence records
   3 attempts, 2 retries and terminal `DEAD_LETTERED`, with `persisted=false`.
4. Backpressure proof: queue soft/hard pressure, drive offline, insufficient
   disk, insufficient API budget, job-type concurrency and same-source conflict.
5. Cleanup allowlist: only `TEMP_STAGING_OUTPUT` and
   `INCOMPLETE_DERIVATIVE_OUTPUT` are eligible. Fact source, manifest, evidence
   ledger, report snapshot and audit log refs remain protected; no delete path ran.

## Actual isolated orderly release

Phase 4 performed one deterministic process-local control sequence over the real
Git-tracked Phase 1 control reference:

- acquire: `LOCK_SET_ACQUIRED`
- renew: `LEASE_RENEWED`
- release: `LOCK_SET_RELEASED`
- active locks after release: `0`
- tombstone version entries: `2`
- stale commit after release: `STALE_FENCING_TOKEN`
- persistent lock write: `false`

This proves only orderly release of the isolated in-memory registry. It does not
prove process-crash recovery, persistence, production scheduling or production
readiness.

## Automatic and manual handling

Automatic lock decisions are limited to exact idempotent replay, matching-holder
renewal and matching-holder release. These are deterministic lock decisions, not
successful recovery. `automatic_recovery_eligible_cases=[]` and
`successful_automatic_recovery_cases_observed=[]`.

Manual action remains required for stale or incomplete CAS, an active
same-source conflict, resource-gate owner revalidation, worker process crash,
protected cleanup requests, invalid or missing contracts, uncalibrated policy,
and process exit without persistent state. Automatic resume remains owned by
`STAGE-042`; process-crash recovery remains owned by `STAGE-043`; cleanup runtime
remains owned by `STAGE-044`.

## Safe shutdown and recovery

Shutdown order is:

1. stop new lock acquisitions;
2. freeze renew and takeover;
3. preserve reference-only audit and checkpoint refs;
4. release only the matching active lock set;
5. verify zero active locks;
6. verify tombstone versions advanced;
7. verify no persistent or runtime output.

Recovery is fail closed: reverify exact source/policy/upstream hashes, rebuild
only from currently authorized evidence, never restore missing process-local lock
state, reject unknown/stale/incomplete CAS, require owner revalidation for manual
cases, and defer Stage042/043 behavior to their separate gates.

## Rollback

1. `STOP_ON_INVALID_DELIVERY_CONTRACT`
2. `DENY_NEW_LOCK_ACQUISITIONS_REQUIRE_MANUAL_REVIEW`
3. `FREEZE_RENEW_AND_TAKEOVER`
4. `REVERT_PHASE4_FILES_ONLY`
5. preserve Phase 1–3 evidence;
6. preserve reviewed Stage037–040 evidence;
7. preserve raw data and durable evidence without accessing raw contents.

Rollback is non-destructive. It does not rewrite main, pop a stash, delete
history, activate an archived candidate, or touch the raw metadata root.

## Known limits and stop condition

- no persistent lock registry;
- no trusted production clock source; caller-supplied logical time is isolated control evidence only;
- no production queue, worker or lock runtime;
- no production calibration;
- no automatic resume or lifecycle runtime;
- no process-crash recovery;
- no cleanup runtime;
- no database or raw-source access;
- no Stage041 whole-stage review in this run;
- static closeout is not production readiness.

Phase 4 stops here. Only the separate `IDS-V0_1-STAGE041-REVIEW` run is allowed
next. Stage042 entry, ten-stage batch review, GitHub upload/merge, issue mutation
and app reinstall remain disabled.

## Validation record

- TDD RED: 12 focused tests produced 15 expected failures because the P4
  checker, contract, closeout and governance route were absent.
- Core GREEN before governance projection: 10/12 focused tests passed; the only
  two remaining failures were the intentionally absent closeout/governance route.
- GREEN: contract checks 16/16, delivery checks 6/6, focused tests 12/12,
  Stage005 157/157, Stage040-041 aggregate 109/109, full IDS v0.1 discovery
  789/789, and the project-scoped dual-plane gate pass.
- The first unstaged aggregate failed closed on two historical Git-index checks
  plus one stale P3 current-state assertion. After staging, the repaired P3
  compatibility test changed its bound hash; rebinding that single P4 upstream
  SHA restored all checks without weakening any review gate.
