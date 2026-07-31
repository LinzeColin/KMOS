# -*- coding: utf-8 -*-
"""Render one closed project into the governed financial-statement layout.

Amounts only come from the canonical Skill runtime fields ``报表归类``,
``项目成本``, ``有效合同额`` and ``毛利``.  A project whose cost basis is not
``READY`` is rejected instead of relabelling its incurred-cost lower bound as a
closed project cost.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


TEMPLATE_B: tuple[tuple[str, str], ...] = (
    ("一、合同额", "contract"),
    ("项目产值", "revenue"),
    ("二、资金运用及各项支出", "sec2"),
    ("（一）原材料", "l2_material"),
    ("采购材料", "d_material"),
    ("（二）租赁费", "l2_rental"),
    ("其中:1.机械费", "rental_only"),
    ("（三）保险费", "insurance"),
    ("（四）现场管理费", "l2_site"),
    ("1.自有人员工资", "d_own_labour"),
    ("2.差旅费", "d_travel"),
    ("3.招待费", "blank"),
    ("4.运输费", "d_logistics"),
    ("5.办公费", "blank"),
    ("6.房租", "d_stay"),
    ("7.水电费", "d_fuel_power"),
    ("8.备用金", "blank"),
    ("9.其他费用", "other"),
    ("（五）工资（承包费）支出", "l2_sub_labour"),
    ("外协人员工资", "l2_sub_labour"),
    ("外协人员生活费", "blank"),
    ("临时用工费用", "blank"),
    ("（六）信息费", "information_fee"),
    ("（七）税金", "tax"),
    ("（八） 分摊的管理费用（合同的2%）", "allocation"),
    ("已发生尚未支付费用", "blank"),
    ("三 利润", "profit"),
)


def _num(value) -> Decimal | None:
    if value in (None, "", "None"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _plus(*values: Decimal | None) -> Decimal | None:
    parts = [value for value in values if value is not None]
    return sum(parts, Decimal(0)) if parts else None


def _money(value: Decimal | None) -> str:
    return "" if value is None else format(value, ",.2f")


def statement_rows(project: dict) -> list[tuple[str, Decimal | None, str]]:
    """Return a closed statement while conserving every project-cost cent."""

    if str(project.get("收入与毛利状态") or "") != "READY":
        raise ValueError("项目成本未闭合，禁止生成正式项目财务分析表")
    contract = _num(project.get("含税合同金额"))
    revenue = _num(project.get("有效合同额"))
    revenue_bridge = _num(project.get("收入桥"))
    buckets = project.get("报表归类") or {}
    material = _num(buckets.get("material"))
    fuel_power = _num(buckets.get("fuel_power"))
    rental = _num(buckets.get("rental"))
    logistics = _num(buckets.get("logistics"))
    ticket = _num(buckets.get("travel"))
    stay = _num(buckets.get("lodging"))
    living = _num(buckets.get("living"))
    road_parking = _num(buckets.get("road_parking"))
    vehicle = _num(buckets.get("vehicle"))
    other = _num(buckets.get("other"))
    own_labour = _num(buckets.get("own_labor"))
    sub_labour = _num(buckets.get("subcontract_labor"))
    information_fee = _num(buckets.get("information_fee"))
    tax = _num(buckets.get("tax"))
    management_allocation = _num(buckets.get("management_allocation"))
    total = _num(project.get("项目成本"))
    profit = _num(project.get("毛利"))

    material_total = _plus(material, fuel_power)
    rental_total = rental
    travel = _plus(ticket, stay)
    vehicle_total = _plus(vehicle, road_parking)
    site = _plus(
        own_labour,
        travel,
        living,
        vehicle_total,
        logistics,
        other,
    )
    classified = _plus(
        material_total,
        rental_total,
        site,
        sub_labour,
        information_fee,
        tax,
        management_allocation,
    )
    if total == Decimal(0) and classified is None:
        classified = Decimal(0)
    if total is None or classified != total:
        raise ValueError(f"闭合项目成本归类不守恒：{classified!r} != {total!r}")
    if revenue is None or profit is None or profit != revenue - total:
        raise ValueError("闭合项目毛利与有效收入、项目成本不守恒")

    own_hours = project.get("自有人工工时")
    sub_hours = project.get("劳务人工工时")
    values: dict[str, tuple[Decimal | None, str]] = {
        "contract": (
            contract,
            (
                "红圈原始含税合同额；批准项目产值 %s 元，收入桥 %s 元"
                % (_money(revenue), _money(revenue_bridge))
            ),
        ),
        "revenue": (revenue, "批准开票项目产值"),
        "sec2": (
            total,
            "项目财务分析成本；会计已发生成本和销项税差额均可追溯",
        ),
        "l2_material": (material_total, ""),
        "d_material": (material, ""),
        "d_fuel_power": (fuel_power, "燃料及动力"),
        "l2_rental": (
            rental_total,
            "设备租赁未细分吊车/脚手架" if rental else "",
        ),
        "rental_only": (rental, ""),
        "insurance": (None, "未单列的项目保险保留在其他费用"),
        "d_logistics": (logistics, ""),
        "l2_site": (
            site,
            (
                f"含未能安全细分到模板行的正式成本 {_money(other)} 元；"
                "已计入本小计"
            )
            if other
            else "",
        ),
        "d_own_labour": (
            own_labour,
            (
                f"自有 {own_hours} 个工"
            )
            if own_hours is not None
            else ("正式自有人工成本" if own_labour is not None else ""),
        ),
        "d_travel": (travel, ""),
        "d_stay": (stay, ""),
        "d_living": (living, ""),
        "d_vehicle": (vehicle_total, ""),
        "d_logistics": (logistics, ""),
        "other": (other, ""),
        "l2_sub_labour": (
            sub_labour,
            f"外协 {sub_hours} 个工" if sub_hours else "",
        ),
        "information_fee": (information_fee, ""),
        "tax": (
            tax,
            "逐张开票销项税扣除税费台账已预缴增值税；不估率、不补差",
        ),
        "allocation": (
            management_allocation,
            (
                "仅批准且在生效期内的项目管理分摊政策可计入；"
                "当前无活动政策，禁止沿用历史2%"
                if management_allocation is not None
                else "当前无活动项目管理分摊政策，留空"
            ),
        ),
        "profit": (
            profit,
            "项目财务分析毛利",
        ),
    }

    output: list[tuple[str, Decimal | None, str]] = []
    for label, kind in TEMPLATE_B:
        amount, note = values.get(kind, (None, ""))
        if (
            amount is not None
            and total not in (None, Decimal(0))
            and kind not in ("contract", "revenue", "sec2", "profit")
        ):
            share = f"{amount / total:.2%}"
            note = f"{note} {share}".strip() if note else share
        output.append((label, amount, note))
    return output


def statement_header(project: dict) -> list[tuple[str, str]]:
    """Return the four-field header block used by the supplied statement."""

    def day(value) -> str:
        text = str(value or "").strip()
        return text.split(" ")[0].replace("-", "/") if text else ""

    return [
        (
            "项目名称：",
            str(project.get("项目名称") or project.get("甲方名称") or ""),
        ),
        ("合同编号", str(project.get("合同编号") or "")),
        ("开工时间", day(project.get("开工时间"))),
        ("完工时间", day(project.get("完工日期"))),
    ]
