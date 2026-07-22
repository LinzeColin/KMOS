# S03 / P3.1 / T-S03-01 — root and edge routing receipt

Status: **LOCAL IMPLEMENTATION PASS; production Oracle WAITING FOR S03 STAGE RELEASE**
Captured: `2026-07-23` (Australia/Sydney)
Executor action: `ACT`
Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`
Parent commit: `a991e1b8eade5e852cc750095ffe466bce1d1bb9`

## 1. Scope and verified baseline

This receipt closes the local implementation unit for `S03 / P3.1 / T-S03-01` only. It implements the
root-domain/legacy-route contract, separates the public entry plane from the private operations plane, adds an
origin-side Access verifier, and records the safe edge apply/rollback sequence. It does not start P3.2, redesign
the App Shell, make existing financial APIs public, change database/object/recovery behavior, apply a production
Cloudflare mutation, upload GitHub, trigger Coolify, or claim whole-S03/GA acceptance.

The fresh pre-release production Oracle remains a real failure: anonymous GET and HEAD for `/`, `/ui`, `/ui/`,
an error canary, `/api/状态` and `/ops/healthz` all return `302` to the known Cloudflare Access login host. The
deployed identity therefore remains source `68306e850fa66ffe6b53622915ca81ff8ba98bf8`, image
`sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841`, deployment
`boh5fsnxe82umwcpqzooam1p`, completed `2026-07-22T11:39:29.000000Z`. The Owner-supplied older tuple remains a
historical rollback point and was not relabelled as current.

## 2. Implemented candidate

- `/` now directly serves the built App HTML for GET/HEAD with `200` and no redirect. Vite assets moved from
  `/ui/assets/*` to `/assets/*`; the local `.app` launcher also opens `/`.
- `/ui`, `/ui/` and stale `/ui/...` deep links accept GET/HEAD only as compatibility aliases and return one
  `308` hop to `/`.
- canonical, `og:url` and the one-entry sitemap all name `https://kmfa.linzezhang.com/`; the public `/healthz`
  returns only `{"status":"ok"}` and unknown paths remain safe `404` responses.
- OpenAPI and Swagger moved to `/ops/openapi.json` and `/ops/docs`; deep health moved to `/ops/healthz`.
  Existing `/api*` and all `/ops*` are the private operations plane.
- Production compose enables `KMFA_PRIVATE_OPS_REQUIRE_ACCESS=1`. The origin verifies
  `Cf-Access-Jwt-Assertion` with the team JWKS, fixed `RS256`, issuer, one-of configured Audience tags, expiry and
  signature. Missing/invalid config returns generic `503`; missing, wrong-audience, malformed or forged JWT
  returns generic `403`; both are `no-store`. An unset guard remains explicit local-development mode only.
- The edge runbook preserves the current host application as an atomic rollback lever, adds more-specific
  applications for `/api`, `/api/*`, `/ops`, `/ops/*` first, deploys the origin guard second, and only then changes
  the host application to `Bypass / Include Everyone`. This ordering avoids a window where private APIs are public.

The implementation follows Cloudflare's primary documentation for
[path precedence and parent-path coverage](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/app-paths/),
[Bypass semantics](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/) and
[cryptographic origin validation/JWKS rotation](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/).

## 3. Requirement / Acceptance status

| Contract | Candidate evidence | Result now |
|---|---|---|
| `R-PUB-001 / AC-PUB-001` root entry | Real local HTTP GET/HEAD `/ = 200`, no Location; Playwright final URL `/`, rendered `#root`, expected title and canonical | **LOCAL PASS** |
| `R-PUB-003 / AC-PUB-003` route convergence | GET/HEAD `/ui` and `/ui/` each produce exactly `308 → / → 200`; sitemap/canonical/share contain root only; error canary `404`, loop `0` | **LOCAL PASS** |
| Private operations canary | Production-mode container leaves `/` and `/healthz` at `200` while missing trusted config blocks `/api/状态` and `/ops/openapi.json` at `503`; valid/invalid signed-JWT cases are unit tested | **LOCAL PASS** |
| Production Oracle | Fresh anonymous production GET/HEAD still sees Access `302` before this unpushed candidate | **FAIL / EXPECTED UNTIL STAGE RELEASE** |
| Loginless complete product journey | P3.2 and later storage/file tasks are intentionally not implemented here | **NOT EVALUATED IN P3.1** |

Task completion here means a verified, locally committed P3.1 release candidate. AC-PUB-001/003 cannot be
promoted to production PASS until the complete S03 Stage is reviewed, uploaded once, deployed with trusted
Access settings, edge paths are applied, and the same anonymous Oracle is replayed against the bound deployment.

## 4. Verification record

| Gate | Result |
|---|---|
| Focused + full backend regression | `94 passed`; valid JWT, forged signature, wrong audience, malformed token, missing/invalid config and public/private path split included |
| Real curl contract | `/` GET/HEAD `200`; `/ui` and `/ui/` GET/HEAD `308 → /`; missing `404`; public health `200`; old OpenAPI `404`; private OpenAPI under `/ops` |
| Focused Playwright | root title/DOM/canonical PASS; both aliases produced exactly `[308, 200]`; error `404`; Access document redirects `0` |
| Existing full App Playwright flow | `11 PASS / 0 WARN / 0 FAIL`; test writes isolated under `/tmp`, not repository/production state |
| Frontend | clean `npm ci && npm run build`; committed dist uses `/assets/*`; production dependency audit `0` vulnerabilities |
| Backend supply chain | resolved requirements audit: no known vulnerabilities |
| Image and compose | both compose files parse; multi-stage Docker build PASS; built container gives root `200`, legacy `308`, unconfigured private canaries `503` |
| Taskpack/repository gates | official taskpack `49 R / 49 AC / 14 Stages / 56 Tasks` PASS; repository projection PASS; required mutation `1 positive + 4 negative`; trace completeness `100%`, gaps `0` |
| Dual plane and legacy governance | auto-discovered five-project dual plane PASS; exact seven-file budget/purity PASS; one existing blocker and no duplicate re-audit |
| Mutation boundary | no production/platform/database/object/recovery write; no GitHub push; production tuple unchanged |

## 5. Release, rollback, stop and next boundary

S03 release must keep the current host Access policy until the guarded image is healthy and all four exact/wildcard
private patterns are active. It then changes only the host policy to public Bypass and runs the anonymous
GET/HEAD/Playwright/private-canary Oracle. Any public private-path response, root login redirect, redirect loop,
untrusted JWT acceptance, missing Audience tag, deployment mismatch or private-data finding is a STOP.

Fast edge rollback is to restore the host application's previous Owner Allow policy. The path applications and
origin JWT guard stay enabled; no data/schema/recovery rollback is involved. Code rollback is an ordinary revert
of the P3.1 commit followed by the normal reviewed Stage release path, never ref rewriting or guard disablement.

The next run may execute only `S03 / P3.2 / T-S03-02`. P3.3, P3.4, whole-S03 review, GitHub upload and production
edge mutation remain out of scope until their ordered runs. v1.5 recovery assets and all sealed S02 authorities
remain untouched.
