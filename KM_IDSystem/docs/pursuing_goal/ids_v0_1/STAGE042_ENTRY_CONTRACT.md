# STAGE-042 Phase 1 Entry Contract

## Identity

- Stage: `STAGE-042 · 自动运行、暂停、恢复与关闭`
- Task: `IDS-V0_1-STAGE042-P1`
- Acceptance: `ACC-STAGE-042`
- Local code: `D07-S006`
- Domain: `D07 · 任务编排与机器控制`
- Entrance: `IDS 系统运营入口`
- Contract: `ids.automatic_lifecycle.v0_1.p1`
- State: `PHASE1_ENGINEERING_CONTRACT_RUNTIME_DISABLED`
- Next gate: `IDS-STAGE042-P2-GATE`

## Goal

Define an executable, testable and rollback-ready engineering contract for
automatic start, safe pause, guarded resume, safe close and cleanup-candidate
emission. Phase 1 produces reference-only lifecycle decisions; it performs no
state mutation, queue admission, worker action, retry scheduling, lock action,
process recovery or delete.

## Source And Predecessor Binding

The unique approved member
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-042_自动运行、暂停、恢复与关闭.md`
has SHA-256
`78a4bed1f5348837699bd7dd227898e6d47cc4099ca268ee1600bae84605ec08`.
The machine contract also binds the approved archive, roadmap, instructions,
the reviewed Stage041 commit/tree and the exact Stage037–041 tracked
contracts. No IDS business source or raw metadata content was read.

## Entry Preconditions

- Stage041 is closed only as `completed_reviewed_local` at commit
  `f6b30f8a55d60f1b37b9d57ee55587149ad43876`.
- Stage037 remains the only job-state and transition authority.
- Stage038 owns queue/worker transport; Stage042 cannot spawn, terminate or
  recover a worker.
- Stage039 owns retry/dead-letter admission and budget.
- Stage040 owns pressure observations and pause decisions.
- Stage041 owns lock, lease and fencing decisions.
- Stage043 owns process-crash recovery; Stage044 owns cleanup execution.
- The raw metadata root remains a path-only boundary and is untouched.

## Phase 1 Deliverables

1. This entry contract.
2. `STAGE042_PHASE1_AUTOMATIC_LIFECYCLE_SCOPE_BOUNDARY.md`.
3. `automatic_lifecycle/stage042_automatic_lifecycle_contract.json`.
4. `scripts/check_automatic_lifecycle.py`.
5. `tests/test_stage042_automatic_lifecycle.py`.
6. Minimal batch, roadmap, event, handoff and dual-plane routing.

## Stop Boundary

`Phase 2 must run separately`. This run stops after a static, fail-closed
contract and does not perform any automatic lifecycle action.

- `NO_PHASE2`
- `NO_AUTOMATIC_LIFECYCLE_RUNTIME`
- `NO_QUEUE_RUNTIME`
- `NO_WORKER_RUNTIME`
- `NO_RETRY_SCHEDULER`
- `NO_PRODUCTION_LOCK_RUNTIME`
- `NO_PROCESS_CRASH_RECOVERY`
- `NO_CLEANUP_DELETE`
- `NO_DATABASE_OR_SCHEMA_CHANGE`
- `NO_RUNTIME_OUTPUT`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

`push_allowed=false`. The next task is only
`IDS-V0_1-STAGE042-P2` in a separate run.

## Rollback

Revert only Stage042 Phase 1 artifacts and its governance projection. Preserve
Stage041 review history, earlier stages, raw data, manifests, evidence ledgers,
audit logs, report snapshots, databases, runtime outputs, GitHub state and app
entries.
