# STAGE-042 Phase 1 Automatic Lifecycle Scope Boundary

## State Authority

Stage042 introduces no job state and no transition shortcut. Every lifecycle
candidate must use the reviewed `ids.job_state.v1` graph:

- start: `QUEUED -> CLAIMED -> RUNNING`;
- pause before claim: `QUEUED -> PAUSED`;
- active pause: `CLAIMED|RUNNING -> PAUSE_REQUESTED -> PAUSED`;
- retry pause: `RETRY_WAIT -> PAUSED`;
- resume: `PAUSED -> QUEUED`, then a new admission/claim/lock cycle;
- retry eligibility: `RETRY_WAIT -> QUEUED`, still owned by Stage039;
- safe close: only existing non-active cancellation paths or
  `PAUSE_REQUESTED -> CANCELLED` after checkpoint/quarantine.

`QUEUED -> RUNNING`, `PAUSED -> RUNNING`, `RUNNING -> PAUSED`,
`RUNNING -> CANCELLED`, and reopening terminal history are forbidden.

## Automatic Start

An automatic-start candidate requires fresh admission evidence, exact
idempotency identity, a Stage038 claim candidate, Stage041 lock/lease evidence
and a current fencing token. It cannot skip `CLAIMED`, invoke a worker or
mutate a job. Missing, stale, conflicting or incomplete evidence returns
`REQUIRE_MANUAL_REVIEW`.

## Automatic Pause

External-drive offline, insufficient disk and insufficient API budget always
produce a pause candidate for related work. Queue pressure, job-type
concurrency and same-source conflict retain Stage040 policy semantics.

- A queued or retry-wait job can pause only without an active claim or lock.
- A claimed/running job first enters `PAUSE_REQUESTED`.
- `PAUSED` or safe cancellation requires checkpoint/quarantine evidence.
- Pause and resume consume no retry budget.
- A pressure observation never authorizes lock bypass or output mutation.

## Guarded Resume

Stage042 owns automatic-resume policy, but Phase 1 authorizes only a
reference-only candidate. `PAUSED -> QUEUED` still requires:

1. owner revalidation required by Stage037;
2. fresh resource observations and all resource gates passing;
3. no active claim or lock;
4. a new admission, claim, lock, lease and fencing cycle before running.

Drive reconnect, disk recovery, API budget recovery or conflict clearance is
not itself owner authorization. A lost worker or missing in-memory state is
process-crash recovery and remains Stage043-owned.

## Retry And Dead Letter Boundary

Stage039 remains the sole retry/dead-letter policy and budget owner.
`RETRY_WAIT -> QUEUED` requires next-eligible evidence, passing resource
gates and no active claim/lock. Stage042 cannot reserve, increment or reset the
retry budget and cannot reopen `FAILED`, `DEAD_LETTERED`, `SUCCEEDED` or
`CANCELLED`.

## Safe Close

Safe close stops new lifecycle decisions and admission, requests active-job
pause, waits for checkpoint/quarantine, freezes retry/resume eligibility,
releases only matching locks, verifies zero active locks, closes the reviewed
transport and preserves audit/checkpoint/evidence references. It does not kill
a process, claim crash recovery, discard terminal history or write runtime
output.

## Cleanup Candidate Boundary

Stage042 may emit only a reference-only candidate for
`TEMP_STAGING_OUTPUT` or `INCOMPLETE_DERIVATIVE_OUTPUT`. It cannot delete.
Stage044 remains the execution owner and must independently enforce approved
root identity, root-relative path, immutable lstat identity, no symlink
following, exclusive lock and writer quiescence.

`FACT_SOURCE`, `MANIFEST`, `EVIDENCE_LEDGER`, `REPORT_SNAPSHOT` and
`AUDIT_LOG` are always protected.

## Deferred Parameters

Phase 1 assigns no numeric values. `lifecycle_tick_interval`,
`resume_stability_window`, `checkpoint_wait_timeout`,
`graceful_shutdown_timeout` and `cleanup_scan_interval` require an explicit
source, rationale, unit, policy version, validation evidence and rollback
before Phase 2 can use them. There is no implicit default and no production
calibration claim.

## Phase 2 Gate

`Phase 2 must run separately`. It may implement only one isolated,
non-production lifecycle decision slice over a real Git-tracked control
reference. It must prove idempotent start/pause/resume/shutdown candidates and
human status projection without persistence, process recovery, cleanup delete
or production activation.

Stop markers:

- `NO_PHASE2`
- `NO_AUTOMATIC_LIFECYCLE_RUNTIME`
- `NO_PROCESS_CRASH_RECOVERY`
- `NO_CLEANUP_DELETE`
- `NO_RAW_METADATA_ACCESS`
- `NO_FAKE_IDS_BUSINESS_DATA`
- `NO_GITHUB_UPLOAD`
- `NO_APP_REINSTALL`

The next gate is `IDS-STAGE042-P2-GATE`; `push_allowed=false`.
