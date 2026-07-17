# STAGE-041 Phase 3 - Lock Registry Scenario Validation

## Contract Identity

- Stage: `STAGE-041 · 锁注册与竞态控制`
- Task: `IDS-V0_1-STAGE041-P3`
- Acceptance: `ACC-STAGE-041` remains `in_progress`
- Policy: `ids.lock_registry_policy.v0_1.stage041.p2`
- Mode: `ISOLATED_NON_PRODUCTION_LOCK_REGISTRY_SCENARIOS`
- Scenario contract:
  `lock_registry/stage041_lock_registry_scenarios.json`
- Checker: `KM_IDSystem/scripts/check_lock_registry_scenarios.py`
- Next separate gate: `IDS-STAGE041-P4-GATE`

The approved taskpack and current roadmap were read before implementation. The
unique Stage041 taskpack member remains
`IDS_v0_1_Final_Chinese_Revised/stages/STAGE-041_锁注册与竞态控制.md`
with SHA-256
`2258a7b57c6c2881f208f43fbe2862c7815a2794c908d6fef108a1a4b5a2ad36`.
The contract binds the committed Phase 2 commit
`22bd9263e38b697dfb681886a97c1b8ba0f4b5e9`, its exact KM_IDSystem tree
`c3e96185d5fe185fc9a8c27e8fa57a6279bc4e6d`, and current hashes for the
Phase 2 runtime/evidence/test surfaces plus the reviewed Stage040 pressure
scenario contract and checker.

## Scenario Evidence

| Scenario | Controlled result | Physical or production action |
|---|---|---|
| duplicate click | exact acquisition replay keeps fence/version unchanged; the same key with changed input fails closed | no job or persistent write |
| five-operation exclusion matrix | each of file processing, archive extraction, index build, index switch and report generation acquires once and replays once; all 25 same-source contender combinations return `RESOURCE_CONFLICT_ACTIVE` | no operation invocation or queue admission |
| renewal | the fence is preserved while every lock version advances once; pre-renewal commit/renew/release evidence is rejected | logical clock only; no sleep |
| expiry takeover | takeover is denied before expiry plus grace and succeeds exactly at the boundary with one fence and all-version advance | no background expiry worker |
| stale CAS | stale and incomplete takeover evidence are rejected without lock-state or fence mutation | no persistence |
| worker exception boundary | an actual isolated `RuntimeError` occurs while the lock remains held and a contender is blocked | no process termination; crash recovery remains `STAGE-043` |
| external drive offline | reviewed Stage040 control metadata requests a pre-lock pause | no physical drive removal |
| low disk | actual project-filesystem free space is observed and a controlled insufficient-space boundary pauses before lock acquisition | no disk allocation |
| API budget | reviewed Stage040 control metadata requests a pre-lock pause | no external API call |
| release/reacquire | release advances tombstone versions; reacquire advances every version and the fence again | no persistent tombstone write |
| protected cleanup | fact source, manifest, evidence ledger, report snapshot and audit log are Git-tracked and return `PROTECTED_ARTIFACT` | no delete API or delete attempt |

The worker scenario is an actual exception boundary, not a worker-process
crash. The drive and API cases are bounded control metadata, not physical
failure claims. The disk scenario performs a read-only observation of the
project filesystem and uses a separate calculated boundary; it does not
allocate disk. Pressure decisions are evaluated before lock acquisition, so
the lock registry remains unchanged for all three resource-pause cases.

## Scope Proof

- no IDS business source or job and no fabricated business data;
- no raw metadata content access;
- no queue, worker, retry scheduler, automatic resume, process recovery,
  cleanup/delete, persistence, state-registry write or database connection;
- no physical drive removal, disk allocation, process termination or external
  API call;
- no production runtime, Phase 4, whole-stage review, batch gate, GitHub action,
  PR, merge, issue mutation or app reinstall;
- `push_allowed=false`.

## Verification State

- TDD RED: all `15` focused tests failed (`18` assertions) because the Phase 3
  contract, checker, evidence and governance transition did not exist.
- GREEN: `17/17` contract checks, `11/11` isolated scenarios, focused tests
  `15/15`, Stage005 governance `157/157`, Stage040-041 aggregate `97/97`, and
  full IDS v0.1 discovery `777/777` passed.
- The first aggregate/full runs reached `95/97` and `762/777`. All `17`
  failures were the expected Git-index-bound historical reviews while the new
  Phase 3 governance sources were still unstaged; staging the complete Phase 3
  set restored every review without weakening a checker.
- The next staged full run reached `776/777` and exposed one stale Stage039
  compatibility map that allowed the Stage041 route only through Phase 2.
  Adding the current `IDS-STAGE041-P3 -> IDS-STAGE041-P4-GATE` mapping repaired
  that compatibility assertion without changing historical Stage039 evidence.
- Project-scoped dual-plane rendering and governance passed after adding the
  four explicit `commit`, `tree`, `drive`, and `disk` glossary terms.
- Remote-main drift from `9f2605ffde977bec1f048d773a4c0549777875d8` to
  `4b0d564122541a024585ca69fb9b990edb27486f` touched zero
  `KM_IDSystem` paths. Phase 2 was rebased to
  `22bd9263e38b697dfb681886a97c1b8ba0f4b5e9` without changing its
  `KM_IDSystem` tree.
- Phase 4 did not run.

## Rollback

Revert only the Phase 3 scenario contract, checker, focused tests, evidence and
governance transition. Preserve Phases 1-2, Stage037-040, owner-authored dirty
files, raw data, database/runtime paths, GitHub state and app entries. A failed
rollback or invalid binding returns to `IDS-STAGE041-P3-GATE`; it must not
authorize Phase 4 automatically.
