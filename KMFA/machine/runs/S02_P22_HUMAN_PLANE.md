# S02 / P2.2 / T-S02-02 — seven-file human plane receipt

Status: **PASS; local phase only**
Captured: `2026-07-23` (Australia/Sydney)
Executor action: `ACT`
Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`
Canonical Facts SHA-256: `5ae070cb4105e83eec0c05b3771759e550a67f1241708810f0b4430300198552`

## 1. Scope and sealed contract

This receipt closes only `S02 / P2.2 / T-S02-02` and sealed `AC-GOV-003`. It does not install the Acceptance Contract, Task DAG or Traceability files, start P2.3/P2.4, review S02 as a Stage, publish Git, deploy, or mutate production/recovery data.

The repository adapter keeps the governed human-plane path `文档/` rather than creating a second `human/` directory. The exact seven filenames are:

1. `00_我在哪.md`
2. `01_产品需求.md`
3. `02_系统架构.md`
4. `03_口径字典.md`
5. `04_操作流程.md`
6. `05_执行与验收.md`
7. `06_运维手册.md`

Every file is `GENERATED` by `machine/tools/render_human.py`; none is Owner-handwritten.

## 2. Baseline and Stop Condition audit

Before the phase, `文档/` already contained exactly seven generated files and the legacy renderer reproduced them with zero diff. However, the combined documents contained `0/14` canonical decision IDs and `0/49` canonical requirement IDs, so the P2.2 key-fact render test correctly failed.

The taskpack's reference `human/*` files were not copied: `01`, `02`, `04`, `05` and `06` exceed this repository's existing line budgets, and those references contain architecture/flow detail that is not a writable Canonical Fact. Copying them would create human-only facts and a second human plane.

No existing human document contained a unique production fact: all seven headers and the pre-change zero-diff render proved their contents came from the 14 legacy `machine/facts/*` sources. Therefore the sealed Stop Condition was not triggered.

## 3. Single-source projection map

| File | v1.5.2 projection | Preserved legacy projection | Responsibility boundary |
|---|---|---|---|
| `00` | contract identity, authorization status, target entry and counts | status, blocker and legacy roadmap | navigation/status only; live delivery points to `HANDOFF.md` |
| `01` | pursuing/strategic goal, 14 decisions, 4 objectives/12 KRs, 7 non-goals, 49 requirement statements | legacy product scope | product contract; metrics and execution links elsewhere |
| `02` | storage and privacy contracts | features, data flow, parameters and entities | architecture contract versus verified legacy implementation |
| `03` | 49 stable `metric::<requirement.id>` rows with baseline/target/window | financial glossary and invariants | sole expanded metric/terminology view |
| `04` | four Owner authorization interpretations and area→requirement index | legacy business flow | authorized usage/flow navigation; no invented step order |
| `05` | 49 requirement→Task/Owner seeds | legacy plan, acceptance and latest five run records | execution mapping only; full AC/trace waits for P2.3 |
| `06` | persistence/reliability/security/operations requirement index | legacy config/runbook/changelog | operational entry; conflicting old Access steps are explicitly historical, not v1.5.2 release instructions |

Canonical Facts and the 14 legacy facts retain their existing writers. `文档/*` has only `WR-RENDER-HUMAN`; taskpack `human/*`, this receipt, `AGENTS.md`, and `HANDOFF.md` do not become fact writers.

## 4. Consistency gate

`machine/tools/check_dual_plane_ci.py` now enforces:

1. for KMFA (and any project explicitly declaring `machine/canonical_facts.yaml`), the complete file set under `文档/` equals the seven names above, with no extra file; other repository projects retain their pre-existing contract;
2. every file declares the GENERATED prefix;
3. renderer execution succeeds and produces byte-stable content;
4. the pre-render document snapshot equals the regenerated output, so hand edits fail;
5. Canonical values are independently projected by responsibility: contract identity to `00`, all decisions/requirements to `01`, storage/privacy to `02`, all metrics to `03`, authorization/domain IDs to `04`, all Task/Owner seeds to `05`, and operations IDs to `06`;
6. existing document-budget, Chinese-term, architecture-purity and blocker gates pass.

Canonical loading itself fails closed on missing/unparseable data, fixed-set count drift, duplicate decision/requirement IDs, incomplete nested contracts or missing requirement metric/owner/task fields.

## 5. Findings and verification

| Finding / gate | Result |
|---|---|
| `F-P22-001` case-fold sort tie | resolved: term index now sorts by `(casefold, original)`; two fresh renderer processes produced identical seven hashes |
| `F-P22-002` shared-checker scope | resolved: Canonical/exact-set rules apply only to projects declaring `machine/canonical_facts.yaml`; the repository-wide gate again covers all five projects without imposing KMFA's contract on four peers |
| writer-map digest | recomputed from its declared 29-row normalization after the P2.2 source mapping; `5bd31aba74cd486d91d4d50a6c6b9972dd6b798a35e7a963a29fe277d1b18b69` |
| exact file budget | `7/7`; lines `74 / 126 / 66 / 182 / 49 / 86 / 136`, all within existing limits |
| canonical coverage | decisions `14/14`; requirements `49/49`; metrics `49/49`; Task/Owner seeds `49/49` |
| negative tamper | appended `P2.2_NEGATIVE_TAMPER` to generated `00`; CI exited non-zero and named the render-consistency gate; renderer restored the file; positive rerun PASS |
| negative eighth file | temporarily added `07_额外.md`; CI exited non-zero and named it as an extra file; fixture removed; positive rerun PASS |
| dual-plane positive | repository gate PASS for all five discovered projects, including KMFA document budget, Chinese/purity and blocker checks |
| source preservation | sealed Canonical Facts and all 14 legacy facts unchanged; no `human/` directory and no eighth human file |
| public safety | no high-confidence credential/private-key/token hit in intended delta; no private payload imported |
| recovery | taskpack recovery ZIP `8066b65d…` test PASS; streamed bundle hash `2d0b516f…`; no replay/import |
| production | latest public-safe query remains `68306e85… / sha256:adfc849b… / boh5fsnx…`; all anonymous probes remain known `302` baseline failures |
| mutation boundary | no push/deploy/database/object/Cloudflare/recovery write; P2.3 not started |

The old business `BLK-001` remains visible and fail closed for formal financial conclusions. It does not become a P2.2 failure because this phase neither accesses private data nor claims legacy S05–S18 completion.

## 6. Rollback and next boundary

Rollback is an ordinary revert of the P2.2 commit. It restores the prior renderer/checker and prior generated seven views without changing Canonical Facts, the 14 legacy facts, application code, production, durable stores or recovery assets.

The only authorized next run is `S02 / P2.3 / T-S02-03`. This receipt does not authorize it in the current run.
