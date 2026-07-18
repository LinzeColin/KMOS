# STAGE-042 Phase 3 - Automatic Lifecycle Scenario Validation

## Contract Identity

- Task: `IDS-V0_1-STAGE042-P3`
- Acceptance: `ACC-STAGE-042` remains in progress.
- Policy: `ids.automatic_lifecycle_policy.v0_1.stage042.p2`
- Scenario contract:
  `automatic_lifecycle/stage042_automatic_lifecycle_scenarios.json`
- Checker: `KM_IDSystem/scripts/check_automatic_lifecycle_scenarios.py`
- Mode: `ISOLATED_NON_PRODUCTION_AUTOMATIC_LIFECYCLE_SCENARIOS`
- Next separate gate: `IDS-STAGE042-P4-GATE`

The approved Stage042 taskpack member remains unique with SHA-256
`78a4bed1f5348837699bd7dd227898e6d47cc4099ca268ee1600bae84605ec08`.
This Phase binds committed Phase 2 `32bd7d9775229e03cd9855edc4e5b737860b6af7`,
its `KM_IDSystem` subtree `6ddb0c27a95afa1662a892e6bb3b5d890f72f963`,
the exact Phase 2 contract/checker/test/evidence hashes, and reviewed Stage041
lock-scenario evidence.

## Scenario Evidence

The checker executes twelve isolated control scenarios:

1. exact duplicate lifecycle request replay;
2. changed payload under one request ID;
3. stale start observation;
4. external-drive pause then owner/stability-gated resume;
5. actual project-volume observation plus controlled low-disk boundary;
6. external-API-budget pause without an API call;
7. actual isolated worker exception with crash recovery retained by Stage043;
8. same-source exclusion for processing, extraction, indexing and reporting;
9. ordered safe-shutdown candidate;
10. shutdown timeout failure closure;
11. five protected cleanup classes;
12. two eligible classes that remain cleanup candidates only.

All lifecycle outputs are candidates. No transition is applied. The drive and
API cases are control metadata, not physical actions. The disk case observes
only free bytes on the project filesystem and allocates nothing. The worker
case replays an actual isolated `RuntimeError`, not a process crash. Lock
evidence is inherited from the reviewed Stage041 5-family/25-conflict matrix.

## Explicit Non-Actions

- no actual start, pause, resume, shutdown or state mutation;
- no queue, worker, retry scheduler or production lock runtime;
- no process termination or process-crash recovery;
- no physical drive removal, disk allocation or external API call;
- no cleanup/delete, persistence, database, schema or runtime-output write;
- no raw metadata or IDS business-source access and no fake business data;
- no Phase 4, whole-stage review, batch review, GitHub action or app reinstall.

## Verification State

- TDD RED: `17` focused tests produced `2` expected failures and `15` expected
  errors because the Phase 3 artifacts and governance route did not exist.
- The first implementation-state run exposed a false-flag naming mismatch and
  a nondeterministic comparison of truthful project free-space observations;
  both are narrowed without weakening any scenario.
- Final GREEN: checker `19/19` contract checks and `12/12` scenarios;
  focused `17/17`; Stage004 `3/3`; Stage005 `159/159`; Stage037-039
  `124/124`; Stage040-042 `162/162`; full IDS v0.1 `844/844` in
  `618.960s`; `203` events with zero parse, duplicate or semantic errors;
  idempotent render and project-scoped dual-plane PASS.
- Governance synchronization exposed two unregistered English terms in
  generated Chinese owner views; both were replaced with governed Chinese
  wording without widening the glossary.
- The exact Stage041 scenario-test -> delivery-contract -> Stage042
  Phase1/2/3 Git-index hash chain was rebound while preserving historical
  evidence.

## Rollback and Stop

Revert only Phase 3 scenario contract/checker/test/evidence and governance
transition files. Preserve Phases 1-2, Stage037-041, owner files, raw data,
database/runtime paths, GitHub state and app entries. Any invalid source,
commit, upstream hash or protected boundary returns to
`IDS-STAGE042-P3-GATE`; Phase 4 never starts in this run.

`push_allowed=false`; `NO_PHASE4_THIS_RUN`.
