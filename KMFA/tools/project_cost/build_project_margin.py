#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目口径毛利：哪些项目在赚钱、哪些在亏、哪些还判不了。

与另外两页的分工（别合并，它们回答的是三个不同问题）：
  · 最近完工成本页 —— 最近做完的项目**花了多少**，按完工日期排；
  · 客户毛利页     —— 哪些**客户**在赚钱，按收入排；
  · 本页           —— 哪些**项目**在赚钱，且把在建的一并摆出来。

为什么在建项目也要列（2026-07-27 定案）：
  红圈信息表里 32 个项目，已完工只有 20 个，另外 12 个在建或待入场。
  只看完工的那 20 个，等于把「正在花钱、还没收钱」的那一半藏起来——
  而那恰恰是现金流最该盯的部分。在建项目不算毛利，但要标出来它处在哪一段。

**这一页给不出真毛利，也不假装给得出。** 两个成本口径都是残的：
  · 业务台账四项——材料费＋交通费＋生活住宿费＋其他费用。**不含人工**，
    而人工约占生产成本八成；且 20 个已完工项目里有一半这四项全填 0
    （不是没花钱，是没填）。
  · 金蝶归集——明细账里按销售合同号归集的生产成本借方发生额。是真账，
    但只覆盖带合同号的那部分；人工约七成记在「不分项目」，归集不到项目头上。

所以成本必然被低估，毛利必然被高估。能算的只有**毛利上限**——
真实毛利只会比它更低，低多少取决于没归集的那部分有多大。
初版按毛利率降序排，结果把六个「台账成本为 0、率 100%」的项目顶到最前面——
那不是最赚钱的六个，是数据最烂的六个。现在先按成本数据是否可用分档，再排序。
"""
from __future__ import annotations
import argparse, collections, json, sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
# 同目录同侪（rollup / render_report）彼此用裸 import 互相引用——那是脚本式跑法的写法。
# 想当包导入就得把这个目录也放进 sys.path，否则 rollup 里的 `from render_report import`
# 会在 import 阶段就炸，而且炸的是别人的文件，看起来完全不像本模块的问题。
sys.path.insert(0, str(Path(__file__).resolve().parent))

import rollup as R                                                   # noqa: E402
from build_recent_completed import (                                 # noqa: E402
    BUSINESS_COST_COLUMNS, collect_ledger_cost, money, read_projects,
)

#: 施工状态归成四段。原始表里的写法不统一（「已完工」「完工」「部分施工」……），
#: 按段分类而不是按原字符串分组——否则同一件事会散成好几档。
STAGES = (
    ("已完工", ("完工", "竣工", "完成", "结束", "已交", "验收")),
    ("施工中", ("施工中", "在建", "进行")),
    ("部分施工", ("部分",)),
    ("待入场", ("待入场", "未开工", "待开工")),
)


#: 排序三级：阶段 → 成本数据可用度 → 毛利上限率。
#: 中间那级是初版漏掉的，结果六个「成本为 0、上限率 100%」的项目占了榜首——
#: 它们不是最赚钱的，是最没数据的。可用度必须排在率的前面。
#: 摆在模块级是为了能被单测钉住：这条顺序一旦被人调换，页面就会重新开始撒谎。
阶段序 = {"已完工": 0, "部分施工": 1, "施工中": 2, "待入场": 3, "状态不明": 4}
可用度序 = {"两口径均有数": 0, "仅单口径有数": 1, "无成本数据": 2}


def stage_of(status: str, done: bool) -> str:
    if done:
        return "已完工"
    for name, markers in STAGES:
        if any(marker in status for marker in markers):
            return name
    return "状态不明"


def data_flags(*, stage: str, revenue: Decimal | None, business: Decimal,
               ledger: Decimal) -> list[str]:
    """每一条都对应一种「这个数不能直接引用」的具体理由。"""
    flags = []
    if stage != "已完工":
        flags.append("未完工：成本在走、收入还没落，不是最终结果")
    if business < 0 or ledger < 0:
        flags.append("成本为负（红冲多于发生）")
    if revenue and business == 0 and ledger == 0:
        flags.append("两个口径都为零：这个项目一分钱成本都没落到它头上，上限率必然是 100%")
    elif revenue and business == 0:
        flags.append("业务台账四项费用全为空——不是没花钱，是没填")
    if ledger == 0 and business > 0:
        flags.append("金蝶按合同号归集为零：成本在账上完全没归到这个项目头上")
    elif business > 0 and ledger > 0 and ledger < business / 2:
        flags.append("金蝶归集不足台账一半——大部分成本记去了『不分项目』")
    if not revenue:
        flags.append("无含税合同金额，算不出上限")
    return flags


def cost_confidence(business: Decimal, ledger: Decimal) -> str:
    """成本数据可用到什么程度。**排序先看这个**——否则数据最烂的会排最前。"""
    if business <= 0 and ledger <= 0:
        return "无成本数据"
    if business <= 0 or ledger <= 0:
        return "仅单口径有数"
    return "两口径均有数"


def _rate(gross: Decimal, revenue: Decimal | None) -> str:
    return f"{float(gross / revenue) * 100:.1f}%" if revenue else ""


def build(data_root: str, account_map: dict) -> dict:
    account_to_row = {m["account"]: m["rows"]["A"]["row"] for m in account_map["mappings"]}
    projects = read_projects(data_root, only_completed=False)
    ledger = collect_ledger_cost(data_root, set(projects), account_to_row)

    rows = []
    for key, record in projects.items():
        leaf: dict[str, Decimal] = collections.defaultdict(Decimal)
        for account, amount in ledger.get(key, {}).items():
            leaf[account_to_row[account]] += amount
        violations = R.check_invariants("A", leaf)
        if violations:
            raise ValueError(f"{key} 上卷不自洽：{violations}")
        by_row, ledger_total = R.rollup("A", leaf)

        business = sum((money(record.get(c)) or Decimal(0)) for c in BUSINESS_COST_COLUMNS)
        revenue = money(record.get("含税合同金额"))
        stage = stage_of(record.get("施工状态", ""), bool(record.get("已完工")))
        # 成本必然被低估（人工没归集），所以两个口径取**大**的那个当成本下限，
        # 由它算出来的才是毛利**上限**。取小的会让上限更虚高，是往错的方向靠。
        cost_floor = max(business, ledger_total)
        gross_business = (revenue - business) if revenue is not None else Decimal(0)
        gross_ledger = (revenue - ledger_total) if revenue is not None else Decimal(0)
        gross_cap = (revenue - cost_floor) if revenue is not None else Decimal(0)
        confidence = cost_confidence(business, ledger_total)
        rows.append({
            "合同编号": key,
            "甲方名称": record.get("甲方名称", ""),
            "施工状态": record.get("施工状态", ""),
            "阶段": stage,
            "完工日期": record.get("完工日期", ""),
            "项目类型": record.get("项目类型", ""),
            "负责人": record.get("负责人", ""),
            "含税合同金额": str(revenue) if revenue is not None else "",
            "业务台账成本": str(business),
            "台账口径毛利": str(gross_business) if revenue is not None else "",
            "台账口径毛利率": _rate(gross_business, revenue),
            "金蝶归集成本": str(ledger_total),
            "金蝶口径毛利": str(gross_ledger) if revenue is not None else "",
            "金蝶口径毛利率": _rate(gross_ledger, revenue),
            "两口径差额": str(ledger_total - business),
            "已知成本下限": str(cost_floor),
            "毛利上限": str(gross_cap) if revenue is not None else "",
            "毛利上限率": _rate(gross_cap, revenue),
            "成本数据": confidence,
            "金蝶成本明细": {row: str(value) for row, value in sorted(by_row.items())},
            "数据提示": data_flags(stage=stage, revenue=revenue,
                                   business=business, ledger=ledger_total),
        })

    def rank(row):
        rate = row["毛利上限率"]
        return (阶段序.get(row["阶段"], 9),
                可用度序.get(row["成本数据"], 9),
                -float(rate.rstrip("%")) if rate else 1e9)

    rows.sort(key=rank)

    by_stage: dict[str, dict] = {}
    for row in rows:
        bucket = by_stage.setdefault(row["阶段"], {
            "项目数": 0, "含税合同金额": Decimal(0), "业务台账成本": Decimal(0),
            "金蝶归集成本": Decimal(0), "已知成本下限": Decimal(0), "无成本数据": 0})
        bucket["项目数"] += 1
        bucket["含税合同金额"] += Decimal(row["含税合同金额"] or 0)
        bucket["业务台账成本"] += Decimal(row["业务台账成本"])
        bucket["金蝶归集成本"] += Decimal(row["金蝶归集成本"])
        bucket["已知成本下限"] += Decimal(row["已知成本下限"])
        if row["成本数据"] == "无成本数据":
            bucket["无成本数据"] += 1
    汇总 = {}
    for stage, bucket in by_stage.items():
        revenue = bucket["含税合同金额"]
        cap = revenue - bucket["已知成本下限"]
        汇总[stage] = {
            "项目数": bucket["项目数"],
            "含税合同金额": str(revenue),
            "业务台账成本": str(bucket["业务台账成本"]),
            "金蝶归集成本": str(bucket["金蝶归集成本"]),
            "已知成本下限": str(bucket["已知成本下限"]),
            "毛利上限": str(cap),
            "毛利上限率": _rate(cap, revenue if revenue else None),
            "其中无成本数据的项目数": bucket["无成本数据"],
        }

    return {
        "schema_version": "kmfa.project_margin.v1",
        "⚠这不是毛利": "两个成本口径都是残的——业务台账那四项不含人工，金蝶只归集到带合同号"
                        "的那部分，而人工约占生产成本八成、其中约七成记在『不分项目』。"
                        "成本必然被低估，所以这里给的是毛利上限，真实毛利只会更低。",
        "口径": {
            "收入": "红圈信息表的含税合同金额（合同口径，非开票口径）",
            "业务台账成本": "红圈里业务自填的 材料费＋交通费＋生活住宿费＋其他费用（不含人工）",
            "金蝶归集成本": "明细账中按『销售合同号』归集的生产成本借方发生额；不含『不分项目』",
            "已知成本下限": "两个口径取大者——成本本就被低估，取小的会让上限更虚高",
            "毛利上限": "含税合同金额 − 已知成本下限。是上限，不是毛利",
            "为什么两个口径并排": "两个都来自真实记录，差异本身就是要看的东西——"
                                  "不做任何调平，也不挑一个好看的",
        },
        # 数字从数据里来，不写死——写死过一次「32 个」，实际只有 31 个带合同号的项目。
        "为什么在建也列": f"{len(rows)} 个项目里已完工只有 {汇总.get('已完工', {}).get('项目数', 0)} 个。"
                          "只看完工的，等于把『正在花钱、还没收钱』的那一半藏起来——"
                          "而那恰是现金流最该盯的部分。",
        "阶段口径": "按施工状态归段；在建项目不算最终毛利，只标它处在哪一段。",
        "项目数": len(rows),
        "分阶段汇总": 汇总,
        "项目": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="生成项目口径毛利 JSON（供驾驶舱页面读取）")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--account-map", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    account_map = json.loads(Path(args.account_map).read_text(encoding="utf-8"))
    payload = build(args.data_root, account_map)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    done = payload["分阶段汇总"].get("已完工", {})
    print(f"✓ {payload['项目数']} 个项目 → {out}；已完工 {done.get('项目数')} 个，"
          f"毛利上限率 {done.get('毛利上限率')}"
          f"（其中 {done.get('其中无成本数据的项目数')} 个没有任何成本数据）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
