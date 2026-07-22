# S02 / P2.1 / T-S02-01 — Canonical Facts receipt

Status: **PASS; local phase only**
Captured: `2026-07-23` (Australia/Sydney)
Executor action: `ACT`
Taskpack: `KMFA_Product_Design_Taskpack_v1.5.2.zip`
Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`

## 1. Scope and authority

This receipt closes only `S02 / P2.1 / T-S02-01`. It does not start P2.2, render the seven human files, install the Acceptance Contract/Task DAG/Traceability artifacts, alter runtime code, publish Git, deploy, or mutate production/recovery data.

The phase adopts the sealed taskpack bytes as `machine/canonical_facts.yaml`:

| Check | Result |
|---|---|
| Sealed catalog path | `machine/canonical_facts.yaml` |
| Sealed and repository SHA-256 | `5ae070cb4105e83eec0c05b3771759e550a67f1241708810f0b4430300198552` |
| Byte comparison | exact match |
| Schema/status | `1.0` / `FINAL_AUTHORIZED` |
| Unique writer | `WR-TASKPACK-PUBLISHER`; changes require an Owner-authorized replacement package or corrigendum |

`machine/canonical_facts.yaml` is the writable authority for the **v1.5.2 delivery product-contract namespace**. The 14 existing `machine/facts/*` files remain the distinct older business-state namespace and keep their existing writers. `machine/runs/*` is evidence only. The current seven `文档/00_我在哪.md` … `06_运维手册.md` remain generated views of the older business facts until P2.2 explicitly reconciles rendering; this phase does not hand-edit or silently replace them.

The sealed `product.product_runtime_version: TO_BE_VERIFIED_IN_S00` value is retained byte-for-byte as package provenance, but it is not allowed to override the live runtime authority `KMFA/VERSION`. Likewise, taskpack version, published Git SHA and deployment identity stay separate namespaces under `AUTHORITY_REGISTER.md`.

## 2. Minimal fact model and identity rules

No second schema or ID registry is introduced. Identities and joins are deterministic projections of the sealed YAML:

| Subject | Canonical identity / rule | Cardinality |
|---|---|---:|
| Decision | `decisions[].id` | 14/14 present and unique |
| Requirement | `requirements[].id` | 49/49 present and unique |
| Metric | stable locator `requirements[id=<requirement.id>].metric`; display ID may be rendered as `metric::<requirement.id>` without persisting another fact | 49/49 locators unique; 49/49 metric values unique |
| Domain | `requirements[].area` on the same requirement row | 14 domains; 49/49 present |
| Owner | `requirements[].owner` on the same requirement row | 49/49 present |
| Task seed | `requirements[].task` on the same requirement row | 49/49 present; P2.3 owns the later AC/task/evidence join |

Metric identity deliberately inherits the requirement ID. Adding 49 separately writable `metric_id` facts would create the redundant structure prohibited by T-S02-01. A consumer must fail closed if the requirement ID is absent, duplicated, or has zero/multiple metric values.

## 3. Fact-domain / Owner projection

This table is a reproducible projection (`group requirements by area; collect row owners`), not a writer or a copied source of product facts:

| Domain | Requirements | Owner values present in canonical rows |
|---|---:|---|
| AI | 1 | AI Owner+Safety |
| 上传 | 4 | Backend; Backend+Security; Data; Security |
| 下载 | 4 | API Owner; Backend; Backend+Frontend; Backend+Ops |
| 产品能力 | 4 | Product Analytics; Product+Backend; Product+Privacy; Search/Data |
| 公开入口 | 5 | Frontend; Frontend+Privacy; Product+Web; Web/Edge |
| 匿名工作区 | 4 | Backend+Security; Backend+UX; Security; Security+Ops |
| 可靠性 | 4 | Release Owner; SRE; SRE+Backend; SRE+QA |
| 安全 | 2 | Security; Security+Engineering |
| 持久化 | 4 | Data/Backend; Product+Privacy; SRE; Storage/Backend |
| 架构 | 3 | Architect+Security; Backend; Data+Release |
| 治理 | 5 | Delivery Lead; Product Owner; Product+Tech Lead; Release Owner; Tech Lead |
| 财务正确性 | 4 | Finance Domain; Finance+Backend; Finance+Data; Product+Finance |
| 质量 | 4 | Delivery Lead; QA+Governance; QA+Product; QA+SRE |
| 运营 | 1 | Ops+Product |
| **Total** | **49** | every row has exactly one non-empty Owner value |

## 4. Derivation rules

All human tables and the future trace matrix must be projections, never reverse writers:

1. Read `machine/canonical_facts.yaml` once and reject invalid YAML, unexpected schema/status, duplicate decision/requirement IDs, missing `area/owner/task/metric`, or non-unique metric locators.
2. Preserve list order for narrative display; use stable IDs for joins. Never join on title, translated text, owner label, or array position.
3. Render the v1.5.2 key tables by responsibility: `00` navigation/status references; `01` goal/authorization/decisions/OKRs/non-goals/requirements; `02` storage/privacy/architecture projections; `03` metric/baseline/target/window definitions; `04` authorized user and operational flows; `05` requirement/task seeds joined later to task/acceptance/trace inputs; `06` reliability/security/release projections joined to measured runtime/deployment facts.
4. Do not persist a second copy of a decision, requirement, metric, Owner, baseline or target in a renderer, receipt or human document. Render values directly from their writer on every check.
5. Runtime version, published source, deployment/image identity, measured production status and recovery identity are external live-authority joins defined by `AUTHORITY_REGISTER.md`; placeholders or historical captures inside the taskpack cannot supersede them.
6. The existing seven `文档/*` files stay under `WR-RENDER-HUMAN` and the existing 14 business facts in this phase. P2.2 must explicitly implement and test any v1.5.2 human-plane reconciliation; P2.1 only proves the canonical side is sufficient.
7. P2.3 may join `requirements[].id/task` to Acceptance Contract, Task DAG and traceability, but must not copy those artifacts into Canonical Facts. A missing or ambiguous join fails closed.

## 5. Verification evidence

| Gate | Result |
|---|---|
| Baseline | repository canonical path absent before phase; expected fail confirmed |
| Package integrity | outer ZIP `unzip -t` PASS; 42-entry manifest/validator PASS; canonical catalog hash matched |
| YAML and fields | parse PASS; 14 decisions, 49 requirements, 4 objectives, 7 non-goals |
| ID uniqueness | decision `14/14`; requirement `49/49`; requirement-scoped metric locator `49/49` |
| Mapping completeness | `area/owner/task/metric/baseline/target/window` each `49/49` |
| Legacy writer isolation | 14 old facts retained; exact seven generated files retained; no renderer mutation |
| Public safety | high-confidence credential/private-key/token and email patterns returned zero hits in the two new files |
| Recovery preservation | recovery ZIP `8066b65d…` test PASS; streamed bundle hash `2d0b516f…`; public recovery ref remains `268acce792…` |
| Production isolation | latest public-safe query run `29931489638` still resolves the previously verified current deployment; anonymous entry remains a known `302` baseline defect |
| Mutation boundary | only P2.1 governance files; no push/deploy/database/object/recovery mutation |

Full command outputs remain CI/terminal evidence rather than being copied into a formal evidence tree. Final local commit plus this sub-64KiB receipt signs the phase. Stage S02 remains open; its whole-Stage Review and upload are forbidden until P2.1–P2.4 all complete.

## 6. Rollback and next boundary

Rollback is an ordinary revert of the P2.1 commit. That removes the added Canonical Facts and compact receipt/navigation changes without touching the old business facts, seven generated documents, application, deployment, database, object storage or protected recovery assets.

The only authorized next run is `S02 / P2.2 / T-S02-02`. This receipt does not authorize it in the current run.
