# DATA.0007 阶段二·首类抽取：collection 回款（2026-07-17）

- 范围：6 个回款类文件（74 sheet）→ `_staging.collection`
- 结果：**3,726 行**入库（2024-01-03 ~ 2026-06-30，4 文件含交易行）；43 sheet 加载，31 sheet（汇总/透视型）如实 deferred
- 纪律：金额 Decimal→整数分（float 拒绝）；幂等键=指纹+sheet+版本，复跑零 diff ✓；库与明细全在 .codex_private_runtime（不 tracked），公开面仅聚合
- 遗留（进 DATA.0010 质量初评）：227 个金额解析拒绝（多为合计行/文本混入），deferred sheet 的分类回填
- 下一类：receivable_aging / invoicing / payment_approval / contract → journal → 新建规格五类
