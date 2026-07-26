# IDS v0.1-only 最终中文执行包（修订版）

本包替代此前的 `IDS_Taskpack_Final.zip`、`IDS_Codex_Development_Roadmap_Final.txt` 和 `IDS_Codex_Usage_Instructions_Final.txt`。

本包只把 **v0.1** 作为当前可执行开发任务；v0.2 到 v2.0+ 只保留压缩后的未来框架，不再生成大量可执行 Stage，避免占用当前 Codex 上下文和开发资源。

## 当前版本路线

```text
v0.1 → v0.2 → v0.3 → v0.4 → v0.5 → v1.0 → v1.5 → v2.0+
```

## 当前执行范围

```text
当前只开发 v0.1。
v0.2+ 不在本次 Codex 执行范围内。
v0.2+ 仅保留 future_framework，用于未来规划。
```

## 两个入口

```text
人类产品入口：面向客户、业务人员、工程人员、管理人员。
IDS 系统运营入口：面向 owner/admin/operator/developer，合并机器控制、数据治理、运行可靠、交付质量门禁。
```

## Stage 编号规则

Stage 采用全局累计编号，不按 Domain 重置。

```text
D01：STAGE-001 至 STAGE-005
D02：STAGE-006 至 STAGE-011
D03：STAGE-012 至 STAGE-017
……
D26：STAGE-162 至 STAGE-168
```

## 并行度字段

每个 Stage 都使用：

```text
建议并行度：是/否
并行说明：如果为“是”，写清楚可以和谁并行，或至少应在哪个 Stage 前完成。
```

## Phase 设计修正

本包已经取消通用重复的 Phase 3 / Phase 4。每个 Stage 的 Phase 3 和 Phase 4 按 Domain 与 Stage 特殊性定制，重点检查数据完整、安全、失败恢复、UI/UX、运行可靠和交付证据。
