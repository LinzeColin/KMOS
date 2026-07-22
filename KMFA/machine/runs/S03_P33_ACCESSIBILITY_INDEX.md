# S03 / P3.3 / T-S03-03 — accessibility and public-index receipt

Status: **LOCAL + FINAL IMAGE CANDIDATE PASS; PRODUCTION SEARCH ORACLE WAITING FOR S03 STAGE RELEASE**
Captured: `2026-07-23T04:35:02+10:00` (Australia/Sydney)
Executor action: `ACT`
Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`
Parent commit: `516bd99c2ebfeefa3e9f5476679fa32bbd2bb025`

## 1. Scope and honest boundary

This receipt closes only `S03 / P3.3 / T-S03-03`. It makes the P3.2 root App Shell responsive and
keyboard/screen-reader testable, adds approved public metadata, and installs a fail-closed crawler/cache boundary
whose only possible index candidate is the canonical root. It does not implement the S08 Publication Gate,
public snapshots, anonymous workspace, real upload/download, persistence/recovery, P3.4, whole-S03 review,
GitHub upload, deployment, Cloudflare mutation, sitemap submission, CDN purge or Google/Bing index mutation.

No production search-engine result is claimed. The unpublished-canary result below is a deterministic local
crawler/index-candidate oracle against the final image. A real external index query remains WAIT until S03 is
reviewed, uploaded and deployed through the ordered guarded rollout.

## 2. Implemented candidate

- The source HTML retains one canonical URL and now carries `robots`, Open Graph, locale, Twitter summary and
  theme metadata. It uses no remote image, font, tracker or third-party share request.
- The interactive and static shells both expose a focus-visible skip link whose target can receive focus. Module
  cards have concise accessible names; the trust strip is a real list; search results are a labelled live region;
  and asynchronous system state is a polite atomic status.
- The initial serious boundary-kicker contrast defect is fixed. A non-essential card color transition that
  produced transient white-on-light text was removed instead of being excluded from axe.
- `KMFA_PUBLIC_INDEXING_ENABLED` is an explicit promotion gate. Its production/compose default is `0`, and
  only `1/true/yes/on` enable it; missing, empty and typo values all fail closed.
- Hold mode keeps `/` human-readable with `200`, but changes both the HTML meta and response header to
  `noindex,nofollow,noarchive`, serves a full-disallow `robots.txt`, and serves an empty sitemap.
- Promoted mode allows only exact `/` plus its hashed render assets and crawler control files. The sitemap
  contains exactly `https://kmfa.linzezhang.com/`. Adding another application route cannot place it in either
  control file.
- Every non-root application response, including private paths, redirects, health, unknown 4xx/5xx and guarded
  errors, receives `X-Robots-Tag: noindex, nofollow, noarchive`. Non-asset responses also receive
  `private, no-store` unless an existing `no-store` is already stronger. Hashed assets retain immutable caching
  and receive noindex; robots/sitemap require revalidation so rollback is not held by the app cache.
- CI now runs TEST-PUB-005 with Playwright `1.60.0`, the current official PyPI release at capture, rather than
  the inherited `1.49.0`. `axe-core 4.12.1` is a build/test-only dependency and is absent from the final image.

## 3. Requirement and Acceptance status

| Contract | Candidate evidence | Result now |
|---|---|---|
| `R-PUB-005 / AC-PUB-005 / TEST-PUB-005` | Chromium 148, Firefox 150 and WebKit 26.4; six desktop module states per engine; 390 px per engine and 320 px Chromium; axe WCAG 2.0/2.1/2.2 A/AA; keyboard and accessible-name contract; crawler simulation | **LOCAL + FINAL IMAGE PASS; PRODUCTION WAIT** |
| Critical/serious accessibility threshold | 22 axe runs; all violations `0`, incomplete checks `0`, therefore critical/serious `0` | **PASS** |
| Core keyboard flow | Focus-visible skip link reaches main; project/upload/search/progress/report/help operate in order in all three engines. macOS WebKit adaptively uses Option+Tab when its full-keyboard setting requires it | **6/6 × 3 PASS** |
| Responsive boundary | 390×844 in all engines and 320×700 in Chromium; document horizontal overflow `0`; six controls stay inside the viewport and exceed the 24 px WCAG 2.2 target floor | **PASS** |
| Unpublished canary index boundary | Not in sitemap; denied by robots; HTTP `404`; response noindex; response no-store; local index-candidate hits `0` | **PASS (0 hits)** |
| Real external search index | No candidate was deployed or submitted in this phase | **WAIT — NOT CLAIMED** |

## 4. Verification record

| Gate | Result |
|---|---|
| Focused public/index contract | `15 passed`; includes default hold, promoted root-only mode, typo fail-closed, metadata, private/error/cache controls and deployment defaults |
| Full backend regression | `101 passed`; one existing TestClient deprecation warning, no failure |
| Current three-browser accessibility oracle | Playwright `1.60.0`; Chromium `148.0.7778.96`, Firefox `150.0.2`, WebKit `26.4`; axe-core `4.12.1`; 22 runs, violations `0`, incomplete `0` |
| Public App Shell regression | Desktop + 390 px mobile + JavaScript-disabled + intercepted shallow-health degradation = `4/4 PASS`; private requests, permission responses and runtime errors `0` |
| Legacy private App regression | Final image, isolated disposable state: `11 PASS / 0 WARN / 0 FAIL` |
| Crawler negative oracle | root allowed and canonical; `/api`, `/ops/app`, `/ui`, `/healthz` and synthetic unpublished canary denied; canary index hits `0`; no private response body written to artifacts |
| Final-image promotion mode | self-contained local arm64/Linux image; three-browser TEST-PUB-005 PASS and public shell `4/4`; local candidate is not a production release identity |
| Final-image hold rollback | human root `200`; header noindex; HTML meta noindex; robots full disallow; sitemap locations `0` |
| Final-image production guard | with origin guard enabled and trust config absent, four private routes return `503` plus no-store and noindex; root remains `200` |
| Build/deployment hygiene | Vite production build PASS; fallback and Coolify compose parse; focused Ruff/py_compile and `git diff --check` PASS |
| Dependency boundary | `npm audit --omit=dev`: `0` production vulnerabilities. Full audit still reports inherited Vite/esbuild dev-server advisories; no dev server or node_modules ships in the multi-stage image, and this phase does not take a risky Vite major upgrade |
| Official + repository taskpack | official ZIP SHA and ZIP integrity PASS; official validator `49 R / 49 AC / 14 Stages / 56 Tasks`; repository validator PASS; mutation `1 positive + 4 negative`, source unchanged `5/5` |
| Dual plane / sealed safety | KMFA dual plane PASS; sealed Canonical/AC/DAG/Trace sources, seven rendered governance files, old business facts and v1.5 recovery assets unchanged |

Browser screenshots and machine-readable axe/crawler results were generated only in disposable local/CI artifact
directories. They contain the intentional public homepage and a synthetic canary, not user files, private API
bodies, credentials or unpublished business values; they are not committed into the public repository.

## 5. Phase review findings and fixes

The P3.3 phase review found and fixed six issues before closure:

1. The page initially had one serious axe contrast violation in the orange boundary kicker.
2. Card state animation could create a transient serious white-on-light contrast failure.
3. Two labelled plain `div` elements needed real list/region roles, and the async health card needed status
   semantics.
4. The skip link target was not programmatically focusable and mobile health text needed an explicit name.
5. The first indexing-flag parser would have treated an unknown typo as enabled; only four explicit true values
   now promote indexing.
6. The inherited Playwright 1.49 browser set was too old to represent mainstream 2026 engines; CI and final
   evidence now use Playwright 1.60.0.

No open P3.3 finding remains. This is a phase review only, not the required whole-S03 review after P3.4.

## 6. Rollback and next boundary

The fastest SEO rollback is `KMFA_PUBLIC_INDEXING_ENABLED=0` plus the normal reviewed redeploy. It keeps the
human homepage available, removes every sitemap URL, serves full-disallow robots, and applies header + meta
noindex without changing data, private guards or the App Shell. The independent UI rollback remains
`KMFA_PUBLIC_SHELL_ENABLED=0`. A later public-edge rollback must restore the host Owner-Allow policy and must
not remove path applications or disable origin JWT validation.

The next run may execute only `S03 / P3.4 / T-S03-04`. Whole-S03 review, GitHub upload, production deployment,
external index query and edge mutation remain out of scope until that ordered work completes. v1.5 recovery
assets and all sealed S02 authorities remain untouched.
