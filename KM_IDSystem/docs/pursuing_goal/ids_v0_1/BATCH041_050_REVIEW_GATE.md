# IDS v0.1 BATCH-041-050 独立批次复审门

- 批次：`IDS-V0_1-BATCH-041-050`
- 任务：`IDS-V0_1-BATCH-041-050-REVIEW-GATE`
- 范围：`STAGE-041..STAGE-050`
- 验收范围：`ACC-STAGE-041..ACC-STAGE-050`
- 当前结论：十个 Stage 的本地复审证据已形成一个可重放的批次矩阵；业务运行、外部服务和上传路径继续关闭。
- 当前开关：`push_allowed=false`，`github_upload_allowed=false`
- 本轮边界：`NO_STAGE051_THIS_RUN`
- 后续入口：`IDS-STAGE051-P1-GATE`

## 复审目标

本门仅复审冻结任务包投影、十个既有 Stage 整阶段复审工件、它们的接口责任链和治理投影。它不重定义业务事实，不建立第二权威事实源，也不把旧 Stage 的历史运行时检查器误当作当前运行入口。

复审矩阵覆盖：锁注册与竞态控制、自动生命周期、Worker 崩溃恢复、半成品清理、文件类型检测、解析器路由、解析器输出、失败降级、差异化评估和提示注入标记。每一项均绑定其冻结任务包引用、复审说明、检查器、聚焦用例和本地 machine run 引用。

## 批次结果

| 项目 | 结论 | 白箱依据 |
|---|---|---|
| 十个 Stage 复审矩阵 | 通过 | `stage041_050_batch_review_contract.json` 要求连续的 041–050、十个验收 ID、现存复审工件和本地运行记录。 |
| 接口责任链 | 通过 | 041→042→043→044→045→046→047→048→049→050 的职责边界被显式声明；不把任一控制证据转换为运行时行为。 |
| 单一事实源 | 通过 | 合同只引用冻结任务包和既有复审证据；不创建业务资料、样本库、平行台账或新的权威来源。 |
| 可恢复性 | 通过 | 仅撤回本批次的复审说明、合同、检查器、用例、machine run、事件和治理投影，即可恢复到 Stage050 本地复审完成状态；十个 Stage 既有证据保持不变。 |
| 运行与外部边界 | 通过 | 没有文件识别、真实路由、解析、降级、质量门、持久化、Agent、模型调用、OVH、生产服务或应用重装。 |
| 全局上传锁 | 通过 | 本批次不进入上传门。只有所有冻结任务包 Stage 与最终 `ACC-STAGE-168` 均完成并通过最终验收后，才可由独立全局门重新评估上传资格。 |

## 发现与修复

| 编号 | 级别 | 发现 | 修复 |
|---|---|---|---|
| `BATCH041-050-REVIEW-F1` | Important | 旧的“批次复审后进入批次上传”路线未表达“所有任务包整体完成后才可上传”的冻结条件。 | 批次完成后只转到 `IDS-STAGE051-P1-GATE`；`IDS-V0_1-BATCH-041-050-UPLOAD-GATE` 仍是延后门，`ACC-STAGE-168` 前不具资格。 |

## 不做什么

- 不读取、列举、打开、复制、散列或修改 `/Users/linzezhang/Downloads/IDS_MetaData` 的任何内容。
- 不打开 IDS 业务来源、文件正文、页面、图像、来源路径或 Owner fixture。
- 不执行真实文件类型检测、路由、parser、fallback、提示注入标记、质量门、人工队列、证据提升或持久化。
- 不启动 Agent、模型调用、模型 Token、OVH、生产服务、上传、合并或应用重装。
- 不进入 Stage051；本轮以 `NO_STAGE051_THIS_RUN` 停止。

## 验证与停止条件

本门的检查器必须同时确认合同形状、十个工件、十个批次状态、接口链、治理路线、中文投影和全部关闭项。任何缺失、未知字段、Stage 失败、路线漂移或开关打开都返回 `FAIL_CLOSED`。

验证命令：

```bash
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_batch041_050_review_gate
python3 -B KM_IDSystem/scripts/check_batch041_050_review.py
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_stage005_governance_regression
python3 -B KM_IDSystem/docs/pursuing_goal/ids_v0_1/validate_stage005_governance_regression.py
```

本轮只在所有上述本地检查通过后结束。它不证明真实 OCR、真实解析质量、OVH 部署、生产可用或任何上传状态。

## 回滚

只回滚本批次复审说明、批次合同、检查器、聚焦用例、machine run、事件、批次锁、路线图、机器事实、中文视图和交接，恢复为 `STAGE050_REVIEWED_LOCAL_PROMPT_INJECTION_MARKER_RUNTIME_DISABLED`。保留冻结任务包、Stage041–050 全部既有证据、原始资料、外部系统状态及任何后续 Stage 状态。
