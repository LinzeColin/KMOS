---
name: project-cost-table-skill
description: 从 KMFA 私有全量来源重算指定年度全部项目的可审计项目成本，生成并验证封印 Excel、CSV、JSON、单项目 A4 PDF 与网站运行态；当用户要求计算、复核、下载或上线项目成本表时使用。
---

# 项目成本表 Skill

运营版本：`OPERATIONAL_0_0_6`；治理内核：`RELEASED_0_2_0_FAIL_CLOSED`。

本 Skill 可从下载 ZIP 直接运行，不需要安装到 Codex，也不会改写输入目录。原始财务、
合同、员工、考勤、聊天和金额数据只能在私有只读输入与私有输出中出现，不得进入公开
Git 仓库或 Skill ZIP。

## 唯一正式口径

`项目已发生成本 = 项目过账实际 + 合格应计`，全程使用整数分。

- 项目过账实际：只取通过法人主体、合同/项目身份、期间、科目、凭证行和语义去重门禁
  的金蝶 `5001` 事件。
- 合格应计：只取项目身份唯一、有来源证据、截至选定账期未见同笔正式过账的成本事件。
- DWS 群反应仅表示“观察到可能的确认动作”；未验证反应人的审批权限时，不得独立
  产生应计，也不得为 OCR 金额补充正式资格。
- OCR 按“文件/页或记录位置 + 文本摘要 + 行与金额出现序号”识别物理发生。不同文件
  或页中的同金额同文本保留为不同事件；同项目、同类、近日期存在任何账簿候选时，即使
  日期和金额相同，也必须提供稳定凭证关联，否则进入 P1，不得自动判成重复过账。
- 工资应计：只分配工资表可审计工资组件，在工资表批准出勤控制内按钉钉唯一项目日使用
  最大余数法分配；已过账 `5001003` 仅按同项目、同期间、同金额控制压减。
- `6401 主营成本已结转`、生产状态表金额、付款/DWS/OCR 金额是独立观察面，不与正式
  成本相加、不覆盖、不取最大值。
- 禁止固定人工单价、合同额自动 2% 管理费、历史报表补差或参考报表补差、无收入确认
  的毛利、按金额相近猜测项目，以及把参考结果回填到计算。
- `销售绩效考核` 和历史项目成本只用于版式、合同身份和金额独立验收，绝不作为目标
  待分析数据，也绝不进入 `calculate`。

## 复核与发布状态

- `PASS`：P0=0、P1=0，公式、守恒、封印和跨格式一致性全部通过。
- `PASS_WITH_OPEN_REVIEWS`：P0=0，全部硬控制通过；P1 对应仍无法唯一归项目、账簿
  截止月早于报表日期或时间证据不足的金额池。这些金额逐分保留在未分配/观察池，**不**
  进入任何项目。该状态可发布“已唯一归属的合格事件结果”，但必须同时显示 P1 数量和
  覆盖提示，不能宣称为所有潜在成本均已分配的最终实际。
- `FAIL`：存在 P0、输入文件/结构/公式/守恒/封印/隐私门禁失败。不得生成或发布正式
  工作簿和网站运行态。
- P2：有证据的其他合同、项目窗口之外记录、非成本、观察面排除、别名修复或控制提示；
  不影响正式公式。

全量数据与“每条成本都可唯一归项目”不是同一件事。Skill 不因 P1 猜数，也不把 P1
伪装成缺文件；它提供可直接审计使用的已确认金额，并把未归属池明确留在复核控制中。
每次 `calculate` 前必须先完成输入充分性检查；强制来源、期间或身份控制未通过时立即
失败，不得借用历史或参考金额补齐。

## 下载 ZIP 后直接运行

依赖 Python 3.9+。在 Skill 根目录执行：

```bash
python3 -m pip install -r requirements.txt

python3 scripts/run_operational_report.py self-test

python3 scripts/run_operational_report.py inventory \
  --data-root /ABSOLUTE/READ_ONLY/KMFA_DATA_ROOT

python3 scripts/run_operational_report.py calculate \
  --data-root /ABSOLUTE/READ_ONLY/KMFA_DATA_ROOT \
  --year 2026 \
  --as-of 2026-07-30 \
  --output-dir /ABSOLUTE/NEW/PRIVATE/OUTPUT_DIR \
  --ocr-jsonl /ABSOLUTE/PRIVATE/dingtalk_ocr.jsonl \
  --payroll-workbook /ABSOLUTE/PRIVATE/payroll_2026_05.xlsx \
  --payroll-workbook /ABSOLUTE/PRIVATE/payroll_2026_06.xlsx \
  --attendance-root /ABSOLUTE/READ_ONLY/dingtalk_attendance \
  --payroll-password-env KMFA_PAYROLL_PASSWORD

python3 scripts/run_operational_report.py verify-output \
  --output-dir /ABSOLUTE/PRIVATE/OUTPUT_DIR
```

加密工资表的密码只通过 `--payroll-password-env` 指定的环境变量读取，禁止写入参数值、
日志、manifest、工作簿或 ZIP。若工资表已经在受控私有临时目录解密，可省略密码环境
变量；Skill 仍不会复制员工姓名到输出。

验证源码目录或下载包：

```bash
python3 scripts/run_operational_report.py verify-skill \
  --skill-root /ABSOLUTE/PATH/TO/项目成本表

python3 项目成本表/scripts/run_operational_report.py verify-skill \
  --skill-root /ABSOLUTE/PATH/TO/KMFA_项目成本报表Skill.zip
```

## 输出合同

每次 `calculate` 的 `--output-dir` 必须是不存在、与全部输入完全分离的绝对路径：

- `KMFA_项目成本报表_*.xlsx`：8 个 values-only 页签；无公式、宏、外链和数据连接。
- `project_cost_snapshot.json`：完整私有谱系、逐事件整数分和复核池。
- `project_cost_summary.csv`：逐项目正式金额，与 Excel/JSON 到分一致。
- `项目单页PDF/`：每项目 1 份 A4 竖版《项目财务分析表》，含合同、正式金额和快照 ID。
- `run_manifest.json`：版本、公式、覆盖、P0/P1/P2、文件集合。
- `run_seal.sha256`：除自身外全部文件的 SHA-256。

`verify-output` 必须重新检查：

1. 封印文件集合与哈希；
2. Excel 无公式/宏/外链；
3. Excel、CSV、JSON 逐项目金额一致；
4. 每项目 PDF 为单页 A4，且合同、正式金额、快照 ID 与 JSON 一致；
5. 工资控制额 = 已分配应计 + 已匹配过账 + 未分配池；
6. P0=0，manifest 复核摘要与封印快照一致；
7. 完整 Skill 源码树摘要、私有输入清单摘要和本次选中来源摘要与快照、manifest 完全
   一致；源码或输入在计算后发生任何变化都使验证失败。离线直跑未提供外部私有
   manifest 时，Skill 自动用本次选中来源清单生成不可为空的派生输入清单摘要。

## KMFA 生产刷新

生产环境只能使用 no-clone 私有来源入口：

```bash
python3 scripts/run_private_refresh.py \
  --manifest-relpath project_cost/operational_input_manifest_v1.json \
  --output-root /app/logs/project-cost-runs \
  --runtime-json /app/logs/recent_completed.json
```

生产 manifest 必须绑定每个私有文件的路径、字节数、SHA-256、总文件数、总字节数、运行
日期、运营版本与预期控制。账簿中过账日期晚于 `as_of` 的记录一律排除并进入 P1。刷新
先在输出卷隐藏 staging 目录完成计算、预期控制和 `verify-output`，
全部通过后才原子改名为正式 run；控制漂移不会遗留正式外观目录。

网站运行态固定为 `kmfa.project_cost.current.v4`，并绑定完整 Skill 源码摘要、输入清单
类型与摘要、私有输入清单摘要、选中来源摘要，以及已验证工作簿的文件名、字节数、
SHA-256 与快照 ID。网站全量下载必须返回这一个封印工作簿，禁止再次生成另一份文件。
App 必须拒绝旧 schema、非可发布状态、项目数不一致、缺少来源绑定或缺少封印工作簿
绑定的运行态。

生产需要：

- 专用只读 `KMFA_PRIVATE_DB_READ_TOKEN`，不得回退到通用高权限 token；
- `KMFA_PAYROLL_PASSWORD`；
- `/project-cost`、`/项目成本`、`/public-api/项目成本表` 及其下载路径是同一份
  已发布报表的公开只读入口；只允许 GET/HEAD，始终 `no-store`/`noindex`；
- JSON `/public-api/项目成本`、重算、`/api` 与 `/ops` 仍受 Cloudflare Access 和
  origin JWT 双重保护；
- 运行态与输出仅落入私有共享卷，公开仓库只保留代码、schema 和合成测试。

## 治理内核兼容入口

运营入口不替代 0.2.0 已封存的治理验证。需要复核旧参考隔离、当前来源阻断或发布性能
时，分别使用：

- `run_reference_regression.py`：参考报表只做独立回放，绝不进入正式计算；
- `prepare_current_regression.py`、`run_current_source_reconstruction.py` 和
  `validate_current_expected_block.py`：验证旧阻断合同。第二次生产运行仍须重新读取真实
  来源；测试 harness `0` 只表示预期阻断被正确复现，不表示生产金额通过；
- `run_release_benchmark.py` 与 `validate_skill_package.py`：验证性能、隐私和包边界。

旧治理快照中的 `NOT_EVALUATED_BLOCKED_SOURCE` 仅描述当时未获真实源授权的基线，不覆盖
本运营版本的全量私有实算证据。未回复不构成授权；Skill 不设置财务负责人或授权人，也
不管理公司内部审批。正式产物只通过绝对输出路径和 `INTERNAL_PROCESS_HANDOFF.md` 交接。

## 停止条件

出现以下任一情况立即返回 `FAIL`，不得用历史结果、0、最大值或默认费率补齐：

- 强制来源缺失、哈希/字节数/结构漂移或危险 Office/ZIP 内容；
- 本年度合同主数据身份重复，或拟进入公式的事件仍不能唯一归项目；
- 货币、符号、期间、科目、凭证、去重、应计/过账关系无法通过硬门禁；
- 工资、事件、跨格式或文件封印守恒不为 0；
- P0 复核项存在；
- 输出与输入重叠，输出目录已存在，或发现真实数据将进入公开 Git/Skill ZIP。
