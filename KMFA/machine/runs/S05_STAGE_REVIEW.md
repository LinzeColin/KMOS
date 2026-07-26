# S05 whole-stage review — durable state, storage, consistency and recovery

Date: 2026-07-26

Scope: `S05 / P5.1-P5.4 / T-S05-01..04`

Status: **PASS — guarded release candidate; remote publication closure pending**

## 1. Authority and review boundary

This receipt closes the required whole-stage review after all four S05 phases.
The authorized product-design taskpack remains v1.5.2, outer ZIP SHA-256
`31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`.
The repository projection still resolves exactly `49 Requirements / 49 primary
Acceptance Contracts / 14 Stages / 56 Phases / 56 Tasks / 49 trace rows / 6
promotion gates`, with zero validator errors or warnings.

The reviewed local phase chain is:

| Phase | Local commit | Contract |
|---|---|---|
| P5.1 | `c2c0b889` | structured database and migrations |
| P5.2 | `4c3d5ae0` | private object storage and inventory |
| P5.3 | `34eac93f` | recoverable DB/object/outbox consistency |
| P5.4 | `e2409eec` | retention, explicit deletion, backup and restore |

The phase chain was integrated with reviewed `origin/main`
`3f7cfd617754615e4b570dacdd39c3ef0af77586`. The runtime candidate tree before
adding this compact receipt was
`a5cf8418b253f2581406921fc2dc59025ef1573c`. The exact application image used
for every final runtime Oracle was
`sha256:9fe6093f19f76726435c73d85a42449ab674e626b7367d2c410789495443a0ed`.
The tree identifier is evidence for the pre-receipt runtime inputs, not a Git
commit or a production deployment identity.

This review does not switch production to PostgreSQL or S3-compatible storage,
enable production lifecycle deletion, create or claim a production backup,
change Cloudflare/Coolify/R2/WAF configuration, delete a volume/object/version,
or replay a recovery bundle. Synthetic MinIO/PostgreSQL measurements are test
evidence only.

## 2. Whole-stage result

S05's four task contracts close together:

| Task | Whole-stage assertion | Result |
|---|---|---|
| `T-S05-01 / AC-DATA-001` | schema-v4 structured project, progress, score, financial/task and recovery state survive process/database restart | **PASS** |
| `T-S05-02 / AC-DATA-002` | private S3-compatible bytes, metadata, checksums, multipart state and exact inventory stay consistent | **PASS** |
| `T-S05-03 / AC-DATA-003 / AC-ARCH-002` | DB/object/outbox operations converge after crash and timeout without partial, duplicate or unexplained terminal effects | **PASS** |
| `T-S05-04 / AC-DATA-004` | default retention has no expiry; explicit deletion is authorized and exact; checksum-closed backup/restore preserves live state and tombstones without resurrection | **PASS** |

The Stage Gate is therefore satisfied in the reviewed candidate: cross
restart/deploy/isolated-restore testing lost no accepted fixture data, the
object/index projections reconciled, and default automatic expiry remained
disabled. This does not make promotion gate G2 green: G2 also requires S03-S07
P0 completion, and S06/S07 have not been executed.

## 3. Cross-phase findings and closures

| Finding | Risk | Minimal correction | Closure |
|---|---|---|---|
| `F-S05-001` origin integration moved the full public App Shell from `/` to `/workspace` and made `/` a marketing page | root-domain product contract and no-account journey regressed | route every public path, including `/`, to `PublicAppShell`; retain `/workspace` only as a noindex compatibility alias; restore canonical metadata and root Oracles | **RESOLVED** |
| `F-S05-002` explicit S3 deletion could fall back to plain `DeleteObject` when version inventory was unavailable | historical private versions could survive a reported deletion | fail closed with `object_version_inventory_unavailable`; require exact provider version/delete-marker enumeration | **RESOLVED** |
| `F-S05-003` restore-target emptiness used current LIST only | hidden versions or delete markers could be mixed into a restore | use separately credentialed lifecycle inventory and require exact provider version count `0`, scoped to the target prefix | **RESOLVED** |
| `F-S05-004` a zero-object deletion could acquire a legal hold after the initial check and still finalize | business rows could be removed despite a current hold | recheck legal hold at each irreversible boundary and inside the final transaction; persist `purge_pending` when blocked | **RESOLVED** |
| `F-S05-005` chunked/concurrent uploads could write an object before the final durable-capacity decision | rejected uploads could amplify orphan bytes and evade reservations | count artifacts plus unprojected durable reservations and serialize the final capacity check before any object effect | **RESOLVED** |
| `F-S05-006` backup restore retained imported access-token hashes | a browser session revoked after the recovery point could be resurrected | clear reconstructed access sessions after chain validation; require fresh recovery to create a new session | **RESOLVED** |
| `F-S05-007` the final P5.4 restore Oracle omitted lifecycle inventory credentials after exact version checks became mandatory | a correct fail-closed path prevented the Oracle from testing the intended restore | inject lifecycle credentials only into the two isolated restore calls; keep backup calls least-privileged | **RESOLVED** |
| `F-S05-008` origin integration removed the complete Walking Skeleton style block | the anonymous product slice became visually unusable and WebKit found a sub-24px mode control | restore the coherent public walking layout, warning/mode/form/workspace/file/feedback/mobile styles and minimum 44px controls | **RESOLVED** |

Whole-stage open findings: `0`. Accepted risk used to waive a finding: `0`.
The initial import-order lint observations are formatting debt in already
reviewed phase/origin files, not runtime defects; E/F static checks, full syntax
compilation and all behavior gates pass. No broad formatting rewrite was added
to this release candidate.

## 4. Final-image and repository verification

```text
backend regression:                                      PASS (225/225)
  warning:                                                1 inherited Starlette/httpx deprecation
frontend production build:                               PASS (622 modules)
Ruff E/F on changed Python + compileall:                  PASS
local and Coolify Compose renders:                        PASS
workflow YAML parse / diff check:                         PASS / PASS
public-safety additions scan:                            PASS
  private key/cloud token/local path/binary/protected
  data deltas:                                            0 / 0 / 0 / 0 / 0
  credential-shaped URLs:                                 6 synthetic E2E DSN templates

P5.1 structured database Oracle:                         PASS (14 checks, schema 4)
P5.2 object-storage Oracle:                              PASS (19 checks)
  normal consistency / unexplained anomalies:             100% / 0
P5.3 crash/timeout consistency Oracle:                   PASS
  crash / timeout-after-apply injections:                 28 / 2
  max recovery:                                           2.166 seconds
  partial operation/outbox, unexplained terminal,
  duplicate external effect, raw delete, staged residue:  0 / 0 / 0 / 0 / 0
P5.4 retention/backup/restore Oracle:                    PASS
  default automatic expiry / accidental deletes:          false / 0
  exact provider versions:                                4 -> 0
  restored fixture / invariant failures:                  1/1 / 0
  synthetic measured RPO / RTO:                           4000ms / 354ms
  final object/business/imported-proof resurrection:      0 / 0 / 0

anonymous recovery/download/secret Oracle:               PASS
  invalid authorization / secret-canary hits:             0 / 0
abuse-control Oracle:                                    PASS
  normal false positives / attack bypasses:               0/100 / 0
public shell desktop/mobile/no-JS/degraded:               PASS (4/4)
Chromium/Firefox/WebKit accessibility and index boundary: PASS
  critical+serious axe / unpublished-canary index hits:   0 / 0

repository taskpack validator:                            PASS
  49 R / 49 AC / 14 Stages / 56 Phases / 56 Tasks
required mutation suite:                                 PASS
  positive / negative / source unchanged:                 1 / 4 / 5
KMFA dual-plane gate:                                    PASS
```

The first parallel backend/build invocation observed a transient root-test
failure while Vite was replacing committed `dist` files. Serial execution then
passed the full suite, and the root/public browser Oracles passed against the
final image. Missing local browser revisions and an early dependency-less
Python collection were harness setup stops before product assertions; the
version-locked Chromium, Firefox and WebKit runs above are the accepted result.

## 5. Promotion state, guarded upload and rollback

This receipt authorizes one non-force S05 code upload only after the final local
gates pass and `origin/main` is rechecked. The existing GitHub workflow may
build, test and request the normal automated deployment of the reviewed source.
There is no manual infrastructure or data-plane mutation in this Stage
publication.

Production-safe defaults remain the existing SQLite/private-filesystem path
with consistency and lifecycle processing paused. PostgreSQL, S3-compatible
storage, backup destinations, provider lifecycle credentials and deletion
workers require a later separately verified bounded cutover. Public root and
anonymous recovery/download must remain available throughout any rollout.

Rollback is an ordinary revert or selection of the previous verified
deployment. It must preserve schema `4`, current readers, all database/object/
backup volumes and provider versions, append-only operation evidence, sessions
and recovery material, plus all v1.5 recovery assets. It pauses
`KMFA_CONSISTENCY_STATE_MODE` and `KMFA_LIFECYCLE_MODE`, uses forward fixes, and
never force-pushes, downgrades schema/binary compatibility, runs
`docker compose down -v`, or deletes data to make an old image start.

The production source commit, image digest, deployment UUID and completion time
must be queried after the guarded upload; they are deliberately not prefilled
from a local candidate or an older deployment.

## 6. Next boundary

Task completion remains `24/56`: S05 changes the durable foundation, not the
number of completed task contracts beyond its four tasks. Once this Stage
publication's remote CI and deployment identity are closed, the published Stage
count becomes `6/14`. G2 and GA remain **NOT PASS**.

The only next new implementation run is `S06 / P6.1 / T-S06-01`, after remote
S05 closure. S06 owns arbitrary-file streaming/resume/scanning work; none of it
is claimed here. If upload, CI, deployment, source-image binding or public
post-deploy verification fails, work remains in S05 publication repair and
must not advance to S06.
