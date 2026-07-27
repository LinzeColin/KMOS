#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按报表自身的行号层级上卷：`2.1车票` → `2.差旅费` → `（四）现场管理费` → `二`。

为什么不能只按二级归并：
  账上只有『车费』『油费』这些末级科目。若直接把它们加到二级，中间行
  （`2.差旅费`、`5.工程车辆使用费`、`4.生活费用`）就会空着，而它们的下级有数——
  一张各级对不上的表，交不了银行税务。

不变量（`check_invariants` 会验）：
  · 二级之和 == 全部叶子之和 —— 上卷既不能漏钱也不能重复计。
  · 每个有下级的行 == 自身直接归集 + 其全部直接下级。

本模块放在公开仓，是为了让口径可读、可测、可审计；私有库的计算作业导入它，
而不是各自实现一份。
"""
from __future__ import annotations
import re
from decimal import Decimal

from render_report import TPL_A, TPL_B

_NUM = re.compile(r"(?:其中[:：])?\s*((?:\d+\.)*\d+)")


def _template(name: str):
    return TPL_A if str(name).upper() == "A" else TPL_B


def hierarchy(tpl_name: str) -> dict[str, tuple[str | None, tuple[int, ...]]]:
    """label -> (所属二级, 行号路径)。二级自身的所属为 None、路径为空。"""
    node: dict[str, tuple[str | None, tuple[int, ...]]] = {}
    cur: str | None = None
    for label, kind in _template(tpl_name):
        if kind == "l2":
            cur = label
            node[label] = (None, ())
        elif kind == "d" and cur:
            m = _NUM.match(label)
            path = tuple(int(x) for x in m.group(1).split(".")) if m else ()
            node[label] = (cur, path)
    return node


def parent_of(node: dict, label: str) -> str | None:
    """同一二级下，路径少一段的那行是父；找不到则父为二级本身。

    模板 B 有一批**没有行号**的明细行（采购材料、外协人员工资、外协人员生活费、
    临时用工费用…）。早先按「无行号即无父」处理，它们就永远卷不上去——
    上卷不变量当场抓到某 B 版报表少了原材料那一笔。无行号的明细行，父就是它的二级。
    """
    l2, path = node.get(label, (None, ()))
    if not l2:
        return None
    if not path:
        return l2
    if len(path) > 1:
        for cand, (g, p) in node.items():
            if g == l2 and p == path[:-1]:
                return cand
    return l2


def rollup(tpl_name: str, leaf: dict[str, Decimal]) -> tuple[dict[str, Decimal], Decimal]:
    """把叶子行金额逐级累加上去，返回 (各行金额, 二级合计)。

    从最深的行开始处理，保证一行被累加到父级时，它自己的下级已经加进来了。
    """
    node = hierarchy(tpl_name)
    val: dict[str, Decimal] = {k: Decimal(str(v)) for k, v in leaf.items()}
    for label in sorted(node, key=lambda x: -len(node[x][1] or ())):
        if label not in val:
            continue
        par = parent_of(node, label)
        if par:
            val[par] = val.get(par, Decimal(0)) + val[label]
    sec2 = sum((val.get(l, Decimal(0)) for l, k in _template(tpl_name) if k == "l2"), Decimal(0))
    return val, sec2


def check_invariants(tpl_name: str, leaf: dict[str, Decimal]) -> list[str]:
    """上卷后的自洽性检查；返回问题清单，空列表代表通过。"""
    node = hierarchy(tpl_name)
    val, sec2 = rollup(tpl_name, leaf)
    errs: list[str] = []
    total_leaf = sum((Decimal(str(v)) for v in leaf.values()), Decimal(0))
    if sec2 != total_leaf:
        errs.append(f"二级之和 {sec2} ≠ 叶子之和 {total_leaf}——上卷漏钱或重复计")
    children: dict[str, list[str]] = {}
    for label in node:
        par = parent_of(node, label)
        if par:
            children.setdefault(par, []).append(label)
    for par, kids in children.items():
        present = [k for k in kids if k in val]
        if not present:
            continue
        own = Decimal(str(leaf.get(par, 0)))
        expect = own + sum((val[k] for k in present), Decimal(0))
        if val.get(par, Decimal(0)) != expect:
            errs.append(f"『{par}』{val.get(par)} ≠ 自身 {own} + 下级之和 {expect - own}")
    return errs
