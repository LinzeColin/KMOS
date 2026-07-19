# STAGE-045 Phase 2 File-Type Detection Slice

## Decision

`IDS-V0_1-STAGE045-P2` implements one
`ISOLATED_NON_PRODUCTION_IN_MEMORY_FILE_TYPE_DETECTION_SLICE`.
It evaluates bounded synthetic control bytes only. It never accepts a source path,
opens a business file, scans a directory, computes a source hash, dispatches a
parser, executes fallback, writes evidence, or activates production runtime.

The detector contract is `ids.file_type_detector.v0_1.stage045.p2`. A successful
result means only that a candidate type and candidate parser family were derived
from bounded control signals. It does not mean that a real file was classified,
parsed, indexed, persisted, promoted to evidence, or made production-ready.

## Source And Predecessor Binding

- The unique approved Stage045 taskpack member and the archive, roadmap and
  instruction hashes remain exact.
- Phase 1 predecessor commit is
  `2f4051b7e9960e10698052b4e3f71fcb093f35e3`; its root tree,
  `KM_IDSystem` tree and parent are bound exactly.
- The Phase 1 contract, checker, boundary, tests and machine run are bound by
  exact SHA-256.
- Stage013 fingerprint checker remains the owner of source fingerprint and MIME
  observation. Phase 2 consumes only explicit metadata references and never
  reopens the referenced source.
- Stage037 remains the owner of `PARSE` jobs and state transitions.
- The raw metadata boundary remains path-only and untouched.

## Runtime Input Boundary

The persistent/control request is metadata-only and contains:

- `detection_request_id` derived from canonical request metadata;
- `source_identity_ref` and `source_fingerprint_ref`;
- a basename-only `filename` and advisory `extension_signal`;
- an explicit `mime_signal` with provenance;
- `detector_contract_version` and caller-supplied RFC3339 UTC time.

The request contains no raw payload, source body, source text, absolute path,
secret, credential, unbounded exception, or output body. Synthetic bytes are
passed directly to the in-memory function and are neither placed in the request
nor retained in its result.

Independent Stage045 review tightened request canonicalization: case-insensitive
`unknown` is represented only as `UNKNOWN`, and `requested_at` must be both the
exact UTC `YYYY-MM-DDTHH:MM:SSZ` shape and a real calendar/time value. An invalid
month, day or `24:00:00` is rejected before a request ID is created.

`MAX_CONTROL_BYTES=1048576` and `MAX_EVIDENCE_TEXT_CHARS=4096` are isolated
safety ceilings for this test slice. They are not production parameters,
performance targets, ingestion limits, or owner-approved thresholds and are not
registered as active product parameters.

## Signature And Container Detection

The slice recognizes these bounded signatures:

- PDF `%PDF-` header;
- PNG eight-byte signature;
- JPEG SOI prefix;
- little- and big-endian TIFF headers;
- ZIP container headers followed by OOXML container-name validation.

Magic bytes are necessary but no longer sufficient for `TYPE_CONFIRMED`. The
reviewed slice also requires a bounded structural invariant: PDF has a valid
header and terminal `%%EOF`; PNG has a CRC-valid first `IHDR`, at least one
`IDAT`, and terminal `IEND`; JPEG has SOI and EOI; TIFF has valid byte-order magic
and an in-bounds IFD table. A recognized magic prefix with invalid/truncated
structure is blocked as `CORRUPT_OR_UNREADABLE`, never downgraded to a MIME or
extension guess.

ZIP magic alone never identifies DOCX or XLSX. The detector inspects only ZIP
entry names in memory:

- DOCX requires `[Content_Types].xml` and a `word/` entry;
- XLSX requires `[Content_Types].xml` and an `xl/` entry;
- both namespaces produce `TYPE_CONFLICT_REVIEW_REQUIRED`;
- corrupt ZIP metadata produces `CORRUPT_OR_UNREADABLE` and
  `TYPE_INPUT_BLOCKED`;
- ZIP without an OOXML marker remains unknown and requires review.

A valid ZIP that lacks the required OOXML markers stays `UNKNOWN` with
`OOXML_CONTAINER_MARKERS_MISSING`; matching DOCX/XLSX MIME and extension cannot
re-enter the candidate route after the container check has failed.

ZIP member names must be canonical relative POSIX names. Absolute, backslash,
empty, dot, parent-traversal or duplicate names block the input before namespace
classification, so a lexical `word/../...` entry cannot impersonate DOCX.

The slice does not decompress entry bodies, parse XML, run macros, inspect
relationships, evaluate archive risk, or perform Stage024-029 extraction work.

## MIME, Extension And Text Heuristic

Signal order remains signature, provenance-bound MIME, then filename extension.
A known signature conflicting with MIME or extension returns
`TYPE_CONFLICT_REVIEW_REQUIRED`; the filename never overrides it.

When no known binary signature exists, an isolated UTF-8/UTF-8-SIG heuristic may
produce a provisional CSV or TXT candidate. CSV requires at least two non-empty
rows, at least two columns and consistent width for one bounded delimiter.
NUL-containing, undecodable or mostly non-printable control bytes do not become
text candidates.

Text heuristic outcomes remain `TYPE_PROVISIONAL`. Extension-only evidence is
at most `LOW` confidence and uses `ROUTE_REVIEW_REQUIRED`. A consistent bounded
text/MIME/extension combination can be `MEDIUM`, but still cannot execute a
parser. This heuristic is explicitly not production-calibrated.

## Result Contract

Every result records:

- detector version and deterministic request ID;
- detected candidate type and all non-duplicate candidate types;
- detection state and confidence;
- candidate parser family and route state;
- bounded signal evidence and error codes;
- Chinese owner status;
- explicit no-side-effect truth fields.

No result contains raw control bytes or source text. `output_refs` stays empty,
`persisted=false`, and all parser, fallback, evidence-write, state-write and
production flags stay false.

## Parser And Fallback Ownership

The Phase 1 candidate mapping is reused only as metadata:

- Stage046 owns the detailed parser route contract and dispatch;
- Stage047 owns parser output shape and compatibility;
- Stage048 owns fallback attempts and stop rules;
- Stage049 owns differentiated parser comparison;
- Stage050 owns prompt-injection scanning and downstream enforcement.

This slice does not instantiate a parser, create a job, enqueue work, retry an
operation, switch parsers, parse content, or call a model. Even a high-confidence
signature result remains a candidate route with `parser_dispatch_performed=false`.

## Untrusted Evidence Text Marker

The helper `mark_evidence_text` wraps bounded synthetic source-derived text as:

- label `UNTRUSTED_EVIDENCE_TEXT`;
- interpretation `EVIDENCE_ONLY`;
- `system_instruction_allowed=false`;
- `tool_authorization_allowed=false`;
- `policy_override_allowed=false`.

This is a mandatory envelope label, not a Stage050 prompt-injection scanner. It
does not decide whether text is malicious, execute an instruction, authorize a
tool, override policy, or persist the text. The Phase 2 report retains only the
boolean marker fact and never includes the synthetic text. Length/type bounds are
validated before signature inspection, so a rejected excerpt cannot be reported
as though signature or container observation already occurred.

## Isolated Smoke Slice

The checker executes exactly three in-memory synthetic controls:

1. matching PDF signature, MIME and extension;
2. an in-memory DOCX ZIP with required container names;
3. UTF-8 evidence text with a deliberately misleading PDF extension, producing
   a conflict-review result and applying the untrusted-evidence label.

The smoke slice exists to prove the implementation path and fail-closed result
shape. It is not the Phase 3 all-format scenario suite and uses no real IDS
business content or fabricated business facts.

## Side-Effect Boundary

Phase 2 performs no:

- real source path access, file open, filesystem scan or source hash;
- raw metadata access or fake IDS business-data creation;
- parser dispatch/execution, fallback, OCR, prompt-injection scan or model call;
- job/queue/state/claim/lock/retry/lifecycle/crash/cleanup action;
- manifest, evidence ledger, audit, index, report or database write;
- schema migration, runtime-output write or production activation;
- GitHub push/merge, issue action or app-entry reinstall.

## Phase 3 Gate

The only next task is a separate `IDS-V0_1-STAGE045-P3` run behind
`IDS-STAGE045-P3-GATE`. Phase 3 owns the complete PDF/DOCX/XLSX/CSV/TXT/image/
unknown/corrupt scenario matrix, fallback-quality behavior and prompt-rule
adversarial checks.

This run stops with:

- `NO_REAL_SOURCE_FILE_READ`
- `NO_FILESYSTEM_SCAN_OR_SOURCE_HASH`
- `NO_PARSER_DISPATCH`
- `NO_PARSER_EXECUTION`
- `NO_FALLBACK_EXECUTION`
- `NO_PROMPT_INJECTION_SCAN`
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

Revert only the Stage045 Phase 2 document, runtime contract, checker, tests and
their minimal governance projections. Preserve Phase 1 commit `2f4051b7...`,
Stage044 reviewed-local evidence and all earlier facts. Rollback must not open,
scan, hash, parse, move, overwrite or delete real source paths, nor modify any
original, manifest, evidence, audit, report, index, database, GitHub or app state.
