# 新批次数据接收 SOP（TSK.KMFA.DATA.0003）

> 建立：2026-07-17 ｜ 适用：Owner 拿到任何新一批原始数据（压缩包/Excel/PDF 均可）
> 原则：Owner 只做「丢文件」一个动作，其余全自动/由执行线程接手。

## Owner 动作（一步）

把新批次文件放进任意本地目录（例如 `~/Downloads/KMFA_MetaData/<域>/<日期>/`），然后告诉执行线程一声（或等采集自动化上线后连说都不用说）。

## 执行线程动作（三步，全部幂等）

```bash
# 1) 内容寻址入仓（同名不同内容自动共存；凭据类文件自动拒绝）
python3 KMDatabase/machine/tools/ingest_data.py add <目录> --domain 财务|WPS钉钉红圈|绩效|预算|对账基准 --batch YYYY-MM-DD

# 2) 桥接登记进 KMFA 导入协议（自动分级 A0/A1/A2/B；zip 自动做成员预检，明细只进私有区）
python3 KMFA/tools/register_kmdb_batch.py --received YYYY-MM-DD --now YYYYMMDD-HHMMSS

# 3) 核对
python3 KMDatabase/machine/tools/ingest_data.py verify
```

## 下游重跑清单（血缘图 DATA.0011 建成前的手册版）

新批次登记后，按顺序检查/重跑：

1. staging 抽取（DATA.0007 管线建成后：仅重跑指纹变化的表）
2. 口径事实 facts 重生成（DATA.0012 生成器）
3. 渲染门 `render_human.py --root KMFA`（DATA.0013 后）
4. 断言表重验（DATA.0016 后：受影响科目×期间）
5. 云端数据卷同步（Oracle 端 `git pull` 自动获得新对象）

> 血缘图建成后，第 1-4 步由指纹比对图遍历自动给出「精确 stale 清单」，不再全量。

## 演练记录（2026-07-16 批，2026-07-17 执行）

- 入仓：53/53（财务 31 / WPS钉钉红圈 13 / 绩效 9），verify 0 损坏 0 账外
- 登记：51 registered + 2 quarantined（.doc 不在 S03-P1 支持格式表，降 B 级待议）
- 幂等复跑：`IDEMPOTENT_NOOP`（零重复登记）✓
- zip 预检：3 个 zip 成员清单落私有区（`.codex_private_runtime/imports/zip_member_lists/`），公开面只有聚合计数

## 红线

- `~/Downloads/KMFA_MetaData` 等来源目录**永远只读**（工具只 read/hash，不写不删不改名）
- 凭据类文件（.env/.pem/token/私钥内容）入仓工具直接拒绝
- zip 成员**名称明细**不进 tracked 区；公开面只有 member_count/体积/可疑计数
- 金额类后续处理一律整数分（`amount_tools.py`），禁 float
