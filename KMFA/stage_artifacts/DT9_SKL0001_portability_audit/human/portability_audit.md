# SKL.0001 可移植性审计（skills 上 Oracle 前置）

> 任务：`TSK.KMFA.SKL.0001` ｜ 日期：2026-07-17 ｜ 结论：**全部技能可上云，无硬阻断**；两个前置（dws 安装+登录、OCR 替换）与一个数据路由改道（OneDrive→KMDatabase/data）。

## 逐技能处置表

| 技能 | macOS 专属依赖 | 外部依赖 | 云端处置 | 前置 |
|---|---|---|---|---|
| 钉钉考勤（在产） | 无（生产代码纯 Python；`BROWSER=/usr/bin/false` 已内建防弹窗） | `dws` CLI（契约面：`contact dept/user`、`attendance group/report/record/summary`、`chat message send`、`ding message send`、`chat message send-by-webhook`） | **直迁**：`run_attendance.py --run-type morning/evening`；秘钥走 `metadata/dingtalk_attendance/private_runtime/.env.local`（gitignored）或容器 env | dws v1.0.52 + `auth login --device` + `pat browser-policy --enabled=false` + `KMFA_DINGTALK_ATTENDANCE_ALLOW_DWS_COMMANDS=1` |
| 每日工作检查 | 无 | OneDrive `DWS_Outputs.zip` 只读输入 | **直迁 + 输入改道**：输入从 OneDrive 改为 `KMOS/KMDatabase/data`（Mac 采集端入仓后拉取） | DT5 数据入仓机制（DATA 线） |
| 资金周报 | **swift OCR**（`tools/generate_screenshot_ocr_sidecars.py`，macOS Vision） | 截图证据输入 | **OCR 替换后直迁**（SKL.0005：默认 PaddleOCR、tesseract 兜底，替换后与 swift 版历史输出对账） | SKL.0005 |
| 经营月报 | 无 | 七输入槽位（文件） | **直迁**：`scripts/mgmt_monthly_report.py`；输入经 KMDatabase/data | DT5 数据入仓机制 |
| 上游归档（钉钉 DWS 全量归档） | 文档提及 launchd（作废，改 cron） | `dws`（drive/存储命令面） | **直迁**，先在 v1.0.52 上核对 drive 命令面与参数兼容性再启用 | dws 同上 |
| 红圈主合同导出 | 真实 Chrome UI（浏览器自动化） | 红圈 `cloud.hecom.cn` 网页 | **例外：留 Mac 采集端**（09 七节既定），产物经 KMDatabase/data 中转 | 无 |

## dws 依赖定案（SKL.0008）

- `dws` = 钉钉**官方开源** CLI：`DingTalk-Real-AI/dingtalk-workspace-cli`（Go，macOS/Linux amd64/**arm64**，204+ 命令，`--format json` 与技能契约一致；守卫引用的 `dws pat browser-policy --enabled=false` 与之原文对上）。
- 固化版本 **v1.0.52**（2026-07-15 稳定版），安装走 `KMFA/deploy/skills-runtime/install_dws.sh`（SHA-256 锁定）。
- 无人值守：`dws auth login --device`（设备码流，官方支持 Docker/SSH/CI；一次性 Owner 确认）；备选自建应用 `--client-id/--client-secret`；凭证 AES-256-GCM 加密存储，Linux 落 `~/.local/share/dws-cli/`。
- 备选方案（若 arm64 资产缺失或设备码不可用）：Python 直连钉钉开放 API 的兼容 shim——调用面已锁定并记录于此，按需再实现。

## 排程与时区

原 6 条排程钟面为本机（悉尼）时间；容器 TZ=Australia/Sydney 保持钟面一致，考勤代码对钉钉数据内部固定 Asia/Shanghai。投产前请 Owner 确认一次钟面口径。

## 双跑与测试授权

- 钉钉考勤切换执行 SKL.0003 双跑制：云端 dry-run ≥3 天与现运行端比对 → 一致后一刀切换 → 旧端同刻停用（防双发）。
- 测试投递收发对象：Owner 2026-07-17 授权可用「张霖泽」（`deploy/skills-runtime/test_send.sh`，默认 dry-run）。
