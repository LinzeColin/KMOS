# cloud_tasks —— 云端任务 C4 / C5 产物（中转区，不合并主干）

2026-09-23，由 Claude Code 云端会话产出。只用了公开信息，不含任何内部数据。

**这个目录只是中转站。** KMOS 是代码仓，按 AGENTS.md 的数据落地铁律，长期数据不进代码仓。云端会话拿不到 `gh` 和 Private-Database 的权限，所以先放在分支 `claude/dreamy-galileo-8luxw4` 上，**不要合并进 main**。

## 本地接手步骤
1. 拉回本地：`git fetch origin claude/dreamy-galileo-8luxw4 && git checkout claude/dreamy-galileo-8luxw4`（或者用 `git worktree add`）。
2. 取件：`回件/C4.txt`、`回件/C5.txt` 已经是 KM00 的取件格式（按「=== 文件: 」切分），可以直接放进共享盘的 `云端任务/回件/`，由 KM00 复审后落到 `B00协作/云端任务/产物/C<号>/`。
   如果改过文件，先运行 `python3 make_huijian.py` 重新生成回件。
3. 长期数据：两份 CSV 用 `KMDatabase/machine/tools/private_db_client.py ingest Private-KMDatabase <文件>` 写进私有库。
4. 自测：`python3 C4/labor_cost.py test`、`python3 C5/tender_volume.py test`。只用标准库，可以离线跑。

## 本地 agent 最值得补的（云端做不到，因为网络被拦 EGRESS_BLOCKED）
- **C4**：下载 C4/README「查了没有」里列出的 6 份官方 PDF 附件，把数字补进 `人工单价.csv`，再运行 `labor_cost.py gap`。
- **C5**：从千里马、剑鱼或集团平台导出近 60 天的公告清单，运行 `tender_volume.py count`，得到真实的每工作日条数，再回填 `类别标量.csv`。

## 目录
| 路径 | 内容 |
|---|---|
| C4/README.md | 摘要、查了没有、复审结论 |
| C4/人工单价.csv | 41 行人工单价和工资 |
| C4/labor_cost.py | 单位换算、定额与市场比较、成本计算（6 项测试） |
| C5/README.md | 摘要、查了没有、统计噪声、复审结论 |
| C5/类别标量.csv | 16 个类别的汇总 |
| C5/样例公告.csv | 55 条样例公告 |
| C5/tender_volume.py | 归类、去重、按工作日计数、金额分档（6 项测试） |
| 回件/C4.txt, 回件/C5.txt | KM00 取件格式的全文 |
| make_huijian.py | 重新生成回件 |
