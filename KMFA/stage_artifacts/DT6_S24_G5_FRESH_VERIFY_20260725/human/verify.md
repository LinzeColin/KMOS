# PROD.0012(S24 复核)+ 0018(G5)现场真跑复核（2026-07-25）

## 我实际执行了什么、看到了什么（非引用旧记录）
在当前 main（含本会话 #181/#182/#183）上,真跑两个权威治理检查器:

**`python3 KMFA/tools/check_g5_exit.py --root KMFA`** →
- `technical_checks_all_green: true`
- `g5_passed: true`（Owner 2026-07-20 签核 `CTRL-KMFA-20260720-G5-SIGNOFF`）
- 渲染门/三道门/阻塞重审门 三项退出码均 0
- `网站内容已亲验: 否`（= 完成判据⑤ Owner 亲登位,与 g5_passed 是两个字段,不混淆）

**`python3 KMFA/tools/check_s24_stage_review.py --root KMFA`** →
- `结论: S24_REVIEW_PASS`（2026-07-20 时为 `S24_REVIEW_INCOMPLETE` 4/5;现 G5 已签+18 项证据齐 → 翻 PASS）
- `裁剪: []`（无砍项）

## 结论（真状态,不写死）
- **PROD.0012（S24 范围复核）= PASS**（检查器现场判 S24_REVIEW_PASS）
- **PROD.0018（G5 出口）技术五项 5/5 且 g5_passed=true**（判据④满足;DT6 已 completed）
- 判据④(G5 全绿+DT6 完成)**满足**;判据⑤(Owner 亲登看真实数据)**仍待 Owner**(亲验=否)

## 这把 M5 计数刷新到
**12 项 PASS**：0001/0002/0003/0004/0007/0008/0009/**0012**/0013/0016/0017/**0018**。
其余:0015(.app,Owner 退役)｜0014(gap 已登记分析,排序权在 Owner)｜0005/0006/0010/0011(页面已建、金额被 A0 治理锁,待缺失导出)。

## 铁律
真跑检查器→真看 JSON 输出为证,非 pytest 绿冒充;输出纯状态,零金额零公司名。
