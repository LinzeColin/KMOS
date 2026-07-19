# STAGE-045 Phase 3 File-Type Detection Scenarios

## Decision

`IDS-V0_1-STAGE045-P3` runs fourteen bounded
`ISOLATED_NON_PRODUCTION_IN_MEMORY_FILE_TYPE_DETECTION_SCENARIOS` over the
committed Phase 2 detector. The scenarios use synthetic control bytes only and
retain no payload. They do not accept a source path, open or hash a business
file, dispatch or execute a parser, execute fallback, scan prompt injection,
persist state, or activate production runtime.

A pass means the Phase 2 candidate detector behaves truthfully for the complete
Stage045 format and failure matrix. It is scenario evidence, not parser output,
fallback-runtime evidence, high-confidence evidence promotion, production
calibration, or whole-stage acceptance.

## Source, Phase 2 And Integration Binding

- The unique approved Stage045 taskpack member, archive, roadmap and instruction
  hashes are bound exactly.
- The committed Phase 2 predecessor is
  `e61e8f7cbf8795a3f5d2b33be4031f1885948b00`; its root tree,
  `KM_IDSystem` tree and parent are exact and it remains an ancestor of HEAD.
- The Phase 2 contract, checker, tests, evidence and local run are each bound by
  exact SHA-256.
- Integration baseline `082565a958459fb4b9ad2b951a74982c30311a03` binds the
  Phase 2 commit and current `origin/main` as its two parents. The canonical
  repository override was retained without reverting the Stage045 current gate.
- Upstream BidScout files remain a separate public-safe contract surface. They
  are not read or treated as Stage045 product evidence.

## Fourteen Scenarios

1. Matching PDF signature, MIME and extension produce a high-confidence
   `PDF_PARSER` candidate without dispatch.
2. DOCX requires a valid in-memory ZIP with `[Content_Types].xml` and `word/`.
3. XLSX requires a valid in-memory ZIP with `[Content_Types].xml` and `xl/`.
4. Consistent bounded CSV text, MIME and extension produce a medium-confidence
   candidate that still requires quality review.
5. Consistent bounded TXT text, MIME and extension produce a medium-confidence
   candidate that still requires quality review.
6. PNG signature, MIME and extension produce an image-parser candidate.
7. JPEG SOI signature, MIME and extension produce an image-parser candidate.
8. Little-endian TIFF signature produces an image-parser candidate.
9. Big-endian TIFF signature produces an image-parser candidate.
10. Unknown binary content produces explicit owner review and
    `NO_RELIABLE_TYPE_SIGNAL`; it is never silently discarded.
11. A corrupt ZIP header produces `CORRUPT_ZIP_CONTAINER`,
    `TYPE_INPUT_BLOCKED` and no fallback execution.
12. Conflicting signature, MIME and extension produce explicit owner review.
13. Extension-only PDF evidence remains low confidence and cannot dispatch.
14. Instruction-like text remains `UNTRUSTED_EVIDENCE_TEXT`; its route matches
    the non-instruction baseline and it cannot override rules or authorize tools.

The scenario count is fixed at fourteen. TIFF endianness variants are separate
scenarios but one canonical supported type. No real IDS business data or fake
business facts are used.

## Fallback And Quality Evidence

Phase 3 evaluates a disposition over Phase 2 detection metadata only:

- confirmed/high results become `PRIMARY_ROUTE_CANDIDATE_ONLY`;
- provisional/medium results become `QUALITY_REVIEW_REQUIRED`;
- provisional/low, conflict and unknown results become
  `OWNER_REVIEW_REQUIRED`;
- blocked corrupt input becomes `EXPLICIT_ERROR_NO_FALLBACK`.

Every non-high-quality result therefore has an explicit review or error route.
`silent_drop_count` must be zero. No parser output is created, no fallback
attempt is executed, and no fallback log is fabricated. Stage048 remains the
runtime owner of fallback attempts, ordering, logging and stop rules.

## Instruction-Like Evidence Text

The adversarial text is passed only as a bounded synthetic source-derived
excerpt. The Phase 2 detector applies `UNTRUSTED_EVIDENCE_TEXT`, and Phase 3
compares its classification with an otherwise identical non-instruction
baseline. Type, state, confidence and route must remain identical.

The scenario report retains only the marker and invariant booleans. It does not
retain the text. `system_rule_override_performed=false`,
`tool_authorization_performed=false`, and
`prompt_injection_scan_performed=false`. This is not the Stage050 scanner.

## Result Boundary

Each scenario summary contains only bounded result metadata:

- detector version, type, state, confidence and candidate route;
- explicit quality disposition and bounded error codes;
- evidence marker, container-inspection and instruction-invariance flags;
- empty output refs and false parser/fallback side-effect flags.

It contains no control bytes, source text, absolute source path, raw metadata,
parser output, manifest row, evidence body, audit record, database row, index
entry, report or runtime log.

## Explicit Non-Actions

- `NO_REAL_SOURCE_FILE_READ`
- `NO_FILESYSTEM_SCAN_OR_SOURCE_HASH`
- `NO_PARSER_DISPATCH`
- `NO_PARSER_EXECUTION`
- `NO_FALLBACK_EXECUTION`
- `NO_PROMPT_INJECTION_SCAN`
- `NO_PROMPT_RULE_OVERRIDE`
- `NO_EVIDENCE_PROMOTION`
- `NO_JOB_OR_STATE_MUTATION`
- `NO_PERSISTENCE_OR_DATABASE`
- `NO_PHASE4_THIS_RUN`
- `NO_STAGE_REVIEW_THIS_RUN`
- `NO_BATCH_REVIEW_THIS_RUN`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

`push_allowed=false`.

## Validation Status

The valid TDD RED ran eighteen tests with two governance failures and sixteen
missing-artifact errors before the Phase 3 contract, checker, evidence and
governance route existed. Final GREEN passed Phase 3 focused `18/18` in
`1.069s`, Phase 1-3 focused compatibility `46/46` in `2.069s`, Stage005
governance final evidence recheck `171/171` in `38.633s`, Stage041-045 aggregate `314/314` in
`1083.079s`, and full IDS v0.1 discovery `1063/1063` in `1540.095s`.

The first aggregate failed closed on fourteen historical current-route/index
assertions. The first full discovery failed closed on four historical forward
routes and one stale owner render. Repairs added only the exact P3-to-P4
compatibility route, preserved Git-index binding, and regenerated owner views.
The final evidence draft temporarily failed `22/171` Stage005 checks because its
exact roadmap result binding still referenced the preliminary wording; the
binding was updated exactly and the final recheck passed.
All seven Stage038-044 historical review checkers, `218` governance events,
idempotent owner rendering and the project-scoped dual-plane gate pass. Root
governance remains `SPARSE_CONFLICT` because `scripts/lean_governance.py` is not
present in this sparse worktree; no sparse expansion was performed.

## Phase 4 Gate

All fourteen scenarios, the complete format/failure matrix, zero silent drops,
instruction-route invariance, exact Phase 2/upstream bindings and all no-effect
truth flags must pass before the next gate can be
`IDS-STAGE045-P4-GATE`.

Phase 4 must run separately. It owns delivery evidence, parser-output samples,
fallback log shape, quality metrics, failure classification and configuration
rollback. This Phase 3 run does not implement or claim those artifacts.

## Rollback

Revert only the Stage045 Phase 3 scenario contract, checker, tests, evidence and
minimal governance projections. Preserve Phase 1/2, integration baseline,
canonical repository override and Stage044 reviewed evidence. Rollback must not
open, scan, hash, parse, move, overwrite or delete any real source, original,
manifest, evidence, audit, report, index, database, GitHub or app state.
