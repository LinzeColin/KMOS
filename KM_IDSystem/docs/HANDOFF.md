# IDS / Industrial Data System Handoff

## Canonical Repository Override - 2026-07-18

- Canonical GitHub repository is `LinzeColin/KMOS`; KMIDS is stored in `KM_IDSystem/`.
- The local main tree `/Users/linzezhang/Documents/Codex/GithubProject/KMOS` is read-only. Development must use an isolated worktree under `/Users/linzezhang/Documents/Codex/GithubProject/_scratch/`.
- Older `LinzeColin/CodexProject`, `main_worktree/CodexProject/KM_IDS`, and `KM_IDS/KM_IDSystem` references below are historical evidence only and must not route new commits or pushes.
- This override changes repository routing only. It does not authorize any IDS Stage/phase entry, production activation, enterprise DWS access, external writes, or raw-data access.
- `/Users/linzezhang/Downloads/IDS_MetaData` remains a path-only no-read/no-list/no-hash/no-copy/no-modify boundary.
- Public-safe BidScout Skill contracts are integrated under `KM_IDSystem/搜标项目/`; they are not evidence that the full BidScout product or real-data pipeline has been implemented.

## Current Gate - 2026-08-12

- 本节覆盖下方较早的“Current Gate”和 GitHub handoff 对当前任务的指向；下方未特别标为当前的内容只保留为历史交接证据。
- 本轮完成任务：`IDS-V0_1-STAGE049-P2`。当前状态为 `PHASE2_CONTROLLED_DIFFERENTIAL_ELIGIBILITY_RUNTIME_DISABLED`：实现一个只在内存处理两个 reference-only control 候选的差异化资格切片，记录 control-fixture parser 版本与置信度，并返回明确中文处置；它不读取文件、不比较解析正文、不创建实际解析产物或任何服务。
- 唯一合同上下文仍是冻结的 Stage049 任务包文本、Stage049 P1 合同与 Stage048 已复审工件；没有建立第二权威事实源，也没有保留业务正文、文件路径、原始异常或原始元数据内容。每个候选继续严格限定为七个 reference-only 字段，Stage047 六字段解析产物形状保持为后续合同，P2 不创建或比较其中的实际内容。
- 合格控制对需要两个不同版本，且只返回 `CONTROL_CANDIDATES_RETAINED_FOR_QUALITY_REVIEW`；版本不足、元数据不一致和非法输入均有明确处置。所有候选仍为 `CANDIDATE`，质量状态仍为 `UNASSESSED`，没有创建人工复核任务、自动 fallback 或高可信证据。
- `UNTRUSTED_EVIDENCE_TEXT/EVIDENCE_ONLY` 继续固定为数据标签；系统指令、工具授权和策略覆盖均为 `false`。Stage048 仍拥有 fallback，Stage050 仍拥有运行时提示注入标记，P2 没有改写上游路由、输出或降级结论。
- 回滚只撤回 Stage049 P2 的切片、合同、范围说明、聚焦用例、machine run 和治理投影，回到 `PHASE1_DIFFERENTIAL_PARSER_EVALUATION_BOUNDARY_RUNTIME_DISABLED`；必须保留 P1、既有阶段工件、原始资料、manifest、evidence ledger、audit 与已交付报告。
- 聚焦 Stage049 P2 直接单元用例通过 `8/8`，P1 前序兼容用例通过 `7/7`，Stage048 P1--P4 及复审前序兼容用例通过 `48/48`，治理回归报告为 `valid=true`，中文视图已重渲染 7 个文件。证据为 P2 范围边界、切片合同、切片实现、聚焦用例、本轮 machine run、event、batch/roadmap、机器事实与生成的中文视图。
- 未读取 IDS 业务源或原始元数据；未执行文件识别、真实路线、真实 parser、解析正文比较、真实 fallback、提示注入扫描、运行时日志、人工复核队列、质量门、证据提升、持久化、Agent、模型调用、OVH 部署、生产激活、Stage049 P3、批次复审、上传或推送。
- 下一步仅允许在独立 run 进入 `IDS-V0_1-STAGE049-P3`，门为 `IDS-STAGE049-P3-GATE`。Stage049 P2 受控资格切片完成不等于解析器运行、实际解析质量、OVH 部署、生产就绪或 GitHub 上传。

## Final GitHub Handoff - 2026-07-26

- Owner explicitly ended this thread and authorized a final GitHub handoff of all existing KMIDS progress, the taskpack and key iteration information.
- Owner then explicitly corrected the destination to `main`: existing PR [LinzeColin/KMOS #193](https://github.com/LinzeColin/KMOS/pull/193) is only the gated merge channel, and final cleanup must leave no open PR, remote task branch or issue created by this delivery. This follow-up supersedes the earlier Draft-only restriction after CI passes; it still does not authorize Stage048 entry, production activation or app reinstall.
- The branch preserves all Stage041–047 commits. `BATCH041_050` remains `7/10`; Stage048–050 and the ten-stage batch review have not started.
- Latest observed `origin/main` is `12d6fa9f46786387ee21d9bd3c682175464f3554`; merge base is `0495b8482b78ff937a92ee061c92980bcbde173b`. Before final handoff commits the branch was 38 commits ahead and 108 behind, so final integration must use GitHub's current merge context and pass CI before merge.
- The approved taskpack was imported as 183 byte-exact UTF-8 text files under `docs/taskpacks/IDS_v0_1_Final_Chinese_Revised/`; the ZIP itself, raw metadata, private data and runtime outputs were not committed. Source/provenance, checksums and iteration recommendations are in `docs/taskpacks/`.
- GitHub full-repo dual-plane CI was blocked only by `KM_IDSystem/搜标项目/文档/05_执行与验收.md` using this branch's newer shared parent renderer. After explicit Owner approval, the final-delivery commit refreshes that exact one-line projection and passes both nested-project and KMIDS dual-plane checks locally; GitHub CI must still pass before merge.
- Read `docs/FINAL_THREAD_HANDOFF_20260726.md` for the concise state, validation, unresolved risks and next-run instructions.
- After remote verification, this thread's local worktree is to be retired. The shared main checkout must remain clean on `main`; no `git gc --prune=now` is permitted.

## Current Gate - 2026-07-24

- Completed task in this run: `IDS-V0_1-STAGE047-REVIEW`. The independent whole-stage review live-rehashed the approved archive, unique Stage047 member, roadmap and instructions; rebound immutable Phase4 commit `007ef85e6ee30e155269284dc9c0fe89572c8161`, exact root/KMIDS trees, parent, HEAD ancestry and five Phase4 artifact hashes; and replayed Phase1-4.
- Six findings are repaired and machine-checked: `2 Critical / 4 Important / 0 Minor`. The current six-field input wrapper completes request/result/source lineage; unencodable Unicode rejects structurally; canonical refs use lower-ASCII token segments; table/page/section graphs are reciprocal; route/error text is exact and bounded; and `produced_at >= requested_at`.
- The committed Phase1 five-field snapshot remains historical evidence. The current Phase1 contract and Phase2 runtime contract explicitly distinguish that immutable snapshot from the review repair; no history was rewritten.
- Stage047 is `completed_reviewed_local`; `ACC-STAGE-047` is closed locally. The only next task is `IDS-V0_1-STAGE048-P1`, behind `IDS-STAGE048-P1-GATE` and only in a separate future run.
- Next allowed task: `IDS-V0_1-STAGE048-P1`; this is a forward route only, not evidence that Stage048 started in this run.
- Review evidence is `STAGE047_STAGE_REVIEW.md`, `check_parser_output_stage_review.py`, repair/final tests, the review machine run, event, batch/roadmap state, machine facts and rendered owner views. Any source, Phase4 binding, phase replay, finding, governance or Git-index mismatch returns `FAIL_CLOSED` to `IDS-STAGE047-REVIEW-GATE`.
- No IDS business source, raw metadata, actual route/parser, fallback, quality gate, evidence promotion, persistence, Stage048, batch review, GitHub action or app reinstall ran. `BATCH041_050` remains locked with seven of ten stages locally reviewed; `push_allowed=false`.
- Final GREEN passed Stage047 focused `72/72`, Stage005 `178/178`, Stage041-047 aggregate `485/485` in `1261.140s`, full IDS v0.1 discovery `1241/1241` in `1689.670s`, all ten Stage038-047 review checkers, `230` unique events, idempotent seven-document owner rendering and project dual-plane. Exact historical repairs only add the current `Stage047 Review -> Stage048 P1 Gate`; failed runs are not counted as PASS. Root governance remains `SPARSE_CONFLICT` because sparse checkout omits root `scripts/lean_governance.py`; do not expand other projects.
- Historical Stage047 Phase4 transition only follows below. Its `P4 -> REVIEW` route is no longer the current gate.

- Completed task in this run: `IDS-V0_1-STAGE047-P4`. The approved source and immutable Phase3 predecessor commit `595a507519b443faa49fca9fa0a6e8bd21cb9dde`, root tree `65a4db060a67ffbb4e7007b25d0dd453fbdbfc88`, KMIDS tree `d0e7058864e6669abcf213cf8c9defe4d57c6fa5`, parent and five Phase3 artifacts were live-rehashed across commit, index and working tree.
- `ids.stage047.parser_output.phase4.delivery.v1` replays all 16 committed control scenarios and derives eight `RECOMPUTED_SANITIZED_CONTROL_OUTPUT_NOT_RUNTIME` projections plus 16 `DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME` records. No fixture text, table cell, page/section text, formula value, raw exception, path, secret or credential is retained.
- Exact metrics remain 11 accepted, 3 rejected and 2 route-no-output results; output states are 6 candidate, 4 partial and 1 failed, with 11 unique output identities, 16 explicit dispositions and zero silent drops. Seven disjoint failure classes cover all ten non-candidate or failed scenarios.
- The eight control formats are explicitly separated from an empty runtime-supported-format set. Output-schema, normalizer and fixture-only parser versions are recorded, no parser configuration changed, and rollback removes only Phase4 artifacts/governance while returning to committed Phase3.
- Next allowed task: `IDS-V0_1-STAGE047-REVIEW`, only in a separate future run behind `IDS-STAGE047-REVIEW-GATE`; `stage_review_entry_authorized=false`, `NO_STAGE_REVIEW_THIS_RUN`, `NO_STAGE048_THIS_RUN`, `NO_BATCH_REVIEW_THIS_RUN`, `NO_GITHUB_UPLOAD`, `NO_APP_REINSTALL`.
- Phase4 evidence is `STAGE047_PHASE4_CLOSEOUT.md`, `parser_output/stage047_parser_output_delivery_contract.json`, `check_parser_output_delivery.py`, focused tests and the Phase4 machine run; any source, Phase3 snapshot, projection, log, metric, classification, boundary, governance or side-effect mismatch returns `FAIL_CLOSED` to `IDS-STAGE047-P4-GATE`.
- TDD RED recorded 13 tests with 16 expected failures and one expected missing-checker error. Core implementation passed 12/13; the sole remaining failure was the expected P4-to-review governance transition. Final layered validation is recorded in the Phase4 machine run and changelog.
- Final GREEN passed focused P4 `13/13`, Phase1-4 `58/58`, Stage005 `178/178`, Stage041-047 aggregate `471/471` in `1192.255s`, and full IDS v0.1 discovery `1227/1227` in `1590.578s`; all nine Stage038-046 review checkers, `229` unique event semantics, idempotent seven-document owner rendering and project dual-plane also pass. Root governance remains `SPARSE_CONFLICT` without sparse expansion.
- The initial aggregate failed 20 checks from six exact historical forward-route gaps plus expected unstaged index binding. The initial full discovery passed `1223/1227`; its four failures were three Stage038 next-gate allowlists and one Stage039 phase-to-gate map ending at P3. Repairs add only exact `P4 -> REVIEW-GATE` compatibility and do not weaken historical review or runtime-safety evidence.
- No IDS business source, raw metadata, actual business route evaluation, runtime parser selection/dispatch/execution, IDS business parser output, fallback attempt/execution/log, differential evaluation, prompt-injection scanner, formula, quality gate, evidence promotion, persistence, whole-stage review, Stage048, GitHub or app action ran. `BATCH041_050` remains locked with six reviewed Stages plus Stage047 Phase1-4 only.
- Historical Stage047 Phase3 transition only: Completed task in this run: `IDS-V0_1-STAGE047-P3`; Next allowed task: `IDS-V0_1-STAGE047-P4`. This is not the current gate.
- Historical Phase3 evidence records 16 bounded format-labelled controls, 11/3/2 dispositions, 6/4/1 output states, 11 unique identities, zero silent drops, instruction-route invariance and formula-text preservation without runtime parsing, fallback, quality evaluation or persistence.
- Historical Stage047 Phase2 transition only: completed task was `IDS-V0_1-STAGE047-P2`; its next allowed task was `IDS-V0_1-STAGE047-P3`. This is not the current gate.
- Historical Stage047 Phase1 transition only: completed task was `IDS-V0_1-STAGE047-P1`; its next allowed task was `IDS-V0_1-STAGE047-P2`. This is not the current gate.
- Historical Stage046 review transition only: Completed task in that run: `IDS-V0_1-STAGE046-REVIEW`. The independent review live-rehashed the approved sources, rebound Phase4 commit `5dee024cd44e2e772776487ee21761f274c7708e` and its exact trees/parent/ancestry, replayed Phase1-4 and repaired all six findings.
- The repaired route contract has a result-level projection digest, sanitized invalid results, canonical non-path references, action-specific fact levels and exact Phase3 PASS invariants. The digest is integrity-only, not external provenance, source authentication or runtime authorization.
- Historical Stage046 review next task only: Next allowed task was `IDS-V0_1-STAGE047-P1`, behind `IDS-STAGE047-P1-GATE`; this is not the current gate.
- Stage046 is `completed_reviewed_local`, but parser/fallback runtime, source I/O, persistence, upload and production activation remain disabled. Six of ten stages in BATCH041_050 are locally reviewed; the batch remains locked.
- Review evidence is `STAGE046_STAGE_REVIEW.md`, `check_parser_routing_stage_review.py`, repair/final tests and the review machine run; any source, Phase4 binding, phase replay, finding, governance or Git-index mismatch returns `FAIL_CLOSED` to `IDS-STAGE046-REVIEW-GATE`.
- Historical Stage046 Phase4 transition only: Completed task in this run: `IDS-V0_1-STAGE046-P4`. The approved sources were live-rehashed; Phase3 commit `49b876ec68ec8f92f0b9df72d57cca7b2d1d3344`, its trees, parent and five indexed artifacts were rebound.
- `ids.stage046.parser_routing.phase4.delivery.v1` derives six schema-only parser-output samples, fourteen non-runtime fallback control logs, exact quality metrics and five fail-closed classifications from all fourteen Phase3 controls; no business content enters the artifacts.
- Every output is `SCHEMA_ONLY_NOT_EXECUTED`, every parser version is `UNASSIGNED_NOT_IMPLEMENTED`, and every fallback record is `DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME` with zero attempts, silent drops or parser switches; Stage047/048/049/050 ownership is unchanged.
- Historical Stage046 Phase4 next task only: Next allowed task: `IDS-V0_1-STAGE046-REVIEW`, behind `IDS-STAGE046-REVIEW-GATE`; this is not the current gate.
- Phase4 evidence is `STAGE046_PHASE4_CLOSEOUT.md`, the delivery contract/checker/tests and machine run; any source, Phase3 snapshot, evidence, governance or side-effect mismatch returns `FAIL_CLOSED` to `IDS-STAGE046-P4-GATE`.
- Historical Stage045 review compatibility assertion only: Completed task in this run: `IDS-V0_1-STAGE045-REVIEW`; Next allowed task: `IDS-V0_1-STAGE046-P1`. This is not the current run or gate.
- Historical Stage044 review compatibility assertion only: Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`; Next allowed task: `IDS-V0_1-STAGE045-P1`. This is not the current run or gate.
- Final GREEN passed Phase4 `13/13`, Phase1-4 `56/56`, Stage005 `174/174`, Stage041-046 aggregate `399/399`, full IDS v0.1 discovery `1151/1151`, eight historical review checkers, `224` unique event semantics, idempotent owner rendering and project dual-plane; root governance remains `SPARSE_CONFLICT` without sparse expansion.
- Historical Stage046 Phase3 transition only: Completed task in this run: `IDS-V0_1-STAGE046-P3`; Next allowed task: `IDS-V0_1-STAGE046-P4`. This is not the current gate; the current gate is Stage046 whole-stage review.
- Historical Phase3 evidence: the approved archive,
  unique Stage046 member, roadmap and instructions were live-rehashed; Phase2
  commit `18c45ee39522891abe4ef65ed609eb5482f2f148`, root/KMIDS trees, parent and
  five Phase2 artifacts were rebound from that immutable snapshot.
- Historical Stage046 Phase2 transition only: Completed task in this run: `IDS-V0_1-STAGE046-P2`; Next allowed task: `IDS-V0_1-STAGE046-P3`. This is not the current gate; the current gate is Stage046 P4.
- Historical Stage046 Phase1 transition only: Completed task: `IDS-V0_1-STAGE046-P1`; Next allowed task: `IDS-V0_1-STAGE046-P2`. This is not the current gate; the current gate is Stage046 P4.
- `ids.stage046.parser_routing.phase3.scenarios.v1` reuses the committed Phase2
  request builder and router over fourteen metadata-only controls covering eight
  governed formats, unknown, corrupt, conflict, low-confidence, unsupported and
  instruction-marker behavior. All fourteen have explicit dispositions and
  `silent_drop_count=0`.
- Confirmed high-confidence inputs record only unavailable route candidates;
  medium, low, unknown, conflict, corrupt and unsupported inputs review or fail
  closed. Instruction-marker routing matches its non-instruction baseline, and
  caller parser override plus forged routing IDs are rejected. Parser dispatch,
  execution, fallback, output, evidence promotion, job/state mutation and
  persistence remain disabled. Stage047/048/049/050 ownership is unchanged.
- Next allowed task: `IDS-V0_1-STAGE046-P4`, only in a separate future run behind
  `IDS-STAGE046-P4-GATE`; `phase4_entry_authorized=false`, `NO_PHASE4_THIS_RUN`,
  `NO_STAGE_REVIEW_THIS_RUN`, `NO_BATCH_REVIEW_THIS_RUN`,
  `NO_GITHUB_UPLOAD_THIS_RUN`, `NO_APP_REINSTALL_THIS_RUN`.
- Final GREEN passes the Phase3 checker with 14/14 explicit scenario dispositions,
  zero silent drops and two rejected invalid requests; focused Phase3 `18/18`,
  Phase1-3 compatibility `43/43`, Stage005 `173/173` in `45.246s`,
  Stage041-046 aggregate `386/386` in `1169.916s`, and full IDS v0.1 discovery `1137/1137` in
  `1607.288s`. All eight Stage038-045 historical review checkers, `223` unique
  event semantics, idempotent owner rendering and project dual-plane pass.
- Layered fail-closed evidence repaired only the exact current
  `IDS-STAGE046-P3 -> IDS-STAGE046-P4-GATE` compatibility in nine historical
  assertions, the Stage005 P3 path/route allowlist, one unittest helper-name
  collision and untranslated P3 owner-view terms. An unstaged Stage039 review
  check correctly failed Git-index binding and passed after the exact KMIDS
  change set was staged; failed runs were not counted as PASS.
- Current source hashes: archive
  `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`,
  unique Stage046 member
  `955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39`,
  roadmap `a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6`,
  instructions `ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8`,
  execution index `2e0088153cd1e13a09d9aebd09a1bd0c8c7162acd0788360d45f5c7320af1e9a`.
- Phase3 evidence: `STAGE046_PHASE3_PARSER_ROUTING_SCENARIOS.md`,
  `parser_routing/stage046_parser_routing_scenarios_contract.json`,
  `scripts/check_parser_routing_scenarios.py`, focused tests and the Phase3 machine
  run. Any source, Phase2 snapshot, scenario outcome, explicit disposition,
  instruction invariance, governance or side-effect mismatch returns
  `FAIL_CLOSED` to `IDS-STAGE046-P3-GATE`.
- Historical Phase2 evidence: `STAGE046_PHASE2_PARSER_ROUTING_SLICE.md`,
  `parser_routing/stage046_parser_routing_runtime_contract.json`,
  `scripts/check_parser_routing_runtime.py`, focused tests and the Phase2 machine
  run. Any source, Phase1 snapshot, request shape, route, version, evidence-only,
  governance or side-effect mismatch returns `FAIL_CLOSED` to
  `IDS-STAGE046-P2-GATE`.
- Historical Phase1 evidence: `STAGE046_PHASE1_PARSER_ROUTING_SCOPE_BOUNDARY.md`,
  `parser_routing/stage046_parser_routing_contract.json`,
  `scripts/check_parser_routing.py`, focused tests and the machine run. Any source,
  predecessor, snapshot, route-family, ownership, quality, state or side-effect
  mismatch returns `FAIL_CLOSED` to `IDS-STAGE046-P1-GATE`.
- Completed task in this run: `IDS-V0_1-STAGE045-P4`; the approved source, committed Phase3 predecessor and five indexed Phase3 artifacts are bound into `ids.stage045.file_type_detection.phase4.delivery.v1`. The checker replays all fourteen Phase3 scenarios and derives six schema-only parser-output samples, seven non-runtime fallback-log samples, exact quality metrics and four fail-closed failure classes without parser or fallback execution.
- Preserved Stage045 Phase 4 transition: Completed task in this run: `IDS-V0_1-STAGE045-P4`; Next allowed task: `IDS-V0_1-STAGE045-REVIEW`. This is historical evidence, not the current gate.
- Preserved Stage045 Phase 3 transition: Completed task in this run: `IDS-V0_1-STAGE045-P3`; Next allowed task: `IDS-V0_1-STAGE045-P4`. This is historical evidence, not the current gate.
- Preserved Stage045 Phase 2 transition: Completed task in this run: `IDS-V0_1-STAGE045-P2`; Next allowed task: `IDS-V0_1-STAGE045-P3`. This is historical evidence, not the current gate.
- Preserved Stage045 Phase 1 transition: Completed task in this run: `IDS-V0_1-STAGE045-P1`; Next allowed task: `IDS-V0_1-STAGE045-P2`. This is historical evidence, not the current gate.
- Preserved Stage044 review transition: Completed task in this run: `IDS-V0_1-STAGE044-REVIEW`; Next allowed task: `IDS-V0_1-STAGE045-P1`. This is historical evidence, not the current gate; `NO_STAGE045_THIS_RUN` applied to that prior review run.
- Preserved Stage044 Phase 4 transition: Completed task in this run: `IDS-V0_1-STAGE044-P4`; Next allowed task: `IDS-V0_1-STAGE044-REVIEW`. This is historical evidence, not the current gate.
- Workspace rule: `/Users/linzezhang/Documents/Codex/GithubProject/KMOS` remains the clean read-only `main` checkout. All work is isolated in `/Users/linzezhang/Documents/Codex/GithubProject/_scratch/kmos-kmids-stage041` on `codex/kmids-recovery-stage041-p1`, with scope limited to `KM_IDSystem/`.
- Approved source: the unique archive member `IDS_v0_1_Final_Chinese_Revised/stages/STAGE-045_文件类型检测.md` has SHA-256 `4eac237a7f63d764cf71789d4949a5168cbe8fe24e1fe7eb816baabe04bb4d27` inside archive SHA-256 `55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`; roadmap and instruction hashes are bound exactly.
- Phase 3 binds Phase2 commit `e61e8f7cbf8795a3f5d2b33be4031f1885948b00`, root tree `94f820df60f592c516c61160ce40e059458d7b9f`, `KM_IDSystem` tree `2daa58d66a496e3b1aede42ed1154de271d80824` and parent `2f4051b7e9960e10698052b4e3f71fcb093f35e3`. Integration baseline `082565a958459fb4b9ad2b951a74982c30311a03` binds Phase2 with the fetched `origin/main` parent without changing the Stage045 gate.
- Detection precedence is `signature > MIME > filename extension`; extension is advisory only. ZIP magic alone never proves DOCX/XLSX: `[Content_Types].xml` plus `word/` or `xl/` is required.
- The contract defines ten canonical types and six detection states. Conflict, unknown, unsupported and corrupt/unreadable inputs fail closed to explicit error or owner review; no silent fallback is permitted.
- Phase 3 replays the Phase2 detector over PDF, DOCX, XLSX, CSV, TXT, PNG, JPEG, both TIFF endiannesses, unknown binary, corrupt ZIP, conflicting signals, extension-only and instruction-like text. All fourteen scenarios pass, `silent_drop_count=0`, and every non-high-quality result has an explicit quality review, owner review or error disposition.
- Phase 4 publishes schema-only samples for six parser-route candidates with exactly `text/tables/pages/sections/confidence/errors`; every sample is `SCHEMA_ONLY_NOT_EXECUTED`, has parser version `UNASSIGNED_STAGE046`, contains no business content and is not a runtime output.
- Seven non-high-quality Phase3 scenarios produce `DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME` fallback control records with `attempted=false`, `attempt_count=0`, `silent_drop=false` and `parser_switch_performed=false`. Stage048 remains the fallback runtime owner.
- Phase4 quality evidence recomputes `14/14` scenario pass, `8/8` governed-format coverage, confidence counts `7/3/1/3`, disposition counts `7/3/3/1`, seven explicitly disposed non-high-quality results and zero parser outputs. Unknown binary, corrupt ZIP, conflicting signals and extension-only low confidence remain fail closed.
- Phase4 final validation passes checker `16/16 + 9/9`, focused `13/13`, Phase1-4 compatibility `59/59`, Stage005 `172/172`, Stage041-045 aggregate `327/327` in `1138.506s`, and full IDS v0.1 discovery `1077/1077` in `1566.023s`; all seven historical review checkers, `219` clean events, exact 30-path event coverage, idempotent owner rendering and project dual-plane pass.
- The first aggregate reached `323/327` and the first full discovery reached `1073/1077`; the eight failures were stale Stage038/039/041-044 forward-route assertions ending at P3. Repairs add only the exact `IDS-STAGE045-P4 -> IDS-STAGE045-REVIEW-GATE` route and do not weaken historical review or runtime-safety evidence.
- Final-evidence synchronization later failed closed only the Stage042 review checker's staged-Handoff allowlist; extending it to the same exact P4 current task restored the checker and its `10/10` review tests in `253.879s`.
- Detector version remains `ids.file_type_detector.v0_1.stage045.p2`; all six parser versions are truthfully `UNASSIGNED_NOT_IMPLEMENTED`. No parser configuration was created or changed, and rollback returns only to the committed Phase3 scenario-only state while preserving all prior evidence.
- Instruction-like source-derived text remains `UNTRUSTED_EVIDENCE_TEXT`; its route matches the non-instruction baseline and it cannot authorize tools or override policy. Parser dispatch, normalized parser output, fallback logging/metrics and Stage050 prompt-injection scanning remain owned by Stage046-050.
- Valid TDD RED produced two governance failures and sixteen missing-artifact errors across eighteen tests before Phase3 artifacts existed. Final GREEN passed focused `18/18` in `1.069s`, Phase1-3 compatibility `46/46` in `2.069s`, Stage005 final evidence recheck `171/171` in `38.633s`, Stage041-045 aggregate `314/314` in `1083.079s`, full discovery `1063/1063` in `1540.095s`, all seven Stage038-044 review checkers, `218` clean events, idempotent owner rendering and project dual-plane.
- The first aggregate failed closed on fourteen historical current-route/index assertions and the first full discovery failed closed on four P3-to-P4 routes plus one stale owner render. A final-evidence Stage005 run failed closed on twenty-two exact result-binding checks before synchronization. Repairs were restricted to exact forward-route compatibility, preservation of existing historical safety invariants, generated owner views and the exact roadmap result binding; one wrong-workdir targeted command was interrupted and not counted as PASS.
- Pre-commit self-review repaired one Important fail-closed gap: the three instruction-control flags now derive from the bounded Phase2 evidence wrapper and are included in scenario PASS evaluation instead of being hard-coded false. The same existing test proves an unsafe wrapper forces `FAIL_CLOSED`; the test count remains eighteen.
- Project governance note: the sparse worktree does not contain root `scripts/lean_governance.py`, so the repository-wide command reports `SPARSE_CONFLICT`; no sparse expansion or unrelated-project inspection was performed.
- Current batch gate: `BATCH041_050` has five locally reviewed Stages plus Stage046 Phase1-4 only and remains locked with `push_allowed=false`; Stage046 review, Stage047-050, single-stage upload, GitHub action, merge, app reinstall, batch review and production action are not authorized.
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
- Current local state: `STAGE-031..STAGE-040` and their independent batch review are merged to GitHub `main`; `STAGE-041..STAGE-047` are locally reviewed. Parser/output/fallback/quality/persistence effects remain disabled.
- Current task: `IDS-V0_1-STAGE047-REVIEW` is complete; the only next task is `IDS-V0_1-STAGE048-P1` in a separate run behind `IDS-STAGE048-P1-GATE`. Stage048-050, ten-stage batch review, upload, merge and app reinstall remain separate gates.
- Stage043 review publishes `ids.stage043.worker_crash_recovery.stage_review.v1`, binds the committed Phase4 baseline, reruns all four phase checkers and machine-checks six repaired findings.
- Phase 2 remains valid at checker `18/18 + 15/15`; its canonical identity, candidate-only transition, fencing, idempotency and safe-reference boundaries are unchanged.
- Preserved Stage043 Phase 4 transition: Completed task in this run: `IDS-V0_1-STAGE043-P4`; Next allowed task: `IDS-V0_1-STAGE043-REVIEW`; `NO_STAGE_REVIEW_THIS_RUN`. This is historical evidence, not the current gate.
- Stage043 Phase 4 publishes `ids.stage043.worker_crash_recovery.phase4.delivery.v1`, binds the committed Phase3 baseline plus current indexed Stage038-042 delivery evidence, and returns `PASS_ISOLATED_CLOSEOUT_PRODUCTION_DISABLED` only when all 14 contract and 14 delivery checks pass.
- The closeout distinguishes three conditional handling candidates from current automatic-recovery eligibility: eligibility and observed success are both empty, all actual process/recovery/mutation/delete/persistence flags remain false, and the whole-stage review is now passed locally.
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
- The previous batch upload is complete. For the current reviewed Stage043 state, GitHub/PR/issue/merge, app reinstall, production runtime, raw metadata content access, Stage044 execution and batch review remain disabled; only `IDS-V0_1-STAGE044-P1` may run next in a separate run.
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
