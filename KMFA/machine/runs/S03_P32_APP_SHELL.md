# S03 / P3.2 / T-S03-02 — public App Shell receipt

Status: **LOCAL + IMAGE CANDIDATE PASS; PRODUCTION ORACLE WAITING FOR S03 STAGE RELEASE**
Captured: `2026-07-23T03:50:40+10:00` (Australia/Sydney)
Executor action: `ACT`
Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`
Parent commit: `df885354152d1f9389cf8bfee1bce49a6499bed4`

## 1. Scope and baseline

This receipt closes only `S03 / P3.2 / T-S03-02`. It turns the root entry delivered by P3.1 into an anonymous
public App Shell with six operable navigation entries and explicit normal/degraded/no-JavaScript states, while
preserving the existing private finance dashboard behind the P3.1 operations boundary. It does not implement an
anonymous workspace, real project creation, file upload/download, durable persistence, recovery, workspace
search, user progress, public report export, P3.3, P3.4, whole-S03 review, GitHub upload, deployment or edge
mutation.

The phase began at the local P3.1 candidate above; remote `origin/main` remained
`a991e1b8eade5e852cc750095ffe466bce1d1bb9`. P3.1 had already proved the local root/private routing boundary but
production remained behind the existing host Access wall. This run did not re-label that production state or
claim that an unpushed image was live.

## 2. Implemented candidate

- `/` dynamically loads a dedicated public bundle. The existing ECharts/finance App is code-split and loads only
  for `/ops/app`; public browser oracles observed zero `/api*`, `/ops*` and private `App-*` bundle requests.
- The header, cards and detail panel expose exactly six entries in product order: project, upload, search,
  progress, report and help. Every control selects a real, addressable state. Search performs a real local search
  over the six public descriptions and explicitly excludes workspace/private data.
- Incomplete downstream capabilities are not simulated. Project/upload/progress/report panels say what is not
  connected, do not create fake projects, do not render a file selector, do not write `localStorage`, and do not
  present software readiness as user progress. “No public report” is an explicit empty state.
- The built HTML contains a complete six-entry static shell and `<noscript>` state, so disabled JavaScript never
  produces a blank page. A module-load fallback preserves that shell; a React error boundary renders a visible
  recovery message; failed/timed-out `/healthz` changes the shell to `degraded` while navigation remains usable.
- `KMFA_PUBLIC_SHELL_ENABLED=0` removes the exactly marked enhancement script server-side and serves the stable
  static shell with `X-KMFA-Shell-Mode: stable-static`. It does not change data, routes or the private guard;
  restoring `1` re-enables the public enhancement bundle.
- The old dashboard is preserved at `/ops/app` and `/ops/app/*`. It remains covered by the P3.1 `/ops*` Access JWT
  origin guard; the active legacy full-flow oracle now enters there rather than following `/ui → /` into the
  public shell.
- The public layout uses a compact editorial grid, strong typography and high-contrast actions with reduced-motion
  support and a 390 px responsive layout. It uses only system fonts and inline SVG controls: no external image,
  font, animation runtime or tracking request was added.

## 3. Requirement and Acceptance status

| Contract | Candidate evidence | Result now |
|---|---|---|
| `R-PUB-004 / AC-PUB-004` App Shell | Desktop 1440×1000 and mobile 390×844 exercise all six controls; JavaScript-disabled DOM retains six entries; intercepted `503 /healthz` shows an explicit degraded state and all six controls still work; no blank, permission response, private request or runtime error | **LOCAL + FINAL IMAGE PASS; PRODUCTION WAIT** |
| `R-PUB-002 / AC-PUB-002` anonymous complete journey | No account/email/OAuth control precedes the shell, and P3.2 contributes the six navigation states. The required workspace → project → upload → save → restore → search → download → export journey does not yet exist | **PARTIAL CONTRIBUTION; NOT CLAIMED** |
| Public/private content boundary | Root DOM contains no legacy `BLK-001`, `NO_GO`, Q3 or receivable content; public runtime calls only shallow `/healthz`; `/ops/app` is denied by the production guard without trusted configuration | **LOCAL + FINAL IMAGE PASS** |
| Legacy dashboard compatibility | Existing real flow at `/ops/app`: header, home, receivables, project cost, decision write, impact preview, four-layer rerun, three downloads and schedule health | **11 PASS / 0 WARN / 0 FAIL** |

`AC-PUB-002` must remain open: navigation and honest empty states are not substitutes for the later anonymous
workspace, storage, file and recovery Tasks. `AC-PUB-004` can only be promoted from candidate to production PASS
after the complete S03 review/upload/deploy and bound production Oracle.

## 4. Verification record

| Gate | Result |
|---|---|
| Focused public/private route contract | `11 passed`; root/static rollback, six static entries, GET/HEAD, no account controls, `/ops/app` guard and valid JWT compatibility covered |
| Full backend regression | `97 passed`; no failure after replacing the stale “root is finance dashboard” smoke assertion with the P3.2 public-shell contract |
| Public Playwright oracle | Desktop + mobile + no-JavaScript + degraded = `4/4 PASS`; entries `6/6` in each relevant mode, mobile overflow `0`, public private-plane requests `0`, private bundle requests `0`, anonymous `401/403` responses `0`, page/runtime errors `0` |
| Legacy private App Playwright | isolated temporary state, `11 PASS / 0 WARN / 0 FAIL`; no repository or production state write |
| Frontend build | Vite production build PASS; shared entry `144.90 kB`, public feature chunk `9.65 kB`; private `579.35 kB` dashboard chunk is not requested by `/` |
| Image/container | final local image built from the complete phase worktree; four public browser modes PASS; production guard with absent trust config returns `503` for `/ops/app` and `/api/状态`; disposable container removed |
| Static rollback in built image | `X-KMFA-Shell-Mode: stable-static`, module marker absent after response transform, static entries `6/6`; data and private guard unchanged |
| Compose and changed-code hygiene | Coolify and fallback compose both parse; new/changed test/oracle Python passes Ruff and `py_compile`; `git diff --check` PASS |
| Official + repository taskpack gates | official ZIP hash exact and validator PASS (`49 R / 49 AC / 14 Stages / 56 Tasks`); repository projection PASS (`56 Phases`, `49 trace rows`, gaps `0`); mutation `1 positive + 4 negative`, source unchanged `5/5` |
| Dual plane / public safety | KMFA dual plane PASS; changed-diff secret/private-key/absolute-user-path scan `0`; sealed machine authorities, seven rendered governance files, v1.5 recovery assets and old business facts unchanged |

An ad-hoc Ruff check over the entire legacy `main.py` still reports the same eight `E741` ambiguous single-letter
variables present in the parent commit. The P3.2 delta adds none; broad cleanup is deliberately deferred because
it is unrelated to this phase and all configured regression gates pass.

## 5. Review findings, rollback and next boundary

The phase review found and fixed three candidate issues before closure:

1. Vite initially preloaded the public feature chunk on `/ops/app` because both dynamic imports shared one
   conditional preload wrapper. Separate loader functions now generate correct per-route dependency maps.
2. The visual evidence exposed an off-screen skip link in full-page stitched screenshots. It now uses the standard
   clipped-until-focused accessibility pattern and remains keyboard-visible.
3. Stable rollback copy initially implied the enhancement bundle was still loading. The static state now says
   directly that the six entries remain readable when enhancement is unavailable.

Fast rollback is `KMFA_PUBLIC_SHELL_ENABLED=0` plus the normal reviewed redeploy. It keeps `/` public and useful,
keeps `/api*` and `/ops*` fail-closed, preserves `/ops/app`, and performs no data/schema/recovery rollback. Edge
rollback remains the P3.1 host Owner-Allow restoration and must not disable path applications or origin JWT
validation.

The next run may execute only `S03 / P3.3 / T-S03-03`. P3.4, whole-S03 review, GitHub upload and production edge
mutation remain out of scope. v1.5 recovery assets and all sealed S02 authorities remain untouched.
