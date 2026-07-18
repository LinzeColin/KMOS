# IDS / Industrial Data System Handoff

## Current Gate - 2026-07-18

- Completed task in this run: `IDS-V0_1-STAGE043-P2`; the isolated reference-only worker-crash-recovery candidate decision slice is valid with all real process and state effects disabled. Stage043 itself is not complete or reviewed.
- Next allowed task: `IDS-V0_1-STAGE043-P3`, in a separate future run behind `IDS-STAGE043-P3-GATE`; this run must not enter Phase 3.
- Workspace rule: `/Users/linzezhang/Documents/Codex/GithubProject/KMOS` remains the clean read-only `main` checkout. All work is isolated in `/Users/linzezhang/Documents/Codex/GithubProject/_scratch/kmos-kmids-stage041` on `codex/kmids-recovery-stage041-p1`, with scope limited to `KM_IDSystem/`.
- Approved source: the unique archive member `IDS_v0_1_Final_Chinese_Revised/stages/STAGE-043_Worker崩溃恢复.md` has SHA-256 `e1d5169cbc30515930a7224743b860d9b577ccfbf9e0f913ec254d2ea060317b` inside archive SHA-256 `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`; roadmap and instruction hashes are bound exactly.
- Phase 2 predecessor baseline: Stage043 Phase 1 commit `d4b5ec1ef9bff3d2390869b4fd2998bd17d2c671`, full commit tree `6d7af7a50506df15f229e35977143ead0f5b3f06` and parent `ba248f66ce993a726cb12547ae1c772ab1228bfa` are exact. The Stage042 reviewed predecessor remains an ancestor.
- Lifecycle authority remains `ids.job_state.v1`: start is `QUEUED -> CLAIMED -> RUNNING`; active pause must pass through `PAUSE_REQUESTED`; resume is only `PAUSED -> QUEUED` followed by a fresh admission/claim/lock cycle; terminal states never reopen.
- A crash decision requires current job, attempt, worker instance/generation, state version, heartbeat, lease, lock, fencing, checkpoint/quarantine/error and audit evidence. Missing, stale, conflicting or incomplete evidence requires manual review.
- Checkpoint continuation is candidate-only and requires integrity, idempotency, owner/resource revalidation, lost-worker fencing, current state version and a fresh admission/claim/lock cycle. Blind continuation and in-memory state restoration are forbidden.
- External-drive offline, insufficient disk and insufficient API budget always pause related work. Partial output is quarantined/reference-only; cleanup candidates remain Stage044-owned and expose no delete path.
- Stage038 owns queue/worker transport, Stage039 retry/dead-letter, Stage040 pressure, Stage041 lock/lease/fencing, Stage043 process-crash recovery and Stage044 cleanup execution. Phase 4 only replays reviewed control evidence and does not absorb downstream runtime ownership.
- Phase 2 assigns proposed values `1s / 30s / 5s / 30s / 30s` for crash detection, heartbeat staleness, lease grace, recovery backoff and checkpoint validation. They are derived exactly from reviewed Stage039-042 isolated bounds, registered as `MOD-012` / `FORM-012` / `PARAM-077..081`, remain uncalibrated and require `TASK-OPME-B-001` before production activation.
- The deterministic in-memory slice evaluates checkpoint continuation, Stage039 retry, safe failure and mandatory resource-pause candidates. It performs no process probe/crash/recovery, state transition, checkpoint continuation, queue/retry/lock mutation, persistence or output write.
- TDD RED produced 19 expected failures across 16 focused tests because the Phase 2 files, registries and route were absent. Final GREEN passed checker `18/18 + 15/15`, focused `16/16`, Stage005 `161/161`, Stage041-043 aggregate `156/156` in `644.177s`, full discovery `895/895` in `1065.039s`, five historical stage-review checkers, `207` clean events, idempotent rendering and project dual-plane.
- Layered validation repaired only glossary registration, the explicit historical Stage042 `11/11/76` registry-count checkpoint, Stage041/042 current handoff compatibility and P2-to-P3 forward-route allowlists. Historical review conclusions, contracts and runtime safety were not weakened.
- Pre-commit self-review repaired one Important fail-closed gap: control identities now use the same safe-reference grammar, and invalid requests cannot project untrusted error/checkpoint/quarantine references into results.
- The first full run exposed seven Stage038/039 current-gate allowlist gaps and the second exposed one stale generated owner view; both were repaired narrowly before the final all-green run. The root governance runner is absent under this sparse checkout; sparse scope was not expanded and no unrelated project was inspected.
- The closeout evidence still composes the exact 8-job-type/11-state/4-terminal/21-transition graph, reviewed 3-attempt/2-retry log, seven pressure signals and twelve passing isolated scenarios. Observed automatic recovery remains empty.
- Current batch gate: `BATCH041_050` has two locally reviewed Stages plus Stage043 Phase 1-2 and remains locked with `push_allowed=false`; no single-stage upload, GitHub action, merge, app reinstall, Stage043 later phase, batch review or production action is authorized.
- Preserve owner-controlled dependency/service paths (`backend/requirements.txt`, `frontend/package.json`, `frontend/pnpm-workspace.yaml`, `scripts/run_local_services.sh`); this phase does not modify them.
- `/Users/linzezhang/Downloads/IDS_MetaData` remains a path-only governance boundary and was not touched. Do not read, list, hash, open, scan, copy, move, delete, modify, dump, or normalize its contents.

## Purpose

IDS / Industrial Data System turns the original industrial-operations CLI prototype into a local Web + PDF industrial data and operations console. It provides dashboard views, module-specific analysis, visualization, report generation, model routing configuration, and recoverable local app launchers.

Legacy aliases such as `Wuhan Kaiming OpMe`, `OpMe`, and the Chinese legacy display name may remain only in migration notes, historical evidence, compatibility paths, or rollback context. New UI, reports, generated titles, and formal documentation should use `IDS / Industrial Data System`.

## Delivery Standard

Any future agent should preserve these standards:

- The app must start locally from `./scripts/run_local_services.sh` or the macOS click entry. Prefer the installed `.command` launcher when Gatekeeper blocks the `.app`.
- The backend health endpoint must return ok at `http://127.0.0.1:8000/api/health`.
- The frontend must load at `http://127.0.0.1:5173/`.
- Four core modules must keep working: dynamic kiln monitoring, fault diagnosis, gear repair, machining service.
- Every case should support dashboard visualization and PDF report generation.
- Missing model API keys must not block operation; offline rules must remain the fail-closed fallback.
- Formal user-facing outputs should remain PDF-first; JSON, CSV, SQLite, and Markdown are support artifacts.

## Current Architecture

- `backend/`: FastAPI service, SQLite persistence, rule analysis, model routing, PDF generation.
- `frontend/`: React + ECharts dashboard and workbench UI.
- `samples/`: small JSON/CSV inputs for demos and tests.
- `scripts/`: local service launcher, smoke test, sample report generation.
- `docs/`: handoff, cleanup, and continuity documents.
- `app_bundle/`: source macOS `.app` bundle resources and icon assets. `scripts/install_app_entries.sh` also installs `.command` launchers to Downloads and Applications.

## Runbook

```bash
./scripts/run_local_services.sh
```

Install local click entries:

```bash
./scripts/install_app_entries.sh
```

Installed entries:

- `/Applications/IDS Industrial Data System.command`
- `/Users/linzezhang/Downloads/IDS Industrial Data System.command`
- `/Applications/IDS Industrial Data System.app`
- `/Users/linzezhang/Downloads/IDS Industrial Data System.app`

Use `.command` as the primary local double-click entry. It runs the same service launcher in Terminal and avoids macOS LaunchServices/Gatekeeper silently blocking ad-hoc `.app` bundles. Keep the Terminal window open while using the app; closing it stops the local runtime.

Regenerate the macOS app icon:

```bash
.venv/bin/python scripts/generate_app_icon.py
./scripts/install_app_entries.sh
```

The tracked final assets remain `app_bundle/assets/OpMeIcon.png` and `app_bundle/assets/OpMeIcon.icns` as legacy asset paths; the intermediate `.iconset` directory is intentionally ignored.

For verification:

```bash
./scripts/smoke_test.sh
```

Quick launcher verification:

```bash
OPEN_BROWSER=0 ./scripts/run_local_services.sh
cat data/backend_port data/frontend_port
curl -fsS "http://127.0.0.1:$(cat data/backend_port)/api/health"
curl -fsS "http://127.0.0.1:$(cat data/frontend_port)/api/health"
```

If dependencies were removed during cleanup, the launcher restores them from:

- `backend/requirements.txt`
- `frontend/package-lock.json`

## GitHub Continuity Rule

All future development for this system should be synchronized into:

`LinzeColin/KMOS`

Use the subdirectory:

`KM_IDSystem/`

Commit/PR summaries must include:

- task purpose
- changed subsystems
- validation commands and results
- remaining risks
- local files that are intentionally not tracked

## IDS v0.1 Staged Development

- Read-only main checkout: `/Users/linzezhang/Documents/Codex/GithubProject/KMOS` (must remain on clean `main`).
- Active task worktree: `/Users/linzezhang/Documents/Codex/GithubProject/_scratch/kmos-kmids-stage041`.
- Project scope: `KM_IDSystem/` only.
- Current local state: `STAGE-031..STAGE-040` and their independent batch review are merged to GitHub `main`; `STAGE-041` is locally reviewed, and `STAGE-042` is locally reviewed.
- Current task: `IDS-V0_1-STAGE043-P2`; the only next task is `IDS-V0_1-STAGE043-P3` in a separate run behind `IDS-STAGE043-P3-GATE`. Ten-stage batch review, upload, merge and app reinstall remain separate gates.
- Preserved Stage042 review transition: Completed task in this run: `IDS-V0_1-STAGE042-REVIEW`; Next allowed task: `IDS-V0_1-STAGE043-P1`. This is historical evidence, not the current gate.
- Stage042 review publishes `ids.stage042.automatic_lifecycle.stage_review.v1`, binds the committed Phase4 baseline, reruns all four phase checkers and machine-checks five repaired findings.
- Stage042 Phase 3 publishes `ids.stage042.automatic_lifecycle.phase3.scenarios.v1`, twelve isolated scenarios with actual lifecycle, process-crash recovery, termination, cleanup/delete, persistence and production effects disabled.
- Stage042 Phase 2 publishes `ids.automatic_lifecycle_policy.v0_1.stage042.p2`, an isolated reference-only in-memory candidate-decision slice. Canonical request IDs, positive versions, action-bound reasons, temporal resume evidence and paused-only cleanup now fail closed.
- `MOD-011`, `FORM-011`, and `PARAM-072..076` remain planned/proposed. The five timing values are derived from reviewed Stage040/041 bounds and require production calibration under `TASK-OPME-B-001`.
- Stage042 Phase 1 binds the unique approved source, reviewed Stage041 commit/tree and exact Stage037–041 contracts into `ids.stage042.automatic_lifecycle.phase1.v1`.
- The static contract preserves the authoritative state graph, owner/resource revalidation, Stage038–044 ownership, reference-only evidence, ordered shutdown and candidate-only cleanup while assigning no numeric parameters and performing no runtime.
- Stage041 review repaired `1 Critical / 3 Important / 0 Minor`: strict-integer CAS evidence, monotonic logical time/live-lease mutations, exact runtime contract semantics, and current handoff/governance truth are now machine checked and fail closed.
- `check_lock_registry_stage_review.py` reverifies the approved external source, reruns all four Stage041 phase checkers, machine-checks every repair, validates reviewed-local governance, and requires every review source to match the Git index.
- Stage041 Phase 4 binds the committed Phase 3 commit/tree and reviewed upstream hashes into an exact-shaped closeout contract plus stdout-only checker; no candidate commit or Stage42-43 review state was activated.
- The Phase 4 report composes the five-family lock lifecycle with the reviewed 8-type/11-state/4-terminal/21-transition graph, 3-attempt/2-retry dead-letter evidence, seven pressure signals and a two-class cleanup allowlist.
- One actual isolated acquire-renew-release sequence leaves zero active locks, two monotonic tombstone versions and a rejected stale commit. It is process-local orderly-shutdown evidence, not persistence, crash recovery or production readiness.
- Exact idempotent replay, matching-holder renewal and matching-holder release are lock decisions, not successful recovery. Automatic-recovery eligibility and observed success remain empty; manual cases stay fail-closed.
- Final Phase 4 validation: checker contract checks 16/16, delivery checks 6/6, focused 12/12, Stage005 157/157, Stage040-041 aggregate 109/109, full IDS v0.1 discovery 789/789, events 199 with zero parse/duplicate/semantic errors, and project-scoped dual-plane PASS.
- Stage041 Phase 1 binds the unique approved taskpack source and the terminal `BATCH031_040` lock hash into an exact-shaped metadata-only contract plus stdout-only fail-closed checker.
- The contract requires a shared source-pipeline guard plus an operation-specific lock, lexicographic multi-key ordering, atomic compare-and-set acquisition, one live holder, same-holder renewal, atomic fencing/version advance on takeover, and stale-token denial for commits, checkpoint/evidence mutation, renew, and release.
- Contention creates no queue record, runs no operation, consumes no retry budget, and assigns no implicit timing defaults. Automatic resume stays with STAGE-042, crash recovery with STAGE-043, and cleanup execution with STAGE-044.
- Final layered evidence: Stage041 checker `20/20`, focused tests `10/10`, Stage005 `156/156`, Stage037-040 `179/179`, historical Stage001-036 plus BATCH031-040 review compatibility `555/555`, and full IDS v0.1 discovery `744/744`. The first full run exposed 32 stale historical governance assertions; all were repaired without changing the immutable `BATCH031_040` hash. Pre-commit self-review also repaired one Important exact-shape gap so unknown nested fields and incomplete human-status projections fail closed.
- Batch review repaired one Critical and two Important findings by adding a strict ten-stage source/review/interface/index contract, a fail-closed checker, and a reviewed-no-upload governance/event route.
- `check_batch031_040_review.py` rehashes the approved archive, exact ten taskpack members, ten Stage review artifacts, reruns all Stage checkers, verifies Stage036-040 interface/hash bindings, and requires every review source to match the Git index.
- Final batch-review validation: batch tests `8/8`, Stage005 `151/151`, Stage031-039 `254/254`, Stage040 `55/55`, and full IDS v0.1 discovery `729/729`; six historical Stage038/039 compatibility assertions were repaired after the first full run exposed the new reviewed-no-upload state.
- Exact source status: `SOURCE_VERIFIED`; the unique Stage040 member is `IDS_v0_1_Final_Chinese_Revised/stages/STAGE-040_反压策略.md` with SHA-256 `f0ef128467300d7541796f8d51caca673f838cac2552eba2e415a94a07af614d`.
- Corrected Phase 1 defines queue/worker separation, envelope idempotency, retry/dead-letter, backpressure, lock granularity, automatic lifecycle, crash-recovery checkpoint, and cleanup allowlist interfaces. STAGE-039..044 retain dedicated runtime policy and implementation ownership.
- A six-surface finite-state check binds batch, roadmap, entry, Phase 1, source evidence, and review evidence. Independent review repaired `1 Critical / 1 Important / 0 Minor` and ended at `0 / 0 / 0`.
- Phase 2 implements one `asyncio` in-memory queue and worker over a real Git-tracked Phase 1 control document. Submission returns before completion; STAGE-037 transitions, Chinese status, duplicate admission, bounded-capacity backpressure, and input/output/error/checkpoint fields are exercised without persistence.
- The Phase 2 smoke runs only in `ISOLATED_NON_PRODUCTION_ASYNC_CONTROL_METADATA_SLICE` mode. It creates one real isolated control job, not an IDS business job, and does not activate a production service.
- Phase 3 repairs the resource conflict domain so `ARCHIVE`, `PARSE`, `INDEX`, and `REPORT` over one input share one lock key. Active conflicts pause before queue admission; terminal records permit a later same-source job.
- The seven Phase 3 scenarios validate duplicate click, an actual isolated worker exception, external-drive-offline control gating, actual project-volume free-space insufficiency, external-API-budget insufficiency without an API call, same-source cross-operation conflict, and protected cleanup denial. Physical drive removal, disk allocation, process termination, cleanup execution, and production runtime are not claimed.
- Phase 4 delivers the exact 8-type/11-state/21-transition graph, actual isolated failure record, capacity/resource/lock backpressure proofs, a two-class cleanup allowlist, an empty automatic-recovery set, six manual-action cases, orderly isolated shutdown proof, rollback steps, and known limits.
- The Phase 4 delivery checker returns `PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED`; this is closeout evidence, not production readiness or whole-stage acceptance.
- Stage040 whole-stage review repaired one Critical and two Important findings: malformed/non-JSON control metadata now returns structured fail-closed output without echoing invalid refs; active resource pauses project `暂停中` until `PAUSED`; and Stage040 explicitly records that scheduler-level starvation prevention is unproved and unimplemented.
- The Stage040 review checker independently rehashes the approved archive, unique ZIP member, roadmap, and instructions; revalidates the Phase 1-4 chain; and requires all review sources to match the Git index before returning `PASS_REVIEWED_LOCAL_PRODUCTION_DISABLED`.
- The previous batch upload is complete. For the current reviewed Stage041 state, GitHub/PR/issue/merge, app reinstall, production runtime, raw metadata content access, Stage042 execution and batch review remain disabled; only `IDS-V0_1-STAGE042-P1` may run next in a separate run.
- Whole-stage review repaired exact contract shapes, the missing API-budget pause proof, and the false same-operation resubmission instruction; all review sources must match the Git index before `completed_reviewed_local` is valid.
- Stage039 Phase 1 publishes `ids.retry_dead_letter.v0_1.p1`. It keeps `FAILED`, `DEAD_LETTERED`, `SUCCEEDED`, and `CANCELLED` immutable; retryable failure uses `RUNNING -> RETRY_WAIT`, exhaustion uses only `RETRY_WAIT -> DEAD_LETTERED`, and permanent failure uses `RUNNING -> FAILED`.
- Retry reservation does not consume budget; only atomic eligible admission increments `retry_count`. Resource pauses consume no retry budget. Duplicate transition replay cannot consume twice.
- The terminal manual-rerun contract requires a future implementation to create a new owner-authorized linked job with new job/idempotency identity and lineage; Stage039 validates only a non-persisted candidate and never reopens the terminal job.
- Phase 2 supplies `ids.retry_policy.v0_1.stage039.p2` with `max_retries=2`, total-attempt limit `3`, `[5, 30]` backoff ceilings, deterministic bounded nonzero hash jitter, and an exact retryable-safe-error allowlist. These values are `PROPOSED`, are not production calibrated, and roll back to `NO_AUTOMATIC_RETRY`.
- The isolated slice uses one real Git-tracked Stage039 control reference, a Stage038 in-memory transport admission, and a separately derived Stage039 in-memory policy snapshot with Stage037 candidate-only CAS transitions. The two control identities differ, so `max_retries` remains immutable. Two due admissions increment budget once each; duplicate failure/admission replay does not increment; exhaustion reaches `DEAD_LETTERED` at `retry_count=2`.
- Input refs, empty failure output refs, safe error, actual tracked-control checkpoint digest, policy version, audit ref, and Chinese owner status are preserved without persistence.
- Phase 3 validates exactly ten isolated scenarios: duplicate retry reservation/admission, actual worker exception with process-crash recovery deferred, drive/disk/API resource pauses, same-source cross-operation locking, retry exhaustion, immutable terminal replay, owner-authorized manual-rerun candidate lineage, and five-class protected cleanup denial.
- Stage038 supplies the actual isolated worker exception and actual local disk-free observation. Phase 3 performs no process termination, physical drive removal, disk allocation, API call, cleanup/delete, production runtime, persistence, database action, raw metadata access, or fake IDS business-data use.
- Manual rerun is candidate-only and idempotent: it requires owner authorization plus a new linked job ID and idempotency key, but creates no job and writes no queue or database state. Protected cleanup verifies exact Git-tracked refs and exposes no deletion path.
- Phase 4 binds the exact Stage037 8-type/11-state/21-transition graph, six failure decisions, the actual isolated three-attempt retry/dead-letter history, five capacity/resource/conflict signals, and the two-class cleanup allowlist into one machine-checked delivery report.
- Automatic handling is narrowly stated: two exact safe codes can enter controlled retry only when policy, budget, resource, CAS, and idempotency gates pass. No successful automatic recovery was observed. Eight conditions remain manual-action cases.
- Safe shutdown reuses reviewed Stage038 isolated transport closure. Stage039 has no persistent scheduler or process-recovery runtime; after exit, only a new linked-job candidate may be revalidated, no job is created, and terminal history remains immutable.
- Stage039 whole-stage review repaired four Important findings: invalid governance enums/task links, total-count drift, overclaimed terminal-rerun creation wording, and the absent durable review gate. All review sources must match the Git index.
- Stage040 Phase 1 publishes `ids.backpressure_policy.v0_1.p1`. Healthy pressure may return `ADMIT`; soft queue pressure throttles admission; hard capacity creates no queue record; drive/disk/API resource pressure uses only legal STAGE-037 pause paths; unknown or stale pressure denies admission and requires manual review.
- Throttle, denial, and resource pause consume no retry budget. Priority cannot bypass a safety gate, terminal states stay immutable, and active jobs must pass through `PAUSE_REQUESTED` before `PAUSED`.
- Phase 1 assigns no numeric values. Queue thresholds, disk reserve, API budget window, high/low watermarks, observation TTL, per-job-type concurrency, and admission rate limit require separately sourced, versioned, tested, and rollback-ready Phase 2 selection.
- Stage040 Phase 2 publishes `ids.backpressure_policy.v0_1.stage040.p2` as an isolated non-production decision slice. Its explicit parameters are soft/hard queue thresholds `2/4`, disk free threshold `1 GiB` above a `512 MiB` reserve, API window `60 s`, queue low watermark `1`, observation TTL `30 s`, per-job-type concurrency `1`, and admission rate `4` per window.
- All nine Phase 2 values are `PROPOSED`, not production calibrated, and linked to `TASK-OPME-B-001`. `MOD-009`, `FORM-009`, and `PARAM-056..064` were the planned registrations at Stage040 Phase 2 completion, when totals were `9/9/64`; after Stage041 and Stage042 Phase 2, current totals are `11/11/76`, while active counts remain `7/7/49`.
- The decision engine is deterministic and in-memory: healthy observations admit, soft pressure/rate/concurrency throttle, hard capacity denies without a job, and drive/disk/API gates return legal pause candidates. Invalid or stale observations require manual review; terminal states remain immutable; duplicate decisions replay idempotently.
- Phase 2 observes actual free space only for the project filesystem and writes no runtime output. It performs no queue/worker/retry scheduler/lock/resume/cleanup/database/raw-source/API/production action and creates no IDS business job.
- Final Phase 2 validation: checker `18/18` contract and `8/8` slice checks; focused `15/15`; Stage040 `25/25`; Stage005 `147/147`; Stage031-039 `254/254`; Stage026-030 `75/75`; full IDS v0.1 discovery `687/687`; changed-only governance `0` errors / `0` warnings; `189` events with no duplicate ID; owner render drift/reference issues `0/0`.
- Stage040 Phase 3 validates eight isolated scenarios: duplicate decision replay, actual isolated worker exception boundary, external-drive-offline pause, actual project-filesystem disk observation plus a no-allocation low-disk boundary, API-budget pause, same-source cross-operation throttling, reviewed one-execution/three-conflict lock proof, and five-class protected cleanup denial.
- The worker exception and project free-space observation are actual isolated observations. Drive/API/low-disk boundary inputs are control metadata; no physical drive removal, disk allocation, process termination, external API call, cleanup/delete, Stage040 queue/worker runtime, production lock, crash recovery, persistence, database action, or production activation occurred.
- Phase 3 replays the reviewed Stage038/039 in-memory lock proof but keeps production lock/lease/fencing with STAGE-041. It verifies Git-tracked fact source, manifest, evidence ledger, report snapshot, and audit log refs without exposing a delete path; cleanup runtime remains owned by STAGE-044.
- Final Phase 3 validation: checker `18/18` contract and `8/8` scenario checks; focused `11/11`; Stage040 `36/36`; Stage005 `148/148`; Stage031-039 `254/254`; Stage026-030 `75/75`; full IDS v0.1 discovery `699/699`; changed-only governance `0` errors / `0` warnings; `190` events with no duplicate ID; owner render drift/reference issues `0/0`.
- Stage040 Phase 4 binds the exact Stage037 8-type/11-state/4-terminal/21-transition graph, seven pressure signals, and the reviewed actual Stage039 three-attempt/two-retry/dead-letter history into one fail-closed delivery report.
- The cleanup allowlist remains limited to temporary staging and incomplete derivative outputs; fact sources, manifests, evidence ledgers, report snapshots, and audit logs are protected. No delete or cleanup runtime runs.
- Automatic recovery eligibility and observed success are both empty. Healthy new admission is not recovery; eight unknown, terminal, resource, worker, conflict, calibration, contract, and crash cases require manual handling or a downstream gate.
- Safe shutdown replays reviewed isolated transport closure and records fresh-observation recovery plus P4-only rollback. There is no persistent pressure state, automatic resume, process recovery, production runtime, or production-readiness claim.
- Final Phase 4 validation: checker `14/14` contract and `8/8` delivery checks; focused `10/10`; Stage040 `46/46`; Stage005 `149/149`; Stage031-039 `254/254`; Stage026-030 `75/75`; full IDS v0.1 discovery `710/710`; changed-only governance `0` errors / `0` warnings; `191` events with no duplicate ID; owner render drift/reference issues `0/0`.
- STAGE-038 retains queue/worker transport; STAGE-039 retry/dead-letter; STAGE-041 locks/leases/fencing; STAGE-042 automatic resume; STAGE-043 crash recovery; STAGE-044 cleanup execution. Phase 1 executed none of these runtimes.
- `BATCH031_040` remains immutable in its terminal uploaded state. `BATCH041_050` is the current lock and remains `push_allowed=false`; do not upload, merge, mutate issues, reinstall app entries, or enter Stage042 in this review run.
- Current Phase 4 evidence adds `STAGE041_PHASE4_CLOSEOUT.md`, `lock_registry/stage041_lock_registry_delivery_contract.json`, `scripts/check_lock_registry_delivery.py`, and `tests/test_stage041_lock_registry_delivery.py`.
- The real metadata root `/Users/linzezhang/Downloads/IDS_MetaData` is path-only governance context. Do not read, list, hash, open, copy, move, delete, modify, dump, scan, normalize, or commit its contents.
- Do not use fake IDS business data, fake database rows, placeholder corpus, fabricated profiles, dumps, execution logs, or evidence.

## Local Files Intentionally Not Tracked

- `.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `.pytest_cache/`
- `__pycache__/`
- runtime SQLite/log files under `data/`
- generated PDF/ZIP artifacts under `reports/` and `outputs/`

These are recoverable from source, scripts, and GitHub.

## Known Limits

- STAGE-039 review reconciled all `21` project-level semantic diagnostics from
  the Phase 2 policy registry by using `planned` / `PROPOSED` and linking
  production calibration to `TASK-OPME-B-001`. Stage040 added one planned model,
  one planned formula and nine planned parameters; Stage041 and Stage042 Phase 2
  add three more of each registry type plus seventeen planned parameters. Current
  totals are 12/12/81 while active counts remain 7/7/49. The remaining `29`
  project-wide diagnostics are expected sparse root or unrelated-project paths
  and must not trigger sparse expansion.
- Docker was not available on this Mac during validation, so Docker Compose syntax could not be executed locally.
- macOS may reject the ad-hoc `.app` bundle through Gatekeeper/LaunchServices. The `.command` launcher is the current reliable click path.
- Real MQTT/OPC-UA/Modbus device ingestion is not implemented in this version.
- Model providers are configurable, but no plaintext API keys should be committed.
- STAGE-039 is locally reviewed, not production-ready. Persistent retry/dead-letter state, measured backpressure/fairness, production lock/lease/fencing, automatic lifecycle, process crash recovery, cleanup execution, PostgreSQL actions, raw source reads, and IDS business job execution remain absent. The selected Phase 2 values remain uncalibrated proposals and production automatic retry remains disabled.
- STAGE-040 Phase 3 provides isolated scenario evidence, not production or physical fault proof. Its values remain uncalibrated proposals; production lock/lease/fencing, automatic resume, crash recovery, cleanup execution, database action, raw-source read, IDS business jobs, GitHub actions, and app reinstall remain absent.
