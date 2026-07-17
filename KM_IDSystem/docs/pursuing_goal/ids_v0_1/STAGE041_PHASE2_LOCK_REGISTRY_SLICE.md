# STAGE-041 Phase 2 Lock Registry Slice

- Stage: `STAGE-041`
- Phase: `Phase 2`
- Task: `IDS-V0_1-STAGE041-P2`
- Acceptance: `ACC-STAGE-041`
- Policy: `ids.lock_registry_policy.v0_1.stage041.p2`
- Result: `PASS_ISOLATED_IN_MEMORY_PRODUCTION_DISABLED`
- Next gate: `IDS-STAGE041-P3-GATE`

## Parameter Truth

The seven numeric values are `PROPOSED` local engineering safety boundaries,
not measured production values and not production calibrated:

| Parameter | Value | Source and constraint |
|---|---:|---|
| `lease_duration_seconds` | 30 | Local safety boundary; exactly three renewal intervals. |
| `renewal_interval_seconds` | 10 | Local safety boundary; strictly before lease expiry. |
| `expiry_grace_seconds` | 5 | Local safety boundary; positive and below one renewal interval. |
| `acquisition_timeout_seconds` | 1 | Finite synchronous decision ceiling; no sleep occurs. |
| `maximum_wait_seconds` | 0 | Preserves STAGE-038 pause-before-queue behavior. |
| `retry_jitter_seconds` | 0 | Preserves STAGE-039 retry ownership; lock contention consumes no retry. |
| `deadlock_timeout_seconds` | 1 | Registered finite guard; canonical all-or-none acquisition does not block. |

Production calibration remains assigned to `TASK-OPME-B-001`. Any invalid
parameter, request, lease, version, or fencing evidence disables the isolated
runtime and requires manual review. Rollback reverts Phase 2 files only while
preserving Phase 1 and STAGE-037..040 evidence.

## Controlled Evidence

The executed input was the real Git-tracked control document
`repo:KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE041_PHASE1_LOCK_REGISTRY_SCOPE_BOUNDARY.md`.
It is control metadata, not IDS business data. No raw body, Downloads metadata
content, fabricated business record, placeholder corpus, database row, or real
IDS job was read or created.

The stdout-only checker executed deterministic logical-clock cases:

1. Canonically sorted `SOURCE_PIPELINE` and operation lock keys were acquired as one set.
2. Exact duplicate acquisition replayed without advancing fence or lock version; the same operation/idempotency key with changed input failed closed without state mutation.
3. A contender received `RESOURCE_CONFLICT_ACTIVE` and paused before queue admission.
4. Matching renewal extended expiry and atomically advanced every lock version while preserving the fencing token, invalidating pre-renewal CAS evidence.
5. Takeover required the incumbent fencing token and complete lock-version map, failed before expiry plus grace or on stale evidence, and succeeded at the boundary by advancing the global fence and every lock version atomically.
6. The stale holder was rejected for commit, renewal, and release; the successor could commit.
7. Matching release advanced every tombstone lock version before removing the whole set and replayed idempotently.
8. Unknown nested contract fields and raw-path requests failed closed without echoing the rejected path.

Machine evidence:

- `KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/stage041_lock_registry_runtime_contract.json`
- `KM_IDSystem/scripts/check_lock_registry_runtime.py`
- `KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/test_stage041_lock_registry_runtime.py`

## Whole-stage review repair note

The separate Stage041 review hardened this isolated slice without changing its
non-production scope:

- CAS lock-version evidence now accepts only strict positive integers; Python
  `bool` and numerically equal `float` values fail closed.
- Request timestamps must be non-negative. Commit, renewal and release reject
  logical-time regression; renewal must strictly extend expiry; release
  requires a live lease.
- Operation-family/job-type mappings, parameter relationships, provenance and
  rollback metadata are machine checked exactly instead of shape-only.
- Caller-supplied logical time is not a trusted production clock and remains an
  explicit production-readiness limit.

## Runtime Boundary

State exists only in `IsolatedLockRegistry` process memory. The checker uses
caller-supplied logical timestamps and never sleeps. It performed no database
connection, schema or state-registry write, persistent lock write, runtime file
write, queue or worker execution, retry scheduling, automatic resume, crash
recovery, cleanup, external API call, production activation, GitHub action, or
app reinstall.

Phase 3 scenarios, Phase 4 closeout, whole-stage review, batch review, and upload
remain separate runs. This run stops at `IDS-STAGE041-P3-GATE`.
