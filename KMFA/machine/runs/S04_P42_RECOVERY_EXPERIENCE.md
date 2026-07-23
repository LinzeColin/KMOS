# S04 / P4.2 / T-S04-02 — cross-device recovery receipt

Status: **LOCAL PHASE PASS — NOT STAGE-REVIEWED, NOT PUBLISHED, NOT DEPLOYED**

Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`
Parent commit: `b7985d779d65f9382b69d58a0e5964afc3dc5ef0`
Requirement / acceptance / test: `R-WS-002 / AC-WS-002 / TEST-WS-002`

## 1. Scope and fixed findings

This receipt closes only `S04 / P4.2 / T-S04-02`. It adds recovery-code and
`.kmfa-recovery` flows, a visible lost-key warning, atomic recovery-secret
rotation and a final-image cross-device Oracle. It does not claim P4.3
whole-chain secret hygiene/session revocation, P4.4 abuse controls, whole-S04
review, GitHub upload or production deployment.

| Finding | Baseline risk | Minimal correction | Result |
|---|---|---|---|
| `F-P42-001` | only a copied recovery code could restore a workspace | strict versioned `.kmfa-recovery` export/import API and UI | **FIXED** |
| `F-P42-002` | secret verification and session issue were not linearized against rotation | verifier check, token issue and audit now share one `BEGIN IMMEDIATE` transaction | **FIXED** |
| `F-P42-003` | UI said recovery file/rotation were unavailable and warning was not persistent | pre-create warning plus copy/download/import/rotation controls | **FIXED** |
| `F-P42-004` | no safe way to revoke leaked recovery material | atomic verifier replacement; old code/file immediately returns 404; data and open short sessions remain | **FIXED** |
| `F-P42-005` | prior Oracle used only recovery code and lacked invalid/truncated/revoked coverage | isolated A/B/C/D browser contexts, database restart, six-case negative matrix and before/after inventory | **FIXED** |
| `F-P42-006` | a native browser trace would retain capability-bearing DOM and POST bodies | secret-redacted structured E2E trace; raw capability trace is deliberately not persisted | **FIXED** |
| `F-P42-007` | App README still said recovery file and rotation were future work | updated implemented/pending boundary without claiming P4.3 | **FIXED** |

P4.2 phase-review open findings: `0` (`7/7` resolved).

## 2. Recovery-file and rotation contract

The download is `kmfa-workspace.kmfa-recovery` with media type
`application/vnd.kmfa.recovery+json`, `attachment`, `private, no-store`,
`nosniff` and `noindex`. Its exact v1 schema has four fields only:

```json
{"format":"kmfa-recovery","version":1,"workspace_id":"<locator>","workspace_secret":"<256-bit capability>"}
```

- Export is a `POST` authorized by both the current short session and current
  workspace secret. The secret never enters a URL.
- Import accepts at most 4 KiB of strict UTF-8 JSON. Duplicate/extra/missing
  keys, wrong types/version/format, malformed IDs/secrets and truncated JSON
  fail closed. It returns a short session and never echoes the secret.
- Rotation is authorized by the current workspace-scoped short session and
  atomically replaces the stored SHA-256 verifier with a new 256-bit CSPRNG
  secret. Old code, old recovery file and old ID+secret exchange then return
  404. Existing short sessions intentionally remain until expiry; P4.3 owns
  revocable-session hardening.
- The database schema remains v1. Existing S03 16-character workspace IDs and
  their unchanged recovery capability can export/import successfully. No
  workspace, project, progress, artifact, volume or v1.5 recovery asset is
  migrated, replayed or deleted.
- The UI warning is visible before create/recover: recovery code/file equals
  full control, cannot be recovered through account/email/support after the
  page session is gone, and must be rotated if leaked.

## 3. AC-WS-002 final-image evidence

The Dockerfile built the current application source and produced local image
ID `sha256:31ae4b64c1ee4c26a875e4cf61deb5ada96b37136c8a47c74de9dd81ec4ab33b`
(subsequent receipt/HANDOFF-only edits are not runtime inputs). The Oracle used
synthetic project/file data only and an initially empty host state directory.

| Oracle step | Result |
|---|---|
| Device A warning → create → save progress 64 → upload → export file | **PASS** |
| restart application/database with the same durable state | **PASS** |
| isolated Device B imports file, compares project/progress/object, downloads same bytes | **PASS** |
| Device B rotates secret and exports replacement recovery file | **PASS** |
| wrong code, truncated file, wrong file secret, revoked code/file/session exchange | `6` attempts, `0` authorization successes, all `404` |
| isolated Device C restores with rotated code | **PASS** |
| Flag `1→0` disables recovery while preserving rows/object; `0→1` restores | **PASS** |
| isolated Device D imports rotated file after re-enable | **PASS** |

Quantitative thresholds:

```text
valid recovery data consistency:     100%
object count before/after:            1 / 1 / 1
object SHA-256 before/after:           501b484c…af011 / identical / identical
project/progress before/after:         identical / identical
invalid authorization successes:      0
warning visible on entry devices:      true
localStorage/sessionStorage/cookies:   0 / 0 / 0
recovery secret in URL:                false
recovery secret state/log/evidence:    0 / 0 / 0 hits
```

The CI artifact contains `result.json`,
`sanitized-e2e-trace.json` and `recovered-after-restart.png`. It deliberately
does not contain a recovery file, raw secret, access token or native Playwright
trace. The structured trace records the seven executed state transitions with
capabilities redacted.

## 4. Unit, regression and build gates

```text
P4.2 + P4.1 + S03 focused tests:  35 passed in 16.05s
all backend tests:                139 passed in 32.88s
Python compile:                   PASS
frontend Vite build:              PASS (622 modules)
production Dockerfile build:      PASS
final-image TEST-WS-002 Oracle:   PASS
git diff --check:                 PASS
```

The backend runs emitted one pre-existing Starlette/httpx deprecation warning.
It did not change behavior or the acceptance result.

## 5. Security review and non-claims

- SQLite/WAL/SHM and object-state scanning found neither old nor rotated
  plaintext recovery secrets. Container access logs and persisted E2E
  evidence also had zero capability hits.
- Recovery material is handled in POST bodies and transient in-page memory;
  `credentials: omit` is used, and the UI did not create Cookie,
  `localStorage` or `sessionStorage` entries.
- Recovery files contain no project name, progress, artifact metadata,
  timestamps, email or account identifiers.
- This focused proof does not replace `AC-WS-003`: P4.3 must still scan
  URL/Referer/request logs/application logs/events/errors/caches across the
  complete chain and implement revocable, protected session credentials.
- Named-volume persistence remains the early adapter. Durable database/object
  services and backup/restore are still unproved and cannot be marked GA.

## 6. Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=KMFA/app/backend uv run --isolated \
  --no-project --python 3.12 \
  --with-requirements KMFA/app/backend/requirements.txt \
  --with pytest==9.1.1 --with httpx==0.28.1 \
  python -m pytest -q KMFA/app/backend/tests

npm run build --prefix KMFA/app/frontend
docker build -f KMFA/app/backend/Dockerfile -t kmfa-app:p42-e2e .

state_dir="$(mktemp -d /tmp/kmfa-p42-state.XXXXXX)"
out_dir="$(mktemp -d /tmp/kmfa-p42-evidence.XXXXXX)"
uv run --isolated --no-project --python 3.12 --with playwright==1.60.0 \
  python KMFA/app/e2e/walking_skeleton_flow.py \
  --image kmfa-app:p42-e2e --state-dir "$state_dir" --out-dir "$out_dir" \
  --container-name kmfa-p34-p42-e2e --port 18142
```

The Oracle removes only its exact test-prefixed container and never deletes
the supplied state directory.

## 7. Rollback and next boundary

Rollback is an ordinary revert of this phase commit or the existing
`KMFA_WALKING_SKELETON_ENABLED=0` runtime flag. Neither path deletes database
rows, artifacts, legacy verifiers, named volumes or recovery bundles. Never
use `down -v`, force-push or recovery replay as rollback.

This is Task `18/56` completed locally; S04 is `2/4` phases complete and the
published Stage remains `4/14`. The next new run may execute only
`S04 / P4.3 / T-S04-03`. Whole-S04 review and GitHub upload remain forbidden
until P4.3 and P4.4 are separately completed.
