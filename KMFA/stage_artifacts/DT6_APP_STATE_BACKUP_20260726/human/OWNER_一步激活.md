# 备份已自助激活 —— 你不用做任何事

> **2026-07-26 终态**：Owner「你自己搞 coolify 的事情吧，我也不懂」。已照办：
> 密钥由 **GitHub Actions 在 runner 内当场生成**，私钥**直接经 Coolify API 注入环境变量**，
> 只把**公钥**登记到 `Private-Database` 作可写 deploy key。
> **私钥全程不落 Owner 手、不落 agent 手、不入任何仓库、不进对话记录。** 本机遗留私钥已删除。

## 现在的状态（我实际执行、看到的输出）
| 步骤 | 实测结果 |
|---|---|
| 找到 Coolify 里的 KMFA 应用 | `kmfa-kmos-p1` uuid `gz5qao2k0zrx3polpbwgcg51`，状态 `running:healthy` |
| 写入 `KMFA_BACKUP_SSH_KEY_B64` | `PATCH env 返回码=201`（先 POST 409=已存在→改 PATCH） |
| 公钥登记到 `Private-Database` | `可写=true`，旧的散落密钥已删 |
| 触发重新部署 | `Application kmfa-kmos-p1 deployment queued`（uuid `vy2ovtdcj2jsaaonp12ag9le`） |

生效后：每天**北京 00:30** 自动把 App 运行记录（拍板／导出／重跑／审计）备份进
`Private-Database/Private-KMDatabase/app-state-backup/`，保留最近 30 份。

## 排障中修掉的两个真问题
1. `POST/PATCH .../envs` 一律 **422**——原本刻意不回显响应（怕泄密）导致无法定位；
   加了**脱敏回显**（≥40 字符 base64 串一律 `<REDACTED>`）后拿到真因：
   `{"errors":{"is_build_time":["This field is not allowed."]}}`——compose 型资源不接受该字段。
2. payload 精简为 `key/value` 后：`POST 409`（键已存在）→ `PATCH 201` 成功。

## 备份工具本身早已实测通过
备份→还原往返：落点正确、sha256 完整性校验通过、JSONL 逐字节一致、SQLite 拍板记录完全一致；
合成测试对象已从私有库删净。未生效期间也不裸奔：自动降级备到服务器持久卷并在日志告警。

## 安全说明
备份目标是唯一私有库 `Private-Database`（Owner 铁律：永不新建 repo），故这把 deploy key 的
爆炸半径覆盖该库。密钥只存在于 Coolify 环境变量，本机与仓库均无副本。
