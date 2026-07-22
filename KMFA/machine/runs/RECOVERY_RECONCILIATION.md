# KMFA v1.5.2 RECOVERY RECONCILIATION

> Task `T-S00-02` / Phase `P0.2 恢复核对`
> Acceptance `AC-GOV-001` / Test `TEST-GOV-001`
> Captured: `2026-07-22T12:05:46Z`
> Closed: `2026-07-22T12:27:30Z`
> Status: **DONE — AC-GOV-001 PASS**

本文是不超过 64 KiB 的 public-safe compact receipt。完整历史 ZIP、Git bundle、full-sweep 明细和私有冗余资产保持原位，只记录非秘密身份、集合计数、摘要、处置与复跑边界；本文件不是新的产品事实源或恢复副本。

## 1. 四方结论

| Subject | VERIFIED identity | Relationship / decision |
| --- | --- | --- |
| Current main | `LinzeColin/KMOS@68306e850fa66ffe6b53622915ca81ff8ba98bf8`; tree `8ee9c56f4d54fee812e7efc2a0164d064a290979` | **Adopt** as the only writable source baseline |
| Current production | image `sha256:adfc849b24e2efc471706c718377c97df07b41b4ce921f972e0cf598b0e25841`; deployment `boh5fsnxe82umwcpqzooam1p`; source `68306e8...` | **Adopt** as the production comparison subject; source equals current main |
| v1.5 recovery | immutable bundle checkpoint `1ee7fb111075225dc39039263d2681a0c0acd155`; public recovery tip `268acce7924d13dd6481b50af7f57d2d2ede81ed` | **Adopt only as protected read-only evidence**; never replay/merge wholesale |
| History | acceptance reference `e0e31fc...`; v1.4.2 `e822c98...`; v1.4.1 index `2d5fa2a...`; pre-v0.1 index | Selective Adopt/Redo/Discard per section 5; never current authority |

P0.1 already proved the current source → image → deployment chain. During P0.2 the latest successful deploy remained run `29916233128` at source `68306e8...`; no later `main` or production subject appeared.

## 2. Commit graph and recovery asset preservation

```text
historical CodexProject recovery lineage

97edb1b8750d49409a4f9372a784d4772fea258e  baseline
  └─ 1ee7fb111075225dc39039263d2681a0c0acd155  bundled checkpoint; 764 changed paths
       └─ 1926014cf272257b0017a894cbe703e8124a06aa  cross-log exact recovery
            └─ 268acce7924d13dd6481b50af7f57d2d2ede81ed  current public recovery tip; PARTIAL

lost original final: 13921decb26ac72445f1b4bc22551d164eedcb1b  (not found; no edge invented)
current canonical:   KMOS@68306e850fa66ffe6b53622915ca81ff8ba98bf8 → production image adfc849b...
```

- `KMFA_v15_partial_recovery_1ee7fb111.bundle` SHA-256 is `2d0b516fe7d578061e97dfca874745bcf3a0bf504b0f80976ad3aa21e01077ed`.
- `git bundle verify` passes against prerequisite `97edb1b...`; bundle head is exactly `1ee7fb111 refs/heads/recovery/kmfa-v15-fuzzy`, hash algorithm `sha1`.
- Standalone and taskpack-embedded v1.5 recovery ZIP are byte-identical at SHA-256 `8066b65dc96f4368b54e2a053e6726a2bf194806d67b1bdbcacb669a457ef2c1`.
- The advertised historical remote recovery ref was independently fetched and equals `268acce792...`; it is three commits after the baseline and two commits after the bundled checkpoint.
- The protected bundle duplicate still has the same digest. The redundant Runtime repository remains `PRIVATE`; its protected Release still has three server-digested assets. No private asset name, manifest content or payload is copied here.
- GitHub commit-object lookups in both `LinzeColin/KMOS` and `LinzeColin/CodexProject` did not find `13921de...`. It is recorded as absent, not reconstructed by guess.

## 3. Full recovery-set partition

The embedded recovery report originally stated `868 touched / 764 safe / 99 unresolved`. A later protected full-sweep found the broader set and is used as supplemental evidence, not as a replacement authority:

| full-sweep terminal status | Count |
| --- | ---: |
| `OK` | 1002 |
| `DELETED_THEN_REGENERATED` | 6 |
| `FAILED` | 49 |
| `NEEDS_MANUAL` | 3 |
| **Total** | **1060** |

Supplemental evidence identities:

- Full-sweep report SHA-256: `6a9f298c610a43b07b251ff7716718ba2476ac31282f80dd924a0ded0be44af1`.
- Recovery report SHA-256: `88d7f3810042ed387b50c4c99b85e0c6dcc07f74641c86bea360470dedf34a9b`.
- Rebuild-method SHA-256: `8599a590293eb124d157a27bebf36ef0ba70fcc0c41e18d956f5dcee515e86fd`.

The 1060 paths were deterministically partitioned using the current-main tree, an explicit 16-entry legacy-skill relocation map, old `v015_` path/domain predicates and four explicitly stale non-canonical paths. Canonical path-level decision rows hash to:

`sha256:a16490a15c5cebdc97d3105e9bfc35d079305a811477f7f66748fa1d11e4470d`

| Cohort | Exact predicate | Count | Decision | Executable meaning |
| --- | --- | ---: | --- | --- |
| `REC-CURRENT-AUTHORITY` | path exists in current `68306e8...` tree | 223 | **Adopt** | Keep current blob; recovery variant is superseded reference |
| `REC-RELOCATED-SKILL` | one of 16 explicit old→canonical skill-path mappings; every target exists in current tree | 16 | **Adopt** | Keep migrated package under `KMFA/skills/`; never restore old path |
| `REC-LEGACY-CODE` | absent-current legacy `v015_` path in `tools/` or `tests/` | 750 | **Redo** | Implement only behavior required by the active v1.5.2 Task/AC; consult old blob read-only and do not recreate files en masse |
| `REC-LEGACY-EVIDENCE` | absent-current legacy `v015_` config/metadata/stage artifact | 67 | **Discard** | Preserve only in recovery history; do not import obsolete 24-stage evidence or parallel facts |
| `REC-STALE-NONCANONICAL` | four absent-current standalone design/run-status authorities | 4 | **Discard** | Use v1.5.2 canonical facts and compact evidence instead |
| **Total** | mutually exclusive and exhaustive | **1060** | `Adopt 239 / Redo 750 / Discard 71` | `Conflict 0 / unclassified 0` |

`Redo` is intentionally semantic, not a file-creation order. A future task may reuse an algorithm only after its current AC proves the need; this decision does not authorize restoring 750 legacy files or the old 24-stage machinery.

The original 99-path list is contained in the 1060-path partition. Supplemental replay classified it as `67 OK / 5 DELETED_THEN_REGENERATED / 25 FAILED / 2 NEEDS_MANUAL`; no original path remains outside the five disposition cohorts.

## 4. Final unresolved paths

The full-sweep's final `49 FAILED + 3 NEEDS_MANUAL` paths are also completely covered:

- 41 paths exist in current main → **Adopt current**, not the failed historical reconstruction. This includes three current top-level historical documents; retaining their current blobs does not promote them above the v1.5.2 machine facts.
- 6 missing legacy skill paths have verified current canonical targets → **Adopt relocated**.
- 3 missing legacy `v015_` tool paths → **Redo behavior through the current Task/AC**, never replay.
- 2 missing legacy `v015_` stage-evidence paths → **Discard**.

Counts sum to 52; `Conflict=0`, because the user-authorized v1.5.2 authority order resolves every source conflict without an irreversible migration or guessed file.

## 5. History reconciliation

| Historical input | Adopt | Redo | Discard |
| --- | --- | --- | --- |
| 2026-07-22 acceptance | Immutable `FAIL`, Access login-wall baseline, anonymous write/export and governance risks, retest requirement | Root `/` contract and public/private authorization under the newer v1.5.2 ACs | Old proposed `/ → /ui/` acceptance target as current behavior |
| v1.4.2 | Existing real software and reusable route/API/state/persistence, amount precision/zero-delta, lineage, rerun, user-flow and layered-test semantics | Root/public/login/write/export/permanence/evidence contracts where v1.5.2 changed the product | Duplicated 24-stage/72-phase/216-task orchestration |
| v1.4.1 | Archive identity only | None in this run | Content as implementation input: excluded due size and possible raw/private material; archive was not expanded |
| pre-v0.1 | Concept index only | None in this run | Any claim to current product/governance authority |

This keeps useful product knowledge without letting lower-priority history weaken public access, anonymous private workspaces, arbitrary-file safe storage, durable DB/object storage or compact evidence.

## 6. Unfinished S24 exclusion proof

The protected full-sweep records five S24 paths, canonical set SHA-256 `9606d85a7cc794b6540b5ecfdfeec1e0d1a6b9a7ffb1ad3c7e2bf0b7e1b8717e`:

1. `KMFA/tools/build_v015_s24_p1_final_acceptance.py`
2. `KMFA/tools/check_v015_s24_p1_final_acceptance.py`
3. `KMFA/tools/run_v015_s24_p1_clean_rebuild.py`
4. `KMFA/tools/run_v015_s24_p1_validations.py`
5. `KMFA/tools/v015_s24_p1_final_acceptance.py`

Proof chain:

- The embedded replay cutoff is `2026-07-17T03:15:00Z`; its contract says S24 began after the lost S23-final state and must not enter S01-S23 recovery.
- The supplemental full-sweep classifier excludes `.codex_private_runtime` 16 paths and S24 5 paths before its 1060-path working set.
- The currently retained local patch logs independently reproduce 13 private-redline paths, the exact same five-path S24 set and the same 1060-path public working set. Three private-redline histories are no longer in the active log corpus; their earlier count remains sealed by the supplemental report digest, and the public/S24 sets are unchanged.
- `git ls-tree` finds `0` matching S24 paths in bundled checkpoint `1ee7fb111`, updated recovery tip `268acce792`, current main `68306e850` and this phase's intended diff.
- The five paths are disposition `Discard` and outside the active v1.5.2 baseline. No replay, cherry-pick, merge or generated substitute was executed.

Therefore unfinished S24 content is neither silently adopted nor lost: its exclusion identity is preserved, while its code remains outside current development.

## 7. Public-safety and read-only audit

- Recovery tip contains `0` `.codex_private_runtime` paths and `0` tracked forbidden data extensions (`.env*`, SQLite/DB, Excel, ZIP/GZ/7z/RAR).
- High-confidence private-key/token scan over the recovery tip returns one syntactic hit: the private-key-header rule literal inside the safety checker's AST tuple named `forbidden`. Executable credential/key hits are `0`; no matched value is copied into this receipt.
- v1.4.1 was hashed and indexed only; it was not expanded or copied.
- No raw inbox, real employee/financial file, token, cookie, session, private Release payload or original platform response entered the worktree.
- No recovery ref was imported into KMOS; no replay, merge, cherry-pick, force-push, deploy, database write or production mutation occurred.

## 8. Validation gate

| Gate | Result |
| --- | --- |
| Approved taskpack | Outer SHA-256 PASS; ZIP `43` files; self-excluding manifest `42/42`; validator `49 requirements / 49 AC / 14 stages / 56 tasks`, 0 errors/warnings |
| Four-way identities/topology | Current main/production unchanged; bundle verify PASS; exact `97edb1b → 1ee7fb1 → 1926014 → 268acce` lineage PASS; missing final absent from both public repositories |
| Recovery partition | 1060 unique paths; canonical inventory digest PASS; `Adopt 239 / Redo 750 / Discard 71 / Conflict 0 / unclassified 0`; original 99 and final 52 fully covered |
| S24 exclusion | Sealed report `16 private + 5 S24 + 1060 public`; retained logs `13 + exact same 5 + same 1060`; exact S24 digest PASS; three recovery/current trees and local diff have 0 S24 paths |
| Disposition CSV | 16 unique cohort/subject/history rows; all decisions, owners, defaults and evidence references present; recovery cohort counts sum to 1060 |
| Public safety | New absolute local paths 0; token/key values 0; one AST-classified scanner-rule literal; forbidden payload paths 0; receipts below 64 KiB |
| Repository gates | Dual-plane PASS; `git diff --check` PASS; no merge/cherry-pick/recovery ref; intended delta limited to four public-safe files |

## 9. Disposition sign-off and phase boundary

Decision basis: user authorization → v1.5.2 canonical facts/current production → active Task/AC → recovery/history. Only irreversible conflicts require human review; this reconciliation has `Conflict=0`.

```text
Signed-off scope: T-S00-02 / AC-GOV-001
Prepared by: Codex recovery executor
Full path decision digest: a16490a15c5cebdc97d3105e9bfc35d079305a811477f7f66748fa1d11e4470d
Disposition: Adopt=239; Redo=750; Discard=71; Conflict=0; Unclassified=0
Writable baseline: KMOS main only
Recovery/history: read-only reference only
```

The local Git commit containing this receipt and its CSV signs the phase together. Passing P0.2 authorizes the next run to start P0.3 from current main plus local S00 receipts; it does not authorize recovery replay, S00 Stage Review or GitHub upload.
