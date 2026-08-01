# KMFA 每日资金

本目录实现 TaskPack `KMFA_每日资金_v0.0.0.1_FINAL_TASKPACK` 的独立云端纵向切片。它在 `KMFA/deploy/coolify/docker-compose.yml` 以 `daily-funds` 服务运行，拥有自己的 DWS 配置、SQLite、命名卷和 cron；不挂载 `skills` 服务的 volume。

## 运行状态

代码可离线验证，但任何生产身份、专用 DWS 群、真实附件类型、D1/R2/OCI 凭据或恢复结果没有证据时都不是 PASS。启动时 `preflight` 会把状态写成 `需处理 / CONFIG_INVALID`，而不是伪造健康。

## 本地无数据验证

```bash
python3 -m pytest -q KMFA/skills/每日资金/tests/test_daily_funds_contract.py
python3 KMFA/tools/check_baseline_slices.py
```

测试只使用合成数据，覆盖整数分边界、3/6 月覆盖门、双事实表、页二失败不推进 cursor、原始分块重组、D1 故障不移动 pointer 和旧阈值回流扫描。它不替代目标群真实采集验证。

## 回滚

- 应用：从 Coolify 回滚到前一已知 image/source；保留所有 `kmfa-daily-funds-*` named volumes。
- 发布：`current.json` 只在 D1 Oracle 后原子替换；失败时保留上一份 VALID snapshot。
- 数据：以 OCI 不可变 restore manifest 回读 Git bundle、D1 export 和 R2 inventory；逐件 hash 校验后，在空 bare Git 库实际导入 bundle 并确认 publication 所引原始 commit。仅当 D1 重建和查询 Oracle 都成功，才原子替换 `current.json`。Git 私库仍是原始数据权威；禁止删除 Git/R2/OCI/SQLite 卷来“修复”。

恢复运行只接受不可变 publication ID：

```bash
python3 /opt/daily-funds/scripts/run_daily_funds.py restore --publication-id <64位publication_id>
```

每月恢复演练另需在 Coolify 配置与正式库不同的 `DAILY_FUNDS_RESTORE_DRILL_D1_DATABASE_ID`；空值或正式库 ID 会失败关闭。

生产变量键位在 `KMFA/deploy/coolify/.env.example`。值只可由 Coolify Secret 注入，不得放入本仓、命令参数或日志。
