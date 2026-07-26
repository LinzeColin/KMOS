# STAGE-043 Whole-Stage Review

## Review Identity

- Task: `IDS-V0_1-STAGE043-REVIEW`
- Acceptance: `ACC-STAGE-043`
- Review gate: `IDS-STAGE043-REVIEW-GATE`
- Result after repairs: `completed_reviewed_local`
- Next gate: `IDS-STAGE044-P1-GATE`
- Production: disabled

This run independently reviewed Stage 043 Phase 1 through Phase 4 against the
approved taskpack, roadmap, instructions, committed Phase 4 baseline and actual
checker behavior. It did not enter Stage 044, perform the ten-stage batch
review, upload to GitHub, or reinstall an app entry.

## Source And Commit Reverification

The review checker hashes the three approved external files and reads only the
exact Stage043 ZIP member without extracting the archive. It also requires
Phase 4 commit `641009f26df2119cf21bf33640789f4928d94037` to remain an
ancestor of the review commit and its `KM_IDSystem` tree to equal
`da8e19520b72cea9db76656c12ae7ba0a1787287`.

| Source | Verified SHA-256 |
|---|---|
| `IDS_Taskpack_v0_1_only_中文修订版.zip` | `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3` |
| exact `STAGE-043_Worker崩溃恢复.md` member | `e1d5169cbc30515930a7224743b860d9b577ccfbf9e0f913ec254d2ea060317b` |
| `IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt` | `a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6` |
| `IDS_Codex使用说明_v0_1_only_中文修订版.txt` | `ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8` |

The IDS raw-data root remained a path-only governance boundary. No content
under it was listed, opened, hashed, copied, scanned, dumped, moved, changed,
or deleted.

## Findings And Repairs

### STAGE043-REVIEW-F1 - Critical - Repaired

The recovery request validated worker, lease, checkpoint and quarantine fields
individually but did not bind them to one recovery identity. A different lease
owner or an arbitrary syntactically valid digest could therefore retain a
checkpoint-resume candidate.

Repair: `lease_owner_ref` must equal `worker_instance_id`. Checkpoint and
quarantine refs are now deterministic digests of their kind plus the canonical
recovery request key, which already binds job, attempt, worker generation,
state version and crash incident. Mismatched identity evidence returns manual
review with no transition candidate.

### STAGE043-REVIEW-F2 - Important - Repaired

Crash evidence checked heartbeat staleness and lease grace only at evaluation
time. A crash could be marked detected one second before the lease grace
actually elapsed and still be treated as proven.

Repair: both heartbeat staleness and lease-expiry grace must already be true at
`crash_detected_at_epoch_seconds`; detection must then be current relative to
evaluation. Inconsistent temporal evidence returns
`CRASH_EVIDENCE_NOT_CURRENT_OR_PROVEN`.

### STAGE043-REVIEW-F3 - Important - Repaired

`resource_gates_passed=true` could coexist with an active disk, drive or API
pressure signal. The contradictory request could receive a checkpoint-resume
candidate.

Repair: a passed resource gate requires `resource_pressure_signal=NONE`; a
failed gate requires exactly one approved pressure signal. Contradictory pairs
are invalid requests and cannot emit a transition candidate.

### STAGE043-REVIEW-F4 - Important - Repaired

The Stage039 retry path accepted any syntactically safe `error:` reference, and
safe failure did not require Stage039's permanent-error classification. A
permanent or unknown code could therefore be projected as retryable.

Repair: retry candidates accept only Stage039's two exact transient codes;
safe-failure candidates accept only its two exact permanent codes. The isolated
process-exit control code remains limited to checkpoint-resume evidence.

### STAGE043-REVIEW-F5 - Important - Repaired

The Phase 1 checker assumed a JSON object and could raise on a non-mapping
contract instead of returning a structured blocked report. Its live source
check also rehashed the archive/member but not the bound roadmap and usage
instructions.

Repair: non-mapping, malformed and unreadable contracts now evaluate through a
structured fail-closed path. The live source check covers archive, exact member,
roadmap and instructions and catches read/ZIP/JSON failures.

### STAGE043-REVIEW-F6 - Important - Repaired

No durable Stage043 whole-stage review event or reviewed-local route existed;
the batch lock and handoff still stopped at the Phase 4 review-pending gate.

Repair: the handoff, batch lock, roadmap, Stage005 structured validator,
machine facts, rendered owner views and append-only review event now identify
`IDS-V0_1-STAGE043-REVIEW` as complete and route only to the separate
`IDS-V0_1-STAGE044-P1` run. `push_allowed=false` and
`stage044_entry_allowed=false` remain explicit.

Final finding count: `1 Critical / 5 Important / 0 Minor`; all six findings are
repaired and machine checked.

## Acceptance Decision

`ACC-STAGE-043` is closed only as `completed_reviewed_local`. The implementation
remains an isolated reference-only recovery decision and scenario slice. It is
not a persistent recovery registry, process monitor, worker restart service,
state-transition executor, cleanup runtime, production calibration or
production-readiness approval.

The next and only authorized task is the separate
`IDS-V0_1-STAGE044-P1` behind `IDS-STAGE044-P1-GATE`. This review did not
activate Stage 44 cleanup code or authorize any delete operation.

## Validation

- Initial review RED: `10` tests produced `12` assertion failures and `1` error.
- Phase 1/2 repair suite: `30/30`.
- Replayed Phase 3 scenarios: `18/18`.
- Stage043 review tests: `10/10`; Stage005 governance regression: `164/164`.
- Stage041-043 aggregate: `198/198` in `988.205s`.
- Full IDS v0.1 discovery: `940/940` in `1355.634s`.
- Six Stage038-043 whole-stage review checkers returned
  `PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED`; the current checker routes only to
  `IDS-STAGE044-P1-GATE`.
- `210` governance events parsed with zero JSON, duplicate-ID or semantic
  errors. Rendering was idempotent and project-scoped dual-plane validation
  passed.
- The first standalone aggregate and full runs exposed only five historical
  current-gate assertions that stopped before the verified Stage043 review
  route. Their allowlists were extended only through
  `IDS-STAGE043-REVIEW -> IDS-STAGE044-P1-GATE`; runtime behavior, historical
  conclusions and Stage044 authorization were unchanged.
- Project-level Stage005 governance returned `valid=true` with no issues,
  missing files, forbidden paths or unexpected changes. No root-wide validator
  is present in this sparse worktree, so unrelated projects were not expanded.

## Stop Markers

- `NO_STAGE044_THIS_RUN`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_PRODUCTION_RUNTIME`

## Rollback

Revert only the Stage043 review repairs, dependent Phase 2 through Phase 4 hash
bindings, review artifacts and this review's governance transition. Preserve
earlier stages, approved external sources, raw data, owner-controlled
dependencies and services, GitHub state and installed app entries. On any
source, commit, contract, phase, finding, governance or Git-index inconsistency,
restore `IDS-STAGE043-REVIEW-GATE` to blocked and do not proceed to Stage 44.
