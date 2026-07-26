# STAGE-041 Phase 1 Lock Registry Scope Boundary

## Controlled Resources

Every operation takes a mandatory `SOURCE_PIPELINE` guard plus the narrowest
operation-specific guard supported by stable reference metadata.

| Operation family | Job type | Specific granularity |
|---|---|---|
| `FILE_PROCESSING` | `PARSE` | source reference |
| `ARCHIVE_EXTRACTION` | `ARCHIVE` | source reference |
| `INDEX_BUILD` | `INDEX` | index-version reference |
| `INDEX_SWITCH` | `INDEX` | index-namespace reference |
| `REPORT_GENERATION` | `REPORT` | report-identity reference |

The mandatory shared guard preserves the reviewed STAGE-038 rule: active
`ARCHIVE`, `PARSE`, `INDEX`, and `REPORT` work for the same source returns
`RESOURCE_CONFLICT_ACTIVE`. STAGE-041 may refine operation-specific exclusion,
but it may not narrow that baseline.

## Lock Identity

- A lock key is SHA-256 over the canonical lock namespace and a stable,
  normalized `resource_identity_ref`.
- Raw paths, source bodies, payloads, credentials, and business content are not
  valid key material.
- Every operation requiring multiple locks sorts the complete key set
  lexicographically before an all-or-none compare-and-set acquisition.
- Acquisition failure retains no partial lock and invokes no operation.
- Missing, malformed, unknown, or stale identity evidence fails closed to
  `REQUIRE_MANUAL_REVIEW`.

## Registry Record

The reference-only registry record binds lock namespace and resource identity
to job, attempt, owner, lease expiry, monotonic fencing token, lock version,
timestamps, release reason, audit, checkpoint and policy references. It stores
no raw path or payload. One `lock_key` may have only one active holder.

## Lease And Takeover

- Renewal requires the same holder job, attempt, lease owner and fencing token,
  plus a currently valid lease.
- Observing an expired timestamp does not grant ownership.
- Takeover requires expiry evidence and one atomic update that advances both
  fencing token and lock version.
- Unknown or stale lease evidence requires manual review.
- Lease duration, renewal interval, grace and timeout values are deliberately
  absent from Phase 1.

## Fencing And Commit Safety

The current fencing token and lock version guard every output, job-state,
checkpoint and evidence commit. A stale worker cannot commit, release, renew,
or mutate terminal history. Token regression rejects the operation and requires
manual review. A release is idempotent only for the matching job, attempt,
owner and current token.

## Idempotency And Retry

- Job identity preserves STAGE-038 `SHA256_TASK_INPUT_JOB_TYPE` behavior.
- Lock-operation identity derives from job, attempt and lock key.
- An exact replay returns its existing decision and never advances the fence.
- Lock contention creates no queue record, invokes no operation, consumes no
  retry budget and retains no partial lock.
- STAGE-039 remains the retry-policy owner.

## Pressure, Resume, Recovery And Cleanup

STAGE-040 drive-offline, disk-space and API-budget decisions can request only a
legal pause candidate. STAGE-041 does not re-observe pressure or auto-resume a
job. Automatic resume belongs to STAGE-042, crash recovery belongs to
STAGE-043, and allowlisted cleanup execution belongs to STAGE-044. Protected
facts, manifests, evidence, audit logs and report snapshots cannot be deleted.

## Deferred Parameters

Phase 1 assigns no numeric values. `lease_duration`, `renewal_interval`,
`expiry_grace`, `acquisition_timeout`, `maximum_wait`, `retry_jitter`, and
`deadlock_timeout` require a source, rationale, unit, policy version, validation
evidence and rollback before Phase 2 uses them. There is no implicit default.

## Phase 2 Gate

`Phase 2 must run separately`. The isolated slice must prove acquire, renew,
release, conflict, expiry takeover and stale-fencing rejection without
persistence or production activation. It must preserve STAGE-038 behavior and
must not claim automatic resume, process-crash recovery or cleanup execution.

Stop markers:

- `NO_PHASE2`
- `NO_LOCK_RUNTIME`
- `NO_LEASE_RUNTIME`
- `NO_FENCING_RUNTIME`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

The next gate is `IDS-STAGE041-P2-GATE`; `push_allowed=false`.
