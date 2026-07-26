# 已锁定 Owner 决策

1. 产品名统一为 IDS / Industrial Data System。
2. 当前代码路径仍为 `OpMe_System`，但新 UI、报告、文档不使用旧产品名。
3. 本次任务只开发 v0.1。
4. v0.2+ 只保留未来框架，不作为本次 Codex 执行任务。
5. macOS + M2 Max + Docker Desktop / Docker Compose 是 v0.1 默认运行环境。
6. 内置硬盘约 800GB；PostgreSQL 控制面放稳定本机/Docker volume，不放会被拔掉的移动硬盘。
7. 5TB 移动硬盘作为 `IDS_DATA_ROOT`，用于原始资料、处理后数据、报告、备份导出、manifest。
8. GitHub 不存 500GB 原始资料，只存代码、schema、manifest template、taskpack、治理文件、小型 fixtures。
9. 移动硬盘目录结构为：

```text
我的硬盘/
  OtherFolder1/
  IDS_DATA_ROOT/
    00_ORIGINAL_RAW_DATA/
    01_PROCESSED_BY_CODEX/
    02_DATABASE_BACKUPS/
    03_INDEX_EXPORTS/
    04_REPORTS/
    05_AUDIT_LOGS/
    06_ERROR_REPORTS/
    99_MANIFEST/
```

10. Codex 默认不得移动、删除、覆盖 `00_ORIGINAL_RAW_DATA`。
11. v0.1 支持自动解压，但必须安全解压到 staging 区。
12. OCR 默认中文简体 + 英文。
13. external_api_policy 默认 denied，owner 不需要逐个标记 chunk；策略从数据源/文档继承。
14. 每次批量导入后触发索引重建；旧索引在重建期间继续服务。
15. 最终开发方式：每次给 Codex 一个 Stage 的追求目标（Pursuing Goal），不要一次性要求全部实现。
16. 开发节奏按每天 8-10 小时强推进估算，但路线图只写每个 Stage 的预计实际执行开发时间，单位为小时。
