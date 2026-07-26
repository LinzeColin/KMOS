# IDS v0.1 任务包迭代反馈（Stage 041–047 实证）

## 结论

任务包的 168-Stage 分解可以继续作为产品路线骨架，但 Stage 041–047 的实际实现和独立复审
表明：当前模板对精确数据合同、证据链、时间语义、失败关闭和“规划/控制证据/真实运行”
边界规定不足。后续迭代应优先强化合同与 gate，而不是增加更多泛化任务描述。

截至 2026-07-26：

- Stage 041–047 已完成 Phase 1–4 和独立 whole-stage review；
- `BATCH041_050` 为 `7/10`，尚未完成 Stage 048–050，也未做十阶段 batch review；
- Stage 048 没有在本线程启动；
- 历史 `NO_GITHUB_UPLOAD_THIS_RUN` 是各 Stage 当轮边界；Owner 本轮只授权将完整进展交付到
  独立远端分支/Draft PR，不等于授权合并 `main` 或激活生产能力。

## 已复审发现

| Stage | 发现数 | 对任务包最重要的反馈 |
|---|---:|---|
| 041 锁注册 | 1 Critical / 3 Important | CAS/version 必须是严格正整数；租约时间必须单调；运行参数关系和来源必须精确绑定；当前 gate 必须耐久记录。 |
| 042 自动生命周期 | 1 Critical / 4 Important | request ID 必须从 canonical payload 派生；version/reason 与 action 绑定；恢复需要可证明的时间窗口；清理候选必须来自允许状态。 |
| 043 崩溃恢复 | 1 Critical / 5 Important | worker/lease/checkpoint/quarantine 必须绑定同一恢复身份；崩溃检测必须在检测时已经成立；资源信号、错误分类和来源检查失败关闭。 |
| 044 半成品清理 | 1 Critical / 5 Important | 可恢复状态不得进入清理；完整合同而非字段子集决定授权；provenance 与候选内容绑定；路径必须词法唯一；中文状态不能夸大。 |
| 045 文件类型检测 | 3 Critical / 4 Important | magic prefix 不能证明完整格式；OOXML container 不能被 MIME/扩展名绕过；member 路径唯一安全；时间、MIME、evidence 校验顺序必须明确。 |
| 046 解析器路由 | 2 Critical / 3 Important / 1 Minor | 需要 result-level identity；非法输入不能回显未验证身份；reference 必须 canonical；fact level 由 action 派生；场景 PASS 必须绑定完整输出。 |
| 047 解析器输出 | 2 Critical / 4 Important | request/result/source 必须形成完整 lineage；非法 Unicode 结构化拒绝；reference lower-ASCII canonical；对象图双向一致；状态/错误有界；时间有序。 |

合计：`11 Critical / 28 Important / 1 Minor`，均已在本地 reviewed commit 中修复并有机器
反例。该统计是工程复审事实，不代表 Stage 048–168 的质量已经验证。

## 建议写入下一版任务包的 P0 规则

### 1. 每个 Stage 提供精确可执行合同

除自然语言目标外，至少新增：

- `contract_id`、`schema_version` 和 exact-shaped input/output schema；
- unknown field、类型、长度、字符集、枚举、整数/布尔边界；
- canonical ID/reference 生成规则；
- 允许的 side effect 与明确禁止的 side effect；
- bounded error taxonomy 与 fail-closed result；
- predecessor commit/tree/artifact 绑定；
- rollback、stop condition 和唯一 next gate。

“字段存在”不等于合同有效；跨字段关系和来源身份必须机器校验。

### 2. 显式区分四种事实层级

每个 Stage/Phase 必须标明产物属于：

1. `PLAN_ONLY`；
2. `SCHEMA_OR_CONTROL_EVIDENCE_NOT_RUNTIME`；
3. `ISOLATED_RUNTIME_SLICE_NON_PRODUCTION`；
4. `PRODUCTION_OBSERVED`。

不得从 schema-only sample、control scenario、fixture 或 fallback log 样例推断真实 parser、
worker、恢复、清理、数据写入或生产能力已启用。

### 3. 把不可变历史与复审修复分开

- Phase 4 交付快照保持不可变；
- whole-stage review 绑定 Phase 4 commit、root tree、项目 tree、parent、HEAD ancestry 和
  关键 artifact hashes；
- 复审修复形成新的 reviewed snapshot，不改写历史 Phase 1–4 已发生事实；
- checker 每次 live rehash 来源和 Git index，不能信任历史 `passed=true`。

### 4. 当前治理覆盖任务包旧路径

下一版应直接写明：

- canonical repo 为 `LinzeColin/KMOS/KM_IDSystem`；
- 主树只读，开发在独立 worktree；
- 长期/业务/运行时数据走当前 Private-Database/KMDatabase 规则；
- GitHub 只保存代码、合同、taskpack、治理和小型合成 fixture；
- ZIP、SQLite、原始元数据、真实员工/财务/群聊/考勤数据、凭据、报告和 runtime outputs
  不进入公开代码仓；
- `IDS_MetaData` 是未经授权不得读取、列出、扫描、哈希、复制或修改的原始数据边界。

## 建议的模板结构

每个 Stage 建议按以下顺序写：

1. Pursuing Goal；
2. source/predecessor binding；
3. exact contract；
4. authorized runtime level；
5. allowed/forbidden side effects；
6. Phase 1–4 专属任务；
7. negative scenarios；
8. machine-checkable acceptance；
9. evidence minimum；
10. rollback/stop/next gate；
11. 与前后 Stage 的 ownership matrix。

Phase 3/4 虽已按 Stage 定制，但 Stage 041–047 仍存在大量同域模板重复。建议把通用 schema、
canonical reference、time、provenance、Git ancestry、event、owner-view 和 forward-route
规则抽成版本化共享合同；Stage 文件只声明差异。这样可减少历史 checker 中不断追加
forward-route allowlist 的维护成本。

## Stage 048–050 迭代重点

### Stage 048 · 失败降级链

- 定义有限 attempt budget、顺序、终止条件与唯一 terminal disposition；
- 每次 attempt 绑定同一 source/detection/routing/output lineage；
- 日志只允许脱敏、有界、非业务正文内容；
- `silent_drop_count` 必须为零；
- fallback control log 与真实 parser attempt 明确分级；
- 任何 runtime dispatch 都需单独授权，不能沿用 Stage 046/047 的 schema/control 证据。

### Stage 049 · 差异化解析器评估

- 先定义可复现的比较指标、样本治理、成本/API budget 和人工复核阈值；
- 多 parser 结果不得自动提升为高可信 evidence；
- 记录 parser/config/version、输入身份、差异和选择原因；
- 禁止把真实业务正文写入公开评估工件；
- 明确无外部 API key 时的 fail-closed/offline 行为。

### Stage 050 · 提示注入标记

- 文档中命令性文字始终是 untrusted evidence text，不是系统指令；
- scanner 需要版本、规则来源、输入/输出 identity、false-positive/negative 证据；
- 标记不能删除或篡改来源文本；
- Stage 047 的 `instruction_marker` 只是合同字段，不能被宣称为 scanner 已实现；
- 注入风险不得绕过 external API policy、quality gate 或 evidence promotion。

## 下一轮建议

1. 先迭代任务包治理头、Stage 模板和 Stage 048–050 三份文件；
2. 从最新 `origin/main` 创建新的独立 worktree/branch；
3. 以本次 Draft PR 为历史实现证据，先解决与当前 `main` 的 108-commit 漂移；
4. 对 Stage 041–047 做集成复审后，再决定是否合并或进入 Stage 048；
5. Stage 048 仍必须从独立 `IDS-STAGE048-P1-GATE` 开始。
