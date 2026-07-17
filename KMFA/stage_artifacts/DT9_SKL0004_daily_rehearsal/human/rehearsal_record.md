# SKL.0004 日检技能本地演练（2026-07-17 深夜）

- **真实输入端到端 dry-run 通过**：OneDrive `DWS_Outputs.zip` → 规则检查 → 通知事件生成 → `LOG_ONLY_DRY_RUN`（零投递）
- 业务正确性佐证：正确检出 `SOURCE_STALE`（zip 内聊天记录最新 2026-07-16 vs 检查日 07-17）
- **天然对齐 Owner 授权**：该技能通知对象原生即「张霖泽」（`target_label`）
- 基座修正：`morning_1135/evening_1705` 即工作检查业务窗（沪 11:35/17:05）——crontab 撤销我虚构的 11:30 日检位，work-check 双窗接真实入口；`--send/--dry-run` 由 `KMFA_DELIVERY_ENABLED` 机械切换（双跑纪律代码化）
- 云端输入路径：`KMFA_DAILY_INPUT_ZIP`（默认 /opt/kmfa/data/DWS_Outputs.zip，经 KMDatabase/data 中转，审计既定路线）
