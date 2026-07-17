# DATA.0001/0002 接入登记完成记录（2026-07-17）

- 截止批次：2026-07-16 批（53 业务文件 / 120M / 三域），指纹快照 = KMDatabase/data/manifest.jsonl（D11：Owner 确认全仓 public 后已入仓，PR #7）
- 公开聚合：31 xlsx + 9 xls + 8 pdf + 3 zip + 2 doc（与任务包 06 圈定口径逐字一致）
- 分级：A0 核心财务 29 ｜ A1 项目合同回款 13 ｜ A2 绩效 1 ｜ B 待议（pdf/doc）10
- 登记：53/53 → KMFA/metadata/imports/raw_file_manifest.jsonl（import_run_id IMP-20260717-193000-kmdb-batch-8142e3dc）；schema 必填字段 + id 正则全合规；raw 字节零入 KMFA/
- zip 安全预检：3 个 zip（金蝶明细账/税务申报/钉钉）成员清单落 .codex_private_runtime（不 tracked），公开面仅聚合计数，可疑成员 0
- 幂等：复跑 = IDEMPOTENT_NOOP
- **范围默认判定（Owner 48h 异议期，自 2026-07-17 晚起算）**：40 个 Excel + 3 个 zip 全接入（D6=A）；8 pdf + 2 doc 按 B 级"登记+关键字段人工录入"处理（DATA.0008），不做全文 OCR。无异议即按此执行。
