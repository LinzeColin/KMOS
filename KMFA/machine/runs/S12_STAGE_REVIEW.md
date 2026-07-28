# S12 whole-stage review —— 可观测性、告警、成本与演练

范围：`T-S12-01..04`
结论：**PASS**

| 任务 | pass_gate | 落点 |
|---|---|---|
| T-S12-01 | 关联率 100%，**敏感命中=0** | `journey_correlation` / `telemetry_sensitive_hits` |
| T-S12-02 | **自愈保持幂等和数据不变量** | `plan_remediation` / `alert_is_actionable` |
| T-S12-03 | 每类资源有预算/owner/告警 | `budget_gaps` / `unit_cost` / `service_trigger_met` |
| T-S12-04 | 演练证据可复现，缺陷有 owner/期限 | 与 S11 的 chaos/RPO-RTO 同一套判据 |

## 没有 trace_id 的 span 就是断的

一条断了的链路在排查时的价值是零，而**它在仪表盘上看起来是正常的**。
所以 orphan 逐条列名，而不是只给一个关联率。

## 自愈：宁可不愈，不可愈错

T-S12-02 的 stop_condition 是「自愈会删除唯一数据、重复财务操作或
跨 workspace 修改」。所以：

- **危险类**（delete / purge / transfer_funds / refund / cross_workspace_write /
  drop_table / rotate_production_secret）**永远只生成工单**；
- **安全类**（retry / isolate / recompute / scale_out / …）才可自动执行；
- **不在白名单里的一律只生成工单**——未知动作自动执行一次，就够了；
- **不幂等的动作永不自动重试**——重试一个不幂等的动作等于把一次故障放大成 N 次。

这个分界**硬编码在代码里，不是配置**——配置会被改。

## 告警必须可执行

缺 symptom / runbook / owner / diagnostic_bundle 任一即判失败。
**没有 runbook 的告警是一次打扰**，它唯一确定的效果是让人更快学会忽略告警。

## 预算缺 owner 的意思是「超了没人管」

每类资源三件齐全（预算、owner、告警阈值），缺一即缺口。
新增服务的触发条件必须是**数**——「感觉需要了」无法被复核，也无法被反驳。

## 实测

`tests/test_s10_s13_posture_and_release.py` —— 敏感遥测检出、
孤儿 span 列名、7 类危险动作逐个只出工单、未知动作默认工单、
不幂等不自动、告警四件套、预算缺口、单位成本整数、触发条件必须量化。
