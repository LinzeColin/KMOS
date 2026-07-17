# OPS.0006（改道版）：KMOS CI 绿基线登记

> 任务：`TSK.KMFA.OPS.0006` ｜ 2026-07-17 ｜ 修订 R1 后，本任务由「圈定 CodexProject 夜间红」改为「登记 KMOS CI 绿基线」。

- KMOS 唯一 CI：GitHub Actions `Dual-Plane Governance`（PR + push 触发，检查 KMDatabase/KMFA/KM_IDSystem/whkmSalary 四项目双平面合规）。
- 基线状态：**连续全绿**。当日样本（run id）：29564565062（PR#2）、29567176037（PR#3）、29567745781（#4 push）、29568253475（#5 push）、29570534057（#6 push）、及 #7 push，全部 success，单次 7-14s。
- 判读口径：DT3 全量验证以 KMOS 本 CI + 仓内验证器/测试为准；CodexProject 夜间旧治理套件的 42F+96E 与 KMFA 无关（恢复线证据仍在其 recovery 分支，不回并）。
- 本地既有红基线（供 DT3 对照）：五技能验证器全绿；pytest 选集（考勤/资金周报/经营月报技能测试 + KMFA/tests 两文件）基线 = 28 failed / 209 passed（全部为缺私有运行时/dws 授权/psql 的环境性失败，清单见 git 历史 2026-07-17 重命名 PR 描述）。
