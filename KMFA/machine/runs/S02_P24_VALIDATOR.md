# S02 / P2.4 / T-S02-04 — taskpack validator receipt

Status: **PASS; local phase only**
Captured: `2026-07-23` (Australia/Sydney)
Executor action: `ACT`
Taskpack SHA-256: `31088516896e98cd7df1f877f7ec5077e6d8afe8013a88b803a616849555cffb`
Parent phase commit: `41cfec078aeb3313fca18fe04938cad954118af8`

## 1. Scope and baseline

This receipt closes only `S02 / P2.4 / T-S02-04`. It adds the read-only repository-projection validator, the required four fail-closed mutation cases, a compact validation report and explicit local CI wiring. It does not review S02 as a whole, publish Git, run GitHub Actions, change the deploy filter, deploy, mutate production/business data or replay v1.5 recovery assets.

The pre-change gate was a real failure: `machine/tools/validate_taskpack.py`, `machine/tools/test_validate_taskpack_mutations.py` and `machine/VALIDATION_REPORT.md` were absent, and `.github/workflows/dual-plane.yml` contained neither validator command. The Task Stop Condition was not triggered: the implementation is read-only, deterministic, local and needs no external service.

## 2. Implemented gate

`machine/tools/validate_taskpack.py` composes the P2.3 semantic checker with the P2.4 repository rules. It verifies:

1. all four sealed S02 machine sources match their approved SHA-256 identities;
2. 49 Requirements, 49 unique primary Acceptance Contracts, 14 Stages, 56 direct Phases, 56 Tasks and 49 exact trace rows remain closed;
3. every Stage has exactly four direct Phases and every Phase exactly one direct Task;
4. Task dependencies topologically visit `56/56`, so any cycle fails;
5. `文档/` contains exactly the seven generated files, with no eighth governance authority;
6. `EVIDENCE/`, `SCHEMAS/`, `state_ledger.py` and `catalog_builder.py` are absent;
7. compact receipts and `VALIDATION_REPORT.md` remain below 64 KiB.

Unexpected loader/shape failures return a readable non-zero `RESULT: FAIL`. The validator never renders or rewrites files, invokes the network, reads private data, or turns UNKNOWN runtime behavior into PASS.

`machine/tools/test_validate_taskpack_mutations.py` first validates the authorized source tree, then copies only the public-safe projection into a fresh temporary directory per case. It proves non-zero readable failures after removing one Acceptance Contract entry, closing a dependency cycle, adding an eighth governance file or adding an `EVIDENCE` directory, then confirms the four source hashes are unchanged.

`.github/workflows/dual-plane.yml` now runs both P2.4 commands before the existing five-project dual-plane gate. `machine/VALIDATION_REPORT.md` is the reproducible structural snapshot and CI instruction; it is evidence only, never a product/business/deployment fact writer.

## 3. Verification

| Gate | Result |
|---|---|
| Approved ZIP | outer SHA matched; fresh official validator PASS with `49 Requirements / 49 AC / 14 Stages / 56 Tasks`, 0 errors/warnings |
| Positive repository projection | PASS: `49 / 49 / 14 / 56 / 56 / 49`, 0 errors/warnings |
| Required negative mutations | PASS: positive `1/1`; negative `4/4` returned non-zero with the expected readable error |
| Source immutability | PASS: Canonical, AC, DAG and Traceability SHA-256 remained `5ae070cb…552 / 1f07bd14…bc1 / a9753e7c…306 / ca369627…727` |
| Focused traceability | PASS: AC fields `735/735`, trace gaps `0` |
| Repository dual plane | PASS: all five discovered projects (`KMDatabase`, `KMFA`, `KM_IDSystem`, `搜标项目`, `whkmSalary`) |
| Workflow structure | PASS: YAML parsed and all three deterministic commands were present; hosted CI intentionally awaits Stage upload |
| Compact/public-safe boundary | report and tools are compact; no forbidden path, raw/private payload, credential, local absolute path or business-data write introduced |
| Mutation boundary | no push, deploy, platform/database/object/recovery write; `git diff --check` PASS |

These results prove the S02 taskpack/repository gate only. The root-domain Access `302`, loginless use, durable DB/object storage, arbitrary-file upload/download, recovery and canary/rollback remain unpassed later-Stage work.

## 4. Known Stage boundary, rollback and next run

The current `.github/workflows/deploy.yml` exact `paths-ignore` list does not cover the S02 candidate delta. Uploading it now could cause a needless production rebuild, so P2.4 does not authorize upload. The next run must be the whole S02 Stage Review: replay P2.1-P2.4 and G1, review the final diff, add only justified exact governance exclusions, prove the negative path-filter case, resolve every finding, then upload the complete Stage once and verify GitHub CI/no deploy. It must not start S03 in that run.

Rollback is an ordinary revert of the P2.4 commit. It removes the validator, mutation suite, report, receipt and CI step, restores the prior navigation, and leaves the four sealed sources, seven rendered files, application/runtime, production data and v1.5 recovery assets unchanged. Unknown state remains unevaluated rather than being reported as PASS.
