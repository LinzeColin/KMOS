---
name: daily-funds-skill
description: 独立云端每日资金纵向切片；仅从指定钉钉群历史消息取数，原始证据进入 Private-Database，经过整数分勾稽后投影到 KMFA 私有页面。
---

# 每日资金

这是一个运行在 Coolify 的确定性服务，不是一个 Agent 提示词。运行时不得调用模型、其他 Skill、本机路径、事件触发或既有 DWS profile。

## 唯一输入与输出

- 输入：`dws chat message search-advanced` 对唯一群 ID 的历史消息；消息须同时匹配唯一发送人 ID 与允许文档族（资金账户明细表、资金流水明细/资金明细）。
- 原始权威：私有 GitHub `LinzeColin/Private-Database` 的 `Private-KMDatabase/KMFA/daily_funds`。仅本服务 single writer 获 Owner 窄例外使用 sparse clone；禁止全库 clone 与 force push。
- 查询投影：Cloudflare D1；热镜像：Cloudflare R2；异地冷备：OCI Object Storage；本地 SQLite 仅含 cursor/inbox/idempotency/outbox/runtime journal。
- 页面：KMFA 私有 `/ops/app?tab=每日资金` 或 `/ops/daily-funds`，Cloudflare Access 保护；根页和公共 API 不暴露金额、附件、ID 或下载链接。

## 固定运行合同

- `*/15` 北京时间：历史轮询，正常页的 `hasMore=false` 才完成，任一页失败不得推进 durable high-water；增量重叠 30 分钟。
- `* * * * *`：授权探测，同一 incident 每 360 分钟最多一次 outbox 记录。
- `0 * * * *`：DWS 显式认证状态保活。
- 每日：最大 7 天的回填、OCI 冷备重试、自主观察；回填永不替换较新的 live pointer。
- 金额：只用整数分/Decimal。固定高风险线 `60_000_000` 分，固定关注线 `120_000_000` 分；动态线为完整自然月 3/6 月平均日可用余额，或经过版本控制的自定义日期/数值线。
- 余额日：仅北京周六、周日可承接上一 VALID 余额并计为承接天；缺失工作日一律标 `coverage_gap` 并从动态线覆盖计算排除。未确认的法定假日不擅自承接，宁可停用动态线。
- 发布：Git 原始字节回读 → R2 → 解析 → 零分勾稽 → D1 事务/查询 Oracle → 私库 publication → atomic current pointer → OCI 异步冷备。R2/D1/Git 任一失败不切 pointer；OCI 失败只显示冷备滞后。
- 恢复：只接受 OCI 不可变 restore manifest；先 hash 校验 Git bundle、D1 export、R2 inventory，再在空 bare Git 库实际导入 bundle 并确认 publication 引用的原始 commit，重建 D1 并通过查询 Oracle 后才切换 pointer。
- 演练：每月 1 日 05:00 北京时间将最新 immutable publication 恢复至**独立非生产 D1**并运行同一 Query Oracle；配置为空或误指向正式 D1 必须失败关闭。

## 三态与停止条件

人类状态只有：`已更新`、`处理中`、`需处理`。风险标签（正常/关注/高风险/动态偏低/数据不足）不能替代运行状态。

以下任一条件立即保持上一份 VALID publication 并进入 `需处理`：授权、来源三重匹配、附件字节、解析模板、业务日期、勾稽、Git/R2/D1、恢复 Oracle 或配置身份不满足。`UNKNOWN` 永远不能写成 PASS。
