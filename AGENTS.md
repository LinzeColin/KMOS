# KMOS Agent Contract

KM 系列商用线仓库，中文优先；代码、API、库名、模型名和错误可保留英文。

## 永久规则

- 本仓库是**商用线**。代码与数据默认专有，不得以任何开源许可对外发布。
- 治理框架来自共享仓库 LinzeColin/Governance。
  **禁止**在本仓库内复制、分叉或重建治理框架。
  **禁止**用 git submodule 引入它 —— 通过 CI checkout 或 pip 安装消费。
- 跨 KM 项目的数据交换必须经过 KMDatabase 声明的 schema，
  **禁止**直接引用其他项目的内部路径。
- **数据落地铁律（长期有效 · 自运行分仓治理）**：长期/业务/运行时数据一律写私有仓
  `LinzeColin/Private-Database` 的 `Private-KMDatabase/`，用 `KMDatabase/machine/tools/private_db_client.py`
  免 clone 读写（`ingest/get/list/verify`）；**禁止把数据提交进本代码仓**，派生/临时物走 `.gitignore`。
  Private-Database 禁止 `git clone`。目的：分仓治理长期自运行，不需 Owner 反复人工迁移。

## 迁移状态

本仓库从 `LinzeColin/CodexProject` 拆分而来。

- `KMFA/` 已在 2026-07-17 迁入并成为 KMFA 的唯一 GitHub 源码归属。
- `KM_IDSystem/` 是 KMIDS 在 `LinzeColin/KMOS` 中的 canonical 目录；业务名 KMIDS 不对应另一个仓库或目录。
- 旧 `CodexProject` checkout 仅是历史/私有运行态来源，不得再作为 KMFA 或 KMIDS 的提交、推送或新开发入口。

处理 KMFA 前先读 `KMFA/HANDOFF.md`；处理 KMIDS 前先读 `KM_IDSystem/docs/HANDOFF.md`。真实员工、财务、群聊、考勤、SQLite、压缩包、凭据和 IDS 原始元数据不得进入本公开仓库。

---

## 云成本红线：对象存储必须零付费（Owner 硬指令 · 长期有效）

**云端账单必须恒为 $0.00。不允许任何 agent 触发收费行为。**

1. **禁止 `InfrequentAccess` 存储类** —— 建桶、写对象、生命周期转换，一律不许。
   R2 的免费额度（10GB 存储 / 100 万 Class A / 1000 万 Class B）**只覆盖 Standard**；
   IA 从第 1 次操作起计费，且**按整计费单位向上取整**。
   2026-08-07 实账单：**51 次 IA 操作 = $9.00**，同期 **301 万次 Standard 操作 = $0.00**。
   根因是建桶时默认存储类选了 IA，写入端不指定存储类就全部继承 —— 一次手滑，之后静默自动计费。
2. **禁止"整包下载来判断存在 / 做校验"的高频轮询。** 判断对象存在用 `HeadObject`
   （写入时把 sha256 放进对象 `Metadata`，Head 就读得到）；真要逐字节复核，
   **按天或按周跑，不许按分钟跑**。
   反例：memory-atlas reconcile 每 15 分钟把 2466 个对象整包拉一遍核 sha256，
   折合 71 万次 Class B/天、21.3M/月，直接打穿 10M/月免费额度。
3. **新增或改动任何周期性任务，先算月操作量**：
   `每轮操作数 × 每天轮数 × 31 < 免费额度 × 50%`。**算不出来就不上线。**
4. **存储优先级**：**GitHub Release 资产 > R2 > OVH 本地**。
   Release 资产不计仓库体积、没有操作计费，永远优先。

完整事故记录、账单逐行归因、免费额度速查表 → **`Private-Database` 仓 `OPS/AGENT_ONBOARDING.md` §9.7**。
机器守卫 → OVH `/usr/local/bin/linze-r2-free-tier-guard.py`（每 6 小时，非 Standard 桶自动熔断改回；
判定 `/srv/linze/apps/status/data/r2_free_tier_guard.json`）。
