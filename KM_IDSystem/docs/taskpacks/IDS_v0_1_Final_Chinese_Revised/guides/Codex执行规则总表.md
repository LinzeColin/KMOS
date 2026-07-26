# Codex 执行规则总表

1. 当前只执行 v0.1。
2. Stage 编号全局累计，不按 Domain 重置。
3. 每次只执行一个 Stage。
4. 每个 Stage 最多 4 个 Phase；每个 Phase 最多 5 个 Task。
5. Stage 内 Phase 3 和 Phase 4 已按能力域定制，不再使用通用重复模板。
6. 建议并行度只有“是/否”。为“是”时必须写明可与谁并行或至少在哪个 Stage 前完成。
7. 真实原始资料、secrets、API key、数据库密码、云端凭证不得提交到 GitHub。
8. `00_ORIGINAL_RAW_DATA` 默认不可移动、删除、覆盖。
9. 没有真实测试输出不得声称完成。
10. v0.2+ 未来框架不作为本次 Codex 实施任务。
