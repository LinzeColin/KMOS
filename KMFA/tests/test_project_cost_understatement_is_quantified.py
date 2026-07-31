# -*- coding: utf-8 -*-
"""项目成本未归属池必须是数，不能只用形容词。

合成回归证明：即使解析、去重和借方口径全部正确，只报已归集项目金额仍可能漏掉
账上记在 `不分项目` 或占位合同中的成本。

产物此前只有一句「成本偏保守、毛利偏乐观」。定性不够——偏 3% 和偏 79%
是两件完全不同的事：前者能拿去谈结算，后者会让人亏着钱以为在赚。
所以本文件把两条钉死：

  ① 被跳过的成本必须**进桶**，不许静默消失（守恒）；
  ② 产物必须带出「未归集成本池」与「毛利方向」，且金额不写死在仓库里
     （KMOS 是公开仓，真实金额只能在运行期出现在产物里）。
"""
from __future__ import annotations

import ast
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "KMFA/tools/project_cost/build_recent_completed.py"
sys.path.insert(0, str(BUILD.parent))


def test_every_skipped_amount_lands_in_a_bucket():
    """**守恒判据。** 每一条跳过的分支都必须先算出 amount、再 `drop(...)`。

    这是唯一防得住「静默丢钱」的写法：只要有一个 `continue` 前面没有 `drop`，
    那部分成本就既不在项目里、也不在未归集池里——两头都查不到，
    而合计看上去还是「对的」。
    """
    tree = ast.parse(BUILD.read_text(encoding="utf-8"))
    handle = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == "handle"), None)
    assert handle is not None, "collect_ledger_cost 里的 handle() 不见了"

    # 归属判定的三个跳过分支（不分项目／占位桶／不在主合同表），
    # 每个 `continue` 之前必须紧跟一次 drop()。科目未登记那条是 raise，不在此列。
    drops = [n for n in ast.walk(handle)
             if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "drop"]
    assert len(drops) >= 3, f"归属跳过分支应各有一次 drop()，实际 {len(drops)} 次"

    reasons = {a.args[0].value for a in drops if a.args and isinstance(a.args[0], ast.Constant)}
    import build_recent_completed as B  # noqa: PLC0415

    assert reasons == set(B.UNATTRIBUTED_REASONS), (
        f"drop() 用的原因 {sorted(reasons)} 与 UNATTRIBUTED_REASONS "
        f"{sorted(B.UNATTRIBUTED_REASONS)} 对不上——对不上就会漏桶")


def test_amount_is_computed_before_the_attribution_branches():
    """`amount` 必须在三个归属分支**之前**算好。

    先 continue 再算金额的话，drop() 拿不到数——桶会是 0，
    于是「未归集池为 0」看起来像「全都归集到了」。这正是要防的那种假绿。
    """
    source = BUILD.read_text(encoding="utf-8")
    body = source[source.index("def handle(sheet_name, sheet):"):]
    body = body[:body.index("\n    bundles")] if "\n    bundles" in body else body
    at_amount = body.index("amount = Decimal(str(value))")
    at_first_branch = body.index('drop("不分项目")')
    assert at_amount < at_first_branch, "amount 算在归属分支之后——drop() 会记到 0"


def test_the_payload_quantifies_the_understatement():
    """产物必须带「未归集成本池」和「毛利方向」，且**金额不硬编码**。"""
    source = BUILD.read_text(encoding="utf-8")
    assert '"未归集成本池"' in source, "产物缺少未归集成本池——少算就退回成形容词"
    assert '"毛利方向"' in source, "产物没说毛利偏哪边"
    assert '"已归集到项目"' in source, "只报未归集不报已归集，读的人算不出归集率"

    # 披露块本身**不许出现具体金额**：那等于把某一次运行的结果焊死进公开仓，
    # 下次数据变了它还在那儿说着旧数。金额只能运行时从 `unattributed` 里取。
    #
    # 判据只覆盖披露块；公共仓中的 fixture 也必须保持合成化。
    import re  # noqa: PLC0415

    block = source[source.index('"未归集成本池"'):source.index('"项目数": len(projects)')]
    for hit in re.findall(r"\d{1,3}(?:,\d{3})+(?:\.\d{2})?", block):
        pytest.fail(f"未归集成本池披露块里硬编码了金额 {hit}——它必须运行时算")
    assert "unattributed.get(reason" in block, "分桶金额没在运行时取，那就是写死的"
    assert "sum(unattributed.values()" in block, "合计没在运行时算"


def test_unattributed_buckets_are_declared_up_front():
    """桶名是常量、不是散在代码里的字符串——散着写迟早漏一个。"""
    import build_recent_completed as B  # noqa: PLC0415

    assert isinstance(B.UNATTRIBUTED_REASONS, tuple)
    assert "不分项目" in B.UNATTRIBUTED_REASONS
    assert "伪合同号占位桶" in B.UNATTRIBUTED_REASONS
    assert "不在主合同表中" in B.UNATTRIBUTED_REASONS


def test_collect_ledger_cost_accepts_the_bucket_dict():
    """签名得真收得下桶——不收就是白写。"""
    import inspect  # noqa: PLC0415

    import build_recent_completed as B  # noqa: PLC0415

    sig = inspect.signature(B.collect_ledger_cost)
    assert "unattributed" in sig.parameters
    assert sig.parameters["unattributed"].default is None, \
        "默认必须是 None：不传就不统计，传了才记，别给调用方留个共享可变默认值"


def test_conservation_holds_on_a_synthetic_ledger(tmp_path):
    """端到端守恒：造一本小账，已归集 + 未归集 = 读到的全部借方。

    合成数据里同时放四种行——真项目、不分项目、伪合同号、不在主合同表——
    每种都给一个能认出来的金额，最后逐分对上。
    """
    openpyxl = pytest.importorskip("openpyxl")
    import zipfile  # noqa: PLC0415

    import build_recent_completed as B  # noqa: PLC0415

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "5001001_测试_KMX"
    sheet.append(["明细账"] * 15)
    sheet.append(["测试公司"] * 15)
    sheet.append(["科目", "客户", "职员", "供应商", "部门", "销售合同号", "研发项目",
                  "往来", "日期", "凭证字号", "摘要", "借方", "贷方", "方向", "余额"])
    rows = [
        ("KMX260101-001", "领料", 100),          # 真项目
        ("不分项目", "领料", 200),        # 桶①
        ("KMX9999", "领料", 400),                # 桶②
        ("KMX260101-999", "领料", 800),          # 桶③：账上有但主合同表里没有
        ("KMX260101-001", "本期合计", 1600),      # 汇总行，两边都不该算
    ]
    for contract, memo, debit in rows:
        sheet.append(["5001001-生产成本_原材料", "", "", "", "", contract, "", "",
                      "2026-01-31", "记-1", memo, debit, 0, "借", 0])

    book = tmp_path / "明细账测试.xlsx"
    workbook.save(book)
    bundle = tmp_path / "金蝶账务数据包.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.write(book, arcname="明细账测试.xlsx")

    unattributed: dict[str, Decimal] = {}
    ledger = B.collect_ledger_cost(
        str(tmp_path), {"KMX260101-001"},
        {"5001001-生产成本_原材料": "（一）原材料"},
        unattributed=unattributed)

    attributed = sum((v for per in ledger.values() for v in per.values()), Decimal(0))
    unallocated = sum(unattributed.values(), Decimal(0))
    assert attributed == Decimal(100), f"归集到项目的应为 100，实际 {attributed}"
    assert unattributed.get("不分项目") == Decimal(200)
    assert unattributed.get("伪合同号占位桶") == Decimal(400)
    assert unattributed.get("不在主合同表中") == Decimal(800)
    # 守恒：汇总行 1600 两边都不算，其余 1500 必须分毫不差地落在两边
    assert attributed + unallocated == Decimal(1500), \
        f"守恒不成立：{attributed} + {unallocated} ≠ 1500——有钱静默消失了"
