# -*- coding: utf-8 -*-
"""单个项目的《项目财务分析表》——**逐行照抄 Owner 的真实模版**。

真源（2026-07-30 Owner 指出）：
`~/Downloads/KMFA_MetaData/销售绩效考核/` 下的「竣工项目财务报表」PDF。
逐行读出四份，确认模版有两套，与 KMFA/tools/project_cost/render_report.py 里
早已复刻的 TPL_A / TPL_B 一致：

  A（池州恒鑫 085 / 崇阳昌华 084 / 新疆宜化 064）
      …（六）信息费 → 三 1.1分摊的管理费用（合同的2%）→ 1.2占用的资金利息
      → 合计支出 →（七）毛利
  B（山东圣川）
      多一行「项目产值」；税金与分摊进二级（（七）（八））；终行是「三 利润」

**为什么这个文件必须存在**：Owner 说过无数遍「单个项目下载和我原来的格式根本
不一样」。前两版我错在两处——
  1. 第一版页签是我自己造的（使用说明／项目总览／毛利复核…），
     注释里却写「对齐 Owner 手上那份」，对照物是**我自己生成的 xlsx**；
  2. 第二版改成了《生产项目状态表》的 30 列横表——那是**项目清单**的格式，
     不是**单个项目**的成本表。单项目要的是这张竖版分析表。

规矩：
  · 行序、层级、编号、括号写法一字不改，照抄 PDF；
  · 金额千分位两位小数；备注列出「占总成本比例」；
  · **我没有的行留空**。留空是「我不知道」，填 0 是「我说它是 0」——
    在给银行/税务看的表上，这两件事差别很大；
  · 钱不许静默消失：台账里的「其他费用」在模版里没有对应行，
    计入（四）小计并在备注里写明，绝不当它不存在。
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

#: A 表行序（照抄 `竣工项目财务报表  池州恒鑫 085.pdf`，49 行里的表体部分）。
#: 元组第二项是这一行的角色，供填值时区分层级。
TEMPLATE_A: tuple[tuple[str, str], ...] = (
    ("一、合同额", "contract"),
    ("二、资金运用及各项支出", "sec2"),
    ("（一）原材料", "l2_material"),
    ("其中:1.主要材料", "d"),
    ("2.辅助材料", "d"),
    ("2.1气体", "d"),
    ("2.2焊材", "d"),
    ("2.3漆料", "d"),
    ("2.4低值易损耗材", "d"),
    ("3 外协 加工费", "d"),
    ("（二）租赁费", "l2"),
    ("其中:1.吊车租赁费", "d"),
    ("2.脚手架租赁费", "d"),
    ("3.物流运输费", "d"),
    ("（三）保险费", "l2"),
    ("（四）现场管理费", "l2_site"),
    ("1.管理人员工资", "d_own_labour"),
    ("2.差旅费", "d_travel"),
    ("2.1车票", "d_ticket"),
    ("2.2住宿", "d_stay"),
    ("3.业务费用", "d"),
    ("3.1招待费", "d"),
    ("4.生活费用", "d"),
    ("4.1生活用品", "d"),
    ("4.2生活费", "d"),
    ("5.工程车辆使用费", "d"),
    ("5.1加油费及保养", "d"),
    ("5.2过路、停车费", "d"),
    ("5.3维修费", "d"),
    ("6.办公费", "d"),
    ("7.安全防护费", "d"),
    ("8.房租", "d"),
    ("9.临电", "d"),
    ("10.体检及工伤支出等", "d"),
    ("11.罚款", "d"),
    ("12.挂靠管理费", "d"),
    ("（五）工资（承包费）支出", "l2_sub_labour"),
    ("（六）信息费", "l2"),
    ("三 1.1分摊的管理费用（合同的2%）", "allocation"),
    ("1.2占用的资金利息", "interest"),
    ("合计支出", "total"),
    ("（七）毛利", "profit"),
)


def _num(value) -> Decimal | None:
    if value in (None, "", "None"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _plus(*values) -> Decimal | None:
    """只在**至少有一个真值**时求和；全空返回 None（留空，不是 0）。"""
    parts = [v for v in values if v is not None]
    return sum(parts, Decimal(0)) if parts else None


def statement_rows(project: dict) -> list[tuple[str, Decimal | None, str]]:
    """按 A 表行序摊成 (行标签, 金额, 备注)。缺值 None，绝不臆造。"""
    contract = _num(project.get("含税合同金额"))
    material = _num(project.get("材料费"))
    ticket = _num(project.get("交通费"))
    stay = _num(project.get("生活住宿费"))
    other = _num(project.get("其他费用"))
    own_labour = _num(project.get("自有人工成本"))
    sub_labour = _num(project.get("劳务人工成本"))
    allocation = _num(project.get("分摊管理费"))
    total = _num(project.get("成本合计"))
    profit = _num(project.get("毛利"))

    travel = _plus(ticket, stay)
    # （四）现场管理费 = 自有人工 + 差旅 + 台账里没细分的其他费用。
    # 其他费用在模版里没有对应行——**不能因此让它消失**，它已经算进成本合计了。
    site = _plus(own_labour, travel, other)
    # 二级合计 = 合计支出 − 三 项（分摊、利息）。PDF 里这条恒等式成立：
    # 41,832.76 + 900.00 + 46.48 = 42,779.24。
    sec2 = None
    if total is not None:
        sec2 = total - (allocation or Decimal(0))

    own_hours = project.get("自有人工工时")
    sub_hours = project.get("劳务人工工时")
    source = str(project.get("现场成本取自") or "")

    values: dict[str, tuple[Decimal | None, str]] = {
        "contract": (contract, "占总成本比例"),
        "sec2": (sec2, ""),
        "l2_material": (material, ""),
        "l2_site": (site, (f"含台账「其他费用」{other:,.2f} 元（本模版无对应行，"
                           "已计入本小计不让它消失）") if other else ""),
        "d_own_labour": (own_labour, (f"自有 {own_hours} 个工"
                                      + (f"｜{source}" if source else "")) if own_hours else source),
        "d_travel": (travel, ""),
        "d_ticket": (ticket, ""),
        "d_stay": (stay, ""),
        "l2_sub_labour": (sub_labour, f"外协 {sub_hours} 个工" if sub_hours else ""),
        "allocation": (allocation, ""),
        "total": (total, ""),
        "profit": (profit, ""),
    }

    out: list[tuple[str, Decimal | None, str]] = []
    for label, kind in TEMPLATE_A:
        amount, note = values.get(kind, (None, ""))
        # 文字备注与百分比**并存**，不是二选一。
        # 真 PDF：「（五）工资（承包费）支出 9,010.00 外协17个工 21.06%」——
        # 第一版写成「有文字就不算百分比」，于是（四）（五）两行的比例凭空消失了。
        if amount is not None:
            # **两个分母，逐行核对真 PDF 反推出来的**（池州恒鑫 085）：
            #   支出各行以「合计支出」为分母 —— 494.10/42,779.24 = 1.15% ✓
            #                                9,010/42,779.24 = 21.06% ✓
            #                                  900/42,779.24 = 2.10% ✓
            #   而（七）毛利以「合同额」为分母 —— 6,120.76/45,000 = 13.60% ✓
            #                       用合计支出会算成 14.31%，与模版不符。
            # 这是给银行/税务看的表，百分比口径错了不行。
            base = contract if kind == "profit" else total
            if base not in (None, Decimal(0)) and kind not in ("contract", "total", "sec2"):
                share = f"{amount / base:.2%}"
                note = f"{note} {share}".strip() if note else share
        out.append((label, amount, note))
    return out


def statement_header(project: dict) -> list[tuple[str, str]]:
    """表头区：项目名称／合同编号／开工-完工时间。照抄 PDF 的字段与措辞。"""
    def day(value) -> str:
        text = str(value or "").strip()
        return text.split(" ")[0].replace("-", "/") if text else ""

    return [
        ("项目名称：", str(project.get("甲方名称") or "")),
        ("合同编号", str(project.get("合同编号") or "")),
        ("开工时间", day(project.get("开工时间"))),
        ("完工时间", day(project.get("完工日期"))),
    ]
