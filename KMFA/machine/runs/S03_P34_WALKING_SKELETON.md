# S03 / P3.4 / T-S03-04 — recoverable-file Walking Skeleton receipt

Status: **LOCAL + FINAL IMAGE CANDIDATE PASS; PRODUCTION ORACLE WAITING FOR S03 STAGE REVIEW/RELEASE**
Captured: `2026-07-23T05:27:47+10:00` (Australia/Sydney)
Executor action: `ACT`
Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`
Parent commit: `2e6a0e9ee2c5089e1b5b95bedf6edee303f4d772`
Verified local application image ID: `sha256:b643fda004340295ea06ef3554ec65f490b6b3630f97a226634bd6caa7aa3810`

## 1. Scope and honest boundary

This receipt closes only `S03 / P3.4 / T-S03-04`, implementing `R-QA-001 / AC-QA-001 /
TEST-QA-001`. It proves one real anonymous server-side journey:

`/` → create workspace → save project/progress → upload one synthetic binary → restart the app container →
recover in a new browser context → download and compare SHA-256 → turn the Feature Flag off → prove the root
still works and state is unchanged → turn it back on and recover/download again.

It does not complete S04-S07, whole-S03 review, GitHub upload, production deployment, durable database service,
S3-compatible object storage, cross-node persistence, backup/restore, RPO/RTO, recovery-file rotation/revocation,
malware scanning, rate limits, multi-file lifecycle, scores, explicit deletion or GA. The local named-volume adapter
is a real non-browser persistence mechanism, but it is deliberately labelled an early replaceable adapter rather
than falsely claimed as long-term production durability.

No real user file, project name, recovery material, credential, business value or private API body was used or
committed. Browser/CI evidence uses only the deterministic `P3.4` synthetic canary and aggregate hashes.

## 2. Failed baseline

Before implementation:

- `GET /public-api/walking-skeleton/v1/status` returned `404`.
- The public frontend contained no file input or recoverable workspace interaction.
- The Coolify App service had no `/var/lib/kmfa/state` mount.
- No `TEST-QA-001` executable existed.

The baseline therefore contradicted every P3.4 journey step; an existing SQLite module for private operational
events did not prove anonymous workspace or file durability.

## 3. Implemented candidate

- `KMFA_WALKING_SKELETON_ENABLED` defaults to `0`; only `1/true/yes/on` enable it. Missing, empty and typo
  values fail closed. Disabled mode keeps `/` available, removes create/recover/upload/download UI, returns `404`
  for state actions and does not delete or mutate the mounted state.
- Public APIs live under `/public-api/walking-skeleton/v1`, outside the guarded private `/api*` and `/ops*`
  namespaces. They remain denied by robots and receive `X-Robots-Tag: noindex, nofollow, noarchive` plus
  `private, no-store` from the existing public-index boundary.
- Each workspace gets an opaque 96-bit identifier, one 256-bit recovery capability and 256-bit one-hour access
  capabilities. Only SHA-256 capability hashes are stored server-side; no cookie, account, email, OAuth,
  `localStorage` or `sessionStorage` is used. Invalid workspace/capability combinations share the same 404 result.
- SQLite stores the early workspace, project name, 0–100 progress, artifact index, hashed capabilities and
  append-only audit events. UPDATE/DELETE triggers protect audit history. User artifact bytes remain outside the
  database under a private random object name.
- The upload accepts any file type but is intentionally limited to one artifact and 8 MiB for this skeleton.
  Original bytes are streamed to a `0600` temporary file, bounded while streaming, fsynced and atomically renamed;
  database insertion follows in a transaction. A second file never overwrites the first, and failed/oversize writes
  leave no `.part` or orphan object.
- Original filenames are decoded from an encoded header, normalized and rejected on path separators/control
  characters. Objects are not routed through `/assets` or another public bucket/path. Unknown/dangerous extensions
  are never executed or previewed and always return `application/octet-stream`, attachment disposition,
  `nosniff`, no-store and the recorded SHA-256.
- Before each download the server rehashes the private object and fails closed on a size/hash mismatch. The browser
  then hashes the received Blob with Web Crypto and refuses to save it unless database, response-header and actual
  byte hashes agree.
- Both the repository compose and Coolify compose mount `kmfa-app-state:/var/lib/kmfa/state`; ordinary restart,
  redeploy and Flag rollback preserve this volume. The runbook explicitly forbids normal rollback via
  `docker compose down -v`.

## 4. Acceptance and verification record

| Gate | Result |
|---|---|
| Focused backend contract | `16 passed`; flag default/typo, hashed capabilities, auth, project/progress, arbitrary binary, attachment headers, recovery, rollback preservation, oversize/traversal/orphan prevention, integrity failure, append-only audit, GET no-business-mutation, origin guard separation, explicit storage-unavailable 503, no public object route, token expiry and compose defaults |
| Full backend regression | `117 passed`; one inherited Starlette TestClient deprecation warning, no failure |
| Final-image TEST-QA-001 | PASS on application image `sha256:b643fda0…3810`; create/save/upload/restart/new-context recovery/download/Flag off/re-enable all executed against the container and mounted state. This local identity is not a production release identity; this receipt identity line was recorded after the runtime/config sources were frozen and built |
| Upload/download equality | Synthetic bytes `4,892`; upload, stored object, first post-restart download and post-rollback re-enable download all SHA-256 `501b484cc19f114fdfed29a9f3f31ec5b0cdc3d12a0a8f75a2d21595998af011` |
| Restart durability | Docker container restarted; project `P3.4 重启恢复 canary`, progress `64`, one DB artifact record and one private object remained and were recovered in a fresh browser context |
| Rollback event | Flag `1→0`: root `200`, UI `rollback`, create form `0`, recovery HTTP `404`, DB row counts unchanged, object hash unchanged; Flag `0→1`: recovery and equal-hash download PASS |
| Audit/monitoring | Ordered actions contain `workspace_created`, `workspace_saved`, `artifact_uploaded`, `workspace_recovered`, `artifact_download`; status reports adapter/schema/limit/hardening without paths, counts or user content |
| Secret/browser hygiene | recovery capability state-file hits `0`, container-log hits `0`, URL hits `0`; browser cookies/localStorage/sessionStorage all `0` |
| Existing public shell | Desktop + 390 px + no-JavaScript + shallow-health degradation = `4/4 PASS`; private requests, permission errors and runtime errors `0` |
| Accessibility/index regression | Playwright Chromium/Firefox/WebKit; 22 axe runs, critical/serious `0`; unpublished canary index hits `0` |
| Existing private App | Final image isolated regression `11 PASS / 0 WARN / 0 FAIL` |
| Build/deployment | Vite production build PASS; image frontend built from current source; repository and Coolify compose both parse PASS |
| Dependency/taskpack/governance | `npm audit --omit=dev`: production vulnerabilities `0`; official ZIP SHA `310885…cffb`, ZIP integrity PASS, 42 manifest hashes match; official and repository validators PASS (`49 R / 49 AC / 14 Stages / 56 Tasks`, repository receipts `22`); mutation `1 positive + 4 negative`, source unchanged `5/5`; dual plane PASS |

Complete screenshots and `result.json` are generated only into disposable local/CI artifact directories. The
repository keeps this compact receipt, not an `EVIDENCE/` tree or runtime state database.

## 5. Phase review findings and fixes

P3.4 self-review found and fixed the following before closure:

1. The first new UI used `aria-label` on two plain `div` elements. The three-browser axe run reported serious
   `aria-prohibited-attr`; they now use `group` and `list/listitem` semantics, and the full 22-run oracle is green.
2. A server hash header alone would not prove the browser received the same bytes. The download UI now computes
   SHA-256 over the received Blob before saving; the Docker E2E independently hashes the saved download.
3. The legacy repository compose build context did not match the self-contained Dockerfile. P3.4 aligns it to the
   repository root and replaces the obsolete read-only repository mount with the named state volume.
4. The rollback proof was strengthened from “API disabled” to a full `1→restart→0→1` sequence with logical DB
   row equality, object hash equality, root availability and renewed recovery/download.
5. Storage-open/write failures could otherwise surface as an opaque 500, and cleanup after an ambiguous late error
   could remove a registered object. Store errors now become an explicit no-detail `503`; object cleanup is allowed
   only before the DB transaction commits, preserving recovery over cosmetic response success.

No open P3.4 finding remains. This is a phase review only; it is not the required whole-S03 review.

## 6. Residual risks and next boundary

The named-volume SQLite/filesystem adapter is intentionally single-node and has no backup/restore proof. Its
recovery capability cannot yet be rotated or revoked, access tokens have no active revocation UI, and recovery has
no rate limit/challenge. File malware/quarantine, multipart/resumable upload, range download, production object
versioning, reconciliation, lifecycle deletion and real capacity thresholds are absent. These are explicit S04-S07
work, not hidden exceptions.

Production remains unchanged and behind its current host Access wall; no GitHub upload, Coolify deployment,
Cloudflare mutation or production user journey was performed. The next run must be the whole-S03 review across
P3.1-P3.4. Only after that review finds/fixes all issues may S03 be uploaded once and follow the guarded rollout;
P4.1 must not start first.
