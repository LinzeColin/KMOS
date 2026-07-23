# S05 / P5.2 / T-S05-02 — private object storage receipt

Status: **LOCAL PHASE PASS — NOT STAGE-REVIEWED, NOT PUBLISHED, NOT DEPLOYED**

Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

Parent commit: `c2c0b8890645237988f0a2864d72ea7bd89c1383`

Requirement / acceptance / test: `R-DATA-002 / AC-DATA-002 / TEST-DATA-002`

## 1. Scope and conclusion

This receipt closes only `S05 / P5.2 / T-S05-02`. It adds an opt-in private
S3-compatible object adapter, immutable application-version keys, conditional
create, byte/checksum verification, database/object inventory reconciliation,
least-privilege local policy, production configuration keys and an automated
production-equivalent Oracle.

`AC-DATA-002` passes for the bounded synthetic fixture: the normal database
index and deep object inventory were `4/4` consistent (`100%`); one missing
object, one byte/metadata mismatch and one orphan were all detected and mapped
to deterministic repair states; unexplained anomalies were `0`; the repaired
rescan returned to `100%`. Direct anonymous object GET/LIST, credential access
outside the allowed prefix, credential deletion and a conditional overwrite
all failed.

This phase does **not** activate production object storage, implement the P5.3
cross-system state machine, perform P5.4 backup/restore or deletion lifecycle,
or claim long-term RPO/RTO. S06 still owns resumable/multi-file upload,
quarantine, content scanning and processor isolation. Default writes therefore
remain `legacy-filesystem`; the existing v1.5 filesystem reader and every
existing object remain intact.

## 2. Implemented contract

### Adapter and object identity

- `KMFA_ARTIFACT_STORAGE_MODE=legacy-filesystem` remains the default.
  `s3` is accepted only with a complete endpoint, bucket, region, prefix and
  access-key configuration. Unknown modes, incomplete configuration, invalid
  SDK configuration and provider outage fail closed with static errors.
- HTTPS is mandatory except when
  `KMFA_S3_ALLOW_INSECURE_LOCAL=1` is explicitly set for loopback,
  `*.localhost` or the isolated Compose service name `object-store`.
- Object keys have the fixed shape
  `<prefix>/artifacts/<workspace>/<artifact>/<artifact-version>/v########-<sha256>.blob`.
  They contain no user filename and are unique per application artifact
  version.
- `PutObject` sends `If-None-Match: *`, Content-MD5, attachment-only/private
  system metadata and the application SHA-256/artifact lineage. A post-write
  HEAD must match byte count and all lineage metadata before the database row
  can be registered.
- Downloads select the adapter recorded on the database version row, deep-hash
  bytes before responding and proxy an attachment-only same-origin response.
  The application never returns bucket or presigned URLs. S3 downloads use a
  `0600` temporary file removed after the response; v1.5 filesystem objects
  retain their original read path.
- Rolling the write mode back to `legacy-filesystem` does not change existing
  S3 rows. With the retained S3 configuration those rows remain readable
  through the backend-specific dual reader.

Cloudflare documents R2's S3 endpoint/`auto` region and current Put/Get/Head/
List behavior, including conditional Put and Content-MD5, while
Get/PutBucketVersioning remain unimplemented:
<https://developers.cloudflare.com/r2/api/s3/api/>.
Therefore the R2 contract is honestly named `immutable-key-v1`; it is not
misreported as native bucket versioning. AWS's conditional-write semantics are
documented at
<https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html>.

### Database index and reconciliation

- Existing schema v2 already records `artifact_version_id`, artifact/project
  lineage, version number, storage backend/key, original name, reported media
  type, byte count, SHA-256, lifecycle state and creation time. P5.2 did not
  require or invent a new schema migration.
- Upload writes the original compatibility row and normalized
  `artifact_versions` row in one structured-store transaction after the object
  create succeeds.
- The reconciler compares every active S3 index row with a paginated inventory
  whose bytes are independently downloaded and SHA-256 hashed. It detects
  missing objects, byte/metadata mismatch, unindexed objects and duplicate
  database keys.
- Every anomaly has one fixed repair state. Compact output contains only a
  truncated SHA-256 reference of the object key, counts and field names; it
  contains no raw object key, filename, credential, capability or user bytes.
- P5.2 only detects and classifies. Automated compensation, outbox/idempotency,
  quarantine execution and crash-point convergence remain explicitly assigned
  to P5.3.

### Access and deployment shape

- The committed MinIO fixture policy grants only `ListBucket` on the fixed
  private prefix and `GetObject`/`PutObject` on its objects. It grants no
  delete, bucket administration, wildcard resource or public operation.
- Local `s3` Compose uses pinned MinIO and MC digests, a dedicated
  `kmfa-object-data` volume, anonymous access `none`, native fixture
  versioning and separate root/App credentials. Bootstrap now mechanically
  rejects equal root and App credentials.
- Coolify only receives external S3/R2 configuration keys. Its default stays
  legacy and this intermediate phase does not enable a profile or change a
  secret.
- `.gitignore` and `.dockerignore` reject `.env`, `.env.*` and `*.env`
  operator files so local database/object credentials cannot be committed or
  burned into the self-contained Docker image. Public `.env.example` remains
  trackable.
- Runtime status says that a private, server-credential-only provider policy is
  required and that a deployment Oracle must verify it; runtime health does
  not pretend to prove a provider control-plane setting.

## 3. Final-image AC-DATA-002 Oracle

Runtime-frozen application image:
`sha256:8b451cbd09b8ca3cd01d68b44c2dc1a1d5abdcff4ad4d242a207286604c35829`.

Object fixture:
`minio/minio:RELEASE.2025-09-07T16-13-09Z` /
`sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e`.

Object client fixture:
`minio/mc:RELEASE.2025-08-13T08-35-41Z` /
`sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727`.

Database fixture:
`postgres:17.10-alpine3.23` /
`sha256:8189a1f6e40904781fc9e2612687877791d21679866db58b1de996b31fc312e4`.

All bytes, identities and credentials were ephemeral synthetic fixtures.

| Gate | Observation | Result |
|---|---|---|
| fixture matrix | 4 objects: `0`, `4,373`, `4,373`, `2,097,408` bytes; multiple reported types; 3 same filenames; 2 duplicate-content objects | **PASS** |
| application versions | all 4 database versions had distinct non-filename keys; version-2 key contract differs from version 1 | **PASS** |
| database metadata | version/backend/name/media type/size/SHA-256/state and project/artifact lineage matched each workspace fixture | **PASS** |
| normal reconciliation | indexed/inventory/consistent=`4/4/4`; consistency=`1.0`; anomaly=`0` | **PASS** |
| manufactured anomalies | missing/mismatch/orphan=`1/1/1`; classified=`3`; unexplained=`0`; deterministic repair states=true | **PASS** |
| repaired rescan | indexed/inventory/consistent=`4/4/4`; consistency=`1.0`; anomaly=`0` | **PASS** |
| private access | anonymous GET/LIST=`403`; scoped credential outside-prefix GET/PUT/LIST denied; DeleteObject denied | **PASS** |
| overwrite | second conditional create of the same application version rejected | **PASS** |
| shared service | objects uploaded alternately through two App nodes and downloaded through the other node | **PASS** |
| replacement | object container was replaced on the retained object volume; index and bytes remained readable | **PASS** |
| outage | stopped object service made status explicitly `503`; database index stayed unchanged | **PASS** |
| browser recovery | a fresh cookie jar used the externally held recovery capability and downloaded hash-identical bytes | **PASS** |
| adapter rollback | new writes switched to legacy while an existing S3-backed version remained downloadable | **PASS** |
| leak scan | generated capabilities and database/object credentials in App/DB/object logs and compact JSON=`0` | **PASS** |

The Oracle records `19/19` named checks. MinIO native bucket versioning is an
extra test-fixture safety property, not a claim about Cloudflare R2.

## 4. Phase review findings and closures

| Finding | Impact | Minimal correction | Closure |
|---|---|---|---|
| `F-P52-001` baseline stored all bytes only in the App filesystem volume | no S3-compatible durable object shape or DB/object Oracle | add opt-in adapter, immutable key/checksum, dual reader and deep reconciliation | **RESOLVED** |
| `F-P52-002` initial public status overclaimed provider bucket privacy | application health cannot prove a control-plane public-access setting | expose only the required access contract and mark deployment Oracle mandatory | **RESOLVED** |
| `F-P52-003` initial App policy included premature `DeleteObject` | App compromise or bug could erase the only object before P5.3/P5.4 | remove delete; lock exact List/Get/Put actions and prefix condition; runtime negative test deletion | **RESOLVED** |
| `F-P52-004` an early download path could leave an S3 response body open if local temp creation failed | connection/resource leak during disk or permission failure | place descriptor creation inside the body-closing `finally` boundary | **RESOLVED** |
| `F-P52-005` initial Oracle did not mechanically compare all database metadata/lineage fields | green byte checks could miss name/media/state or lineage drift | add per-workspace DB equality assertions and a named check | **RESOLVED** |
| `F-P52-006` malformed region escaped client construction as `InvalidRegionError` | misconfiguration could produce an uncontracted 500 | wrap SDK-construction errors as static object-storage configuration failure; add regression | **RESOLVED** |
| `F-P52-007` root/App credential separation existed only in prose | an operator typo could invalidate least privilege | make Compose bootstrap reject equal access IDs or secrets without printing values | **RESOLVED** |
| `F-P52-008` repository and Docker context did not exclude local env files | future S3/DB credentials could be staged or copied into an image | add `.gitignore`/`.dockerignore` env boundaries and contract assertions | **RESOLVED** |

Phase-review open findings: `0` (`8/8` resolved; accepted risk=`0`).

## 5. Verification

```text
focused object/Walking/recovery/structured tests:       43 passed
all backend tests:                                      172 passed
Ruff changed-Python checks / Python compile:             PASS / PASS
production Dockerfile build:                             PASS
AC-DATA-002 final-image Oracle:                          PASS (19 checks)
P5.1 exact-image structured regression:                 PASS (14 checks)
S03/P3.4 + S04/P4.2-P4.3 exact-image Oracle:            PASS
  invalid authorization / secret-canary hits:            0 / 0
S04/P4.4 exact-image abuse Oracle:                       PASS
  normal false positives / attack bypasses:              0/100 / 0
S03/P3.2 public shell desktop/mobile/no-JS/degraded:     PASS (4/4)
S03/P3.3 Chromium/Firefox/WebKit accessibility/index:   PASS (0 severe, 0 canary)
local + Coolify Compose default/profile config:          PASS (4 renders)
object policy JSON and actionlint 1.7.12:                PASS
Python dependency audit / npm production audit:          0 / 0 known findings
sealed ZIP / manifest / package validator:               PASS (42/42, 49/49)
repository validator / mutation suite / dual-plane:      PASS
Docker owned-resource residue:                           0
```

The backend suite emits one pre-existing Starlette/httpx deprecation warning;
it does not alter the result. The final repository validator is rerun after
this receipt and HANDOFF are added.

## 6. Rollout, rollback and next boundary

P5.2 performs no production rollout. Production remains the verified S04
source/image/deployment tuple; no Cloudflare, Coolify, R2, PostgreSQL, WAF,
production database, object or volume was changed.

A later S05-reviewed rollout must create/verify a private provider bucket,
disable all public development/custom-domain access, issue a bucket-scoped
credential, preserve the legacy reader, run the same-image DB/object inventory
and anonymous/prefix/delete negative Oracles, then switch only the write mode.
Cloudflare documents that buckets are private by default and public access is
a separately enabled surface:
<https://developers.cloudflare.com/r2/buckets/create-buckets/> and
<https://developers.cloudflare.com/r2/buckets/public-buckets/>.

Fast rollback restores `KMFA_ARTIFACT_STORAGE_MODE=legacy-filesystem` while
retaining the S3 configuration for dual reads. It preserves
`kmfa-app-state`, `kmfa-postgres-data`, `kmfa-object-data`, every DB row,
provider object/version and the v1.5 recovery bundle. It never uses
`docker compose down -v`, credential revocation, object deletion, schema
downgrade, recovery replay or force-push.

Stop immediately if provider privacy cannot be independently verified,
conditional writes are unsupported, normal consistency is below `100%`, an
anomaly lacks a deterministic state, an unpublished object is publicly
readable, evidence contains a capability/credential, or backup/version
requirements cannot be met.

This is Task `22/56` completed locally; S05 is `2/4` phases complete and the
published Stage remains `5/14`. The next new run may execute only
`S05 / P5.3 / T-S05-03` consistency state machine. It must not start P5.4,
perform whole-S05 review, activate production PostgreSQL/S3 or upload this
intermediate phase to GitHub.
