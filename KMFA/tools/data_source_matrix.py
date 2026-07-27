#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四平台数据源矩阵：声明「该有什么」，**实测**「实际有没有」。

Owner 2026-07-27：「我根本看不到你的数据源矩阵」+「钉钉红圈金蝶WPS四个平台，
每个平台都有自己的固定输入，你全部都需要让系统能做到自己定时定期收集上传整理」。

设计上只有一条硬规矩：**声明和实测必须分开，且实测不许读声明**。
  · 声明在 machine/facts/data_source_matrix.json——「这个平台应该给我哪几个输入」；
  · 实测在这里——照着 pattern 去源目录里找，找到几个文件、多少行、最新批次是哪天。
合在一起写就只剩自我确认：矩阵会永远显示「都齐了」，因为它抄的是自己的清单。
分开之后才可能出现「声明要这个输入、实测它不在」——而那一格才是这张表存在的理由。

行数为什么必须实测而不是信文件（血的教训）：
  WPS/红圈导出的 xlsx 声明 `<dimension ref="A1"/>`，openpyxl 只读模式信了它，
  于是红圈主合同 4341 行、项目开票 4525 行、付款审批 1200 行**全部读为 0 行**，
  不报错不告警。这张矩阵如果只查「文件在不在」，那三个文件会显示绿的——
  文件确实在，只是一行都读不出来。所以矩阵报的是**读得出来的行数**。

公开边界：只出平台名、输入名、文件数、行数、批次日期。
  **不出**金额、不出客户名、不出文件绝对路径（会暴露目录结构）。
"""
from __future__ import annotations
import argparse, glob, json, os, sys, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent / "project_cost"))

BEIJING = timezone(timedelta(hours=8))
FACTS = Path(__file__).resolve().parents[1] / "machine" / "facts" / "data_source_matrix.json"

#: 批次目录形如 2026-07-04。用它报「数据截至哪天」，比文件 mtime 可靠——
#: mtime 会被一次 rsync 全部刷新，看着像今天的数，其实是三个月前的批次。
_BATCH = "20[0-9][0-9]-[0-1][0-9]-[0-3][0-9]"


def _batch_of(path: str) -> str:
    import re
    found = re.findall(r"(20\d{2}-\d{2}-\d{2})", path)
    return max(found) if found else ""


def count_rows(path: str) -> tuple[int, str]:
    """返回（读得出来的行数, 说明）。读不出来就说读不出来，不返回 0 冒充空表。"""
    lower = path.lower()
    if lower.endswith(".zip"):
        try:
            with zipfile.ZipFile(path) as archive:
                inner = [n for n in archive.namelist() if n.lower().endswith((".xlsx", ".xlsm"))]
            return len(inner), f"压缩包内 {len(inner)} 本工作簿"
        except Exception as exc:                  # noqa: BLE001
            return -1, f"压缩包打不开：{type(exc).__name__}"
    if not lower.endswith((".xlsx", ".xlsm")):
        return -1, "非表格文件，未计行"
    try:
        from build_recent_completed import iter_sheet_rows, open_workbook
        workbook = open_workbook(path)
        total = 0
        for name in workbook.sheetnames:
            # iter_sheet_rows 会先 reset_dimensions——WPS 导出谎报尺寸，信它就整表读空。
            total += sum(1 for _ in iter_sheet_rows(workbook[name]))
        workbook.close()
        return total, "实测行数（已丢弃文件自称的尺寸）"
    except Exception as exc:                      # noqa: BLE001
        return -1, f"读不出来：{type(exc).__name__}"


def measure(data_root: str, declared: dict) -> dict:
    platforms = []
    for platform in declared["platforms"]:
        inputs = []
        for slot in platform["inputs"]:
            pattern = slot.get("pattern") or ""
            if pattern.startswith("（"):          # 直连接口类，没有文件可数
                inputs.append({**{k: v for k, v in slot.items() if k != "pattern"},
                               "实测": "接口直连，无文件产物", "文件数": None,
                               "行数": None, "数据截至": None, "状态": "接口"})
                continue
            hits = sorted(glob.glob(os.path.join(data_root, pattern), recursive=True))
            hits = [h for h in hits if os.path.isfile(h)]
            rows, note = (0, "没有匹配到文件")
            batch = ""
            if hits:
                rows = 0
                bad = 0
                for one in hits:
                    n, note = count_rows(one)
                    if n < 0:
                        bad += 1
                    else:
                        rows += n
                    batch = max(batch, _batch_of(one))
                if bad:
                    note = f"{bad}/{len(hits)} 个文件读不出来"
            状态 = ("缺输入" if not hits else
                    "读不出来" if rows <= 0 else
                    "已接入")
            inputs.append({
                **{k: v for k, v in slot.items() if k != "pattern"},
                "文件数": len(hits), "行数": rows if hits else 0,
                "数据截至": batch or None, "实测": note, "状态": 状态,
            })
        platforms.append({
            "平台": platform["name"], "id": platform["id"],
            # 平台连接层。**头条数字必须是它**——「文件到位」不等于「平台打通」，
            # 混在一起就是假绿：Owner 当场纠正过一次，当时矩阵显示「已接入 11」，
            # 而那 11 个是他自己手动导出的文件到位了，自动通道一个都没通。
            "连接": platform.get("connection", {}),
            "采集方式": platform["collector"], "采集周期": platform["schedule"],
            "输入数": len(inputs),
            "已接入": sum(1 for i in inputs if i["状态"] in ("已接入", "接口")),
            "自动收集": sum(1 for i in inputs if i.get("collection") == "collected"),
            "输入": inputs,
        })

    全部输入 = [i for p in platforms for i in p["输入"]]
    连接 = [p["连接"].get("status") for p in platforms]
    return {
        "⚠平台打通情况": {
            "平台总数": len(platforms),
            "自动通道跑通的": sum(1 for c in 连接 if c == "connected"),
            "通道在但没跑通的": sum(1 for c in 连接 if c == "partial"),
            "完全没有通道的": sum(1 for c in 连接 if c == "none"),
            "按约定走人工的": sum(1 for c in 连接 if c == "by_design_manual"),
            "口径": declared["连接状态口径"],
            "为什么这是头条": declared["为什么分两层"],
        },
        "schema_version": "kmfa.data_source_matrix.measured.v1",
        "生成时间": datetime.now(BEIJING).isoformat(),
        "口径": declared["purpose"],
        "为什么声明与实测分开": declared["为什么分开"],
        "采集现状口径": declared["采集现状口径"],
        "平台数": len(platforms),
        "输入总数": len(全部输入),
        "已接入": sum(1 for i in 全部输入 if i["状态"] in ("已接入", "接口")),
        "缺输入": sum(1 for i in 全部输入 if i["状态"] == "缺输入"),
        "读不出来": sum(1 for i in 全部输入 if i["状态"] == "读不出来"),
        "系统自动收集的": sum(1 for i in 全部输入 if i.get("collection") == "collected"),
        "还靠人工放文件的": sum(1 for i in 全部输入 if i.get("collection") == "manual"),
        "完全没接的": sum(1 for i in 全部输入 if i.get("collection") == "not_wired"),
        "平台": platforms,
    }


def to_csv(measured: dict) -> str:
    """给下载按钮用。逗号分隔，字段里的逗号换成中文逗号——不引入引号转义。"""
    lines = ["平台,平台连接,输入,采集现状,状态,文件数,行数,数据截至,喂给哪些业务,卡在哪"]
    for platform in measured["平台"]:
        for slot in platform["输入"]:
            def clean(value):
                return str(value if value not in (None, "") else "—").replace(",", "，").replace("\n", " ")
            lines.append(",".join(clean(v) for v in (
                platform["平台"], platform["连接"].get("status"),
                slot.get("name"), slot.get("collection"), slot.get("状态"),
                slot.get("文件数"), slot.get("行数"), slot.get("数据截至"),
                "/".join(slot.get("feeds") or []), slot.get("blocker"))))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="实测四平台数据源矩阵")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--csv-out")
    parser.add_argument("--facts", default=str(FACTS))
    args = parser.parse_args()

    declared = json.loads(Path(args.facts).read_text(encoding="utf-8"))
    measured = measure(args.data_root, declared)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(measured, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.csv_out:
        Path(args.csv_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.csv_out).write_text(to_csv(measured), encoding="utf-8-sig")
    通 = measured["⚠平台打通情况"]
    print(f"⚠ 平台自动通道：跑通 {通['自动通道跑通的']}、通道在但没跑通 {通['通道在但没跑通的']}、"
          f"完全没通道 {通['完全没有通道的']}、按约定人工 {通['按约定走人工的']}")
    print(f"✓ {measured['平台数']} 个平台 / {measured['输入总数']} 个输入 → {out}；"
          f"已接入 {measured['已接入']}、缺输入 {measured['缺输入']}、读不出来 {measured['读不出来']}；"
          f"系统自动收 {measured['系统自动收集的']}、靠人工放 {measured['还靠人工放文件的']}、"
          f"完全没接 {measured['完全没接的']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
