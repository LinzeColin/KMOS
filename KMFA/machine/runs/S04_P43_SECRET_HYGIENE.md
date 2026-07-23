# S04 / P4.3 / T-S04-03 — secret hygiene receipt

Status: **LOCAL PHASE PASS — NOT STAGE-REVIEWED, NOT PUBLISHED, NOT DEPLOYED**

Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`
Parent commit: `8c9b9e10d154f475d6b9b848270c078b1a3463c9`
Requirement / acceptance / test: `R-WS-003 / AC-WS-003 / TEST-WS-003`

## 1. Scope and fixed findings

This receipt closes only `S04 / P4.3 / T-S04-03`. It adds a protected,
revocable browser session, whole-process capability redaction, an
anti-exfiltration browser boundary and a final-image secret scan Gate. It does
not claim P4.4 abuse controls, whole-S04 review, GitHub upload, production
deployment, durable database/object services, backup/restore or GA.

| Finding | Baseline risk | Minimal correction | Result |
|---|---|---|---|
| `F-P43-001` | browser endpoints returned the access token in JSON and React retained it | access token is removed from browser JSON; same-origin API uses a protected host-only Cookie and rejects cross-origin Cookie mutations | **FIXED** |
| `F-P43-002` | sessions expired but could not be explicitly revoked | idempotent `DELETE /sessions/current` deletes the server verifier and clears the Cookie | **FIXED** |
| `F-P43-003` | recovery-secret rotation left every old short session valid | rotation now deletes all workspace sessions and atomically issues one replacement | **FIXED** |
| `F-P43-004` | raw or encoded capability could enter URL/Referer and default access logging | raw/double-percent-decoded detection fails closed; process logs redact capabilities; production Uvicorn raw access log is disabled | **FIXED** |
| `F-P43-005` | responses lacked one explicit browser exfiltration policy | CSP self-only connect, no-referrer, no-store, HSTS, frame/resource isolation and `Vary: Cookie` are applied globally | **FIXED** |
| `F-P43-006` | frontend and React internals could log raw `Error` objects | all browser console levels redact raw/encoded capabilities and structured values; app handlers emit static codes | **FIXED** |
| `F-P43-007` | no proof covered URL/Referer/log/event/error/cache/screenshot together | final-image Oracle scans all required surfaces, state, audit events and replay behavior | **FIXED** |
| `F-P43-008` | telemetry collection boundary was implicit | dependency/source Gate proves no analytics/error SDK; CSP and browser Oracle allow no foreign HTTP request | **FIXED** |
| `F-P43-009` | strict production CSP correctly blocked TEST-PUB-005's local inline axe injection | only the isolated accessibility-audit BrowserContext bypasses CSP; production headers stay strict | **FIXED** |

P4.3 phase-review open findings: `0` (`9/9` resolved).

## 2. Session and secret-hygiene contract

New browser sessions use one host-only Cookie:

```text
name:      __Secure-kmfa_session
Secure:    true
HttpOnly:  true
SameSite:  Strict
Path:      /public-api/walking-skeleton/v1
Max-Age:   3600 seconds
```

- Create, recovery-code exchange, recovery-file import and secret rotation set
  the Cookie but never return `access_token` in browser JSON.
- Existing bearer capabilities remain accepted for S03/P4.1 compatibility.
  If bearer and Cookie are both present but differ, authorization fails closed.
- Any state-changing request carrying the browser Cookie must have an `Origin`
  whose scheme and host exactly match the request. Same-site sibling origins
  and missing origins fail closed before application state is touched.
- Explicit revoke removes only the presented server-side session verifier and
  clears the matching Cookie. Expired, unknown and already-revoked sessions are
  idempotent; storage failures are not reported as successful revocation.
- Recovery-secret rotation, all old-session deletion, replacement-session
  issue and audit append share one SQLite transaction. Old recovery material
  and every old session replay return 404; workspace, project, progress,
  artifact and recovery assets are not deleted or migrated.
- Raw, percent-encoded and repeatedly decoded `kmfa-r1` / `kmfa-a1`
  capabilities are rejected in query strings and Referers. Log records redact
  recovery codes, access capabilities, Cookie material, bearer values,
  sensitive assignments and exception text.
- The runtime has no third-party analytics/error SDK. `connect-src 'self'`,
  `Referrer-Policy: no-referrer` and static frontend error codes keep the
  browser boundary explicit. Recovery material still appears only where
  intentionally needed: a no-store POST response/body and transient DOM for
  one-time user capture.

## 3. AC-WS-003 final-image evidence

The Dockerfile built the current runtime source and produced local image ID
`sha256:d555a0eee75cbd936e8dfba03dfd29101e5e1f87a0272f7e1f6e100ee724d07f`.
Receipt/HANDOFF-only edits made afterward are not runtime inputs. The Oracle
used synthetic fixtures and an initially empty host state directory.

| Surface / behavior | Observations | Canary hits / result |
|---|---:|---:|
| browser request URLs | `43` | `0` |
| Performance resource URLs | `38` | `0` |
| Referers | `0` because `no-referrer` | `0` |
| browser console redaction canary | `1` synthetic raw-Error attempt | `0` |
| application/browser error samples | `7` | `0` |
| Cache Storage entries | `0` after explicit scan | `0` |
| walking responses | `18`, all `private, no-store` | **PASS** |
| foreign HTTP requests | `0` | **PASS** |
| container/request/application logs | all test container logs | `0` |
| SQLite/WAL/object state and audit events | `1` workspace, `1` object, `14` events | `0` |
| safe screenshot | `1` | `0` |
| persisted result/structured trace | raw capabilities omitted | `0` |

Session/replay thresholds:

```text
Cookie Secure / HttpOnly / SameSite=Strict: true / true / true
Cookie host-only / API Path / document.cookie hidden: true / true / true
browser JSON access_token fields:                  0
rotation old-session replay:                       404
explicit-revoke old-session replay:                404
negative recovery authorization successes:         0
foreign telemetry/network requests:                0
total canary hits:                                  0
```

The same Oracle still proves the P4.2 journey: device A create/save/upload/file
export, database restart, isolated device B file restore/hash download and
secret+session rotation, six invalid/revoked inputs, isolated device C
code restore plus explicit session revoke, Flag `1→0→1` state preservation and
isolated device D replacement-file restore. Object count remains `1`, project
progress remains `64`, and object SHA-256 remains
`501b484cc19f114fdfed29a9f3f31ec5b0cdc3d12a0a8f75a2d21595998af011`.

The CI artifact may contain only `result.json`,
`sanitized-e2e-trace.json` and the safe recovery screenshot. A native browser
trace is deliberately omitted because it would retain capability-bearing DOM
and POST bodies.

## 4. Unit, regression and build gates

```text
P4.3 focused contract tests:        7 passed
P4.1/P4.2/S03 focused regression:  35 passed
all backend tests:                 146 passed
Python compile:                    PASS
Ruff changed-Python check:         PASS
frontend Vite build:               PASS (622 modules)
production Dockerfile build:       PASS
final-image TEST-WS-003 Oracle:    PASS
public shell 4-mode regression:    PASS
3-engine a11y/index regression:    PASS (0 serious/critical; 0 canary hits)
private operations browser flow:   PASS (11/11)
git diff --check:                  PASS
```

Backend runs emit one pre-existing Starlette/httpx deprecation warning. It does
not change behavior or the acceptance result.

## 5. Security review and non-claims

- The E2E scanner keeps raw synthetic capabilities in memory only, removes them
  from result objects before serialization and scans the persisted evidence
  again. No recovery file, secret, access token, Cookie value or native trace is
  committed.
- Existing S03 legacy workspace IDs, schema v1, verifier hashes,
  `kmfa-app-state`, artifacts and the v1.5 recovery bundle remain unchanged.
- No third-party analytics/error SDK exists, so the task stop condition did not
  trigger. A future SDK addition must re-open this Gate and prove it cannot
  collect secrets or file metadata.
- This local final-image proof is not an edge deployment claim. Whole-S04
  review must re-run the Stage gates before any GitHub upload; a later guarded
  rollout must verify the published source/image/deployment tuple separately.
- Named-volume persistence is still only the replaceable early adapter.
  Durable database/object services and backup/restore remain unproved.

## 6. Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=KMFA/app/backend uv run --isolated \
  --no-project --python 3.12 \
  --with-requirements KMFA/app/backend/requirements.txt \
  --with pytest==9.1.1 --with httpx==0.28.1 \
  python -m pytest -q KMFA/app/backend/tests

npm run build --prefix KMFA/app/frontend
docker build -f KMFA/app/backend/Dockerfile -t kmfa-app:p43-final .

state_dir="$(mktemp -d /tmp/kmfa-p43-state.XXXXXX)"
out_dir="$(mktemp -d /tmp/kmfa-p43-evidence.XXXXXX)"
uv run --isolated --no-project --python 3.12 --with playwright==1.60.0 \
  python KMFA/app/e2e/walking_skeleton_flow.py \
  --image kmfa-app:p43-final --state-dir "$state_dir" --out-dir "$out_dir" \
  --container-name kmfa-p34-p43-final --port 18104
```

The Oracle removes only its exact test-prefixed container and never deletes
the supplied state or evidence directory.

## 7. Rollback and next boundary

Code rollback is an ordinary revert of this local phase commit. Runtime rollback
uses the existing `KMFA_WALKING_SKELETON_ENABLED=0` Flag, which preserves all
state while explicit session revoke remains available. A real leakage incident
requires immediate workspace-secret rotation/session revocation and controlled
log/cache cleanup; it never authorizes volume deletion, `down -v`, recovery
replay or force-push.

This is Task `19/56` completed locally; S04 is `3/4` phases complete and the
published Stage remains `4/14`. The next new run may execute only
`S04 / P4.4 / T-S04-04`. Whole-S04 review and GitHub upload remain forbidden
until P4.4 is separately completed and the complete Stage is reviewed/fixed.
