# STAGE-047 Phase 2 Parser Output Normalization Slice

## Decision

`IDS-V0_1-STAGE047-P2` implements one
`ISOLATED_NON_PRODUCTION_IN_MEMORY_OUTPUT_NORMALIZATION_SLICE`.
It exercises the exact Stage047 output envelope over three bounded, synthetic,
non-business control payloads. The result proves that the contract can construct,
validate and reject outputs deterministically; it does not prove that a source file
was parsed or that a Stage046 parser implementation exists.

The normalizer version is `ids.parser.output_normalizer.v0_1.stage047.p2`.
The only declared adapter is
`ids.parser.output.control_fixture_adapter.v0_1.stage047.p2` with state
`CONTROL_FIXTURE_ONLY_NOT_STAGE046_RUNTIME_PARSER`. Its parser-version field is
`ids.parser.control_fixture.v0_1.stage047.p2` and is valid only inside this
deterministic fixture contract. It is not registered in the Stage046 runtime route
registry and cannot authorize parser selection, dispatch, execution or production use.

## Approved Source And Phase 1 Binding

- The exact approved Stage047 task-pack member, archive, roadmap and instructions
  retain their verified SHA-256 values.
- The immutable Phase1 predecessor is commit
  `7d44f72c6a5d50e9042b8af1f588cd40e1caf4f3`, root tree
  `32304095210786139b38ff2036d6711868d01fe0`, `KM_IDSystem` tree
  `55255a2db6ef720228c38560f68c8abce9ad53df` and parent
  `c7d66380cfab7cf00ccbb9af34ef43a7f44a7bde`.
- The Phase1 entry, boundary, contract, checker, focused tests and machine run are
  read from that commit and bound by exact SHA-256. A mutable working-tree copy
  cannot impersonate the predecessor.
- Phase1 must still return
  `PASS_PHASE1_PARSER_OUTPUT_CONTRACT_RUNTIME_DISABLED` and route only to
  `IDS-STAGE047-P2-GATE`.

## Lineage Proof Refinement

The immutable Phase1 predecessor originally required five wrapper fields:
`route_result_id`, `route_result`, `source_identity_ref`,
`requested_output_schema_version` and `requested_at`. The Stage046 route-result
schema does not itself carry `source_identity_ref`, so those five fields alone
cannot prove that the wrapper source and route result share one detection lineage.

The Stage047 independent review repaired the current Phase1 contract to require
the same six fields as Phase2, including mandatory `routing_request`. The Phase2
contract preserves the immutable five-field snapshot as historical evidence and
separately records that the current six-field lineage repair is applied. The proof
is the exact Stage046 request shape and binds:

- `source_identity_ref` and `source_fingerprint_ref`;
- Stage045 detection request, evidence, type, state and confidence;
- canonical `detection_result_id`;
- Stage046 registry version and canonical `routing_request_id`;
- the route result's request/detection IDs, type, state, confidence and marker;
- canonical `route_result_id`.

Any unknown field, digest mismatch, source mismatch, non-canonical lower-ASCII
control reference, unexpected route `human_status`, placeholder parser version,
path, URI, source body, raw exception, secret or credential rejects the request
before output construction. Rejection output is sanitized and does not echo the
unvalidated value.

## Control Adapter Boundary

The fixture adapter consumes only a pre-parsed six-field Python mapping supplied
directly by the checker. It never opens, stats, hashes, sniffs, decodes or traverses
a source file. It is not a parser implementation and does not create a business
job or business fact.

The concrete control version exists to prove that parser family/version lineage
is copied and verified rather than filled with `UNASSIGNED_NOT_IMPLEMENTED`.
Its scope is fixed to `CONTROL_FIXTURE_ONLY`; using it in Stage046 runtime,
production, evidence promotion or a real IDS job is forbidden.

## Exact Payload And Envelope

The payload has exactly the Phase1 core fields:

1. `text`
2. `tables`
3. `pages`
4. `sections`
5. `confidence`
6. `errors`

The normalizer validates bounded UTF-8-encodable text, exact nested item shapes,
unique IDs, ascending page numbers, rectangular table cells, safe errors and all
page/table/section references. Table-to-page and table-to-section links must be
reciprocal. Safe-error code and message-key lengths are capped at 96 and 128
characters. A formula-like string remains untrusted text and is never executed.

Accepted controls receive the exact 18-field Phase1 envelope and canonical
`parser-output:sha256:<digest>` identity. The digest covers every field except
`output_id`; it proves projection integrity only, not external provenance, source
authenticity, content truth, quality approval or runtime authorization.
`produced_at` must be valid UTC and cannot precede the input `requested_at`.

## Completion And Failure Rules

- Non-empty `HIGH` or `MEDIUM` content without errors becomes
  `OUTPUT_CANDIDATE_NOT_VALIDATED`.
- Non-empty content with a warning or `LOW`/`UNKNOWN` confidence becomes
  `OUTPUT_PARTIAL_REVIEW_REQUIRED`.
- Empty content with an `ERROR` or `FATAL` safe error becomes
  `OUTPUT_FAILED_EXPLICIT`.
- Empty content without error, fatal error with content, invalid safe error,
  duplicate/orphan reference, non-rectangular table, identity mismatch or unknown
  field returns `OUTPUT_REJECTED_FAIL_CLOSED` and creates no envelope.

No branch permits silent success, silent drop or silent parser switch.

## Evidence Text And Quality Boundary

Every textual location is classified as `UNTRUSTED_EVIDENCE_TEXT` with
interpretation `EVIDENCE_ONLY`, including:

- top-level text;
- table cells;
- page text;
- section title and text.

The classification is unconditional, so command-like fixture content remains
data. `system_instruction_allowed`, `tool_authorization_allowed` and
`policy_override_allowed` are false.

Phase2 does not impersonate Stage050. It performs no prompt-injection scan and
applies no runtime marker; state stays `REQUIRED_NOT_APPLIED_STAGE050`.

The normalizer assigns only an initial disposition:

- candidate: `UNASSESSED`;
- partial: `REVIEW_REQUIRED`;
- failed: `BLOCKED`.

This is not a quality-gate evaluation. Every output stays `CANDIDATE`, and
downstream promotion plus high-trust evidence are false.

## Three Smoke Controls

The checker evaluates exactly three bounded controls:

1. one high-confidence candidate containing command-like fixture text;
2. one low-confidence partial table/page/section output with a safe warning;
3. one explicit empty failure with a safe error.

The controls prove the three allowed statuses, distinct canonical output IDs,
parser-version/confidence recording, nested references, safe errors and evidence-
only classification. They are not the Phase3 PDF/DOCX/XLSX/CSV/TXT/image/unknown/
bad-file matrix and contain no IDS business facts or placeholder corpus.

## Ownership And Side Effects

- Stage045 remains detection authority.
- Stage046 remains route-contract authority; no runtime registry is changed.
- Stage047 owns normalization and the output envelope.
- Stage048 retains fallback attempts, stop reasons and non-silent failure handling.
- Stage049 retains differentiated parser comparison.
- Stage050 retains prompt-injection scanning and runtime marker enforcement.
- Stage037 retains `PARSE` job state and transitions.

No manifest, evidence ledger, audit, index, report, database, job, state, source,
original file or delivered output is created or mutated. The checker returns only
an in-memory structure and a stdout control report.

`candidate_output_envelope_constructed=true` means that the normalizer built a
fixture envelope. `ids_business_parser_output_produced=false` and
`parser_execution_performed=false` remain authoritative for real execution.

## Phase 3 Gate

The only next task is a separate `IDS-V0_1-STAGE047-P3` run behind
`IDS-STAGE047-P3-GATE`. Phase3 owns the all-format and adversarial scenario matrix,
fallback non-silence, low-quality handling and prompt-injection invariance.
`phase3_entry_authorized=false` during this run.

This run stops with:

- `NO_REAL_OR_BUSINESS_SOURCE_READ`
- `NO_RAW_METADATA_ACCESS`
- `NO_FILE_TYPE_REDETECTION`
- `NO_ACTUAL_ROUTE_EVALUATION`
- `NO_STAGE046_REGISTRY_CHANGE`
- `NO_PARSER_SELECTION_OR_DISPATCH`
- `NO_PARSER_EXECUTION`
- `NO_IDS_BUSINESS_PARSER_OUTPUT`
- `NO_FALLBACK_EXECUTION`
- `NO_DIFFERENTIAL_EVALUATION`
- `NO_PROMPT_INJECTION_SCAN_OR_RUNTIME_MARKER`
- `NO_QUALITY_GATE_EVALUATION`
- `NO_EVIDENCE_PROMOTION`
- `NO_JOB_STATE_OR_PERSISTENCE`
- `NO_PHASE3_THIS_RUN`
- `NO_STAGE_REVIEW_THIS_RUN`
- `NO_BATCH_REVIEW_THIS_RUN`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

`push_allowed=false`.

## Rollback

Revert only the Phase2 boundary, runtime contract, checker, focused tests, machine
run and minimum governance projection, returning to commit
`7d44f72c6a5d50e9042b8af1f588cd40e1caf4f3`. Rollback must preserve the approved
source, Phase1 evidence, original data, manifest, evidence ledger, audit, index,
report, database, GitHub and app state.
