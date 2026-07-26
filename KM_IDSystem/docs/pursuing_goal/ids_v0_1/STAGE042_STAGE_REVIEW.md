# STAGE-042 Whole-Stage Review

## Review Identity

- Task: `IDS-V0_1-STAGE042-REVIEW`
- Acceptance: `ACC-STAGE-042`
- Review gate: `IDS-STAGE042-REVIEW-GATE`
- Result after repairs: `completed_reviewed_local`
- Next gate: `IDS-STAGE043-P1-GATE`
- Production: disabled

This run independently reviewed Stage 042 Phase 1 through Phase 4 against the
approved taskpack, roadmap, instructions, committed Phase 4 baseline and actual
checker behavior. It did not enter Stage 043, perform the ten-stage batch
review, upload to GitHub, or reinstall an app entry.

## Source And Commit Reverification

The review checker hashes the three approved external files and reads only the
exact Stage042 ZIP member without extracting the archive. It also requires
Phase 4 commit `2c489d049d73cd632e905c7af1b39ba662a2139b` to remain an ancestor of
the review commit and its `KM_IDSystem` tree to equal
`7d77abfd6c00ea3b663d899335d971342ac40384`.

| Source | Verified SHA-256 |
|---|---|
| `IDS_Taskpack_v0_1_only_中文修订版.zip` | `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3` |
| exact `STAGE-042_自动运行、暂停、恢复与关闭.md` member | `78a4bed1f5348837699bd7dd227898e6d47cc4099ca268ee1600bae84605ec08` |
| `IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt` | `a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6` |
| `IDS_Codex使用说明_v0_1_only_中文修订版.txt` | `ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8` |

The IDS raw-data root remained a path-only governance boundary. No content
under it was listed, opened, hashed, copied, scanned, dumped, moved, changed,
or deleted.

## Findings And Repairs

### STAGE042-REVIEW-F1 - Critical - Repaired

The contract declared a canonical lifecycle request-ID formula, but the
runtime accepted any string with the expected prefix. A caller could alter the
ID while preserving the payload and admit what should be the same request as a
new lifecycle decision.

Repair: new requests must use exactly
`lifecycle:stage042:<sha256(canonical request without ID)>`. A mismatch returns
`REJECT_LIFECYCLE_REQUEST_ID_MISMATCH` without a ledger write. Exact replay
still returns the original result, while changed payload under an existing ID
retains `REJECT_LIFECYCLE_REQUEST_CONFLICT` precedence.

### STAGE042-REVIEW-F2 - Important - Repaired

`expected_state_version=0` passed the non-negative integer guard, and a valid
uppercase reason code was not bound to its lifecycle action.

Repair: versions must be strict positive integers, excluding booleans and
floats. Each of the five actions now has one exact reason code in both the
contract and validator; zero, negative, boolean, float and mismatched-action
requests fail closed before candidate evaluation.

### STAGE042-REVIEW-F3 - Important - Repaired

Resume accepted a caller-reported `resource_stable_for_seconds=60` even when
the observation and evaluation timestamps provided no proof that the window
had elapsed.

Repair: resume evidence includes a stability-start timestamp and requires
`start <= observed <= evaluated` plus an exact
`stable_for == evaluated - start` relationship. Only a temporally consistent
window of at least 60 proposed seconds can emit a resume candidate.

### STAGE042-REVIEW-F4 - Important - Repaired

Cleanup candidate evaluation did not require a quiescent job state. A caller
could set `active_claim_or_lock=false` and obtain a cleanup candidate from
`CREATED`, `QUEUED`, `RUNNING`, or `RETRY_WAIT`.

Repair: the Stage042 decision slice admits cleanup candidates only from
`PAUSED`. Eligible artifacts remain candidate-only and Stage044-owned; no
delete or cleanup runtime is exposed.

### STAGE042-REVIEW-F5 - Important - Repaired

The lower staged-development handoff still routed from Phase 3 to Phase 4, and
no durable Stage042 whole-stage review event or reviewed-local gate existed.

Repair: handoff, batch lock, roadmap, Stage005 structured validation, machine
facts, rendered owner views and the append-only review event now identify
`IDS-V0_1-STAGE042-REVIEW` as complete and route only to the separate
`IDS-V0_1-STAGE043-P1` run. `push_allowed=false` and
`stage043_entry_allowed=false` remain explicit.

Final finding count: `1 Critical / 4 Important / 0 Minor`; all five findings
are repaired and machine checked.

## Acceptance Decision

`ACC-STAGE-042` is closed only as `completed_reviewed_local`. The lifecycle
engine remains deterministic in-memory decision evidence, not an executor,
scheduler, process-crash recovery service, cleanup runtime, persistence layer,
production calibration or production-readiness approval.

The next and only authorized task is the separate
`IDS-V0_1-STAGE043-P1` behind `IDS-STAGE043-P1-GATE`. This review did not
activate Stage 43 or claim its ancestry review.

## Validation

- Initial review RED: `10` tests, `12` assertion failures and `3` errors.
- Repaired Phase 2: checker `20/20` contract and `18/18` decision checks;
  focused `16/16`.
- Replayed Phase 3 scenarios: focused `17/17`.
- Replayed Phase 4 delivery: focused `12/12`.
- Final Stage042 review suite: `10/10` in `266.052s`; affected Phase 2–4
  compatibility suite: `45/45` in `113.725s`.
- Stage005 governance regression: `159/159` in `17.454s`; Stage040–042
  aggregate: `184/184` in `678.115s`.
- The first full `866`-test discovery exposed three Stage038 historical
  current-gate allowlists that ended at Stage042. The allowlists were bounded
  to the reviewed `IDS-STAGE043-P1-GATE`; the final full discovery passed
  `866/866` in `985.194s`.
- Stage038, Stage040, historical batch, Stage041 and Stage042 review checkers
  all passed. Stage005 reported `valid=true`; `205` events had zero parse,
  semantic or duplicate-ID errors; rendering was idempotent and the
  project-scoped dual-plane gate passed.
- The root governance runner is absent from this sparse checkout. The sparse
  scope was not expanded and no unrelated project was inspected.

## Stop Markers

- `NO_STAGE043_THIS_RUN`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_PRODUCTION_RUNTIME`

## Rollback

Revert only the Stage042 review repairs, dependent Phase 2 through Phase 4
hash bindings, review artifacts and this review's governance transition.
Preserve earlier stages, approved external sources, raw data, owner-controlled
dependencies and services, GitHub state and installed app entries. On any
source, commit, contract, phase, finding, governance or Git-index
inconsistency, restore `IDS-STAGE042-REVIEW-GATE` to blocked and do not proceed
to Stage 43.
