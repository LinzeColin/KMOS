# 数据上云 + .app 退役 + A0 云算就绪(2026-07-25)

Owner 2026-07-25 连下三条真实指令,逐条落地:

## ① 「全上云、不占本地」+「私有数据都进 GitHub 数据库」
- 本会话起**清空本地 docker**(容器/网络/镜像归零),构建走 GitHub Actions、部署走 Coolify、
  视觉验证用 CI 云端截图——**零本地容器**。
- A0 所需真实原始财务源**已上云**:用 `KMDatabase/machine/tools/private_db_client.py`
  把税务权威源 + 3 家金蝶明细账(主体名脱敏) ingest 进私有库 `LinzeColin/Private-Database` 的
  `Private-KMDatabase` 区(免 clone、gh API 直传)。sha256 见 `machine/private_db_ingest.json`;
  **真实金额只在私有库,公开 KMOS 零金额**。
  - 我实际执行:`python3 private_db_client.py ingest Private-KMDatabase <文件> --domain KMFA财务税务|KMFA金蝶明细账`,
    看到输出「✓ 入库完成 sha256=…」(税务源提示「已在库」——先前线程已传;3 家金蝶为本次新传)。

## ② 「全上云了,不需要本地 app」——判据 3(.app 双击)Owner 退役
- Owner 明确:全上云后**不再需要本地 `.app`**。据此 **PROD.0015 本地 .app 双击入口退役**,
  完成判据第 3 条(.app 双击可用)由 Owner 决定**不再适用**(云上无本地 app)。
  往期 `DT6_PROD0015`/`V014_S05` 记录留档,不删;新状态:云端 Coolify 部署即产品入口。

## ③ 「金蝶你自己解决」——会计口径 agent 自定,不再问 Owner
- 授权我按**满足财税/银行/政府合规的标准口径**自裁:项目成本 = 损益类**主营业务成本(6401)借方净额**
  (排除期间费用 6601/6602/6603 与内部划转——上轮 737% 假差就是错在全取 1159 科目);
  对税务 A0 按**现金基础**对齐。此口径不再需要 Owner 逐句确认。

## 现在卡在哪(唯一一步,且是 Owner 侧最小动作)
云上 compute 要读私有库 `Private-Database`,需 KMOS 仓加一个 **`PRIVATE_DB_TOKEN`** secret
(一个对 Private-Database 有 read 权限的 GitHub PAT)——**和你此前加 `COOLIFY_API_TOKEN` 一模一样的操作**。
加好后:我写的 GitHub Actions 从私有库取税务+金蝶源、云上按上述口径跑 A0 重算与 zero-delta、
**只回 public-safe 结果(差额率/通过与否,无金额)入 KMOS**,那 4 项(0005/0006/0010/0011)即可真验收。

## 铁律遵守
真实财务与业务名只进私有库,永不进公开 KMOS;不改门禁阈值、不动 append-only 台账;
本单元仅记录里程碑与状态,零业务逻辑改动。
