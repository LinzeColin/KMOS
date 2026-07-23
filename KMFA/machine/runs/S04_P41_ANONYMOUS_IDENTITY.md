# S04 / P4.1 / T-S04-01 — anonymous workspace identity receipt

Status: **LOCAL PHASE PASS — NOT STAGE-REVIEWED, NOT PUBLISHED, NOT DEPLOYED**

Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`
Parent commit: `ce9c27da2c6518fec2c740897c788bd63069678f`
Requirement / acceptance / test: `R-WS-001 / AC-WS-001 / TEST-WS-001`

## 1. Scope and entry gate

This receipt closes only `S04 / P4.1 / T-S04-01`. The S03 guarded rollout entry
gate was already closed before this phase: published `main` and the production
source are `ce9c27da…`, deploy Gate run `29955179158` passed, read-only identity
query run `29996883514` returned deployment `amffqczj7p2o22yz3en1or13` with
image `sha256:bafa6a96…4e60c`, and anonymous root/private-path/rollback/persistence
Oracles passed. This phase does not mutate production or re-label its identity.

The only output here is the minimum anonymous authorization boundary:

- high-entropy workspace ID and workspace secret generation;
- an irreversible server-side verifier;
- a one-hour session exchange API;
- reproducible collision, entropy, timing, plaintext and concurrency evidence.

It does not implement `.kmfa-recovery`, recovery export/import UI, secret
rotation/revocation, analytics/log redaction, rate limiting/challenge, durable
database/object migration, backup/restore, P4.2, whole-S04 review or Stage
upload.

## 2. Baseline and fixed findings

The S03 walking skeleton already generated a 256-bit `kmfa-r1` recovery
capability and stored only SHA-256 hashes, but it was intentionally not an
`AC-WS-001` proof.

| Finding | Baseline risk | Minimal correction | Result |
|---|---|---|---|
| `F-P41-001` | new workspace IDs used 96 random bits | new IDs use 16 CSPRNG bytes / 128 bits | **FIXED** |
| `F-P41-002` | no explicit ID + secret session exchange contract | added `POST /public-api/walking-skeleton/v1/sessions` | **FIXED** |
| `F-P41-003` | no equal negative verifier path for unknown ID vs wrong secret | one lookup + one SHA-256 + `hmac.compare_digest`, same 404 | **FIXED** |
| `F-P41-004` | no 10,000-create or concurrent database property evidence | added `TEST-WS-001` focused suite | **FIXED** |
| `F-P41-005` | increasing ID entropy could strand S03 recovery assets | verifier accepts legacy 16-char and new 22-char ID payloads | **FIXED** |

P4.1 phase-review open findings: `0`.

## 3. Implemented contract

- `secrets.token_urlsafe(16)` creates each new workspace ID: 128 CSPRNG bits.
- `secrets.token_urlsafe(32)` creates the workspace secret and access token:
  256 CSPRNG bits each.
- The existing one-time `recovery_code` response field is the P4.1 workspace
  secret. Its name remains stable so the deployed S03 UI and saved recovery
  material are not broken before P4.2.
- SQLite retains the existing `recovery_hash` schema. For uniformly random
  256-bit secrets, SHA-256 is an irreversible capability verifier; plaintext
  secrets are never inserted into workspace, token or audit rows.
- `POST .../sessions` accepts `workspace_id` and `workspace_secret`, verifies
  them without selecting by secret, and returns a new workspace-scoped bearer
  capability with a 3,600-second expiry. It never returns the workspace secret.
- Unknown ID, wrong secret and malformed-but-schema-valid input all return
  `404 {"detail":"workspace_not_found"}`. Unknown and known-wrong paths execute
  the same verifier operations using a dummy verifier when no row exists.
- Session responses remain `private, no-store` and
  `noindex, nofollow,noarchive`.
- The schema version stays `1`: no destructive migration, data rewrite or
  recovery-asset replay is needed.

## 4. TEST-WS-001 evidence

Production-equivalent Python 3.12 `secrets`, `hashlib`, `hmac`, SQLite and the
real workspace creation/store functions were used with synthetic data only.

Quantitative run:

| Check | Result |
|---|---:|
| sequential workspaces created | `10,000` in `13.335s` |
| workspace ID collisions | `0` |
| workspace secret collisions | `0` |
| access token collisions | `0` |
| workspace ID entropy input | `128-bit` |
| workspace secret / access token entropy input | `256-bit / 256-bit` |
| concurrent creates | `256`, collision/error `0` |
| final workspace/token/audit rows | `10,256 / 10,256 / 10,256` |
| syntactically valid SHA-256 verifier rows | `10,256` |
| raw SQLite/WAL/SHM `kmfa-r1-` plaintext hits | `0` |
| raw SQLite/WAL/SHM `kmfa-a1-` plaintext hits | `0` |
| known-wrong vs unknown-ID median verifier time | `6.209µs / 5.167µs` |
| negative median delta | `1.042µs` |

Focused and regression gates:

```text
TEST-WS-001 + S03 walking skeleton: 23 passed in 14.70s
all backend tests:                    127 passed in 36.98s
production Dockerfile build:          PASS
container create/session/get:         201 / 200 / 200
container wrong-secret exchange:      404
container session secret repeat:      false
container cache/robots boundary:       private,no-store / noindex,nofollow,noarchive
```

Both runs emitted one pre-existing Starlette/httpx deprecation warning. CI pins
the same Python 3.12 / pytest 9.1.1 / httpx 0.28.1 environment; the warning did
not alter behavior or acceptance results.

## 5. Security and compatibility review

- New IDs are public locators, not authorization. Every workspace read/write
  still requires a separate workspace-scoped short session capability.
- A token issued for workspace A returned 404 against workspace B; universal
  anonymous tokens do not exist.
- Correct exchange produced a new token, never repeated the workspace secret,
  and recorded only `workspace_session_exchanged` in the append-only audit.
- Existing S03 96-bit workspace IDs successfully exchanged their unchanged
  `kmfa-r1` verifier for a new session. Existing database rows, recovery
  materials, artifacts and named volume are not rewritten or deleted.
- Capability material is carried in JSON request/response bodies, never URL
  parameters. P4.3 still owns whole-chain URL/Referer/log/event/error/cache
  canary scanning and session revocation; this receipt does not claim it.

## 6. Validation commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=KMFA/app/backend uv run --isolated \
  --no-project --python 3.12 \
  --with-requirements KMFA/app/backend/requirements.txt \
  --with pytest==9.1.1 --with httpx==0.28.1 \
  python -m pytest -q \
  KMFA/app/backend/tests/test_anonymous_identity.py \
  KMFA/app/backend/tests/test_walking_skeleton.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=KMFA/app/backend uv run --isolated \
  --no-project --python 3.12 \
  --with-requirements KMFA/app/backend/requirements.txt \
  --with pytest==9.1.1 --with httpx==0.28.1 \
  python -m pytest -q KMFA/app/backend/tests
```

The final phase closure additionally runs the taskpack validator, negative
mutations, Dual-Plane gate, forbidden-payload/secret/path scans and
`git diff --check`.

## 7. Rollback and next boundary

Rollback is an ordinary revert of this phase commit. It restores the previous
session issuer while preserving the schema, workspace rows, artifact bytes,
legacy verifier values and `kmfa-app-state`; no `down -v`, database deletion,
secret logging, force-push or recovery replay is allowed.

This is Task `17/56` completed locally and published Stage remains `4/14`.
The next new run may execute only `S04 / P4.2 / T-S04-02`; whole-S04 review and
GitHub upload remain forbidden until P4.2–P4.4 are separately completed.
