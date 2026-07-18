# Changelog

## IDS v0.1 STAGE-043 Phase 3 - 2026-07-18

- Added `ids.stage043.worker_crash_recovery.phase3.scenarios.v1` and a fail-closed checker for thirteen task-pack-aligned isolated scenarios: duplicate replay, changed-payload conflict, stale evidence, isolated process loss, unfenced generation, three resource pauses, same-source lock exclusion, active conflict, terminal immutability, protected cleanup and partial-output quarantine.
- Observed one ephemeral control child self-exit with code `73`, empty stdout/stderr and no IDS input. The checker sends no signal, performs no external process probe, restart or recovery, and does not describe this as a production worker crash or successful recovery.
- Replayed the reviewed Stage041 same-source exclusion proof for processing, extraction, indexing and reporting. The full source matrix retains `25` conflicts and the selected four-family subset covers `16`; no operation, queue admission, retry-budget consumption or production lock runtime occurs.
- Verified drive/API control pauses, an actual project-volume free-space observation with a no-allocation low boundary, five protected Git refs and two Stage044-owned quarantine candidates. No physical drive action, API call, cleanup/delete, state mutation, checkpoint continuation, persistence, database, raw data or production action occurs.
- TDD RED produced `2` expected failures and `16` expected errors across `18` focused tests because the Phase 3 artifacts and governance route were absent. Final GREEN: checker `18/18 + 13/13`, focused `18/18`, Stage005 `162/162`, Stage041-043 aggregate `174/174` in `563.213s`, full discovery `914/914` in `928.016s`, five historical review checkers, 208-event semantics, idempotent render and project dual-plane all pass.
- Routed the only next task to separate `IDS-V0_1-STAGE043-P4` with `push_allowed=false`; no Phase 4, whole-stage review, batch review, GitHub upload/merge, issue action or app reinstall ran.

## IDS v0.1 STAGE-043 Phase 2 - 2026-07-18

- Added `ids.worker_crash_recovery_policy.v0_1.stage043.p2`, an exact-shaped, deterministic, in-memory and reference-only candidate-decision slice; production process and state effects remain disabled.
- Registered `ASM-008`, `MOD-012`, `FORM-012` and `PARAM-077..081` as `planned` / `PROPOSED`: crash detection `1 s`, heartbeat staleness `30 s`, lease-expiry grace `5 s`, recovery retry backoff `30 s` and checkpoint validation timeout `30 s`. Values are derived from reviewed Stage039-042 isolated bounds and remain uncalibrated under `TASK-OPME-B-001`.
- Bound each request to canonical job/attempt/worker-generation/state-version/crash-incident identity and evaluated only four outcomes: checkpoint-resume candidate, Stage039 retry candidate, safe-failure candidate, or mandatory resource-pause candidate. Exact replay is idempotent; changed payload, terminal state, fresh heartbeat/live lease, missing fencing, active lock conflict and incomplete checkpoint evidence fail closed.
- Preserved partial output as quarantine references only and kept cleanup ownership with Stage044. The slice performs no process probe, crash injection, termination, restart, recovery, state transition, checkpoint continuation, queue/retry/lock mutation, persistence, database, raw-data, external-API, delete or runtime-output action.
- TDD RED produced `19` expected failures across `16` focused tests because the Phase 2 artifacts, registries and route were absent. Final GREEN passed checker `18/18 + 15/15`, focused `16/16`, Stage005 `161/161`, Stage041-043 aggregate `156/156` in `644.177s`, full discovery `895/895` in `1065.039s`, five historical review checkers, `207` clean events, idempotent rendering and project dual-plane.
- Stage005 first exposed three stale tamper targets, the first aggregate reached `154/156`, the first full discovery reached `891/895`, and dual-plane exposed nine missing glossary entries. Repairs were limited to exact historical registry-count evidence and P2-to-P3 forward compatibility; no historical review conclusion or runtime safety contract changed.
- Pre-commit self-review repaired one Important identity/evidence gap: unsafe control identifiers fail validation, and invalid requests no longer project untrusted error, checkpoint or quarantine references. The post-fix full discovery is the final `895/895` result above.
- Routed the only next task to separate `IDS-V0_1-STAGE043-P3` with `push_allowed=false`; no Phase 3, whole-stage review, batch review, GitHub upload/merge, issue action or app reinstall ran.

## IDS v0.1 STAGE-043 Phase 1 - 2026-07-18

- Bound the unique approved Stage043 taskpack member, committed Stage042 review predecessor and exact Stage037–042 control chain into `ids.stage043.worker_crash_recovery.phase1.v1`, an exact-shaped static engineering contract with a stdout-only fail-closed checker.
- Reused the authoritative 11-state/4-terminal graph. A crashed active job must first use a legal `RETRY_WAIT` candidate, and any checkpoint continuation must pass Stage039 retry admission plus a fresh claim/lock/lease/fencing cycle; direct `RUNNING -> RUNNING`, active-to-queued recovery and terminal reopen remain forbidden.
- Required current job/attempt/worker-generation/state-version/heartbeat/lease/lock/fencing/checkpoint/quarantine/error/audit evidence. Missing, stale or conflicting evidence requires manual review; exact recovery-request replay is idempotent and changed payload fails closed.
- Required drive-offline, insufficient-disk and insufficient-API-budget work to pause. Partial output remains quarantined/reference-only, five evidence classes remain protected, and Stage044 alone owns cleanup execution.
- TDD RED produced 13 expected failures and one missing-file error across 11 focused tests. Phase 1 sets no numeric values and performs no crash injection, process termination/restart, recovery, state mutation, persistence, database, raw metadata, cleanup/delete, GitHub or app action.
- Routed the only next task to separate `IDS-V0_1-STAGE043-P2` with `push_allowed=false`; Stage043 remains incomplete until its later phases and independent whole-stage review pass.
- Final GREEN passed checker `19/19`, focused `11/11`, Stage005 `160/160`, Stage041–043 aggregate `140/140`, final full IDS v0.1 discovery `878/878` in `1013.621s`, five historical stage-review checkers, idempotent rendering and the project-scoped dual-plane gate.
- The first full run exposed seven Stage038/039 current-gate allowlist gaps; each was bounded only through the current `IDS-STAGE043-P1 -> IDS-STAGE043-P2-GATE` route. The second full run exposed one stale generated owner view; rendering repaired it before the final all-green run. Immutable Stage037–042 delivery contracts were not changed.

## IDS v0.1 STAGE-042 Review - 2026-07-18

- Completed the independent whole-stage review under `ACC-STAGE-042` and repaired one Critical and four Important findings: unenforced canonical request IDs, zero/invalid versions and unbound reasons, self-reported resume stability, non-paused cleanup candidates, and stale handoff/governance truth.
- Enforced exact canonical lifecycle IDs for new requests while preserving exact replay and changed-payload conflict semantics. State versions are strict positive integers and every action has one exact reason code.
- Added stability-start evidence with exact temporal relationships for resume, restricted cleanup candidates to `PAUSED`, and rebound the dependent Phase2-to-Phase4 content-hash chain without enabling any executor.
- Added the fail-closed Stage042 review checker/tests, Phase4 commit/tree ancestry binding, reviewed-local batch/roadmap/event evidence and dual-plane facts. Every review source must match the Git index before `PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED` is possible.
- Final GREEN passed Stage042 review `10/10`, Stage005 `159/159`, Stage040–042 `184/184`, full IDS v0.1 discovery `866/866`, five review checkers, `205` clean events, idempotent rendering and the project-scoped dual-plane gate. Three Stage038 historical gate allowlists were bounded only through `IDS-STAGE043-P1-GATE` after the first full run exposed them.
- Routed the only next task to separate `IDS-V0_1-STAGE043-P1` while preserving `stage043_entry_allowed=false` and `push_allowed=false`. No actual lifecycle, process-crash recovery, termination, cleanup/delete, persistence, raw metadata, production, GitHub or app action ran.

## IDS v0.1 STAGE-042 Phase 4 - 2026-07-18

- Added `ids.stage042.automatic_lifecycle.phase4.delivery.v1`, an exact source/commit/tree/upstream-bound closeout contract and stdout-only fail-closed checker.
- Composed the 8-type/11-state/4-terminal/21-transition graph, reviewed 3-attempt/2-retry `DEAD_LETTERED` log, seven pressure signals, twelve lifecycle scenarios, four-operation same-source exclusion, two cleanup candidates and five protected artifact classes.
- Classified drive, disk and API recovery as three controlled requeue eligibility cases only. Observed automatic recovery remains empty; eleven conflict, stale, ownership, lock, timeout, crash, cleanup, terminal, contract, calibration and lost-memory-state cases require manual handling.
- Added ordered safe-shutdown, current-evidence recovery, no in-memory state restoration, Phase4-only rollback and explicit downstream ownership. No actual lifecycle, process termination, crash recovery, cleanup/delete, persistence, database, raw metadata or production runtime ran.
- TDD RED produced 14 expected assertion failures and one missing-checker error across 12 focused tests. Final GREEN passed checker `18/18 + 6/6`, focused `12/12`, Stage005 `159/159`, Stage037-039 `124/124`, Stage040-042 `174/174`, full discovery `856/856` in `673.264s`, `204` clean events, idempotent rendering and the project dual-plane gate.
- Routed the only next task to separate `IDS-V0_1-STAGE042-REVIEW` with `push_allowed=false`; no whole-stage review, Stage043, batch review, GitHub upload/merge, issue action or app reinstall ran.

## IDS v0.1 STAGE-042 Phase 3 - 2026-07-18

- Added `ids.stage042.automatic_lifecycle.phase3.scenarios.v1`, an exact Phase 2 and Stage041-bound contract plus stdout-only checker for twelve isolated lifecycle-control scenarios.
- Verified exact duplicate replay, changed-input conflict rejection, stale-start denial, drive/disk/API pause and owner/stability-gated resume, one actual isolated worker `RuntimeError`, four-operation same-source exclusion, ordered shutdown, timeout denial and protected cleanup.
- Preserved five protected artifact classes and kept two eligible classes as candidates only. No delete API, physical drive action, disk allocation, external API call, process crash recovery, process termination, state write, persistence or production runtime ran.
- TDD RED produced two expected failures and fifteen expected errors across 17 focused tests. Final GREEN passed checker `19/19 + 12/12`, focused `17/17`, Stage004 `3/3`, Stage005 `159/159`, Stage037-039 `124/124`, Stage040-042 `162/162`, full IDS v0.1 `844/844` in `618.960s`, `203` clean events and the dual-plane gate.
- Governance sync repaired two generated-Chinese terminology findings and rebound the exact Stage041 scenario-test → delivery-contract → Stage042 Phase1/2/3 Git-index hash chain without changing historical conclusions.
- Routed the only next task to separate `IDS-V0_1-STAGE042-P4` with `push_allowed=false`; no Phase 4, whole-stage review, batch review, GitHub upload/merge, issue action or app reinstall ran.

## IDS v0.1 STAGE-042 Phase 2 - 2026-07-18

- Added `ids.automatic_lifecycle_policy.v0_1.stage042.p2`, an exact-shaped isolated reference-only contract and stdout-only checker for automatic-start, resource-pause, guarded-resume, safe-shutdown and cleanup-scan candidates.
- Registered `ASM-007`, `MOD-011`, `FORM-011` and `PARAM-072..076` as `planned` / `PROPOSED`; tick `1 s`, stability `60 s`, checkpoint wait `30 s`, shutdown `60 s` and cleanup scan `300 s` are derived from reviewed Stage040/041 boundaries and linked to `TASK-OPME-B-001`.
- Implemented deterministic in-memory request validation, candidate evaluation and idempotent replay. Terminal history is immutable; active pause uses `PAUSE_REQUESTED`; resume returns only to `QUEUED`; input/output/error/checkpoint/audit refs remain truthful and raw payloads are not echoed.
- Safe shutdown is an ordered candidate and never terminates a process. Cleanup emits only Stage044-owned eligible candidates and exposes no delete path. No state, queue, worker, retry, lock, database, persistence, business-job, raw metadata, external API or production action ran.
- TDD RED produced four failures and fifteen errors across 16 focused tests because Phase 2 artifacts and governance were absent. Final GREEN passed checker `20/20 + 13/13`, focused `16/16`, Stage004 `3/3`, Stage005 `159/159`, Stage037-039 `124/124`, Stage040-042 `145/145`, full IDS v0.1 `827/827`, `202` clean events and the dual-plane gate. The first full run reached `826/827`; exact governance-ID compatibility was narrowed without accepting legacy display names.
- Routed the only next task to separate `IDS-V0_1-STAGE042-P3` with `push_allowed=false`; no Phase 3, whole-stage review, batch review, GitHub upload/merge, issue action or app reinstall ran.

## IDS v0.1 STAGE-042 Phase 1 - 2026-07-18

- Bound the unique approved Stage042 taskpack member, reviewed Stage041 commit/tree and exact Stage037–041 control contracts into `ids.stage042.automatic_lifecycle.phase1.v1`, an exact-shaped static engineering contract with a stdout-only fail-closed checker.
- Preserved the authoritative 11-state/4-terminal graph: automatic start uses `QUEUED -> CLAIMED -> RUNNING`, active pause passes through `PAUSE_REQUESTED`, resume returns only to `QUEUED` for a fresh admission/claim/lock cycle, and terminal history never reopens.
- Required external-drive offline, insufficient disk and insufficient API budget to emit pause candidates; owner revalidation, fresh resource observations, checkpoint/quarantine, lease and fencing evidence remain mandatory.
- Kept queue/worker, retry/dead-letter, backpressure, lock/fencing, process-crash recovery and cleanup execution with Stage038–044. Lifecycle evidence is reference-only, shutdown is ordered, cleanup is candidate-only, and all five timing parameters remain deferred.
- TDD RED produced 13 expected assertion failures and one missing-file error across 11 focused tests. Final GREEN passed checker 19/19, focused 11/11, Stage005 158/158, Stage037-039 124/124, Stage040-042 129/129, full IDS v0.1 810/810, 201 clean events and the project dual-plane gate.
- Routed the only next task to separate `IDS-V0_1-STAGE042-P2` with `push_allowed=false`. No Phase 2, lifecycle runtime, persistence, database, raw metadata, fake business data, cleanup delete, GitHub upload/merge, app reinstall or production action ran.

## IDS v0.1 STAGE-041 Review - 2026-07-18

- Completed the independent whole-stage review under `ACC-STAGE-041` and repaired one Critical and three Important findings: strict positive-integer CAS evidence, monotonic logical time/live-lease mutations, exact operation/provenance/parameter contract semantics, and stale handoff/governance truth.
- Hardened the process-local lock engine so boolean/float version evidence, negative or backward time, non-extending renewal, expired commit/release and semantic contract tampering fail closed. Added `NO_TRUSTED_PRODUCTION_CLOCK_SOURCE` as an explicit production limit and rebound the dependent Phase 2→4 hash chain.
- Added the fail-closed Stage041 review checker/tests, reviewed-local batch/roadmap/event evidence and dual-plane facts. Every review source must match the Git index before `PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED` is possible.
- Final review validation passed Stage041 `63/63`, Stage005 `157/157`, Stage040–041 `118/118`, full IDS v0.1 `798/798` in `555.092s`, `200` clean governance events, exact event/index `34/34`, idempotent rendering and the project-scoped dual-plane gate.
- Reconciled the KM_IDS portion of latest `origin/main` renderer fix `dec58884` so newest-first changelog facts render the latest ten entries; no unrelated remote commit was merged and the Phase 1–4 ancestry was not rewritten.
- Routed the only next task to the separate `IDS-V0_1-STAGE042-P1` while preserving `push_allowed=false` and `stage042_entry_allowed=false`. Stage042 execution, batch review, GitHub upload/merge, app reinstall, raw metadata access, persistence and production runtime did not run.

## IDS v0.1 STAGE-041 Phase 4 - 2026-07-17

- Added an exact-hash-bound Phase 4 delivery contract and stdout-only checker that compose the five-family Stage041 lock lifecycle with the reviewed 8-type/11-state/4-terminal/21-transition graph, three-attempt/two-retry dead-letter log, seven pressure signals and two-class cleanup allowlist.
- Performed one deterministic process-local acquire, renew and matching-holder release over the real Git-tracked control reference. Release left zero active locks and two monotonic tombstone versions; the old evidence returned `STALE_FENCING_TOKEN`; no persistent lock write occurred.
- Classified exact replay, matching renewal and matching release as lock decisions rather than recovery. Automatic-recovery eligibility and observed success remain empty; stale CAS, active conflict, owner resource revalidation, process crash, protected cleanup, invalid contract, uncalibrated policy and missing process-local state remain manual.
- Added explicit shutdown, evidence-only rebuild, no-memory-state restoration, P4-only rollback and known-limit instructions. Whole-stage review, Stage042, persistence, database, raw metadata, fake business data, physical fault, cleanup, production, GitHub upload/merge and app reinstall remain disabled.
- Passed contract checks 16/16, delivery checks 6/6, focused tests 12/12, Stage005 157/157, Stage040-041 aggregate 109/109, full IDS v0.1 discovery 789/789, event integrity and the project-scoped dual-plane gate. The first index-bound runs exposed only a stale P3 current-state assertion and its consequent P4 hash drift; both were repaired without weakening review.

## IDS v0.1 STAGE-041 Phase 3 - 2026-07-17

- Added an exact-hash-bound eleven-scenario contract and stdout-only checker for duplicate replay, the five-operation same-source exclusion matrix, renewal, expiry-plus-grace takeover, stale CAS, an actual isolated exception, resource pauses, release tombstones, and protected-cleanup denial.
- Verified five primary acquisitions, five exact replays, and all `25` same-source contender combinations without invoking an operation, creating a queue record, retaining a partial lock, or consuming retry budget.
- Replayed reviewed drive/disk/API pressure gates before lock acquisition, observed project-filesystem free space read-only, and verified five Git-tracked protected artifact classes without physical removal, disk allocation, API calls, cleanup, or deletion.
- Rebased onto `origin/main` after confirming eleven remote KMFA commits changed zero `KM_IDSystem` paths; rebound Phase 3 to Phase 2 commit `22bd9263e38b697dfb681886a97c1b8ba0f4b5e9` and unchanged tree `c3e96185d5fe185fc9a8c27e8fa57a6279bc4e6d`.
- Passed contract checks `17/17`, scenarios `11/11`, focused tests `15/15`, Stage005 `157/157`, Stage040-041 aggregate `97/97`, full IDS v0.1 discovery `777/777`, and the project-scoped dual-plane gate. The unstaged first runs failed closed only on `17` Git-index-bound historical review assertions; after staging, a `776/777` run exposed one stale Stage039 route map, repaired only by adding the current P3→P4 compatibility mapping.
- Kept Phase 4, whole-stage review, persistence, database, raw metadata, fake business data, queue/worker/retry/resume/recovery/cleanup runtime, physical fault actions, production activation, GitHub upload, merge, and app reinstall disabled.

## IDS v0.1 STAGE-041 Phase 2 - 2026-07-17

- Added `ids.lock_registry_policy.v0_1.stage041.p2`, seven sourced `PROPOSED` parameters, `MOD-010` / `FORM-010` / `PARAM-065..071`, and a deterministic process-local checker over one real Git-tracked control reference; production calibration remains open under `TASK-OPME-B-001`.
- Implemented canonical all-or-none acquisition, fencing-preserving/version-advancing renewal, tombstone-version-advancing release, expiry-plus-grace takeover bound to current CAS evidence, stale-holder denial, and same-key changed-input idempotency rejection.
- Rebound the historical second candidate patch to current Phase 1 and Stage038-040 hashes and independently repaired four concurrency gaps; no candidate commit was cherry-picked and no Stage42-43 review claim was activated.
- Passed P1 checker `20/20`, P2 checker `20/20 + 11/11`, P1 tests `10/10`, P2 focused tests `17/17`, Stage004 `3/3`, Stage005 `156/156`, Stage035 dual-plane compatibility `1/1`, Stage039 review `6/6`, Stage040-041 aggregate `82/82`, full IDS v0.1 discovery `761/761` in `348.250s`, and the project dual-plane gate. The first full run reached `759/761`; both stale current-state compatibility assertions were repaired without changing historical batch evidence.
- Kept Phase 3, whole-stage review, persistence, database, raw metadata, fake business data, queue/worker/retry/resume/recovery/cleanup runtime, production activation, dependency installation, GitHub upload, merge, and app reinstall disabled.

## IDS v0.1 STAGE-041 Phase 1 KMOS Rebind - 2026-07-17

- Applied only the first archived candidate patch's file content in the dedicated `kmos-kmids-stage041` worktree; no candidate commit identity was restored and no cherry-pick, Stage 42-43 activation, upload, or merge occurred.
- Rebound four historical CodexProject evidence commits to their KMOS equivalents after verifying commit-message equality, current-KMOS ancestry, and exact blob equality at `18/18`, `14/14`, `24/24`, and `15/15`; repaired the dependent Stage039-041 SHA-256 chain without changing the immutable `BATCH031_040` terminal hash.
- Passed the Stage041 checker `20/20`, focused tests `10/10`, Stage005 governance regression `156/156`, batch index review `8/8`, full IDS v0.1 discovery `744/744` in `356.105s`, and the project-scoped dual-plane gate.
- Moved all 63 `KM_IDSystem` change paths from the KMOS main checkout into `/Users/linzezhang/Documents/Codex/GithubProject/_scratch/kmos-kmids-stage041`; the main checkout is back on `main` with zero `KM_IDSystem` changes. Phase 2, production runtime, raw metadata access, app activation, push, PR, and merge remain disabled.

## IDS v0.1 STAGE-041 Phase 1 - 2026-07-14

- Bound the unique approved Stage041 taskpack member, approved archive/roadmap/instruction hashes, and terminal `BATCH031_040` lock hash into `ids.lock_registry.v0_1.p1`, an exact-shaped metadata-only contract with a stdout-only fail-closed checker under `ACC-STAGE-041`.
- Defined five governed operation domains, a shared source-pipeline guard plus operation lock, reference-only SHA-256 keys, lexicographic all-or-none compare-and-set acquisition, one-live-holder lease rules, atomic fencing/version takeover, stale-holder write denial, and matching-token idempotent release.
- Preserved the Stage038 same-source conflict baseline and specified that contention creates no queue record, executes no operation, and consumes no retry budget. All numeric lease/renewal/timeout/contention parameters remain deferred to Phase 2 with no implicit defaults.
- Routed automatic resume to STAGE-042, crash recovery to STAGE-043, cleanup execution to STAGE-044, and the only next task to a separate `IDS-V0_1-STAGE041-P2` run. No lock runtime, queue/worker, persistence, database, raw metadata, fake IDS business data, GitHub/PR/issue/merge, app reinstall, or production action ran.
- Added current `BATCH041_050` and governance/event routing with `push_allowed=false`; historical `BATCH031_040` remains immutable in its terminal uploaded state. Final validation passed Stage041 checker `20/20`, focused tests `10/10`, Stage005 `156/156`, Stage037-040 `179/179`, historical Stage001-036 plus BATCH031-040 review compatibility `555/555`, and full IDS v0.1 discovery `744/744` after repairing 32 stale historical governance assertions without changing the old batch hash. Pre-commit self-review repaired one additional Important exact-shape gap so unknown nested fields and incomplete human-status projections fail closed.

## IDS v0.1 BATCH-031-040 Upload Gate - 2026-07-14

- Opened the separate upload gate only after the ten-stage independent review and repairs passed; TDD RED captured the missing gate plus pending/terminal state contracts.
- Confirmed GitHub had zero open PRs and zero open issues, the reviewed branch and `origin/main` diverged by `52/862` commits, and remote-main drift since the merge base did not touch `KM_IDSystem`.
- Authorized one feature-branch PR targeting `main` while prohibiting direct pre-merge `HEAD:main`, owner dirty-file staging, sparse expansion, unrelated-project work, raw metadata content access, fake IDS business data, and STAGE-041.
- Resolved PR #276's only content conflict by accepting `origin/main`'s `scripts/lean_governance.py`, reran the IDS full suite at `732/732`, and regenerated the one owner view required by the newer renderer to restore drift/reference `0/0`.
- Merged PR #276 into GitHub `main` with SHA `565babef3a610f289fed0da38b58e550b5707e3e`, deleted the remote feature branch, and verified zero open PRs and zero open issues.
- Reinstalled all four Downloads/Applications `.app` and `.command` entries from the merged tree; diagnostics and codesign passed, and both command launchers point to this `KM_IDS/KM_IDSystem` worktree.

## IDS v0.1 BATCH-031-040 Independent Review - 2026-07-14

- Independently reverified the exact approved Stage031-040 taskpack members, ten whole-stage review artifacts, all Stage checkers, and the Stage036-040 state/interface/hash chain under `ACC-STAGE-031..ACC-STAGE-040`.
- Repaired one Critical and two Important batch findings by adding a strict machine contract, fail-closed checker/tests, uniform Git-index/source binding for all ten stages, and explicit reviewed-no-upload governance/event semantics.
- Repaired six historical Stage038/039 regression assertions so they preserve their original Stage evidence while accepting the reviewed-no-upload batch state and upload-only next gate; final full v0.1 discovery passed `729/729`.
- Hardened malformed Stage identity handling so a shape-valid but invalid `stage_id` returns `FAIL_CLOSED` instead of raising during artifact validation.
- Routed the only next task to the separate `IDS-V0_1-BATCH-031-040-UPLOAD-GATE` while preserving `push_allowed=false`. No GitHub/PR/issue/merge, app reinstall, production/database action, raw metadata content access, fake IDS business data, or STAGE-041 work ran.

## IDS v0.1 STAGE-040 Review - 2026-07-14

- Completed the independent whole-stage review under `ACC-STAGE-040` and repaired one Critical and two Important findings: non-JSON/non-hashable control metadata could escape fail-closed handling, active pause requests were mislabeled as completed pauses, and scheduler fairness was claimed without an implemented scheduler or measured proof.
- Added structured invalid-metadata handling with reference redaction, state-aware `已暂停`/`暂停中` projection, truthful `starvation_prevention_proved=false` governance, focused RED/GREEN tests, and a repaired P1→P4 SHA-256 evidence chain.
- Added the fail-closed Stage040 review checker, reviewed-local batch/roadmap/event evidence, and next gate `IDS-V0_1-BATCH-031-040-REVIEW-GATE`. Batch review, GitHub/upload/issue action, app reinstall, STAGE-041, production runtime, raw metadata access, and fake IDS business data remain disabled.

## IDS v0.1 STAGE-040 Phase 4 - 2026-07-14

- Added an exact-hash-bound closeout contract and stdout-only checker for the Stage037 job-state graph, seven backpressure signals, reviewed actual Stage039 failure/retry evidence, protected cleanup rules, recovery classification, shutdown, recovery, and rollback.
- Recorded three attempts, two retry admissions, terminal `DEAD_LETTERED`, zero eligible or observed automatic-recovery cases, eight manual-action cases, and restrained Chinese owner feedback without inventing persistent logs or successful recovery evidence.
- Routed the only next task to the separate `IDS-V0_1-STAGE040-REVIEW` run. Production queue/worker, persistence, database, raw metadata, fake IDS business data, lock/resume/crash/cleanup runtimes, whole-stage review, batch gates, GitHub/issue action, and app reinstall remain disabled.

## IDS v0.1 STAGE-040 Phase 3 - 2026-07-13

- Added an exact-hash-bound eight-scenario contract and stdout-only checker for duplicate decisions, actual isolated worker-exception boundaries, drive/disk/API pressure, same-source cross-operation concurrency, reviewed lock conflicts, and protected cleanup denial.
- Reused the reviewed Stage038/039 isolated worker and lock evidence while keeping production locks with STAGE-041, crash recovery with STAGE-043, and cleanup execution with STAGE-044. Actual project free space is observed read-only; low disk is tested at a deterministic boundary without allocation.
- Verified fail-closed idempotency, legal pause paths, zero retry-budget consumption, zero job creation under throttle, one control lock invocation with three conflicts, and five Git-tracked protected refs with no delete path. No physical drive removal, process termination, disk allocation, API call, cleanup, persistence, database, raw metadata, fake IDS data, production, GitHub, batch gate, Phase 4, review, or app reinstall ran.

## IDS v0.1 STAGE-040 Phase 2 - 2026-07-13

- Added `ids.backpressure_policy.v0_1.stage040.p2`, a versioned isolated decision contract and standard-library checker covering queue depth, admission rate, same-type concurrency, actual project-filesystem free space, external-drive availability, API budget, observation TTL, and hysteresis.
- Registered `MOD-009`, `FORM-009`, and `PARAM-056..064` as `planned` / `PROPOSED`, linked production calibration to `TASK-OPME-B-001`, and updated total registry counts to `9/9/64` while preserving active counts `7/7/49`.
- Implemented deterministic fail-closed admit/throttle/deny/legal-pause/manual-review decisions, in-memory idempotent replay, immutable terminal handling, bounded refs, Chinese owner status, and a Phase3-only route. No queue, worker, retry scheduler, lock, resume, cleanup, persistence, database, raw metadata, fake IDS data, external API, production activation, GitHub action, batch gate, or app reinstall ran.

## IDS v0.1 STAGE-040 Phase 1 - 2026-07-13

- Bound the unique approved Stage040 taskpack member and reviewed Stage037-039 control sources into an exact-shaped metadata-only backpressure engineering contract and stdout-only checker under `ACC-STAGE-040`.
- Defined fail-closed queue soft/hard pressure, external-drive, disk, and API-budget decisions; legal pause paths; retry/idempotency/fairness invariants; restrained Chinese status; and protected partial-output cleanup boundaries.
- Deferred all numeric thresholds and scheduling parameters to a separately evidenced Phase 2, while preserving STAGE-041 lock, STAGE-042 automatic-resume, STAGE-043 crash-recovery, and STAGE-044 cleanup ownership. No runtime, database, raw metadata, fake IDS data, GitHub action, batch gate, or app reinstall ran.

## IDS v0.1 STAGE-039 Review - 2026-07-13

- Completed the local whole-stage review under `ACC-STAGE-039` and repaired four Important findings: invalid governance status/fact enums and missing calibration-task links, total registry count drift, overclaimed terminal manual-rerun job creation wording, and absent Git-index-bound review evidence.
- Registered the Stage039 policy as `planned` / `PROPOSED`, linked unresolved production calibration to `TASK-OPME-B-001`, and separated total model/formula/parameter counts `8/8/55` from active counts `7/7/49`.
- Added the fail-closed Stage039 review checker, tests, reviewed-local batch/roadmap/event evidence, and next gate `IDS-STAGE040-P1-GATE`. Production runtime, raw metadata access, fake IDS data, GitHub upload, batch gates, Stage040 execution, and app reinstall remain disabled.

## IDS v0.1 STAGE-039 Phase 4 - 2026-07-13

- Added a hash-bound Phase 4 delivery contract and stdout-only checker that expose the exact Stage037 8-type/11-state/21-transition graph, six failure decisions, and the actual isolated three-attempt retry/dead-letter history ending at `DEAD_LETTERED` with `retry_count=2`.
- Delivered five bounded capacity/resource/conflict signals, a two-class cleanup allowlist with eight protected classes, two automatically retry-eligible safe codes, zero observed successful automatic recoveries, eight manual-action cases, reviewed orderly transport shutdown, and fail-closed recovery/rollback instructions.
- Routed the only next task to the separate `IDS-V0_1-STAGE039-REVIEW` run. Production, persistence, database, raw metadata, fake IDS business data, Stage040-044 runtime ownership, whole-stage review, GitHub upload, and app reinstall remain disabled.

## IDS v0.1 STAGE-039 Phase 3 - 2026-07-13

- Added an exact-hash-bound ten-scenario contract and stdout-only checker for duplicate retry requests, worker-exception/crash boundary, drive/disk/API resource pauses, same-source cross-operation locking, retry exhaustion, immutable terminal replay, owner-authorized manual-rerun lineage, and protected cleanup denial.
- Reused the reviewed Stage038 isolated queue evidence for one actual worker exception and one actual local free-space observation. No process termination, physical drive removal, disk allocation, external API call, cleanup/delete, production runtime, persistence, or database action was performed.
- Verified that resource pauses consume no retry budget, duplicate reservation/admission replay is idempotent, exhaustion stops at `retry_count=2`, terminal jobs are not reopened, manual rerun creates only a new in-memory candidate, and five protected evidence classes remain Git-tracked and undeleted. Phase 4, Stage040+, whole-stage review, GitHub upload, and app reinstall remain separate and disabled.

## IDS v0.1 STAGE-039 Phase 2 - 2026-07-13

- Added `ids.retry_policy.v0_1.stage039.p2` with `max_retries=2`, bounded `[5, 30]` backoff ceilings, deterministic nonzero hash jitter, an exact two-code retry allowlist, default-deny unknown errors, explicit `ASSUMPTION` fact level, and production calibration still required.
- Composed the reviewed Stage038 in-memory transport admission with a separately derived Stage039 policy job and Stage037 CAS transitions, so the Stage038 `max_retries=0` job is never mutated into the Stage039 `max_retries=2` job. Retry reservation consumes no budget; failure/admission replays are idempotent; due admission increments exactly once; resource pause preserves pending retry; exhaustion follows `RUNNING -> RETRY_WAIT -> DEAD_LETTERED`.
- Recorded the tracked control input, empty failure output refs, safe error, actual checkpoint digest, Chinese owner status, rollback, and no-side-effect flags. No production service, persistence, database, raw metadata, fake IDS data, API, runtime output, GitHub action, app reinstall, Phase 3, or Stage040+ runtime ran.

## IDS v0.1 STAGE-039 Phase 1 - 2026-07-13

- Bound the unique approved Stage039 taskpack member and the reviewed Stage037/038 state/queue sources into an exact-shaped metadata-only retry/dead-letter engineering contract and stdout-only checker under `ACC-STAGE-039`; unknown root or nested contract fields fail closed.
- Defined immutable terminal states, retry budget and atomic admission semantics, exact failure classes, resource pause without budget consumption, bounded dead-letter evidence, and owner-authorized new linked jobs for terminal manual reruns.
- Deferred numeric retry/backoff/jitter/error-allowlist values to a separately evidenced Phase 2 and defaulted missing or unversioned policy to no automatic retry. No scheduler, dead-letter runtime, queue/worker, database, raw metadata, fake IDS data, GitHub action, app reinstall, or later phase ran.

## IDS v0.1 STAGE-038 Review - 2026-07-13

- Completed the local whole-stage review under `ACC-STAGE-038` and repaired four Important findings: exact contract-shape enforcement, the missing external-API-budget pause proof, false same-operation resubmission guidance, and absent Git-index-bound review evidence.
- Added a seventh isolated Phase 3 scenario that returns `PAUSED_EXTERNAL_API_BUDGET_INSUFFICIENT` without calling an API; terminal same-operation replay now remains explicitly unavailable until STAGE-039 defines retry/new-attempt policy.
- Added the Stage038 review checker, structured Stage005 review governance, reviewed-local batch/roadmap/event evidence, and the next gate `IDS-STAGE039-P1-GATE`. Production runtime, raw metadata access, fake IDS data, GitHub upload, batch gates, and app reinstall remain disabled.

## IDS v0.1 STAGE-038 Phase 4 - 2026-07-13

- Added a hash-bound Phase 4 delivery contract and stdout-only checker that expose the exact STAGE-037 job-state graph, the actual isolated failure record, capacity/resource/lock backpressure proofs, and orderly isolated shutdown evidence.
- Delivered a cleanup allowlist limited to temporary partial output and rebuildable cache, with original data, facts, manifests, evidence, report snapshots, audit logs, active indexes, and required checkpoints protected.
- Recorded `automatic_recovery_cases=[]`, six manual-action conditions, rollback steps, known limits, restrained Chinese feedback, and `PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED`. Whole-stage review, STAGE-039, production runtime, raw metadata access, fake IDS data, cleanup execution, GitHub, and app reinstall remain disabled.

## IDS v0.1 STAGE-038 Phase 3 - 2026-07-13

- Repaired the resource conflict identity so archive, parse, index, and report jobs over one tracked input share one lock key; active conflicts now return `RESOURCE_CONFLICT_ACTIVE` before a second queue record is created.
- Added six isolated scenarios for duplicate clicks, an actual worker exception and lock release, external-drive-offline gating, actual low-disk boundary observation without allocation, same-source cross-operation locking, and protected cleanup denial.
- Added a hash-bound Phase 3 machine contract, stdout-only checker, focused tests, and governance evidence. No physical drive removal, process termination, cleanup execution, raw metadata access, fake IDS data, production activation, GitHub upload, app reinstall, Phase 4, or whole-stage review occurred.

## IDS v0.1 STAGE-038 Phase 2 - 2026-07-13

- Added a standard-library `asyncio` in-memory queue and one isolated worker that returns submission acknowledgement before completion and processes only real Git-tracked control references.
- Reused STAGE-037 `QUEUED -> CLAIMED -> RUNNING -> SUCCEEDED/FAILED` transitions and Chinese owner projections; records now carry bounded input, output, error, checkpoint, state-history, and audit refs.
- Added idempotent duplicate admission, bounded capacity backpressure, fail-closed raw/untracked/secret rejection, and an actual worker-failure path without persisting runtime files.
- Pinned the Stage037 checker/index and Phase1 source evidence hashes in a machine contract. Production queue activation, database/schema writes, IDS_MetaData access, fake business data, GitHub, app reinstall, Phase 3, and whole-stage review remain disabled.

## IDS v0.1 STAGE-038 Phase 1 Source Reverification - 2026-07-11

- Reverified the unique approved Stage038 taskpack member and recorded the exact archive, member, roadmap, and instruction SHA-256 values under `ACC-STAGE-038`.
- Reconciled Phase 1 with the restored source: STAGE-038 now defines queue/worker separation, idempotency, retry/dead-letter, backpressure, lock, lifecycle, crash-recovery, and cleanup interfaces while STAGE-039..044 retain dedicated runtime ownership.
- Added a six-surface finite-state validator and negative cross-file mutations so mixed hashes, counts, review states, or Phase 2 authorization fail closed.
- Repaired the Phase 2/3 plan to allow a separate isolated non-production queue/worker slice and the exact source scenarios without raw metadata, fake IDS data, production activation, or runtime-ownership takeover.
- Independent review progressed from `1 Critical / 1 Important / 0 Minor` to `0 / 0 / 0`; only the next separate Phase 2 run is authorized. No Phase 2, GitHub upload, app reinstall, stage review, or batch gate ran.

## IDS v0.1 STAGE-038 Phase 1 - 2026-07-11

- Recorded the source-limited Worker queue boundary under `ACC-STAGE-038`: inherited STAGE-037/022/030 constraints and STAGE-039..044 ownership are fixed, while exact ordering, idempotency, dependency, queue-entry, and claim contracts remain unassigned.
- Recorded the absent external taskpack truthfully with no fabricated SHA-256, set `phase2_entry_authorized=false`, and routed the next run only to a P1 source-reverification gate.
- Kept queue/worker runtime, claim persistence, PostgreSQL/schema actions, raw metadata access, fake IDS data, runtime outputs, GitHub upload, app reinstall, stage review, and batch gates out of this phase.

## IDS v0.1 STAGE-037 Review - 2026-07-11

- Reviewed and repaired the STAGE-037 unified job-state engineering contract under `ACC-STAGE-037` without running a queue, worker, retry scheduler, database, cleanup action, or real IDS job.
- Added fail-closed direct and paused retry eligibility, cancellation stop reasons, `ids.job_control_envelope.v1`, distinct “暂停中” projection, structured review governance, and Git-index-bound delivery/review sources.
- Kept raw metadata content, fake IDS data, runtime outputs, GitHub upload, app reinstall, batch gates, and STAGE-038 execution out of this review.

## IDS v0.1 STAGE-036 Review - 2026-07-11

- Reviewed and repaired the STAGE-036 database-quality engineering contract under `ACC-STAGE-036` without changing product version, diagnostic models, formulas, or active parameter values.
- Added hash-pinned migration section selection, ownership-safe public-schema rollback, bounded real-data authorization queries, dependency/snapshot provenance checks, and fail-closed governance regressions.
- Kept PostgreSQL access, raw metadata access, fake IDS data, runtime outputs, GitHub upload, app reinstall, batch gates, and STAGE-037 execution out of this review.

## 1.0.0 - 2026-06-24

- Added Other8 S3PCT01 lifecycle contract coverage for dependency fail-fast entrypoints, owned launcher PID cleanup, and temporary SQLite persistence recovery.
- Added `stop_local_services.sh` and LF enforcement for OpMe shell scripts.
- Kept diagnostic formulas, LLM routing values, provider calls, and production readiness unchanged.

## 1.0.0 - 2026-06-20

- Established CodexProject governance baseline for KM_IDSystem without changing backend/frontend behavior.
- Recorded offline rule models, risk scoring formulas, LLM routing/fallback strategy, parameters, version matrix, and traceability.
- Marked engineering calibration, prompt/provider governance, and signoff evidence as UNKNOWN under `TASK-OPME-B-001`.
