# IDS v0.1 BATCH-051-060 独立批次复审门

- 批次：`IDS-V0_1-BATCH-051-060`
- 任务：`IDS-V0_1-BATCH-051-060-REVIEW-GATE`
- 范围：`STAGE-051..STAGE-060`
- 验收范围：`ACC-STAGE-051..ACC-STAGE-060`
- 当前结论：十个既有整阶段复审证据已形成连续的本地白箱批次矩阵；运行、外部服务与上传路径继续关闭。
- 当前开关：`push_allowed=false`，`github_upload_allowed=false`
- 本轮边界：`NO_STAGE061_THIS_RUN`
- 后续入口：`IDS-STAGE061-P1-GATE`

## 复审目标

本门只复审冻结任务包投影、Stage051–060 的既有整阶段复审工件、接口责任链和中文治理投影。它不重定义任何业务事实、不建立第二权威事实源，也不把旧 Stage 的控制检查器误作当前运行入口。

矩阵依次覆盖 OCR 队列、中英文合同、按页输出、低置信度人工复核、回归语料、缓存保留、XLSX/CSV 接入、Schema 推断、事实抽取和表格到 RAG 摘要。每一项都绑定冻结任务包、复审说明、检查器、聚焦用例和既有本地 machine run 引用。

| 项目 | 结论 | 白箱依据 |
|---|---|---|
| 十个 Stage 复审矩阵 | 通过 | `stage051_060_batch_review_contract.json` 要求连续 Stage、验收 ID、既有复审工件和 machine run 引用完整。 |
| 接口责任链 | 通过 | 051→052→053→054→055→056→057→058→059→060 的职责边界被明确保留。 |
| 单一事实源 | 通过 | 仅引用冻结任务包和既有本地复审证据；不创建业务资料、样本库、平行台账或新的权威来源。 |
| 可恢复性 | 通过 | 仅撤回本批次说明、合同、检查器、用例、machine run、事件和治理投影，即可恢复 Stage060 本地复审完成状态。 |
| 运行与外部边界 | 通过 | 没有 OCR、XLSX/CSV 解析、Schema 推断、事实抽取、RAG、质量门、持久化、Agent、模型调用、OVH、生产服务或应用重装。 |
| 全局上传锁 | 通过 | 本批次不进入上传门；仅在冻结任务包至 `ACC-STAGE-168` 全部完成并经独立全局验收后，才可重新评估上传资格。 |

## 不做什么

- 不读取、列举、打开、复制、散列或修改 `/Users/linzezhang/Downloads/IDS_MetaData` 的任何内容。
- 不打开 IDS 业务来源、文件正文、页面、图像、来源路径或 Owner fixture。
- 不执行 OCR、真实 XLSX/CSV 检测或解析、Schema 推断、字段或事实抽取、RAG 摘要、数值统计、质量门、持久化或真实回滚。
- 不启动 Agent、模型调用、模型 Token、OVH、生产服务、上传、合并或应用重装。
- 不进入 Stage061；本轮以 `NO_STAGE061_THIS_RUN` 停止。

## 验证与停止条件

检查器必须同时确认合同形状、十个工件、十个阶段状态、接口链、治理路线、中文投影和全部关闭项。任何缺失、未知字段、阶段失败、路线漂移或开关打开都返回 `FAIL_CLOSED`。

```bash
python3 -B -m unittest -q KM_IDSystem.docs.pursuing_goal.ids_v0_1.tests.test_batch051_060_review_gate
python3 -B KM_IDSystem/scripts/check_batch051_060_review.py
python3 -B KM_IDSystem/scripts/check_batch041_050_review.py
python3 -B KM_IDSystem/docs/pursuing_goal/ids_v0_1/validate_stage005_governance_regression.py
```

本门只证明本地静态复审一致，不证明真实 OCR、真实表格处理、真实事实、真实 RAG、OVH 部署、生产可用或任何上传状态。

## 回滚

只回滚本批次复审说明、批次合同、检查器、聚焦用例、machine run、事件、批次锁、路线图、机器事实、中文视图和交接，恢复为 `STAGE060_REVIEWED_LOCAL_TABLE_RAG_SUMMARY_RUNTIME_DISABLED`。保留冻结任务包、Stage051–060 既有证据、原始资料、外部系统状态及任何后续 Stage 状态。
