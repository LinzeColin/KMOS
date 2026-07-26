# STAGE-041 Phase 1 Entry Contract

## Identity

- Stage: `STAGE-041 · 锁注册与竞态控制`
- Task: `IDS-V0_1-STAGE041-P1`
- Acceptance: `ACC-STAGE-041`
- Local code: `D07-S005`
- Domain: `D07 · 任务编排与机器控制`
- Entrance: `IDS 系统运营入口`
- Contract: `ids.lock_registry.v0_1.p1`
- State: `PHASE1_ENGINEERING_CONTRACT_RUNTIME_DISABLED`
- Next gate: `IDS-STAGE041-P2-GATE`

## Goal

Define an executable and testable engineering contract for lock registration,
lease ownership, fencing and race control across file processing, archive
extraction, index build, index switch and report generation. Phase 1 defines
reference-only metadata and fail-closed decisions; it does not acquire a lock
or start a worker.

## Source Binding

The unique task-pack member
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-041_锁注册与竞态控制.md` was read
from the approved v0.1 archive. Its member SHA256 is
`2258a7b57c6c2881f208f43fbe2862c7815a2794c908d6fef108a1a4b5a2ad36`.
The archive, Roadmap, instruction and reviewed upstream-contract hashes are
recorded in the machine contract. No IDS business source or raw metadata
content was read.

## Entry Preconditions

- BATCH-031-040 is merged to GitHub main and its terminal evidence is bound.
- STAGE-037 `ids.job_state.v1` remains authoritative for legal state changes.
- STAGE-038 owns queue/worker transport and its same-source conflict baseline
  remains mandatory.
- STAGE-039 owns retry/dead-letter policy; lock contention consumes no retry.
- STAGE-040 owns pressure observation and legal pause decisions.
- The metadata root remains path-only and untouched.
- Owner-authored dirty files and root `.DS_Store` remain outside this task.

## Phase 1 Deliverables

1. This entry contract.
2. `STAGE041_PHASE1_LOCK_REGISTRY_SCOPE_BOUNDARY.md`.
3. `lock_registry/stage041_lock_registry_contract.json`.
4. `scripts/check_lock_registry.py`.
5. `tests/test_stage041_lock_registry.py`.
6. `BATCH041_050_UPLOAD_LOCK.yaml` and minimal governance routing.

## Stop Boundary

`Phase 2 must run separately`. It must source every numeric parameter before
running an isolated non-production lock decision slice. This run stops at:

- `NO_PHASE2`
- `NO_LOCK_RUNTIME`
- `NO_LEASE_RUNTIME`
- `NO_FENCING_RUNTIME`
- `NO_QUEUE_RUNTIME`
- `NO_WORKER_RUNTIME`
- `NO_RETRY_SCHEDULER`
- `NO_AUTOMATIC_RESUME`
- `NO_CRASH_RECOVERY_RUNTIME`
- `NO_CLEANUP_RUNTIME`
- `NO_POSTGRES_CONNECTION`
- `NO_SCHEMA_CHANGE`
- `NO_RUNTIME_OUTPUT`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

`push_allowed=false`. The next task is only `IDS-V0_1-STAGE041-P2` in a
separate run.

## Rollback

Revert only STAGE-041 Phase 1 artifacts and its governance transition. Do not
touch earlier Stages, the raw metadata root, databases, runtime outputs,
reports, owner-authored dirty files, GitHub state, or app entries.
