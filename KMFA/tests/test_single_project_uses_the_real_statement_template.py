# -*- coding: utf-8 -*-
"""单个项目下载 = 竖版《项目财务分析表》，逐行照抄 Owner 的真实模版。

Owner 2026-07-30：「/Users/linzezhang/Downloads/KMFA_MetaData/销售绩效考核
这里面的才是真实模版，你现在用的不知道是什么恶心东西」。

**我在这件事上错了两版，都记下来：**
  1. 第一版：页签是我自己造的（使用说明／项目总览／毛利复核／成本明细），
     注释里写「对齐 Owner 手上那份竣工报表参考表」，而对照物
     `KMFA_项目成本_真实参考回放_8项目.xlsx` **是我自己生成的产物**。
     测试于是变成「我的输出等于我的输出」，Owner 每说一次不一样它都全绿。
  2. 第二版：改成《生产项目状态表》的 30 列横表。那张表是对的——但它是
     **项目清单**的格式。单个项目要的是竖版分析表。**两件不同的东西，我混了。**

真源是 `销售绩效考核/` 下的「竣工项目财务报表」PDF，逐行读出四份：
  A（池州恒鑫 085 / 崇阳昌华 084 / 新疆宜化 064）—— 终行 合计支出 +（七）毛利
  B（山东圣川）—— 多「项目产值」，（七）税金（八）分摊，终行「三 利润」

行序与百分比口径都是从真 PDF 反推的，写死在本文件里做独立对照。
不把 PDF 提交进仓：KMOS 是公开仓，那几份里是真实甲方名与真实金额。
"""
from __future__ import annotations

import importlib
import io
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "KMFA/app/backend"

#: 从 `竣工项目财务报表  池州恒鑫 085.pdf` 逐行抄下来的表体行序（**独立一份**，
#: 不 import 主程序常量——只 import 来比自己等于什么都没验）。
PDF_ROWS_AS_READ = [
    "一、合同额", "二、资金运用及各项支出",
    "（一）原材料", "其中:1.主要材料", "2.辅助材料", "2.1气体", "2.2焊材", "2.3漆料",
    "2.4低值易损耗材", "3 外协 加工费",
    "（二）租赁费", "其中:1.吊车租赁费", "2.脚手架租赁费", "3.物流运输费",
    "（三）保险费",
    "（四）现场管理费", "1.管理人员工资", "2.差旅费", "2.1车票", "2.2住宿",
    "3.业务费用", "3.1招待费", "4.生活费用", "4.1生活用品", "4.2生活费",
    "5.工程车辆使用费", "5.1加油费及保养", "5.2过路、停车费", "5.3维修费",
    "6.办公费", "7.安全防护费", "8.房租", "9.临电", "10.体检及工伤支出等",
    "11.罚款", "12.挂靠管理费",
    "（五）工资（承包费）支出", "（六）信息费",
    "三 1.1分摊的管理费用（合同的2%）", "1.2占用的资金利息",
    "合计支出", "（七）毛利",
]

#: 用真 PDF 那个项目的数喂进来，好逐格核对。
SAMPLE = {
    "生成时间": "2026-07-30T15:00:00+08:00",
    "项目": [{
        "合同编号": "KMX20251222-085", "甲方名称": "池州恒鑫材料科技有限公司",
        "施工状态": "已完工", "开工时间": "2025-12-23 00:00:00", "完工日期": "2025-12-30",
        "含税合同金额": "45000", "材料费": "494.10", "交通费": "542.81",
        "生活住宿费": "1300", "其他费用": "56", "自有人工工时": "41",
        "劳务人工工时": "17", "自有人工成本": "24098.85", "劳务人工成本": "9010",
        "分摊管理费": "900", "成本合计": "42779.24", "毛利": "6120.76",
        "现场成本取自": "红圈工时＋台账费用",
    }, {
        "合同编号": "KMX20251222-086", "甲方名称": "乙公司",
        "含税合同金额": "50000", "成本合计": "9000", "毛利": "41000",
    }],
}


def _client(tmp_path: Path):
    artifact = tmp_path / "recent_completed.json"
    artifact.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    sys.path.insert(0, str(BACKEND))
    os.environ["KMFA_RECENT_COST"] = str(artifact)
    import app.main as m  # noqa: PLC0415

    importlib.reload(m)
    from fastapi.testclient import TestClient  # noqa: PLC0415

    return TestClient(m.app, raise_server_exceptions=False)


def _statement(tmp_path: Path, key: str = "KMX20251222-085"):
    from openpyxl import load_workbook  # noqa: PLC0415

    r = _client(tmp_path).get("/项目成本/下载", params={"合同": key})
    assert r.status_code == 200, r.text[:300]
    book = load_workbook(io.BytesIO(r.content))
    return book, r


def _body(ws):
    """表体 → {行标签: (金额, 备注)}，并保留出现顺序。"""
    order, data = [], {}
    for row in ws.iter_rows(values_only=True):
        label = row[0]
        if not isinstance(label, str) or label not in PDF_ROWS_AS_READ:
            continue
        order.append(label)
        data[label] = (row[1] if len(row) > 1 else None,
                       row[2] if len(row) > 2 else None)
    return order, data


def test_it_is_the_vertical_statement_not_a_flat_row(tmp_path):
    """**本文件的正主。** 单项目件必须是竖版分析表，不是横表一行。"""
    book, _ = _statement(tmp_path)
    assert book.sheetnames[0] == "项目财务分析表", f"页签不对：{book.sheetnames}"
    # 第二版那个 30 列横表是**清单**格式，不该出现在单项目件里
    assert "信息表" not in book.sheetnames, "单项目件又变成项目清单格式了"


def test_the_row_order_is_the_pdfs_row_order(tmp_path):
    """行序、层级、编号、括号写法一字不改。"""
    book, _ = _statement(tmp_path)
    order, _ = _body(book["项目财务分析表"])
    assert order == PDF_ROWS_AS_READ, (
        "行序与真 PDF 不一致。\n"
        f"  少了：{[r for r in PDF_ROWS_AS_READ if r not in order]}\n"
        f"  多了/错序：{[r for r in order if r not in PDF_ROWS_AS_READ]}")


def test_the_amounts_land_on_the_pdfs_own_lines(tmp_path):
    """我有的数必须落在模版**它自己那一行**上，不是挪到别处。"""
    book, _ = _statement(tmp_path)
    _, data = _body(book["项目财务分析表"])
    for label, expected in (
        ("一、合同额", 45000),
        ("（一）原材料", 494.10),
        ("1.管理人员工资", 24098.85),
        ("2.差旅费", 1842.81),
        ("2.1车票", 542.81),
        ("2.2住宿", 1300.00),
        ("（五）工资（承包费）支出", 9010.00),
        ("三 1.1分摊的管理费用（合同的2%）", 900.00),
        ("合计支出", 42779.24),
        ("（七）毛利", 6120.76),
    ):
        got = data[label][0]
        assert got == expected, f"{label}：出的 {got}，应为 {expected}"


def test_the_profit_share_uses_the_contract_as_denominator(tmp_path):
    """**这条是逐行核对真 PDF 反推出来的，别改回去。**

    支出各行以「合计支出」为分母（494.10/42,779.24 = 1.15%），
    而（七）毛利以「合同额」为分母（6,120.76/45,000 = 13.60%）。
    用合计支出会算成 14.31% —— 这是给银行/税务看的表，比例口径错了不行。
    """
    book, _ = _statement(tmp_path)
    _, data = _body(book["项目财务分析表"])
    assert "13.60%" in (data["（七）毛利"][1] or ""), \
        f"毛利比例分母错了：{data['（七）毛利'][1]}（14.31% = 用了合计支出）"
    assert "1.15%" in (data["（一）原材料"][1] or "")
    assert "2.10%" in (data["三 1.1分摊的管理费用（合同的2%）"][1] or "")


def test_free_text_and_share_coexist_in_the_note(tmp_path):
    """真 PDF：「（五）工资（承包费）支出 9,010.00 外协17个工 21.06%」——两者并存。

    第一版写成「有文字就不算百分比」，于是（四）（五）两行的比例凭空消失了。
    """
    book, _ = _statement(tmp_path)
    _, data = _body(book["项目财务分析表"])
    note = data["（五）工资（承包费）支出"][1] or ""
    assert "17" in note and "21.06%" in note, f"文字与比例没并存：{note!r}"


def test_lines_i_have_no_data_for_stay_empty(tmp_path):
    """没有的行**留空**。留空是「我不知道」，填 0 是「我说它是 0」。"""
    book, _ = _statement(tmp_path)
    _, data = _body(book["项目财务分析表"])
    for label in ("（二）租赁费", "（三）保险费", "（六）信息费",
                  "5.工程车辆使用费", "1.2占用的资金利息", "8.房租"):
        assert data[label][0] in (None, ""), \
            f"{label} 我并没有这个数，却填了 {data[label][0]!r}"


def test_money_never_silently_disappears(tmp_path):
    """台账里的「其他费用」在模版里没有对应行——不能因此当它不存在。

    它已经算进成本合计了；如果既不进任何小计、又不写明，
    表里的分项就永远加不出合计，而看表的人不知道差额去哪了。
    """
    book, _ = _statement(tmp_path)
    _, data = _body(book["项目财务分析表"])
    site = data["（四）现场管理费"]
    assert site[0] == 25997.66, f"（四）小计没含其他费用：{site[0]}"
    assert "其他费用" in (site[1] or ""), f"其他费用没在备注里交代：{site[1]!r}"


def test_the_second_level_subtotal_satisfies_the_templates_identity(tmp_path):
    """模版恒等式：二、资金运用 + 三 项 = 合计支出。

    真 PDF：41,832.76 + 900.00 + 46.48 = 42,779.24。
    """
    book, _ = _statement(tmp_path)
    _, data = _body(book["项目财务分析表"])
    sec2 = data["二、资金运用及各项支出"][0]
    alloc = data["三 1.1分摊的管理费用（合同的2%）"][0] or 0
    interest = data["1.2占用的资金利息"][0] or 0
    assert round(sec2 + alloc + interest, 2) == data["合计支出"][0], \
        f"恒等式不成立：{sec2} + {alloc} + {interest} ≠ {data['合计支出'][0]}"


def test_the_header_block_copies_the_pdfs_fields(tmp_path):
    """表头区：项目名称／合同编号／开工时间／完工时间，措辞照抄。"""
    book, _ = _statement(tmp_path)
    ws = book["项目财务分析表"]
    text = "\n".join(
        "\t".join("" if c is None else str(c) for c in row)
        for row in ws.iter_rows(min_row=1, max_row=8, values_only=True))
    for must in ("项目财务分析表", "项目名称：", "合同编号", "开工时间", "完工时间",
                 "金额（元）", "备注", "池州恒鑫材料科技有限公司", "KMX20251222-085"):
        assert must in text, f"表头缺「{must}」：\n{text}"
    assert "2025/12/23" in text and "2025/12/30" in text, "日期没按模版的斜杠写法"


def test_there_is_a_signature_line_like_the_pdf(tmp_path):
    """PDF 末行是「项目经理: 日期：…」——交付件要能签字。"""
    book, _ = _statement(tmp_path)
    ws = book["项目财务分析表"]
    tail = "\n".join(
        "\t".join("" if c is None else str(c) for c in row)
        for row in ws.iter_rows(min_row=ws.max_row - 3, max_row=ws.max_row, values_only=True))
    assert "项目经理" in tail and "日期" in tail, f"没有签字行：\n{tail}"


def test_the_full_download_is_still_the_project_list_format(tmp_path):
    """不带合同号的全量件仍是《生产项目状态表》的清单格式——两种格式各归其位。"""
    from openpyxl import load_workbook  # noqa: PLC0415

    r = _client(tmp_path).get("/项目成本/下载")
    book = load_workbook(io.BytesIO(r.content))
    assert book.sheetnames[0] == "信息表", f"全量件不该变成竖表：{book.sheetnames}"
    assert [c.value for c in book["信息表"][1]][:3] == ["甲方名称", "省份", "合同号"]


def test_the_caliber_sheet_explains_where_each_number_came_from(tmp_path):
    """银行/税务要能看懂。口径放第二个页签，不挤占数据表。"""
    book, _ = _statement(tmp_path)
    assert book.sheetnames[0] == "项目财务分析表"
    assert "口径" in book.sheetnames
    text = "\n".join(
        "\t".join("" if c is None else str(c) for c in row)
        for row in book["口径"].iter_rows(values_only=True))
    assert "不是 0" in text, "没有写明空行的含义"
    assert "合计支出" in text


def test_the_filename_says_it_is_a_statement(tmp_path):
    _, r = _statement(tmp_path)
    disposition = r.headers.get("content-disposition", "")
    assert "KMX20251222-085" in disposition
    assert "statement" in disposition or "%E5%88%86%E6%9E%90%E8%A1%A8" in disposition, \
        f"文件名没体现这是分析表：{disposition}"
