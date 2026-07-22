# KMFA v1.5.2 repository-projection validation report

Status: **PASS — structural/taskpack gate only**
Validated at: `2026-07-22T16:09:09Z`
Scope: `S02 / P2.4 / T-S02-04`

This report is a compact, reproducible snapshot of the repository projection. It is not a fact writer, runtime Acceptance result, release artifact, S02 Stage Review or GA decision. The validator and CI command determine PASS; this document cannot override a failing command.

## Structural results

| Gate | Result | Deterministic evidence |
|---|---|---|
| Required machine sources | PASS | Canonical Facts, Acceptance Contract, Task Graph and Traceability present |
| Sealed source identity | PASS | four SHA-256 values match the authorized v1.5.2 taskpack bytes |
| Exact human plane | PASS | `文档/` contains exactly seven generated files and no eighth authority file |
| Requirements / primary AC | PASS | 49 unique Requirements; 49 unique primary ACs; one AC per Requirement |
| AC completeness | PASS | 15 required fields × 49 contracts = `735/735` non-empty |
| Task graph | PASS | 14 unique Stages, 56 unique Tasks, topological visit `56/56`, cycles `0` |
| Granularity | PASS | each Stage has exactly four direct Phases; each Phase has exactly one direct Task |
| References / traceability | PASS | 49/49 rows exactly join Requirement, AC, Oracle, Task, Test, evidence, artifact and Owner; gaps `0` |
| Formalism guard | PASS | no `SCHEMAS/`, `EVIDENCE/`, `state_ledger.py` or `catalog_builder.py` |
| Compact evidence | PASS | every `machine/runs/*` file and this report are below 64 KiB |
| Read-only behavior | PASS | validator reads files only; mutation tests operate only in temporary directories and preserve all four source hashes |

## Sealed source identities

| Source | SHA-256 |
|---|---|
| `machine/canonical_facts.yaml` | `5ae070cb4105e83eec0c05b3771759e550a67f1241708810f0b4430300198552` |
| `machine/acceptance_contract.yaml` | `1f07bd14a382a4bad552f43e7ba281064c06bae7ab52c5e0d75139c305c43bc1` |
| `machine/task_graph.yaml` | `a9753e7c76dea6041b7386fd31735db869a6e371bcbce57c2fc794256a4d1306` |
| `machine/traceability.csv` | `ca36962746546e66c729dd564f4a3d316e47270199d5a1bec988c86949ca0727` |

## Fail-closed mutation results

| Mutation | Expected | Result |
|---|---|---|
| remove one Acceptance Contract while keeping its source file | non-zero with count/reference errors | PASS |
| add `T-S00-01 → T-S00-02` to close a dependency cycle | non-zero with cycle error | PASS |
| add `文档/07_额外治理.md` | non-zero naming the extra file | PASS |
| add `EVIDENCE/README.md` | non-zero naming the forbidden directory | PASS |

Authorized positive projection exits `0`; all four negative projections exit non-zero with the named readable error. A sealed-hash mismatch is also reported for mutated machine bytes but does not replace the semantic cycle/reference check.

## CI integration

`.github/workflows/dual-plane.yml` installs pinned-major Python 3.12 plus PyYAML, then runs these deterministic local gates before the existing repository-wide dual-plane check:

```bash
python3 KMFA/machine/tools/validate_taskpack.py --root KMFA
python3 KMFA/machine/tools/test_validate_taskpack_mutations.py --root KMFA
python3 KMFA/machine/tools/check_dual_plane_ci.py --root . --require-projects
```

The first command validates the current repository projection. The second proves the four required fail-closed cases using disposable local fixtures. Neither command needs a secret, network request, production service or private dataset.

## Boundary and reproduction

The authorized taskpack ZIP remains separately verified by its original `tools/validate_taskpack.py` and manifest. This repository adapter intentionally does not copy package PDFs, safe reference ZIPs, source inputs or release-policy material that is not an S02.1–S02.3 repository input.

The current `.github/workflows/deploy.yml` exact `paths-ignore` list does not yet cover the S02 candidate file set. Therefore P2.4 does not authorize a GitHub upload: the S02 whole-Stage Review must enumerate the final delta, add only the exact governance-only exclusions it can justify, replay the negative path-filter case and confirm that the Stage upload creates no deployment. Any non-excluded path remains a production release.

Reproduce from repository root with the three commands above. UNKNOWN runtime behavior stays UNKNOWN: the root-domain Access `302`, loginless journey, durable DB/object storage, arbitrary-file upload/download, recovery and canary/rollback remain later Stage gates.
