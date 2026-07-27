#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最近完工项目成本：从真实源算出，写成 App 能直接读的 JSON。

Owner 2026-07-27：「我根本没有看到项目成本，我说了我要最近完工的项目成本」。
所以这支程序的产物不是给人看的 CSV，而是**给页面读的 JSON**——数据要出现在驾驶舱里，
不是出现在聊天里。

两个口径并排，不调平：
  · 业务台账口径——红圈《生产项目状态表》里业务自己按项目填的
    材料费／交通费／生活住宿费／其他费用，以及自有与劳务人工工时；
  · 金蝶归集口径——明细账中按『销售合同号』归集的生产成本借方发生额。
差异本身就是要看的东西。任何一方缺失都如实留空，不拿另一方顶替。

口径锁（都是实测踩出来的，改动前先看这里）：
  · 账簿按名去重——源包里每本明细账存了 3 份同 CRC 副本，不去重直接三倍放大；
  · 取借方发生额而非净额——生产成本归集后结转到主营业务成本，净额会互相对冲成 0；
  · 合同号按完整主号匹配——序号跨年重复，按序号归并会把不同项目的钱并到一起；
  · 『不分项目』占位桶不计入任何项目。
"""
from __future__ import annotations
import argparse, collections, glob, io, json, os, re, sys, tempfile, zipfile
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_report  # noqa: E402
import rollup as R  # noqa: E402

STATUS_SHEET = "生产项目状态表.xlsx"
SUMMARY_ROWS = ("期初余额", "本期合计", "本年累计", "本期发生额", "期末余额")
BUSINESS_COST_COLUMNS = ("材料费", "交通费", "生活住宿费", "其他费用")


def norm_contract(value) -> str:
    """合同号归一：去空白、去重复自拼、只留主号。"""
    text = re.sub(r"\s", "", str(value or "")).upper()
    if "_" in text:
        head, tail = text.split("_", 1)
        if head == tail:
            text = head
    matched = re.match(r"(KMX\d+-?\d*)", text)
    return matched.group(1) if matched else text


def money(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return Decimal(repr(float(value)))
        except Exception:
            return None
    text = re.sub(r"[,\s，元]", "", str(value))
    return Decimal(text) if re.fullmatch(r"-?\d+(\.\d+)?", text) else None


def open_workbook(path: str):
    """打开 xlsx；先剥掉新版 Excel 的数据验证标签。

    实测：《生产项目状态表》带 `<dataValidation id=...>`，openpyxl 解析不了
    （`TypeError: DataValidation.__init__() got an unexpected keyword argument 'id'`）。
    只读模式是惰性解析，错误要到迭代行时才抛，try/except 包 load_workbook 接不住——
    所以不试探，一律先剥。数据验证与取数无关，且只在临时副本上剥，不改原文件。

    ⚠ 拿到 sheet 后**必须调 `sheet.reset_dimensions()`**，或者直接用 `iter_sheet_rows()`。
      见下面那个函数的注释：WPS/红圈导出的表声明 `<dimension ref="A1"/>`，
      只读模式信这个声明，于是 max_row=1、整表静默变空。
    """
    import openpyxl
    temporary = os.path.join(tempfile.mkdtemp(), os.path.basename(path))
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(
        temporary, "w", zipfile.ZIP_DEFLATED
    ) as target:
        for item in source.infolist():
            payload = source.read(item.filename)
            if item.filename.startswith("xl/worksheets/") and item.filename.endswith(".xml"):
                text = payload.decode("utf-8", "replace")
                text = re.sub(r"<dataValidations.*?</dataValidations>", "", text, flags=re.S)
                text = re.sub(r"<dataValidations[^>]*/>", "", text)
                text = re.sub(r"<extLst>.*?</extLst>", "", text, flags=re.S)
                payload = text.encode("utf-8")
            target.writestr(item, payload)
    return openpyxl.load_workbook(temporary, read_only=True, data_only=True)


def iter_sheet_rows(sheet, values_only: bool = True):
    """迭代一张表的所有行——**先把它自称的尺寸扔掉**。

    2026-07-27 实测的一个静默数据丢失（Owner：「wps的数据为什么不拉进来」）：
      WPS / 红圈导出的 xlsx 在 sheet 里写 `<dimension ref="A1"/>`——声称整表只有一个单元格。
      openpyxl 只读模式**信这个声明**去定 max_row，于是表头之后的每一行都读不到。
      它不报错、不告警，就是零行。

      被它吃掉的（都是真数据，不是边角料）：
        红圈主合同 4341 行、项目开票 4525 行、付款审批（日常费用）1200 行。
      而《生产项目状态表》没这个毛病，所以过去只有它一个源进得来——
      项目成本因此建在 20 个完工项目上，而红圈主合同里有 390 个。

    reset_dimensions() 让 openpyxl 改为**边读边算**真实范围。
    代价是不能提前知道行数，换来的是不会静默丢数据——这个交换在任何时候都值。
    """
    sheet.reset_dimensions()
    return sheet.iter_rows(values_only=values_only)


def read_completed_projects(data_root: str) -> dict:
    """红圈《生产项目状态表》：完工项目 + 业务自填的成本与工时。"""
    return read_projects(data_root, only_completed=True)


def read_projects(data_root: str, only_completed: bool = True) -> dict:
    """红圈《生产项目状态表》：项目 + 业务自填的成本与工时。

    only_completed=False 时连在建、待入场一起读出来——项目毛利要看的是「哪些项目在赚钱」，
    而在建项目「成本在走、收入还没落」本身就是一条要摆出来的信息，不是该被滤掉的噪声。
    """
    found: dict[str, dict] = {}
    for path in glob.glob(f"{data_root}/**/{STATUS_SHEET}", recursive=True):
        workbook = open_workbook(path)
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            header = header_row = None
            for index, row in enumerate(sheet.iter_rows(min_row=1, max_row=8, values_only=True)):
                cells = ["" if x is None else str(x).strip() for x in (row or [])]
                if sum(1 for c in cells if c) >= 4 and any("合同" in c for c in cells):
                    header, header_row = cells, index
                    break
            if not header:
                continue

            def column(*keys):
                for position, cell in enumerate(header):
                    if any(key in cell for key in keys):
                        return position
                return None

            contract_col = column("合同编号", "合同号")
            if contract_col is None:
                continue
            name_col = column("甲方名称", "项目名称", "工程名称")
            status_col = column("施工状态", "状态")
            done_col = column("完工时间", "竣工时间")
            amount_col = column("含税合同金额", "合同额", "合同金额")
            cost_cols = {label: column(label) for label in BUSINESS_COST_COLUMNS}
            other_cols = {
                label: column(label)
                for label in ("自有人工工时", "劳务人工工时", "结算金额", "开票金额",
                              "项目类型", "负责人", "开工时间", "是否提供项目成本表")
            }

            def cell(row, position):
                if position is None or position >= len(row) or row[position] is None:
                    return None
                return row[position]

            for row in sheet.iter_rows(min_row=header_row + 2, values_only=True):
                if not row:
                    continue
                key = norm_contract(cell(row, contract_col))
                if not key.startswith("KMX"):
                    continue
                status = str(cell(row, status_col) or "").strip()
                completed_at = str(cell(row, done_col) or "")[:10]
                done = bool(re.search(r"完工|竣工|完成|结束|已交|验收", status + completed_at))
                if only_completed and not done:
                    continue
                record = {
                    "合同编号": key,
                    "甲方名称": str(cell(row, name_col) or "").strip(),
                    "施工状态": status,
                    "完工日期": completed_at,
                    "含税合同金额": str(money(cell(row, amount_col)) or ""),
                }
                for label, position in cost_cols.items():
                    value = money(cell(row, position))
                    record[label] = str(value) if value is not None else ""
                for label, position in other_cols.items():
                    value = cell(row, position)
                    record[label] = "" if value is None else str(value)[:24]
                record["已完工"] = done
                previous = found.get(key)
                if not previous or completed_at > previous.get("完工日期", ""):
                    found[key] = record
        workbook.close()
    return found


def sort_key(record: dict) -> str:
    """完工日期缺失时用合同号里的日期兜底，让排序不至于把无日期的全推到末尾。"""
    if record.get("完工日期"):
        return record["完工日期"]
    matched = re.match(r"KMX(\d{6,8})", record["合同编号"])
    if matched:
        digits = matched.group(1)
        if len(digits) == 8:
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"
        if len(digits) == 6:
            return f"20{digits[:2]}-{digits[2:4]}-{digits[4:]}"
    return ""


def collect_ledger_cost(data_root: str, targets: set[str], account_to_row: dict) -> dict:
    """明细账按项目归集生产成本借方发生额。返回 {合同主号: {科目: 金额}}。"""
    import openpyxl
    aggregate: dict[str, dict[str, Decimal]] = collections.defaultdict(
        lambda: collections.defaultdict(Decimal))
    seen_books: set[str] = set()
    unknown_accounts: set[str] = set()

    def handle(sheet_name, sheet):
        prefix = re.match(r"(\d{4})", sheet_name)
        if not prefix or prefix.group(1) != "5001":
            return
        head = []
        for row in sheet.iter_rows(min_row=1, max_row=6, values_only=True):
            head.append(["" if x is None else str(x).strip() for x in (row or [])])
        header = header_row = None
        for index, row in enumerate(head):
            if "摘要" in row and "借方" in row:
                header, header_row = row, index
                break
        if not header:
            return
        try:
            contract_i = header.index("销售合同号")
            account_i = header.index("科目")
            memo_i = header.index("摘要")
            debit_i = header.index("借方")
        except ValueError:
            return
        for row in sheet.iter_rows(min_row=header_row + 2, values_only=True):
            if not row:
                continue
            memo = str(row[memo_i]).strip() if memo_i < len(row) and row[memo_i] is not None else ""
            if not memo or memo in SUMMARY_ROWS:
                continue
            raw = row[contract_i] if contract_i < len(row) else None
            if raw in (None, "") or "不分项目" in str(raw):
                continue
            key = norm_contract(raw)
            if key not in targets:
                continue
            account = str(row[account_i]).strip() if account_i < len(row) and row[account_i] else ""
            if account not in account_to_row:
                unknown_accounts.add(account)
                continue
            value = row[debit_i] if debit_i < len(row) else None
            try:
                amount = Decimal(str(value)) if value not in (None, "") else Decimal(0)
            except Exception:
                amount = Decimal(0)
            aggregate[key][account] += amount

    bundles = sorted(set(glob.glob(f"{data_root}/**/*金蝶*.zip", recursive=True)
                         + glob.glob(f"{data_root}/**/*明细账*.zip", recursive=True)))
    for bundle in bundles:
        with zipfile.ZipFile(bundle) as archive:
            for member in archive.namelist():
                if not member.lower().endswith((".xlsx", ".xlsm")):
                    continue
                base = os.path.basename(member)
                if base in seen_books:          # 源包里每本存 3 份同 CRC 副本
                    continue
                seen_books.add(base)
                try:
                    workbook = openpyxl.load_workbook(
                        io.BytesIO(archive.read(member)), read_only=True, data_only=True)
                except Exception:
                    continue
                for sheet_name in workbook.sheetnames:
                    try:
                        handle(sheet_name, workbook[sheet_name])
                    except Exception:
                        continue
                workbook.close()
    if unknown_accounts:
        raise KeyError(f"这些成本子科目未在映射表登记，拒绝静默丢弃：{sorted(unknown_accounts)}")
    return aggregate


def build(data_root: str, account_map: dict, limit: int = 20) -> dict:
    account_to_row = {m["account"]: m["rows"]["A"]["row"] for m in account_map["mappings"]}
    completed = read_completed_projects(data_root)
    ranked = sorted(completed.values(), key=sort_key, reverse=True)[:limit]
    ledger = collect_ledger_cost(data_root, {r["合同编号"] for r in ranked}, account_to_row)

    projects = []
    for record in ranked:
        key = record["合同编号"]
        leaf: dict[str, Decimal] = collections.defaultdict(Decimal)
        for account, amount in ledger.get(key, {}).items():
            leaf[account_to_row[account]] += amount
        violations = R.check_invariants("A", leaf)
        if violations:
            raise ValueError(f"{key} 上卷不自洽：{violations}")
        by_row, direct_total = R.rollup("A", leaf)

        business_total = sum((money(record.get(c)) or Decimal(0)) for c in BUSINESS_COST_COLUMNS)
        contract = money(record.get("含税合同金额"))
        projects.append({
            **{k: v for k, v in record.items()},
            "完工排序": sort_key(record),
            "业务台账成本合计": str(business_total),
            "台账口径毛利": str(contract - business_total) if contract is not None else "",
            "金蝶归集直接成本": str(direct_total),
            "金蝶成本明细": {row: str(value) for row, value in sorted(by_row.items())},
            "两口径差额": str(direct_total - business_total),
        })

    return {
        "schema_version": "kmfa.project_cost.recent_completed.v1",
        "口径": {
            "业务台账": "红圈《生产项目状态表》里业务自填的 材料费＋交通费＋生活住宿费＋其他费用",
            "金蝶归集": "明细账中按『销售合同号』归集的生产成本借方发生额；不含记入『不分项目』的部分",
            "为什么并排": "两个口径都来自真实记录，差异本身就是要看的东西——不做任何调平，也不挑一个好看的",
        },
        "锁定的算法": [
            "账簿按名去重：源包里每本明细账存了 3 份同 CRC 副本，不去重直接三倍放大",
            "取借方发生额而非净额：生产成本结转到主营业务成本，净额会互相对冲成 0",
            "合同号按完整主号匹配：序号跨年重复，按序号归并会把不同项目的钱并到一起",
            "『不分项目』占位桶不计入任何项目",
        ],
        "项目数": len(projects),
        "项目": projects,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="生成最近完工项目成本 JSON（供驾驶舱页面读取）")
    parser.add_argument("--data-root", required=True, help="KMFA_MetaData 根目录")
    parser.add_argument("--account-map", required=True, help="project_cost_account_map.json")
    parser.add_argument("--out", required=True, help="输出 JSON 路径")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    account_map = json.loads(Path(args.account_map).read_text(encoding="utf-8"))
    payload = build(args.data_root, account_map, args.limit)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {payload['项目数']} 个完工项目 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
