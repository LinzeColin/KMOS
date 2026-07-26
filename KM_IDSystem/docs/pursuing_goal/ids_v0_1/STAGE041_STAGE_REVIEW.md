# STAGE-041 Whole-Stage Review

## Review Identity

- Task: `IDS-V0_1-STAGE041-REVIEW`
- Acceptance: `ACC-STAGE-041`
- Review gate: `IDS-STAGE041-REVIEW-GATE`
- Result after repairs: `completed_reviewed_local`
- Next gate: `IDS-STAGE042-P1-GATE`
- Production: disabled

This run independently reviewed Stage 041 Phase 1 through Phase 4 against the
approved taskpack, roadmap, instructions, current engineering contracts and
actual checker behavior. It did not enter Stage 042, perform the ten-stage
batch review, upload to GitHub, or reinstall an app entry.

## Source Reverification

The review checker hashes the three approved external files and reads only the
exact Stage041 ZIP member with Python `zipfile`; it does not extract the
archive.

| Source | Verified SHA-256 |
|---|---|
| `IDS_Taskpack_v0_1_only_中文修订版.zip` | `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3` |
| `IDS_v0_1_Final_Chinese_Revised/stages/STAGE-041_锁注册与竞态控制.md` | `2258a7b57c6c2881f208f43fbe2862c7815a2794c908d6fef108a1a4b5a2ad36` |
| `IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt` | `a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6` |
| `IDS_Codex使用说明_v0_1_only_中文修订版.txt` | `ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8` |

The IDS raw-data root remained a path-only governance boundary. No content
under it was listed, opened, hashed, copied, scanned, dumped, moved, changed,
or deleted.

## Findings And Repairs

### STAGE041-REVIEW-F1 - Critical - Repaired

CAS evidence accepted Python `bool` and integral `float` values because both
compare equal to integers. A forged `lock_versions` map containing `true` or
`1.0` could therefore pass `can_commit`, and a boolean map could authorize a
takeover.

Repair: all lock-version evidence now requires `type(value) is int` and
`value > 0`. Invalid commit evidence returns `STALE_FENCING_TOKEN` with
`REJECT_COMMIT`; invalid takeover evidence returns
`STALE_TAKEOVER_EVIDENCE`. Focused tests cover both Python edge types.

### STAGE041-REVIEW-F2 - Important - Repaired

The process-local engine accepted negative or backward caller-supplied logical
time. Renewal could shrink a lease, commit could be backdated, and release at
the expiry boundary could discard an expired lock despite the absence of a
trusted production clock.

Repair: request time must be non-negative; mutation and commit observations
cannot precede the latest record time; renewal must strictly extend expiry;
release requires a live lease. Regression, non-extension and expiry return
explicit fail-closed codes while preserving the lock. The delivery known
limits now include `NO_TRUSTED_PRODUCTION_CLOCK_SOURCE`.

### STAGE041-REVIEW-F3 - Important - Repaired

The Phase 2 contract checker validated field presence but not the exact
operation-to-job mapping, parameter relationships, or nonblank provenance.
Semantically unrelated values could therefore retain a green structural
report.

Repair: the checker now requires the exact five operation scopes and job-type
mappings, exact relationship expressions and metadata, nonblank source and
validation evidence, and the exact rollback action for every proposed
parameter. Tampering any of these fields fails the contract.

### STAGE041-REVIEW-F4 - Important - Repaired

The top of `HANDOFF.md` still identified an older Stage041 phase and conflicted
with the later Phase 4/governance state. No durable reviewed-local route or
Stage041 review event existed, so an agent could resume from the wrong gate.

Repair: the handoff, batch lock, roadmap, Stage005 structured validator,
machine facts and rendered owner views now identify
`IDS-V0_1-STAGE041-REVIEW` as complete and route only to the separate
`IDS-V0_1-STAGE042-P1` run. `push_allowed=false` and
`stage042_entry_allowed=false` remain explicit.

Final finding count: `1 Critical / 3 Important / 0 Minor`; all four findings
are repaired and machine checked.

## Acceptance Decision

`ACC-STAGE-041` is closed only as `completed_reviewed_local`. The lock
registry remains an isolated process-memory engineering slice with
caller-supplied logical time. It is not a persistent registry, a production
clock/lease service, an automatic-resume implementation, crash recovery, or a
production-readiness approval.

The next and only authorized task is the separate
`IDS-V0_1-STAGE042-P1`. That task must run behind
`IDS-STAGE042-P1-GATE`; this review did not activate Stage 42 code or claim its
ancestry review.

## Validation

The initial review test run produced nine failing test methods plus two error
outcomes. After all four findings were repaired and the complete review source
set was staged, final layered validation passed:

- Stage041 review focused tests: `9/9`.
- Phase 4 plus review aggregate: `21/21` in `196.971s`.
- Stage041 Phase 1–4 plus review aggregate: `63/63` in `207.846s`.
- Stage040–041 aggregate: `118/118` in `296.487s`.
- Stage005 governance regression: `157/157`.
- Full IDS v0.1 discovery: `798/798` in `555.092s`.
- Governance events: `200`, with zero parse, duplicate-ID, or semantic errors.
- Review-event changed files and staged paths: exact `34/34` match.
- Project-scoped machine/human dual-plane gate: `PASS`.
- Human rendering is idempotent; cached and unstaged diff checks are clean.

The repository-root `scripts/lean_governance.py` entry point is absent from
this sparse worktree. Per the sparse-scope stop rule, the review did not expand
or inspect unrelated projects; project-scoped Stage005, event, render and
dual-plane gates are the minimum governance evidence for this run.

Before final commit, `origin/main` advanced with the KM_IDS renderer fix from
`dec58884`. This worktree reproduced only that four-line project-local change,
verified that `render_human.py` matches `origin/main`, and did not merge or
rebase the unrelated remote commits that would rewrite the Phase 1–4 lineage.

## Stop Markers

- `NO_STAGE042_THIS_RUN`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_PRODUCTION_RUNTIME`

## Rollback

Revert only the Stage041 review repairs, dependent Phase 2→4 hash bindings,
review artifacts and this review's governance transition. Preserve earlier
stages, approved external sources, raw data, owner-controlled dependency and
service files, GitHub state and installed app entries. On any source,
contract, phase, finding, governance or Git-index inconsistency, restore
`IDS-STAGE041-REVIEW-GATE` to blocked and do not proceed to Stage 42.
