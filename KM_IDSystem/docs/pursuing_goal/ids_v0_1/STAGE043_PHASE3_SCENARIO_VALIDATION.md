# STAGE-043 Phase 3 - Worker Crash Recovery Scenario Validation

## Contract Identity

- Task: `IDS-V0_1-STAGE043-P3`
- Acceptance: `ACC-STAGE-043` remains in progress.
- Policy: `ids.worker_crash_recovery_policy.v0_1.stage043.p2`
- Scenario contract:
  `worker_crash_recovery/stage043_worker_crash_recovery_scenarios.json`
- Checker: `KM_IDSystem/scripts/check_worker_crash_recovery_scenarios.py`
- Mode: `ISOLATED_NON_PRODUCTION_WORKER_CRASH_RECOVERY_SCENARIOS`
- Next separate gate: `IDS-STAGE043-P4-GATE`

The unique approved Stage043 task-pack member remains SHA-256
`e1d5169cbc30515930a7224743b860d9b577ccfbf9e0f913ec254d2ea060317b`.
This phase binds committed Phase 2
`b1a8e4689eb9c3a3a469a9f8d77dff4683aa709c`, its `KM_IDSystem` subtree
`6a3c6f683ab2e2e263b36463f0dc20d2ff277985`, the exact Phase 2
contract/checker/test/evidence hashes and current Stage041 lock-scenario
evidence.

## Scenario Evidence

The checker executes thirteen isolated control scenarios:

1. exact duplicate recovery-request replay;
2. changed payload under one recovery request key;
3. stale crash/heartbeat evidence;
4. one ephemeral control child that self-exits with code `73`;
5. an unfenced lost-worker generation;
6. external-drive-offline control pause;
7. actual project-volume observation plus a controlled low-disk boundary;
8. external-API-budget pause without an API call;
9. same-source exclusion for processing, extraction, indexing and reporting;
10. an active lock or claim conflict;
11. immutable terminal history;
12. five Git-tracked protected cleanup classes;
13. two reference-only partial-output quarantine candidates.

The child process receives no IDS input, emits no output and exits itself. The
checker sends no signal, performs no external process probe, and does not
restart or recover it. This is isolated process-loss evidence, not a production
worker-crash claim. Every recovery result remains a candidate; no transition,
checkpoint continuation or persistent write is applied.

The drive and API scenarios use controlled metadata, not physical actions. The
disk scenario observes only free bytes on the project filesystem and allocates
nothing. The four-operation exclusion proof is a selected subset of the
reviewed Stage041 five-family, 25-conflict matrix and invokes no operation.

## Protected Output Boundary

`FACT_SOURCE`, `MANIFEST`, `EVIDENCE_LEDGER`, `REPORT_SNAPSHOT` and
`AUDIT_LOG` are resolved to exact Git-tracked refs and never enter a delete
surface. `TEMP_STAGING_OUTPUT` and `INCOMPLETE_DERIVATIVE_OUTPUT` receive only
deterministic quarantine refs; Stage044 remains the sole cleanup owner and no
delete attempt occurs.

## Explicit Non-Actions

- no external process probe, signal, kill, termination, restart or recovery;
- no production worker, queue, retry scheduler, pressure or lock runtime;
- no job-state, lock, lease, fence, checkpoint, output or registry mutation;
- no physical drive removal, disk allocation or external API call;
- no cleanup/delete, persistence, database, schema or runtime-output write;
- no raw metadata, IDS business-source access or fake business data;
- no Phase 4, whole-stage review, batch review, GitHub action or app reinstall.

## Verification State

- TDD RED: `18` focused tests produced `2` expected failures and `16` expected
  errors because the Phase 3 contract, checker, evidence and governance route
  did not exist.
- Final GREEN: checker `18/18` contract and `13/13` scenarios, focused `18/18`, Stage005 `162/162`, Stage041-043 aggregate `174/174` in `563.213s`, full IDS v0.1 discovery `914/914` in `928.016s`, five historical Stage038-042 review checkers, 208-event semantics, idempotent render and project dual-plane all pass.

## Rollback and Stop

Revert only the Phase 3 scenario contract/checker/test/evidence and governance
transition files. Preserve Phases 1-2, Stage037-042, owner files, raw data,
database/runtime paths, GitHub state and app entries. Any invalid source,
commit, upstream hash or protected boundary returns to
`IDS-STAGE043-P3-GATE`; Phase 4 never starts in this run.

`push_allowed=false`; `NO_PHASE4_THIS_RUN`.
