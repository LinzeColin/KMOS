# -*- coding: utf-8 -*-
"""Render one project's formal cost into the owner statement layout.

The row order is a public-safe transcription of the supplied A-family project
financial statement. Values only come from the canonical Skill runtime fields
``报表归类`` and ``项目已发生成本``. The historical “合同的2%” and profit rows
remain for layout parity but stay blank until their own governed inputs exist.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


TEMPLATE_A: tuple[tuple[str, str], ...] = (
    ("一、合同额", "contract"),
    ("二、资金运用及各项支出", "sec2"),
    ("（一）原材料", "l2_material"),
    ("其中:1.主要材料", "d_material"),
    ("2.辅助材料", "blank"),
    ("2.1气体", "d_fuel_power"),
    ("2.2焊材", "blank"),
    ("2.3漆料", "blank"),
    ("2.4低值易损耗材", "blank"),
    ("3 外协 加工费", "blank"),
    ("（二）租赁费", "l2_rental"),
    ("其中:1.吊车租赁费", "blank"),
    ("2.脚手架租赁费", "blank"),
    ("3.物流运输费", "d_logistics"),
    ("（三）保险费", "blank"),
    ("（四）现场管理费", "l2_site"),
    ("1.管理人员工资", "d_own_labour"),
    ("2.差旅费", "d_travel"),
    ("2.1车票", "d_ticket"),
    ("2.2住宿", "d_stay"),
    ("3.业务费用", "blank"),
    ("3.1招待费", "blank"),
    ("4.生活费用", "d_living"),
    ("4.1生活用品", "blank"),
    ("4.2生活费", "blank"),
    ("5.工程车辆使用费", "d_vehicle"),
    ("5.1加油费及保养", "d_vehicle_fuel"),
    ("5.2过路、停车费", "d_road_parking"),
    ("5.3维修费", "blank"),
    ("6.办公费", "blank"),
    ("7.安全防护费", "blank"),
    ("8.房租", "blank"),
    ("9.临电", "blank"),
    ("10.体检及工伤支出等", "blank"),
    ("11.罚款", "blank"),
    ("12.挂靠管理费", "blank"),
    ("（五）工资（承包费）支出", "l2_sub_labour"),
    ("（六）信息费", "blank"),
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


def _plus(*values: Decimal | None) -> Decimal | None:
    parts = [value for value in values if value is not None]
    return sum(parts, Decimal(0)) if parts else None


def statement_rows(project: dict) -> list[tuple[str, Decimal | None, str]]:
    """Return statement rows while conserving the formal project-cost total."""

    contract = _num(project.get("含税合同金额"))
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
    total = _num(project.get("项目已发生成本"))

    material_total = _plus(material, fuel_power)
    rental_total = _plus(rental, logistics)
    travel = _plus(ticket, stay)
    vehicle_total = _plus(vehicle, road_parking)
    site = _plus(own_labour, travel, living, vehicle_total, other)
    classified = _plus(material_total, rental_total, site, sub_labour)
    if total == Decimal(0) and classified is None:
        classified = Decimal(0)
    if total is not None and classified != total:
        raise ValueError(f"正式成本归类不守恒：{classified!r} != {total!r}")

    own_hours = project.get("自有人工工时")
    sub_hours = project.get("劳务人工工时")
    values: dict[str, tuple[Decimal | None, str]] = {
        "contract": (contract, "原始合同额；不等于有效合同额或收入确认额"),
        "sec2": (total, "正式项目成本；三项政策行未自动计提"),
        "l2_material": (material_total, ""),
        "d_material": (material, ""),
        "d_fuel_power": (fuel_power, "燃料及动力"),
        "l2_rental": (rental_total, "设备租赁未细分吊车/脚手架" if rental else ""),
        "d_logistics": (logistics, ""),
        "l2_site": (
            site,
            (
                f"含未能安全细分到模板行的正式成本 {other:,.2f} 元；"
                "已计入本小计，不让金额消失"
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
        "d_ticket": (ticket, ""),
        "d_stay": (stay, ""),
        "d_living": (living, ""),
        "d_vehicle": (vehicle_total, ""),
        "d_vehicle_fuel": (vehicle, ""),
        "d_road_parking": (road_parking, ""),
        "l2_sub_labour": (
            sub_labour,
            f"外协 {sub_hours} 个工" if sub_hours else "",
        ),
        "allocation": (
            None,
            "模板原行；无合格管理费政策，禁止按合同额2%自动生成",
        ),
        "interest": (None, "无合格资金占用政策，留空"),
        "total": (total, ""),
        "profit": (
            None,
            "有效合同变更链与收入确认口径未闭合，禁止生成毛利",
        ),
    }

    output: list[tuple[str, Decimal | None, str]] = []
    for label, kind in TEMPLATE_A:
        amount, note = values.get(kind, (None, ""))
        if (
            amount is not None
            and total not in (None, Decimal(0))
            and kind not in ("contract", "total", "sec2")
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
