# S05 / P5.1 / T-S05-01 — structured database receipt

Status: **LOCAL PHASE PASS — NOT STAGE-REVIEWED, NOT PUBLISHED, NOT DEPLOYED**

Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

Parent commit: `031bf9923b92d8d2ac4a690a39476825940ba587`

Requirement / acceptance: `R-DATA-001 / AC-DATA-001`

## 1. Scope and conclusion

This receipt closes only `S05 / P5.1 / T-S05-01`. It adds a versioned
structured database for projects, progress, score, finance, file
indexes/versions, tasks and audit; a repository/service transaction boundary;
an opt-in shared PostgreSQL deployment shape; and a read-only, additive v1.5
SQLite migration path.

`AC-DATA-001` passes in the bounded production-equivalent synthetic Oracle:
the same business fixture survived two application nodes, application-node
replacement, PostgreSQL-container replacement on the retained data volume,
client-cookie clearing and recovery. Lost, duplicated or constraint-corrupted
business rows were `0`; an invalid transaction committed `0` partial rows.

This phase does **not** implement P5.2 object storage, P5.3 state/deletion
semantics, P5.4 backup/restore, production cutover or whole-S05 review. File
bytes still use the P3.4 private filesystem adapter. Therefore this receipt
does not claim long-term RPO/RTO, backup recovery, explicit deletion, GA or
production durability.

## 2. Implemented contract

### Database and migrations

- `SCHEMA_VERSION=2`; SQLite and PostgreSQL each have an ordered
  `0001_legacy_walking_skeleton.sql` and `0002_structured_data.sql` chain.
- `schema_migrations` records version, filename, SHA-256 and application time.
  Missing versions, a newer database or changed applied bytes fail closed.
- Migration execution is atomic. SQLite uses `BEGIN IMMEDIATE`; PostgreSQL
  uses a transaction-scoped advisory migration lock. DDL is expand-only;
  rollback is forward-fix plus the retained legacy reader, not destructive
  down-migration.
- Migration digests at the frozen runtime source:

| Backend / migration | SHA-256 |
|---|---|
| SQLite `0001` | `f49d5b5429c62a17f2d153a2154741fac745d734489c6d23d13591090f709ae9` |
| SQLite `0002` | `53c26bec6a62bf60359f2a63c31458ba403f399b9258c9e4e39bb11d8f31610e` |
| PostgreSQL `0001` | `34722f982a5493f0cad3c00e512e1429d14b189a211eff50cd345a3ba826eb40` |
| PostgreSQL `0002` | `e359cdebcf79c1c5609a969c1d9f338cce6245a96bb8ed7aad640cd23604ee0d` |

### Structured schema

| Table | Durable meaning / principal constraints |
|---|---|
| `projects` | one active/archived project per workspace; nonblank name; row version |
| `project_metrics` | one row per project; progress and nullable score each `0..100` |
| `financial_records` | integer minor units only; non-negative amount; record type enum; uppercase 3-letter currency; ISO-shaped date; row version |
| `artifact_versions` | project/file/version index; unique artifact+version; byte count; lowercase SHA-256; lifecycle enum; no file bytes in DB |
| `workspace_tasks` | project task; status enum; deterministic sort order; row version |
| `audit_events` | retained append-only audit with update/delete triggers |
| `access_tokens` | explicit global `issuance_order` preserves oldest-session eviction across SQLite/PostgreSQL and same-second issuance |

Existing `workspaces`, capability verifiers, access-token hashes, artifact
metadata and audit rows remain readable. New project create/update and
artifact registration dual-maintain the compatibility rows and normalized
rows in one transaction; public project/progress/file reads use the normalized
projection. Raw recovery codes, session tokens and file bytes are never added
to the structured schema.

### Adapter, repository and service

- `legacy-sqlite` remains the default if no mode is set. This preserves the
  current v1.5 recovery path and makes an intermediate code rollback a mode
  change rather than a data rewrite.
- `postgresql-primary` requires
  `KMFA_STRUCTURED_DATABASE_URL` from the environment. Unknown mode, missing
  URL, invalid scheme, driver failure or connection failure returns a static
  storage error; the DSN is not returned in API status/evidence.
- PostgreSQL is `postgres:17.10-alpine3.23`; the application pins
  `psycopg[binary]==3.3.4`. The adapter uses autocommit for reads and explicit
  transactions for writes.
- Explicit writes use a transaction advisory lock, retaining the P4 capacity,
  session-budget and audit invariants while P5.1 traffic is small. This is a
  deliberate compatibility boundary, not a claim of final high-write
  scalability.
- `StructuredRepository` owns SQL projections, finance/tasks, artifact
  versions and deterministic snapshots. `StructuredDataService` validates the
  P5.1 fixture and commits score+finance+task atomically.
- Compose defines an opt-in `postgresql` profile, persistent
  `kmfa-postgres-data`, environment-only secrets and a structured DB-aware
  container healthcheck. Default Compose mode remains `legacy-sqlite`; this
  phase does not authorize production profile activation.

## 3. v1.5 preservation and migration

`python -m app.legacy_sqlite_import --source <path>`:

- accepts only a source path on the CLI; target DSN is environment-only;
- opens SQLite with `mode=ro` and `query_only=ON`;
- imports legacy v1 core rows and, when present, all v2 project/metric/finance/
  artifact-version/task rows;
- preserves legacy `rowid` session order relatively while assigning a
  conflict-free target issuance order;
- is additive and idempotent; existing unequal target rows abort the complete
  transaction rather than overwrite history;
- never deletes or edits the source, target history, object volume or recovery
  bundle.

The final Oracle imported both a pure v1 source and a v2 SQLite source twice.
The pure v1 source remained byte-identical at
`58787880f06613140dff5b64922a80e8700cd5836795ccc86e592414609da569`.
The v2 source remained byte-identical at
`ba9bc964524bfb4de9ce1ef7b2f66279649ef2286dae71d1701e42ad3a3fecd2`,
and PostgreSQL retained its score `77`, one finance row and one task.

No actual user database, private runtime, v1.5 recovery ZIP/bundle, production
volume, Cloudflare setting or Coolify setting was read or mutated.

## 4. AC-DATA-001 final-image Oracle

Runtime-frozen local application image:
`sha256:4d9f40ac7469f08e231da1c564f695e6fe84c19980b03ea2312ae6d4cf1d74be`.
PostgreSQL image:
`postgres:17.10-alpine3.23` /
`sha256:8189a1f6e40904781fc9e2612687877791d21679866db58b1de996b31fc312e4`.
All inputs and records were synthetic.

| Gate | Observation | Result |
|---|---|---|
| concurrent migration startup | two fresh App processes opened the same empty PostgreSQL target; schema ended exactly at v2 | **PASS** |
| core fixture | project/progress `67`, score `93`, one finance row, one artifact version and 21 tasks persisted | **PASS** |
| transaction failure | score update followed by negative-amount insert raised a constraint error; pre/post full snapshot hash remained identical | **PASS** |
| concurrency | 20 parallel task writers plus the base task produced 21 unique ordered tasks; loss/duplicate `0/0` | **PASS** |
| shared database | session created on App A read/downloaded successfully from App B | **PASS** |
| rolling App replacement | App A removed, App C introduced while App B served; project/progress/file remained available | **PASS** |
| cleared-client recovery | a fresh empty cookie jar recovered with the externally held recovery capability; browser storage was not authoritative | **PASS** |
| database-node replacement | PostgreSQL container was gracefully replaced using only the retained named data volume; both App nodes reconnected | **PASS** |
| structured consistency | business-state SHA-256 before/after replacement was `63e35ac2d162e3a502705b436f6dbcd26ff40ca65734ecf40ed47632604d39b0` | **PASS** |
| append-only audit | expected recovery/download events increased audit rows `3 → 5` and survived replacement | **PASS** |
| arbitrary file | attachment download SHA-256 equalled upload SHA-256 `4353561b5e5774b25d7137034839a23d95814879258f8c2ec2bc70f80acb18e0` | **PASS** |
| v1/v2 migration | pure v1 and structured v2 sources each imported twice without duplication or source-byte change | **PASS** |
| leak scan | raw recovery/session capabilities and generated PostgreSQL credential hits in App/DB logs and compact report were `0` | **PASS** |

The full pre/post snapshot hashes intentionally differ because recovery and
download append audit events. The separately defined business-state hash
excludes only the expected audit count and is identical. This distinction
prevents a valid append-only audit from being mislabeled as business-state
corruption.

## 5. Phase findings and closures

| Finding | Impact | Minimal correction | Closure |
|---|---|---|---|
| `F-P51-001` baseline had only four SQLite tables and no shared DB mode | project score/finance/tasks/version index and node replacement could not pass | add v2 schema, dual adapter and repository/service | **RESOLVED** |
| `F-P51-002` a full-snapshot hash changed after a valid recovery | expected audit append was initially indistinguishable from business corruption | retain full hashes but compare a separately named business-state hash; assert audit growth | **RESOLVED** |
| `F-P51-003` replacing SQLite `rowid` ordering with token-hash ordering broke oldest-session eviction | same-second sessions could evict the wrong capability; one full regression failed | migrate explicit `issuance_order`, backfill existing rows and use it in both backends | **RESOLVED** |
| `F-P51-004` initial importer copied source issuance order into a nonempty target | a unique-order collision rolled back the Oracle | preserve source relative order while allocating stable conflict-free target order; rerun twice | **RESOLVED** |
| `F-P51-005` initial importer covered only v1 core rows | later v2 SQLite score/finance/task writes could be omitted at cutover | detect all-or-none v2 schema and import/verify every structured table | **RESOLVED** |
| `F-P51-006` shallow HTTP health did not exercise the selected database | a configured PostgreSQL outage could look healthy to Compose | add schema-v2 structured-store check before shallow HTTP health | **RESOLVED** |

Phase-review open findings: `0` (`6/6` resolved).

## 6. Verification

```text
focused structured + Walking + lifetime-cap tests: 25 passed
all backend tests:                                  165 passed
Ruff changed-Python checks:                         PASS
Python compile:                                     PASS
production Dockerfile build:                        PASS
PostgreSQL 17.10 AC-DATA-001 Oracle:                PASS (14 checks)
S03/P3.4 + S04/P4.2-P4.3 exact-image Oracle:        PASS
S04/P4.4 exact-image abuse Oracle:                  PASS
  normal false positives / attack bypasses:         0/100 / 0
  concurrency admitted/blocked and recovery:        2/4 / PASS
local + Coolify Compose default/profile config:     PASS (4 renders)
structured container healthcheck:                   PASS
taskpack validator:                                 PASS (49/49, 14/56/56, 29 receipts)
validator mutation suite:                           PASS (1 positive, 4 negative)
dual-plane CI checker:                              PASS (5 projects)
git diff --check:                                   PASS
```

The backend suite emits one pre-existing Starlette/httpx deprecation warning;
it does not affect the result. The taskpack, mutation and dual-plane gates were
run after this receipt was added, so the receipt itself is inside the checked
phase candidate.

## 7. Rollout, rollback and stop conditions

There is no production rollout in P5.1. Production remains on the already
verified S04 tuple and the existing SQLite/object volume. A later authorized
cutover must first satisfy P5.4 backup/restore prerequisites, quiesce and hash
the source, run the read-only importer, compare counts/snapshots, then activate
both the `postgresql` profile and `postgresql-primary` mode. A failed migration
or mismatch stops before traffic switch.

Fast rollback restores `KMFA_STRUCTURED_DATABASE_MODE=legacy-sqlite` while
retaining both `kmfa-app-state` and `kmfa-postgres-data`, keeps the S04 dual-ID
reader and performs a forward fix. It never uses `down -v`, table drops,
destructive migration, recovery replay or pre-P4.1 binaries.

Stop immediately if a production source lacks a verified backup, import
conflicts, source bytes change, row/snapshot counts diverge, a DSN/capability
appears in evidence, or the source of truth is ambiguous.

This is Task `21/56` completed locally; S05 is `1/4` phases complete and the
published Stage remains `5/14`. The next run may execute only
`S05 / P5.2 / T-S05-02` object storage. It must not start P5.3/P5.4, perform
whole-S05 review, activate production PostgreSQL or upload this intermediate
phase to GitHub.
