# 钉钉DWS归档 / DWS 全文件原始数据归档

本项目只负责钉钉群聊的全文件原始数据归档，不负责周报、月报、业务分析结论或经营判断。

## 当前运行边界

- 只允许通过 Codex automation 或用户手动让 Codex 唤起脚本执行。
- 禁止本机 `launchd` 或本地脚本无人值守自动跑。
- `scripts/archive_dingtalk_all_files.py` 是 Codex 受控执行器。
- `scripts/run_daily.sh`、`scripts/run_weekly.sh` 仅作为 Codex 受控 wrapper；没有 `DWS_CODEX_CONTROLLED=1` 时会拒绝运行。
- `launchd/com.linze.dingtalk-dws-archive.daily.plist` 和 `launchd/com.linze.dingtalk-dws-archive.weekly.plist` 保留为历史配置，但已标记 `Disabled=true`。

Codex automation：

- 名称：`每日钉钉DWS归档`
- 时间：每天 11:00 和 19:00
- 旧 automation `钉钉 DWS Archive 每日运行检查` 应删除。
- automation 只触发 Codex 受控流程，不直接绕过 Codex 调本机定时任务。
- 增删改 `config/target_groups.yaml` 的目标群时，必须同步检查并更新 Codex automation；automation 不得硬编码旧群清单，验证应从当前配置动态读取所有 enabled 群。

Codex 受控运行命令：

```sh
DWS_CODEX_CONTROLLED=1 DWS_RUN_SOURCE=codex_manual /bin/sh scripts/run_daily.sh
```

Codex automation 使用：

```sh
DWS_CODEX_CONTROLLED=1 DWS_RUN_SOURCE=codex_automation DWS_AUTOMATION_NAME="每日钉钉DWS归档" /bin/sh scripts/run_daily.sh
```

运行前脚本必须展示本次会处理哪些群、哪些跳过、cursor 起点和预计风险；运行后必须写中文报告和机器 JSON。

## 关键文件

| 路径 | 用途 |
| --- | --- |
| `config/target_groups.yaml` | 唯一当前目标群配置 |
| `scripts/archive_dingtalk_all_files.py` | Codex 受控主执行器 |
| `scripts/validate_dws_output_structure.py` | 输出结构、热窗口、镜像和冷存储验证 |
| `scripts/sync_notion_skill_backup.py` | skill/config 指纹和恢复说明同步 |
| `scripts/run_daily.sh` | Codex 受控每日 wrapper |
| `scripts/run_weekly.sh` | Codex 受控维护 wrapper |
| `data/all_files_manifest.sqlite3` | 永久 manifest、消息表、cursor 表 |
| `data/archive/` | 本机热存储文件本体，只保留最近 60 天 |
| `reports/daily_report.md` | 中文人类可读报告 |
| `reports/daily_summary.json` | 机器可读 JSON |

## 群配置规则

`scan_mode` 只能是：

- `auto`：Codex automation 被触发时可主动扫描。
- `manual_only`：不会被 automation 主动扫描，只能用户显式指定手动补扫、重建包、查历史。
- `manual_only` 群不会主动调用 DWS 扫描，但当前包仍必须从历史 manifest/messages 重建该群目录和质量证据，不能因为跳过扫描而从 `DWS_Outputs.zip` 消失。

`group_type` 只能是：

- `standing`：常驻群，默认长期 `auto`，不因日期自动停止。
- `project`：项目群，必须有 `start_date`、`completed_date`、`grace_days`；成功增量扫描确认连续 7 天无新增消息和文件时，自动记录最后一次有消息的时间为 `completed_at`/`completed_date`，并把 `scan_mode` 转为 `manual_only`。

当前分类：

- `生产管理群`：常驻，auto
- `2026年商务部报价群`：常驻，auto
- `付款请示群`：常驻，auto
- `松滋葛洲坝小齿调整（原为调窑）2026.06.28`：项目，按配置决定 `auto` 或 `manual_only`
- `萍乡钢铁2026.6.3`：项目，按配置决定 `auto` 或 `manual_only`
- `湘东区萍乡钢铁20260622`：项目，按配置决定 `auto` 或 `manual_only`
- `盐湖海纳大齿圈小齿更换2026.7.5`：项目，按配置决定 `auto` 或 `manual_only`
- `内蒙古金鄂博氟化工2026.7.5`：项目，按配置决定 `auto` 或 `manual_only`
- `山东日照检修群`：项目，按配置决定 `auto` 或 `manual_only`

## Cursor 与扫描规则

- 每个群在 SQLite `group_cursors` 表维护独立 cursor。
- 成功扫描到 `hasMore=false` 后才更新 cursor。
- 下一次 `auto` 扫描从该群 cursor 之后开始。
- 不再每日默认从 `2026-01-01` 或项目 `start_date` 全量扫描。
- 手动全量 reconciliation 需要显式传 `--full-reconciliation`。
- cursor 更新 fail closed：如果扫描没有完成边界，cursor 不更新。
- 长时间跨度的常驻群和项目群是正常对象，不是异常。
- 全时、全盘、全量、深度完整收集是硬要求：不得为缩短 automation 运行时间而截断页数、缩短时间窗、跳过历史资源、只扫最近消息或抽样。
- 长跨度扫描必须依靠每群 cursor、heartbeat 和可恢复报告来保证可观测性；只要 heartbeat 或子进程仍在推进，就不得把长运行直接判定为失败。
- 真正的阻塞判定必须基于无 heartbeat、无日志增长、无 DWS 子进程进展且超过 `stale_heartbeat_minutes_before_blocked`。
- DWS 网络韧性：所有 DWS CLI 调用必须显式传 `--timeout`，当前 `dws_http_timeout_seconds=120`；遇到 `io_timeout`、`request_timeout`、`dial tcp`、`context deadline` 等瞬态网络错误时最多按 `dws_command_retries=3` 重试，退避基准 `dws_retry_backoff_seconds=5` 秒。
- 项目群自动完工规则：当本轮扫描成功到 `hasMore=false`，本轮无新增消息、无新增文件信号，且距 `group_cursors.last_message_time_seen` 已满 `project_auto_complete_idle_days=7` 天，脚本会自动写回 `config/target_groups.yaml`，将该项目群转为 `manual_only`；后续 automation 不再主动扫描，但仍允许用户显式补扫、重建包和查历史。

## 失败资源 backoff

- 每个资源最多主动尝试 3 次。
- 超过 3 次后标记 `exhausted=1`。
- exhausted 资源不再每日主动重试。
- exhausted 仍保留在 manifest、missing、status 和报告中。
- 用户可显式传 `--retry-exhausted` 手动补扫。

失败记录保留：

- `attempt_count`
- `first_failed_at`
- `last_failed_at`
- `attempted_methods`
- `dws_error_code`
- `error_summary`
- `next_action`
- `exhausted`

## 输出与存储

当前交付包：

```text
/Users/linzezhang/onedrive/DWS_Outputs.zip
```

语义：

- `DWS_Outputs.zip` 只包含热存储窗口内的数据。
- 热存储窗口：最近 60 天。
- 60 天及以上文件本体迁入冷存储。
- 冷存储目录：`/Users/linzezhang/onedrive/DWS_Archive/<群名>/files/MM/<文件>`
- 冷存储不使用年份目录，不生成 zip。
- 历史残留的冷存储 `files/MMDD/` 会在真实运行中安全迁移为 `files/MM/`，并同步更新 SQLite manifest 路径。
- 冷存储文件不进入当前 `DWS_Outputs.zip`。
- SQLite manifest 永久保留冷热路径和追溯字段。
- 本机 `data/archive/` 只保留最近 60 天文件本体。
- `~/Downloads/DWS_Outputs/` 只是临时构建输出，OneDrive 当前包验证通过后删除。

当前包内每群结构：

```text
DWS_Outputs/<群名>/
├── files/
│   └── MM/
│       └── <下载文件>
├── chat_records/
│   ├── chat_records.csv
│   ├── chat_records.jsonl
│   └── raw_messages.jsonl
├── _manifest/
│   ├── manifest.csv
│   ├── missing_media.csv
│   ├── chat_record_files.csv
│   └── status.md
└── _analysis/
    ├── recent_30d_file_records.csv
    └── similar_recent_30d.csv
```

禁止生成或保留每群 `<群名>_latest.zip`。

## 清理规则

- `data/staging/` 超过 24 小时的临时文件可清理；清理前必须确认没有其他正在运行的 DWS 归档进程。
- `logs/` 本机只保留 15 天；15 天以上日志必须先写中文摘要到 Notion，再删除本机旧日志。
- 日志摘要不得包含 token、open_conversation_id、完整 resource_id、cookie、账号敏感信息。
- `reports/` 保留必要质量证据；旧报告可摘要入 Notion 后轮转。

## Notion 同步

skill/config 变化后必须同步 Notion。

- 有 `NOTION_TOKEN` 或 `NOTION_API_KEY`：用 API。
- 没有 token：用 Notion connector；本项目 automation 视为允许使用 connector 读写 Notion。
- connector 不可用：尝试 Chrome/computer-use。
- 都失败：写 `reports/notion_skill_backup_pending.md`，最终报告必须明确 pending 路径。
- Notion 只写中文摘要、关键指标和脱敏配置，不写敏感 ID。

## 验证命令

```sh
/usr/bin/python3 -m py_compile scripts/archive_dingtalk_all_files.py scripts/weekly_dws_smoke.py scripts/sync_notion_skill_backup.py scripts/validate_dws_output_structure.py
/bin/sh -n scripts/run_daily.sh scripts/run_weekly.sh
plutil -lint launchd/com.linze.dingtalk-dws-archive.daily.plist launchd/com.linze.dingtalk-dws-archive.weekly.plist
/usr/bin/python3 scripts/validate_dws_output_structure.py --config config/target_groups.yaml --mirror "/Users/linzezhang/onedrive/DWS_Outputs.zip" --expect-downloads-deleted --hot-days 60 --summary-json reports/daily_summary.json --cold-root "/Users/linzezhang/onedrive/DWS_Archive"
```

## 安全边界

- 只使用官方 DWS CLI。
- 不读取浏览器 Cookie、Keychain、钉钉 live DB 或私有 API。
- 不把 `open_conversation_id`、token、账号信息写入 Notion、聊天或公开文档。
- 不删除 `data/all_files_manifest.sqlite3`、manifest 历史记录、reports 必要质量证据、Notion 同步状态或冷存储文件。
