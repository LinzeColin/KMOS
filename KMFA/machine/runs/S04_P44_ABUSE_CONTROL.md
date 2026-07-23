# S04 / P4.4 / T-S04-04 — anonymous abuse-control receipt

Status: **LOCAL PHASE PASS — NOT STAGE-REVIEWED, NOT PUBLISHED, NOT DEPLOYED**

Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`
Parent commit: `08641fb34175f218ec8bd559b295fc0a37ae09b5`
Requirement / acceptance / test: `R-WS-004 / AC-WS-004 / TEST-WS-004`

## 1. Scope and fixed findings

This receipt closes only `S04 / P4.4 / T-S04-04`. It adds bounded,
production-configured anonymous admission control, actor challenges, hard
business-state ceilings, aggregate operational evidence and attack generators.
It does not claim whole-S04 review, GitHub upload, edge-WAF mutation,
production deployment, measured production demand/SLO, S05 durability, S06
malware handling or GA.

| Finding | Baseline/review risk | Minimal correction | Result |
|---|---|---|---|
| `F-P44-001` | anonymous APIs had no production abuse-control policy | add one versioned policy for identity, recovery, mutation, upload, export, read and unknown operations | **FIXED** |
| `F-P44-002` | workspaces, sessions, artifact bytes and audit rows could grow for the process lifetime | add transactional hard ceilings, deterministic session eviction and storage reserve checks | **FIXED** |
| `F-P44-003` | attacker-selected identifiers could grow limiter state independently of service capacity | admit against global windows first, expire counters and bucket bounded aggregate events | **FIXED** |
| `F-P44-004` | a concurrency check could release before a streamed response completed | hold the persistent lease through the final ASGI body/path-send, with TTL recovery | **FIXED** |
| `F-P44-005` | initial response-header mutation used an unsupported `MutableHeaders` operation | use supported case-insensitive deletion and cover the runtime path | **FIXED** |
| `F-P44-006` | fail-closed control storage could mask the pre-existing invalid-state-root error contract | delegate only when the configured business root itself is a non-directory; otherwise fail closed | **FIXED** |
| `F-P44-007` | the initial upload actor threshold challenged a normal negative-validation fixture | retain global/concurrency/hard ceilings while allowing six short-window device/workspace attempts | **FIXED** |
| `F-P44-008` | the initial recovery IP threshold could penalize independent devices behind one NAT | make IP budgets deliberately broader than device budgets; strict device/global budgets remain | **FIXED** |
| `F-P44-009` | API tests did not prove that a real browser could solve and retry the challenge | add a Chromium Oracle for in-memory proof-of-work and one automatic retry | **FIXED** |
| `F-P44-010` | same-second session issuance broke “oldest session” eviction ties with a random token hash | break equal-time ties by SQLite insertion order and run the focused suite three times | **FIXED** |

P4.4 phase-review open findings: `0` (`10/10` resolved).

## 2. Policy, challenge and isolation contract

Policy `p44-v1` has independent `10s` and `1h` windows and four scopes:
trusted-edge IP HMAC, protected device-cookie HMAC, workspace HMAC where
applicable, and global. Raw IP, device, workspace, session, filename and
recovery values are never stored in the control database.

- `identity`, `recovery`, `mutation`, `upload`, `export`, `read` and unknown
  operations have separate budgets. Shared-NAT IP limits are wider than device
  limits; upload and export have global concurrency budgets `2` and `4`.
- Actor/workspace exhaustion returns a `90s`, one-use, SHA-256 leading-zero
  proof challenge at difficulty `11`. The signed challenge is bound to policy,
  actor, workspace context and operation. Replay, cross-actor and
  cross-operation use fail closed.
- A proof may pass only an actor-local threshold. Global rate and concurrency
  budgets are never challenge-bypassable.
- Request classification and admission occur before body streaming. A
  concurrency lease remains held until the complete response is sent.
- `__Host-kmfa_device` is Secure, HttpOnly, SameSite=Strict, Path `/`, with a
  30-day maximum age. It is an abuse signal, not an authentication credential.
- Control state is separate under `abuse-control/`, with `0700` directory and
  `0600` database/key permissions. Rate counters and challenge uses expire;
  decision windows and capacity-alert deduplication retain only bounded,
  hashed aggregates. The private `/ops/abuse-control/status` route publishes
  aggregates only and remains behind the existing operations boundary.
- Hard business ceilings are `10,000` workspaces, `8` active sessions per
  workspace, `512 MiB` total artifacts, `128 MiB` minimum free state space,
  `10,000` audit events per workspace and `250,000` audit events total. A
  rejected write rolls back without deleting existing workspace/recovery data.
- Production default is `KMFA_ABUSE_POLICY_MODE=enforced`. Unknown values fail
  all guarded operations closed. The emergency rollback mode exempts low-cost
  read/mutation operations while continuing to control identity, recovery,
  upload and export. The root page and shallow Walking Skeleton status remain
  browsable even if admission control is unavailable.

No account, email or OAuth step is introduced.

## 3. AC-WS-004 final-image evidence

The Dockerfile built the final runtime source and produced local image ID
`sha256:63e37f8940f2e93040efe7d0c0ae5856bfaac03c9b2c4305f870f0c40dea8e65`.
Only this receipt and HANDOFF were edited afterward; they are not runtime
inputs. All traffic and stored values below are synthetic.

| Fixture / attack | Final observation | Result |
|---|---|---|
| normal anonymous fixture | `20` actors, `100` requests, false positives `0` (`0%`); p50 `12.43ms`, p95 `17.33ms`, max `20.57ms` | **PASS** |
| brute recovery enumeration | first `6` retained uniform `404`; attempt `7` challenged; valid proof reached the same `404`; replay and cross-actor proof both `403`; authorization successes/bypasses `0/0` | **PASS** |
| browser challenge | `7` creates completed with one challenge and automatic in-memory solve/retry; account prompts `0`, console sensitive hits `0` | **PASS** |
| upload flood | `7` attempts produced `1` object, `5` deterministic business rejections and `1` challenge | **PASS** |
| export flood | `6` exports served, attempt `7` challenged; public root/status remained `200/200` | **PASS** |
| real concurrency flood | `6` parallel uploads against budget `2`: admitted `2`, capacity-blocked `4`; after lease release retry returned `200` | **PASS** |
| distributed low-speed | `600` unique-actor requests allowed at `5s` simulated spacing; request `601` globally blocked with no proof bypass; next window recovered | **PASS** |
| post-attack browsing | root/status `200/200`; root snapshot latency `3.33ms` | **PASS** |

The distributed generator produced `405` live counter rows against a
calculated bound of `1,832`; no raw identifier was stored. The complete
synthetic run ended with:

```text
business: workspaces=34, active_sessions=28, artifacts=4,
          artifact_bytes=1,310,745, audit_events=70
control:  rate_counters=405, concurrency_leases=0, challenge_uses=2,
          decision_metrics=15, decision_windows=58, capacity_alerts=1
state:    files=11, bytes=1,626,169, raw_sensitive_hits=0,
          capability_pattern_hits=0, resource_growth_bounded=true
runtime:  memory=44.03MiB, PIDs=7 (single local snapshot; not a production SLO)
```

Attack bypasses were `0`, normal false positives were below `1%`, no
unbounded growth was observed, and public browsing stayed available.

## 4. Recovery, privacy and product regressions

The same exact image re-ran the P4.2/P4.3 Oracle:

```text
valid recovery consistency:                   100%
invalid authorization successes:             0
restart / Flag re-enable object SHA-256:      501b484cc19f114fdfed29a9f3f31ec5b0cdc3d12a0a8f75a2d21595998af011
rotation old-session replay:                  404
explicit revocation replay:                   404
URL/Referer/console/error/cache canary hits:  0
container-log/state/screenshot canary hits:   0
foreign browser requests:                     0
Flag rollback state/hash unchanged:           true
```

Public App Shell desktop/mobile/no-JavaScript/degraded modes all passed with
six entries, zero private requests and zero permission/runtime errors.
Chromium/Firefox/WebKit accessibility/index checks reported zero
serious/critical findings and zero unpublished-canary index hits. The private
operations browser audit passed `11/11`; the final service log scan found zero
capability values.

## 5. Verification gates

```text
P4.4 focused contract tests:            10 passed × 3 consecutive runs
P4.1-P4.3 focused regression:           42 passed
all backend tests after final fix:      156 passed
Python compile:                        PASS
Ruff changed-Python checks:            PASS
frontend Vite build:                   PASS (622 modules)
production Dockerfile build:           PASS
final-image TEST-WS-004 Oracle:        PASS
final-image P4.2/P4.3 Oracle:          PASS
public shell 4-mode regression:        PASS
3-engine a11y/index regression:        PASS
private operations browser flow:       PASS (11/11)
taskpack validator:                    PASS (49/49, 14/56/56, 0 warnings)
validator mutation suite:              PASS (1 positive, 4 negative)
dual-plane CI checker:                 PASS (5 projects)
git diff --check:                      PASS
```

Backend runs emit one pre-existing Starlette/httpx deprecation warning. It
does not change the acceptance result.

## 6. Evidence safety and non-claims

- The attack Oracle keeps device/session/recovery/proof values in memory,
  persists only a compact `result.json`, and scans state, logs and evidence for
  raw fixtures and capability patterns. Hits were `0`.
- Existing S03 legacy workspace IDs, schema v1, verifier hashes, artifacts,
  named volume and v1.5 recovery assets are not migrated, replayed, rewritten
  or deleted.
- This is a production-configured application-layer equivalent to the required
  limiter/WAF behavior. It does not claim a Cloudflare WAF rule change. Edge
  tuning and real traffic/cost observations remain release work.
- The evidence is a bounded local attack run, not an assertion about
  unmeasured production demand or a long-window production SLO.
- Named-volume/SQLite/file storage remains the early adapter. Durable database
  and object services, backup/restore, explicit deletion lifecycle, arbitrary
  multi-file lifecycle and malware isolation remain later Stages.

## 7. Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=KMFA/app/backend uv run --isolated \
  --no-project --python 3.12 \
  --with-requirements KMFA/app/backend/requirements.txt \
  --with pytest==9.1.1 --with httpx==0.28.1 \
  python -m pytest -q KMFA/app/backend/tests

docker build -f KMFA/app/backend/Dockerfile -t kmfa-app:p44-final .

state_dir="$(mktemp -d /tmp/kmfa-p44-state.XXXXXX)"
out_dir="$(mktemp -d /tmp/kmfa-p44-evidence.XXXXXX)"
uv run --isolated --no-project --python 3.12 --with playwright==1.60.0 \
  python KMFA/app/e2e/abuse_control_flow.py \
  --image kmfa-app:p44-final --state-dir "$state_dir" --out-dir "$out_dir" \
  --container-name kmfa-p44-e2e --port 18105
```

The Oracle removes only its exact test-prefixed container. It never deletes
the supplied state/evidence directory or a production volume.

## 8. Rollback and next boundary

Policy rollback uses `KMFA_ABUSE_POLICY_MODE=emergency-expensive-only`;
complete Walking Skeleton rollback uses
`KMFA_WALKING_SKELETON_ENABLED=0`. Code rollback is an ordinary revert of
this local phase commit. None authorizes `down -v`, object/state deletion,
recovery replay, force-push or a login wall.

This is Task `20/56` completed locally; S04 is `4/4` phases complete and the
published Stage remains `4/14`. The next new run may perform only the
whole-S04 review, fix any cross-phase findings, and upload the complete Stage
after all gates pass. It must not start S05 or treat this local image as a
production deployment.
