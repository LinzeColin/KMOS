# STAGE-046 Phase 2 Parser Routing Slice

## Decision

`IDS-V0_1-STAGE046-P2` implements one
`ISOLATED_NON_PRODUCTION_METADATA_ONLY_PARSER_ROUTING_SLICE`.
It consumes only a governed Stage045 detection-result reference and deterministically
derives a parser-route candidate. It does not reopen or re-detect a file, instantiate
or select a parser implementation, dispatch work, execute fallback, create parser
output, or write persistent state.

The router version is `ids.parser_router.v0_1.stage046.p2`; the static registry is
`ids.parser_route_registry.v0_1.stage046.p2`. A successful checker result proves
only that metadata-only route evaluation is executable and fail-closed. It does not
mean that a document was parsed or that a parser is production-ready.

## Approved Source And Phase 1 Binding

- The unique approved Stage046 task-pack member and the archive, roadmap and
  instruction SHA-256 values remain exact.
- The Phase1 predecessor is commit
  `c82e4e928b167c718d462dc8cef3eed5b5dbb3ea`, root tree
  `403e4057c028667c23a35588f09b3c00ebb51735`, `KM_IDSystem` tree
  `c59be0f27521a15dc876656c753ee9b503611f94` and parent
  `76027b8dc89e325c212d492d7f5df88357ea7112`.
- The Phase1 entry, boundary, machine contract, checker, focused tests and machine
  run are read from that immutable commit and bound by exact SHA-256.
- Stage045 remains the only file-type detection authority. Phase2 does not inspect
  extension, MIME, signature, container, source bytes or source path.

## Routing Request Boundary

The request contains only bounded references and governed detection metadata:

- deterministic `routing_request_id` and upstream `detection_request_id`;
- `source_fingerprint_ref`, `source_identity_ref` and `detection_evidence_ref`;
- `detected_type`, `detection_state` and `detection_confidence`;
- exact Stage045 detector and Stage046 registry versions;
- upstream `evidence_text_marker_applied` boolean;
- a real RFC3339 UTC timestamp.

The exact request shape rejects extra fields. It cannot contain a source path,
source body, source text, raw exception, secret, credential or caller-selected
parser. IDs and refs are bounded and canonical; the request ID is the canonical
SHA-256 of all request metadata except itself.

## Static Route Evaluation

The in-memory registry maps eight governed types to six route families:

| Type | Route | Parser family |
|---|---|---|
| PDF | `ROUTE_PDF` | `PDF_PARSER` |
| DOCX | `ROUTE_OOXML_WORD` | `OOXML_WORD_PARSER` |
| XLSX | `ROUTE_OOXML_WORKBOOK` | `OOXML_WORKBOOK_PARSER` |
| CSV | `ROUTE_DELIMITED_TEXT` | `DELIMITED_TEXT_PARSER` |
| TXT | `ROUTE_PLAIN_TEXT` | `PLAIN_TEXT_PARSER` |
| PNG/JPEG/TIFF | `ROUTE_IMAGE` | `IMAGE_PARSER` |

Only `TYPE_CONFIRMED/HIGH` selects a candidate route. Parser implementations are
still absent, so every such result records:

- the exact candidate route and parser family;
- detection/routing confidence;
- `parser_version=UNASSIGNED_NOT_IMPLEMENTED`;
- `parser_version_status=RECORDED_UNASSIGNED`;
- action `ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE`;
- no parser selection, dispatch or execution.

This is intentional fail-closed truth, not a missing default. The route candidate
is a `CANDIDATE` fact and never dispatch authorization.

## Review, Unsupported And Blocked Inputs

- `TYPE_PROVISIONAL/MEDIUM|LOW` returns `ROUTE_REVIEW_REQUIRED`.
- conflict and unknown-review states return `ROUTE_REVIEW_REQUIRED`.
- `TYPE_UNSUPPORTED` returns `ROUTE_UNSUPPORTED`.
- blocked, corrupt or unreadable inputs return `ROUTE_BLOCKED`.
- invalid state/type/confidence combinations, version mismatches and extra fields
  fail before route evaluation as `INVALID_ROUTING_REQUEST`.
- no case enters a generic parser, silent fallback or silent parser switch.

## Parser Version And Confidence

Phase2 records the upstream detection confidence without changing it. It also
records parser-version status on every result. Because no parser implementation
exists in this Stage, the only truthful value is `UNASSIGNED_NOT_IMPLEMENTED`.
Assigning a numeric or implementation version without code makes the contract
invalid and fails the checker.

## Evidence Text Boundary

The router accepts no text. If Stage045 metadata reports that a source-derived
excerpt was marked, the route result preserves only this classification:

- label `UNTRUSTED_EVIDENCE_TEXT`;
- interpretation `EVIDENCE_ONLY`;
- `system_instruction_allowed=false`;
- `tool_authorization_allowed=false`;
- `policy_override_allowed=false`.

No source content is copied into request, result or report. This preserves the
evidence-only rule required by the task pack without impersonating Stage050:
Phase2 does not scan for prompt injection and does not apply a runtime marker.
Stage050 still owns downstream scanning and enforcement.

## Isolated Smoke Slice

The checker evaluates exactly three synthetic metadata-only controls:

1. a governed `PDF / TYPE_CONFIRMED / HIGH` result with the evidence-text marker;
2. a governed `DOCX / TYPE_CONFIRMED / HIGH` result;
3. an `UNKNOWN / TYPE_UNKNOWN_REVIEW_REQUIRED / UNKNOWN` result.

The first two choose the exact candidate routes and stop because parser
implementations are unavailable. The third enters review without a candidate.
All results record version status and confidence while retaining zero parser,
fallback, output or persistence side effects. These controls contain no IDS
business facts and are not the Phase3 all-format/adversarial scenario matrix.

## Ownership And Side-Effect Boundary

- Stage037 owns `PARSE` job state and transitions.
- Stage047 owns detailed parser output and compatibility.
- Stage048 owns fallback attempts and stop rules.
- Stage049 owns differentiated parser comparison.
- Stage050 owns prompt-injection scanning and runtime enforcement.

Phase2 performs no source-file open, stat, scan, hash, sniff, decode, extraction,
parser selection, parser dispatch, parser execution, fallback, OCR, model call,
job/queue/lock/state action, output creation, evidence promotion, manifest/audit/
index/report/database write, schema change, production activation, GitHub action
or app reinstall.

## Phase 3 Gate

The only next task is a separate `IDS-V0_1-STAGE046-P3` run behind
`IDS-STAGE046-P3-GATE`. Phase3 owns the full PDF/DOCX/XLSX/CSV/TXT/image/unknown/
bad-input route matrix, fallback non-silence checks and instruction-like metadata
adversarial scenarios. `entry_authorized=false` during this run.

This run stops with:

- `NO_REAL_SOURCE_FILE_READ`
- `NO_FILE_TYPE_REDETECTION`
- `NO_EXTERNAL_PARSER_REGISTRY`
- `NO_PARSER_SELECTION`
- `NO_PARSER_DISPATCH`
- `NO_PARSER_EXECUTION`
- `NO_FALLBACK_EXECUTION`
- `NO_DIFFERENTIAL_PARSER_EVALUATION`
- `NO_PROMPT_INJECTION_SCAN`
- `NO_RUNTIME_PROMPT_MARKER_APPLICATION`
- `NO_PARSER_OUTPUT`
- `NO_EVIDENCE_PROMOTION`
- `NO_JOB_OR_STATE_MUTATION`
- `NO_PERSISTENCE_OR_DATABASE`
- `NO_PHASE3_THIS_RUN`
- `NO_STAGE_REVIEW_THIS_RUN`
- `NO_BATCH_REVIEW_THIS_RUN`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

`push_allowed=false`.

## Rollback

Revert only the Phase2 document, runtime contract, checker, tests and minimum
governance projections, returning to Phase1 commit
`c82e4e928b167c718d462dc8cef3eed5b5dbb3ea`. Rollback must preserve the approved
source, raw-data boundary, Stage045 reviewed-local evidence, Phase1 evidence,
manifest, evidence ledger, audit, index, report, database, GitHub and app state.
