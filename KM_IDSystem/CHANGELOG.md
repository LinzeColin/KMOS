# Changelog

## IDS v0.1 STAGE-045 Phase 4 - 2026-07-20

- Added `ids.stage045.file_type_detection.phase4.delivery.v1`, bound to the approved source, exact committed Phase3 predecessor and five indexed Phase3 artifacts.
- The stdout-only checker replays the fourteen Phase3 scenarios, derives six schema-only parser-output samples and seven non-runtime fallback-log samples, and recomputes format coverage, confidence/disposition metrics and four fail-closed failure classes.
- Parser-output samples contain only `text/tables/pages/sections/confidence/errors`, no business content, and are explicitly `SCHEMA_ONLY_NOT_EXECUTED`; all parser versions remain `UNASSIGNED_NOT_IMPLEMENTED` and available parser routes remain empty.
- Fallback samples are derived control evidence with zero attempts, zero silent drops and zero parser switches. They are not Stage048 runtime logs; no parser, fallback, configuration mutation, persistence or evidence promotion ran.
- Valid TDD RED produced fifteen expected assertion failures and one expected missing-checker error across thirteen tests. Final GREEN passed checker `16/16 + 9/9`, focused `13/13`, Phase1-4 compatibility `59/59`, Stage005 `172/172`, Stage041-045 aggregate `327/327` in `1138.506s`, and full discovery `1077/1077` in `1566.023s`; seven historical review checkers, `219` clean events, exact 30-path event coverage, idempotent owner rendering and project dual-plane also pass.
- The first aggregate reached `323/327` and the first full discovery reached `1073/1077`; all eight failures were stale historical forward-route assertions ending at Stage045 P3. Repairs add only the exact `Stage045 P4 -> Stage045 Review` route and preserve every historical evidence and safety assertion.
- Final-evidence synchronization then failed closed only the Stage042 review checker's staged-Handoff allowlist; adding the same exact P4 current task restored the checker and its review tests `10/10` in `253.879s`.
- Routed the only next task to separate `IDS-V0_1-STAGE045-REVIEW` with `push_allowed=false`. No business source-file access, whole-stage review, Stage046, batch review, GitHub action, app reinstall, dependency installation, raw metadata access or production action ran.

## IDS v0.1 STAGE-045 Phase 3 - 2026-07-20

- Added `ids.stage045.file_type_detection.phase3.scenarios.v1`, exact source/Phase2/integration/upstream-bound scenario evidence, and a checker that imports rather than duplicates the committed Phase2 detector.
- Replayed fourteen bounded synthetic in-memory scenarios across PDF, DOCX, XLSX, CSV, TXT, PNG, JPEG, both TIFF endiannesses, unknown binary, corrupt ZIP, conflicting signals, extension-only evidence and instruction-like text. All fourteen return the exact governed type/state/confidence/route tuple.
- Enforced explicit quality dispositions: high-confidence results are route candidates only; medium results require quality review; low, conflict and unknown results require owner review; corrupt input returns an explicit no-fallback error. `silent_drop_count=0`.
- Proved instruction-route invariance without retaining the instruction text: the result remains `UNTRUSTED_EVIDENCE_TEXT`, cannot override system rules or authorize tools, and does not claim the Stage050 scanner.
- Valid TDD RED produced two governance failures and sixteen missing-artifact errors across eighteen tests. Final GREEN passed focused `18/18` in `1.069s`, Phase1-3 compatibility `46/46` in `2.069s`, Stage005 final evidence recheck `171/171` in `38.633s`, Stage041-045 aggregate `314/314` in `1083.079s`, and full discovery `1063/1063` in `1540.095s`; seven historical review checkers, `218` events, idempotent owner rendering and project dual-plane also pass.
- The first aggregate failed closed `14/314` on stale current-route/index assertions; the first full discovery failed closed `5/1063` on four P3-to-P4 route assertions and one stale owner render. A final-evidence Stage005 run also failed closed `22/171` until its exact roadmap result binding was synchronized. Repairs were limited to exact forward-route compatibility, existing historical safety invariants, generated owner views and that exact result binding; the invalid wrong-workdir targeted command was interrupted and is explicitly not counted as PASS.
- Pre-commit self-review repaired one Important fail-closed gap: instruction control flags are now derived from the bounded Phase2 evidence wrapper and participate in scenario status instead of being hard-coded in the summary. The existing instruction test now proves an unsafe wrapper forces `FAIL_CLOSED`, without changing the eighteen-test count or entering Phase4.
- Routed the only next task to separate `IDS-V0_1-STAGE045-P4` with `push_allowed=false`. No business source-file access, parser dispatch/execution, fallback, prompt-injection scan, evidence promotion, persistence, Phase4, whole-stage review, batch review, GitHub action, app reinstall, dependency installation, raw metadata access or production action ran.

## IDS v0.1 STAGE-045 Phase 2 - 2026-07-19

- Added `ids.stage045.file_type_detection.phase2.v1` and `ids.file_type_detector.v0_1.stage045.p2`, exact source/Phase1/upstream-bound artifacts for a bounded synthetic in-memory detection slice.
- Evaluated three controls: PDF signature, DOCX ZIP container with canonical markers, and misleading `.pdf` text content. The first two emit high-confidence parser-route candidates without dispatch; the conflict returns owner review with `UNKNOWN` confidence.
- Recorded detector version, candidate types, confidence, bounded signal evidence and route state. OOXML requires `[Content_Types].xml` plus exactly one governed namespace; extension alone remains low-confidence review-only evidence.
- Wrapped instruction-like source-derived text as `UNTRUSTED_EVIDENCE_TEXT` with system-instruction, tool-authorization and policy-override permissions all false. This is not the Stage050 scanner.
- Valid TDD RED produced eighteen expected failures across fifteen tests while Phase2 artifacts were absent. Final GREEN passes the isolated checker, focused `15/15`, Phase1 compatibility `13/13`, Stage005 `170/170` in `37.209s`, Stage041-045 aggregate `296/296` in `1157.221s`, and full IDS v0.1 discovery `1044/1044` in `1524.911s`.
- The first aggregate ran `296` tests in `1113.138s` and failed twelve checks because four historical current-route allowlists ended at Stage045 P1 and eight review assertions rejected unstaged modified review sources. A second aggregate failed one remaining Stage042 route assertion, and the first full discovery failed four Stage038/039 route assertions. Repairs were bounded to the exact P2-to-P3 route and one staged validation snapshot; all failed runs remain recorded and are not counted as PASS.
- Routed the only next task to separate `IDS-V0_1-STAGE045-P3` with `push_allowed=false`. No business source-file access, parser dispatch/execution, fallback, Stage050 scanner, evidence promotion, persistence, Phase3, whole-stage review, batch review, GitHub action, app reinstall, dependency installation, raw metadata access or production action ran.

## IDS v0.1 STAGE-045 Phase 1 - 2026-07-19

- Added `ids.stage045.file_type_detection.phase1.v1`, an exact-shaped static engineering contract plus stdout-only fail-closed checker bound to the unique approved Stage045 taskpack member, reviewed Stage044 commit/tree/parent and exact Stage013/027/037/044 authority hashes.
- Defined signal precedence as `signature > MIME > filename extension`; filename extension remains advisory and can never route alone. ZIP magic is insufficient for OOXML: DOCX requires `[Content_Types].xml` plus `word/`, while XLSX requires `[Content_Types].xml` plus `xl/`.
- Defined ten canonical types, six detection states and explicit conflict/unknown/unsupported/corrupt outcomes. Silent fallback is forbidden; unresolved cases require owner review or an explicit error.
- Reserved parser route, normalized output, fallback and prompt-injection implementation for Stage046-050. `text`, `tables`, `pages`, `sections`, `confidence` and `errors` are untrusted candidate artifacts and cannot bypass the quality gate into high-confidence evidence.
- TDD RED produced four expected failures and twelve missing-artifact errors across thirteen focused tests. Final GREEN passed core checker `22/22`, focused `13/13`, Stage005 `169/169` in `35.381s`, Stage041-045 aggregate `281/281` in `1152.681s`, full discovery `1028/1028` in `1583.104s`, all seven Stage038-044 review checkers, `216` clean events, idempotent owner rendering and project dual-plane.
- The first two aggregate runs (`272/281`, `270/281`) and first full run (`1022/1028`) failed closed on stale historical current-route assertions and one exact Stage044 scenario-test hash binding. Repairs were limited to the exact `IDS-STAGE045-P1 -> IDS-STAGE045-P2-GATE` forward route and one narrowly enumerated Git-index hash; historical review conclusions and runtime safety boundaries were not relaxed.
- Routed the only next task to separate `IDS-V0_1-STAGE045-P2` with `push_allowed=false`. No source file open/scan/hash/sniff, detector/parser/fallback execution, evidence promotion, manifest/audit/state/persistence/database write, Phase 2-4/review, Stage046-050, batch review, GitHub action, app reinstall, dependency installation, raw metadata access or production action ran.

## IDS v0.1 STAGE-044 Review - 2026-07-19

- Completed the independent whole-stage review under `ACC-STAGE-044` and repaired `1 Critical / 5 Important / 0 Minor` findings: recoverable nonterminal states admitted as cleanup candidates, subset-only contract validation, unbound candidate provenance, noncanonical lexical paths, mutable human-status claims, and missing durable reviewed-local governance.
- Restricted candidate states to `FAILED`, `DEAD_LETTERED`, and `CANCELLED`; `PAUSED` and `RETRY_WAIT` now always return `CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN` because resume/retry owners may still recover them.
- Bound creator to job, input refs to the exact five approved Git-tracked sources, and root/manifest/writer/resource refs to canonical candidate payloads. Dot segments, duplicate separators, forged identities and arbitrary tracked refs now fail closed.
- Replaced the subset fast path with full contract evaluation plus canonical whole-contract SHA-256. Human status action, Chinese label and severity are exact, so an overclaim such as “文件已自动删除” invalidates the contract.
- Added `ids.stage044.half_product_cleanup.stage_review.v1`, the Phase4 commit/tree ancestry binding, four-phase replay, six canonical finding checks, Git-index source binding, review tests, event, machine run and Stage045 separate-entry gate.
- Review RED produced `18` expected failures across `10` tests; final focused review passed `10/10` in `159.695s`, Stage041-044 aggregate passed `268/268` in `1189.358s`, and full IDS v0.1 discovery passed `1014/1014` in `1665.517s`. Earlier failed runs exposed and bounded stale historical routes plus one reverted hash-chain edit; none were hidden or treated as PASS. Final short gates passed Stage005 `168/168` in `34.019s`, all seven Stage038-044 review checkers, `215` clean events, idempotent owner rendering and project dual-plane.
- Routed the only next task to separate `IDS-V0_1-STAGE045-P1` with `push_allowed=false`. No Stage045, batch review, GitHub upload/merge, issue action, app reinstall, dependency installation, raw metadata content access, cleanup/delete, persistence or production action ran.

## IDS v0.1 STAGE-044 Phase 4 - 2026-07-19

- Added `ids.stage044.half_product_cleanup.phase4.delivery.v1`, an exact source/Phase3/upstream-hash-bound closeout contract and fail-closed checker that compose the reviewed state graph, retry log, pressure, lock, crash-recovery and cleanup evidence without enabling a runtime.
- Reverified 8 job types, 11 states, 4 terminals, 21 transitions, 3 attempts, 2 retries ending in `DEAD_LETTERED`, 7 pressure signals, 14/14 isolated scenarios, child exit evidence `73`, 25 full and 16 selected same-source conflicts, and zero operation/queue/retry/delete effects.
- Preserved only `TEMP_STAGING_OUTPUT` and `INCOMPLETE_DERIVATIVE_OUTPUT` as all-gates-satisfied conditional cleanup candidates. Fourteen original/source/database/fact/manifest/evidence/audit/report/index/checkpoint/held/succeeded classes remain protected; delete attempt and deleted ref counts are zero.
- Distinguished three upstream recovery candidates and two cleanup candidates from current automatic eligibility. Automatic recovery/cleanup eligibility and observed success are empty; fourteen missing, stale, active, conflicting or uncalibrated conditions require manual action.
- Added executable safe-shutdown, durable-evidence-only recovery, Phase4-only rollback and known-limit instructions. No filesystem or writer probe, scan/traversal, production lock, process recovery, state mutation, `dirfd`/`openat`/`unlinkat`, move/overwrite/delete, audit/persistence/database or production action ran.
- TDD RED produced `14` expected assertion failures and `1` expected missing-checker error across `12` focused tests. Final GREEN passes checker `15/15 + 12/12`, focused `12/12`, Stage005 `168/168`, Stage041-044 aggregate `258/258` in `1196.647s`, full discovery `1004/1004` in `1749.795s`, six Stage038-043 historical review checkers, `214` clean events, idempotent rendering and project dual-plane.
- The initial aggregate reached `257/258` and exposed one Stage044 Phase2 historical handoff assertion ending at P4. Repair extended only the exact P4-to-Review route and rebound the exact Phase2-test -> Phase3-checker -> Phase4-checker hash chain; no historical review conclusion or runtime safety boundary was weakened.
- Routed the only next task to separate `IDS-V0_1-STAGE044-REVIEW` with `push_allowed=false`. No whole-stage review, Stage045, batch review, GitHub upload/merge, issue action, app reinstall, dependency installation, raw metadata content access, cleanup/delete or production action ran.

## IDS v0.1 STAGE-044 Phase 3 - 2026-07-19

- Added `ids.stage044.half_product_cleanup.phase3.scenarios.v1` and `ids.half_product_cleanup_policy.v0_1.stage044.p3.scenarios`, exact source/Phase2/upstream-hash-bound artifacts for fourteen isolated reference-only cleanup scenarios.
- Verified exact duplicate replay, changed-payload conflict, reviewed isolated child self-exit `73`, controlled drive/disk/API pressure, active or unknown writers, stale identity, same-path lock conflict, four-operation source-pipeline exclusion, five core protected artifacts, all fourteen protected classes and review-only eligible candidates.
- Replayed the Stage041 full `25`-conflict matrix and selected four-family `16`-conflict matrix with zero operation, queue or retry effects. Replayed Stage043 output-free control-process evidence without signal, kill, production crash, process recovery or worker restart.
- Kept cleanup scan, real path access, filesystem probe/traversal, production lock, `openat`, `unlinkat`, move, overwrite, delete, state mutation, audit/persistent/runtime/database write and production activation disabled; every candidate has `delete_allowed=false`.
- TDD RED produced `3` expected failures plus `16` missing-artifact errors across `19` focused tests. Final GREEN passes checker `18/18 + 14/14`, focused `19/19` in `14.295s`, Stage005 `167/167` in `31.893s`, Stage041-044 aggregate `246/246` in `1093.223s`, full discovery `991/991` in `1436.808s`, six Stage038-043 historical review checkers, `213` clean events, idempotent rendering and project dual-plane.
- The initial aggregate `231/246` and full discovery `990/991` runs failed closed on historical current-route/index bindings and one overbroad automatic-recovery fact. Repairs were limited to the verified P3→P4 forward route, exact upstream hash compatibility and explicit `persistent_recovery_state_available_after_exit=false` / `automatic_recovery_performed=false`; no historical review conclusion or runtime safety boundary was weakened.
- Routed the only next task to separate `IDS-V0_1-STAGE044-P4` with `push_allowed=false`. No Phase 4, whole-stage review, Stage045, batch review, GitHub upload/merge, issue action, app reinstall, dependency installation, raw metadata content access, cleanup/delete or production action ran.

## IDS v0.1 STAGE-044 Phase 2 - 2026-07-19

- Added `ids.stage044.half_product_cleanup.phase2.v1` and `ids.half_product_cleanup_policy.v0_1.stage044.p2`, a deterministic in-memory, reference-only cleanup-candidate decision slice with no scanner, traversal, filesystem probe, lock operation, persistence or delete path.
- Registered `ASM-009`, `MOD-013`, `FORM-013` and `PARAM-082..086` as planned / `PROPOSED`: scan `300 s`, retention `600 s`, lock lease `30 s`, writer quiescence `60 s` and attempt timeout `30 s`. They remain uncalibrated under `TASK-OPME-B-001` and do not start timers or runtime work.
- Restricted positive decisions to two governed classes in five non-active states. Fourteen protected classes plus any hold, durable reference, resource block, unknown identity, missing exclusive lock or missing quiescence fail closed; every result keeps `delete_allowed=false` and requires human review.
- Exact canonical request replay is idempotent and changed-payload reuse conflicts. The slice emits no absolute path or raw payload and performs no read, stat, `lstat`, walk, `dirfd`, `openat`, `unlinkat`, move, overwrite, audit write, database, queue, process, API or production action.
- TDD RED produced `19` expected failures across `16` focused tests. Final GREEN passes checker `20/20 + 15/15`, focused `16/16` in `1.891s`, Stage005 `166/166` in `29.280s`, Stage041-44 aggregate `227/227` in `1018.985s`, full discovery `971/971` in `1415.789s`, six historical review checkers, `212` clean events, idempotent rendering and project dual-plane.
- Layered regression exposed stale historical current-route allowlists and exact upstream-hash drift. Repairs were bounded to verified Stage042/043 hash sets plus the exact `IDS-STAGE044-P2 -> IDS-STAGE044-P3-GATE` route while retaining Git-index binding; no historical contract, review conclusion or runtime safety boundary was relaxed.
- Routed the only next task to separate `IDS-V0_1-STAGE044-P3` with `push_allowed=false`. No Phase 3, Phase 4, whole-stage review, Stage045, batch review, GitHub upload/merge, issue action, app reinstall, dependency installation, raw metadata content access, cleanup/delete or production action ran.

## IDS v0.1 STAGE-044 Phase 1 - 2026-07-19

- Added `ids.stage044.half_product_cleanup.phase1.v1`, an exact-shaped static engineering contract plus stdout-only fail-closed checker bound to the unique approved Stage044 taskpack member, committed Stage043 reviewed-local baseline and reviewed Stage029/037–043 controls.
- Restricted possible cleanup candidates to `TEMP_STAGING_OUTPUT` and `INCOMPLETE_DERIVATIVE_OUTPUT`; fourteen raw/source/database/fact/evidence/audit/report/index/checkpoint/held/succeeded classes are immutable protected artifacts.
- Bound every future candidate to governed job/attempt/creator, approved canonical root and relative path, artifact class and rebuildability, retention/legal/owner holds, manifest plus immutable `lstat` identity, durable references, resource observations, exclusive namespace lock and writer quiescence.
- Specified future `dirfd`/`openat`/`O_NOFOLLOW`/`unlinkat` and immediate identity-revalidation semantics while keeping scan, traversal, candidate evaluation, lock acquisition, move, overwrite, unlink, delete, audit write, state mutation, persistence and production runtime disabled in Phase 1.
- Preserved exact-replay idempotency, changed-payload conflict, separate audit identity and immutable terminal results. All five policy numbers remain deferred and uncalibrated.
- TDD RED produced four expected assertion failures and twelve missing-artifact errors across thirteen tests. Final GREEN passes checker `22/22`, focused `13/13`, Stage005 `165/165`, Stage041-44 aggregate `211/211` in `1014.663s`, full discovery `954/954` in `1403.519s`, six historical review checkers, `211` clean events, idempotent rendering and project dual-plane.
- Layered regression repaired only exact forward compatibility through `IDS-STAGE044-P1 -> IDS-STAGE044-P2-GATE`; one accidental Stage043 hash drift was reverted instead of rebinding historical contracts. Root governance remains a reported sparse-worktree conflict because `scripts/lean_governance.py` is absent.
- Routed the only next task to separate `IDS-V0_1-STAGE044-P2` with `push_allowed=false`. No Phase 2, Stage045, whole-stage review, batch review, GitHub upload/merge, issue action, app reinstall, dependency installation, raw metadata content access, cleanup/delete or production action ran.

## IDS v0.1 STAGE-043 Review - 2026-07-19

- Completed the independent whole-stage review under `ACC-STAGE-043` and repaired `1 Critical / 5 Important / 0 Minor` findings: unbound worker/lease/checkpoint/quarantine identities, premature crash detection, contradictory resource signals, unclassified retry/safe-failure errors, non-structured Phase1 failures with incomplete live-source checks, and missing durable reviewed-local governance.
- Bound lease ownership to the worker instance and checkpoint/quarantine digests to the canonical recovery kind and request key. Cross-worker or forged evidence now returns manual review with no transition candidate.
- Required heartbeat staleness and lease grace at the recorded detection time, exact resource-gate/signal agreement, and Stage039 transient/permanent error allowlists. Malformed Phase1 contracts now return structured fail-closed checks while rehashing the archive, unique Stage043 member, roadmap and instructions.
- Added `ids.stage043.worker_crash_recovery.stage_review.v1`, a committed Phase4 commit/tree ancestry binding, reruns of all four phase checkers, six canonical finding checks, Git-index source binding, review tests, reviewed-local batch/roadmap/event state and the Stage044 separate-entry gate.
- Review RED produced `12` assertion failures and `1` error across `10` tests. Final GREEN passes review `10/10`, Phase1/2 repairs `30/30`, Phase3 replay `18/18`, Stage005 `164/164`, Stage041-043 aggregate `198/198` in `988.205s`, full discovery `940/940` in `1355.634s`, six Stage038-043 review checkers, `210` clean events, idempotent rendering and project dual-plane. The first aggregate/full runs exposed five historical current-gate assertions; repairs were limited to the verified `Stage043 review -> Stage044 P1 gate` route and did not authorize Stage044.
- Routed the only next task to separate `IDS-V0_1-STAGE044-P1` with `push_allowed=false`. No Stage044 implementation, batch review, GitHub upload/merge, issue action, app reinstall, process recovery, state mutation, cleanup/delete, persistence, raw-data or production action ran.

## IDS v0.1 STAGE-043 Phase 4 - 2026-07-19

- Added `ids.stage043.worker_crash_recovery.phase4.delivery.v1`, an exact source/commit/tree/upstream-bound closeout contract and fail-closed checker that compose the reviewed state graph, retry log, pressure, lock, lifecycle and crash-recovery evidence without enabling a runtime.
- Replayed the 8-job-type/11-state/4-terminal/21-transition graph, 3-attempt/2-retry `DEAD_LETTERED` log, seven pressure signals and all 13 Stage043 scenarios. The isolated control self-exit remains code `73`; no process probe, signal, kill, restart or recovery ran.
- Classified three paths as conditional engineering candidates only. Current automatic-recovery eligibility and observed success are both empty; all 13 governed cases require manual action because durable recovery state and production calibration are absent.
- Preserved 25 full and 16 selected same-source conflicts with zero operation/queue/retry effects. Two cleanup classes remain reference-only candidates, five evidence classes remain protected, and Stage044 retains cleanup ownership.
- Final GREEN passed checker `14/14 + 14/14`, focused `11/11` in `98.108s`, Stage005 `163/163`, Stage041-043 aggregate `185/185` in `660.796s`, full discovery `926/926` in `1024.295s`, five historical Stage038-042 review checkers, 209-event semantics, idempotent rendering and project dual-plane.
- Layered validation repaired only bounded forward compatibility through `IDS-STAGE043-P4 -> IDS-STAGE043-REVIEW-GATE` and the resulting exact P2-test → P3 → P4 hash chain. No historical review conclusion or runtime safety boundary changed.
- Routed the only next task to separate `IDS-V0_1-STAGE043-REVIEW` with `push_allowed=false`; no whole-stage review, Stage044, batch review, GitHub upload/merge, issue action, app reinstall or production action ran.

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
