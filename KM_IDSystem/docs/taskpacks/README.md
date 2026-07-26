# IDS v0.1 任务包基线

本目录保存 Owner 于 2026-07-26 明确要求交付到 GitHub 的 IDS v0.1 中文任务包文本基线，供后续任务包迭代、差异评审和 Stage 执行引用。

## 导入事实

- 来源文件名：`IDS_Taskpack_v0_1_only_中文修订版.zip`
- 来源 ZIP SHA-256：`55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3`
- 导入目录：`IDS_v0_1_Final_Chinese_Revised/`
- 文件数：`183`
- 未压缩总字节数：`801574`
- 类型：`179 Markdown + 2 TXT + 1 CSV + 1 JSON`
- 完整性：导入后 `183/183` 文件与 ZIP 成员逐字节一致

ZIP 本体没有提交。仓库只保存通过审计的文本成员以及独立校验清单
`IDS_v0_1_Final_Chinese_Revised.sha256`。

## 导入审计

导入前已确认：

- 所有成员均为相对安全路径，没有 `..`、绝对路径或符号链接；
- 所有成员均为 UTF-8 文本，没有 NUL 或未批准扩展名；
- JSON 与 CSV 可解析；
- 未命中 private key、OpenAI/GitHub/AWS token、Bearer token 或本机 `/Users/...`
  绝对路径规则；
- 没有读取、列出、扫描、哈希、复制或修改 `IDS_MetaData` 原始数据目录。

## 治理优先级

该目录是 2026-07-01 生成的任务包基线，不是当前仓库治理的替代品。若内容冲突，按以下
顺序执行：

1. 当前系统/Owner 指令；
2. 仓库根 `AGENTS.md` 与 `KM_IDSystem/AGENTS.md`；
3. `KM_IDSystem/docs/HANDOFF.md` 的当前 gate；
4. 本任务包基线。

因此，任务包内旧 `OpMe_System` 路径、外接硬盘数据目录和其他历史表述只保留为来源事实。
当前 canonical 代码路径是 `LinzeColin/KMOS` 的 `KM_IDSystem/`；长期、业务和运行时数据
必须遵守当前 Private-Database/KMDatabase 治理，不得因本任务包旧文本改变路由。

## 迭代方式

- 不静默改写本目录中的来源基线；
- 先在 `ITERATION_FEEDBACK_20260726.md` 或后续版本目录记录差异与决策；
- 每个新版本保留来源、版本、SHA-256、变更理由和适用 gate；
- Stage 文件只描述该 Stage 的授权范围，不能凭后续 Stage 的规划文本宣称能力已实现；
- 真实原始资料、业务数据、凭据、数据库、报告、运行输出和 ZIP 不进入本仓库。

## 校验

从 `KM_IDSystem/docs/taskpacks/` 运行：

```bash
shasum -a 256 -c IDS_v0_1_Final_Chinese_Revised.sha256
```

预期：`183/183` 均为 `OK`。
