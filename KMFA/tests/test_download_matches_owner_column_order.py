# -*- coding: utf-8 -*-
"""下载件的列序必须与 Owner 的《生产项目状态表》「信息表」一模一样。

Owner 2026-07-29：「项目成本单个项目下载下来的和我原来的格式根本不一样，
你不要用乱七八糟的东西恶心我，这个东西很急，我和你说了无数遍」。

**我错在哪，写下来免得再犯：**
上一版下载件的页签是 使用说明／项目总览／毛利复核／成本明细／合同号存疑，
注释里写着「对齐 Owner 手上那份竣工报表参考表」，对照物是
`KMFA_项目成本_真实参考回放_8项目.xlsx`——**而那份是我自己生成的产物**。
拿自己的输出当基准、再宣称对齐了对方的格式，这就是「说了无数遍」的由来。

真源是 `生产项目状态表.xlsx` 的「信息表」，30 列。列名已钉进
`main.OWNER_STATUS_COLUMNS`，本文件守着它不许被悄悄改动。

为什么不把那个 xlsx 提交进仓做对照：KMOS 是**公开仓**，那份表里是真实甲方名与
真实合同额（见 kmos-public-repo-financial-leak）。所以钉的是**列名**——列名不是
业务数据；真值一个都不进。
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

#: 逐列从 Owner 那份 xlsx 的「信息表」表头读出（2026-07-29）。
#: 这份清单是**独立抄录**的，不是 import 来的——两边各写一份，
#: 改了一边另一边就红。若只 import 主程序里的常量来比自己，那等于什么都没验。
OWNER_HEADER_AS_READ = [
    "甲方名称", "省份", "合同号", "含税合同金额", "税率", "负责人", "项目类型",
    "开工时间", "完工时间", "实际工期", "施工状态", "结算时间", "开票时间", "回款时间",
    "完工后结算时间", "结算后开票时间", "开票后回款90%时间", "结算金额", "开票金额",
    "结算审计偏差率", "自有人工工时", "劳务人工工时", "生活住宿费", "交通费", "材料费",
    "其他费用", "项目成本表截止提供时间", "截止剩余时间", "是否提供项目成本表",
    "是否已计算提成",
]

SAMPLE = {
    "生成时间": "2026-07-29T20:00:00+08:00",
    "项目": [
        {"合同编号": "KMX2026001-001", "甲方名称": "甲公司", "施工状态": "已完工",
         "完工日期": "2026-06-30", "含税合同金额": "128000", "项目类型": "自有人员",
         "负责人": "某某", "开工时间": "2026-05-24 00:00:00",
         "材料费": "774.25", "交通费": "1470", "生活住宿费": "1370",
         "自有人工工时": "37", "自有人工成本": "18500", "劳务人工成本": "0",
         "金蝶归集直接成本": "0", "分摊管理费": "2560", "成本合计": "24674.25",
         "毛利": "103325.75", "现场成本取自": "红圈工时＋台账费用",
         "身份来源": "红圈主合同（权威）"},
        {"合同编号": "KMX2026001-002", "甲方名称": "乙公司", "成本合计": "9000",
         "含税合同金额": "50000", "毛利": "41000"},
        {"合同编号": "KMX2026001-009", "甲方名称": "丙公司", "成本合计": "1234",
         "合同号存疑": True},
    ],
}


def _client(tmp_path: Path):
    artifact = tmp_path / "recent_completed.json"
    artifact.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    sys.path.insert(0, str(BACKEND))
    os.environ["KMFA_RECENT_COST"] = str(artifact)
    import app.main as m  # noqa: PLC0415

    importlib.reload(m)
    from fastapi.testclient import TestClient  # noqa: PLC0415

    return TestClient(m.app, raise_server_exceptions=False), m


def _sheet(response):
    from openpyxl import load_workbook  # noqa: PLC0415

    book = load_workbook(io.BytesIO(response.content))
    return book


def test_the_first_thirty_columns_are_the_owners_columns_in_his_order(tmp_path):
    """**本文件的正主。** 前 30 列逐列相同、顺序相同、一个字不改。"""
    client, _ = _client(tmp_path)
    book = _sheet(client.get("/项目成本/下载"))
    assert "信息表" in book.sheetnames, f"工作表名不是「信息表」：{book.sheetnames}"
    ws = book["信息表"]
    header = [c.value for c in ws[1]]
    assert header[:30] == OWNER_HEADER_AS_READ, (
        "前 30 列与 Owner 的《生产项目状态表》不一致。\n"
        f"  他的：{OWNER_HEADER_AS_READ}\n"
        f"  出的：{header[:30]}")


def test_the_module_constant_matches_the_header_read_from_his_file(tmp_path):
    """主程序里的常量必须等于我从他文件里抄下来的这份。

    两边**各写一份**是故意的：只 import 常量来比自己，等于什么都没验。
    """
    _, m = _client(tmp_path)
    assert list(m.OWNER_STATUS_COLUMNS) == OWNER_HEADER_AS_READ


def test_computed_values_are_appended_never_interleaved(tmp_path):
    """我算的东西只能接在第 31 列往后。

    插进去等于改了他的表；顶掉某一列等于我认为我的口径比他的表更权威。
    """
    client, m = _client(tmp_path)
    ws = _sheet(client.get("/项目成本/下载"))["信息表"]
    header = [c.value for c in ws[1]]
    for column in m.COMPUTED_COLUMNS:
        assert header.index(column) >= 30, f"{column} 插进了原表 30 列之内"
    assert len(header) == 30 + len(m.COMPUTED_COLUMNS), f"列数不对：{len(header)}"


def test_the_old_invented_sheets_are_gone(tmp_path):
    """那几个我自己造的页签必须消失——它们正是 Owner 说的「乱七八糟的东西」。"""
    client, _ = _client(tmp_path)
    names = _sheet(client.get("/项目成本/下载")).sheetnames
    for invented in ("使用说明", "项目总览", "毛利复核", "成本明细", "合同号存疑"):
        assert invented not in names, f"自造页签「{invented}」还在：{names}"


def test_the_single_contract_download_is_deliberately_a_different_format(tmp_path):
    """单合同件**不是**这个 30 列横表——它是竖版《项目财务分析表》。

    2026-07-30 本条整条改向：我上一版把它写成「单合同件必须与全量件同格式」，
    那是又一次搞混。Owner 指出真模版在 `销售绩效考核/` 下的
    「竣工项目财务报表」PDF：
      · 全量件 = 《生产项目状态表》30 列横表 → **项目清单**
      · 单项目 = 竖版《项目财务分析表》     → **单个项目的成本表**
    两种格式各归其位。竖表的行序与口径归
    KMFA/tests/test_single_project_uses_the_real_statement_template.py 管。
    """
    client, _ = _client(tmp_path)
    one = _sheet(client.get("/项目成本/下载", params={"合同": "KMX2026001-001"}))
    assert one.sheetnames[0] == "项目财务分析表", f"单合同件页签不对：{one.sheetnames}"
    assert "信息表" not in one.sheetnames, "单合同件又变回清单格式了"


def test_his_own_field_names_land_in_his_own_columns(tmp_path):
    """材料费／交通费／生活住宿费这些字段**本来就来自他的表**，必须回到原位。"""
    client, _ = _client(tmp_path)
    # 用**全量件**验列位：单合同件已改为竖版分析表，不再是这个横表。
    ws = _sheet(client.get("/项目成本/下载"))["信息表"]
    header = [c.value for c in ws[1]]
    row = {header[i]: ws.cell(row=2, column=i + 1).value for i in range(len(header))}
    assert row["甲方名称"] == "甲公司"
    assert row["合同号"] == "KMX2026001-001"
    assert row["含税合同金额"] == 128000
    assert row["材料费"] == 774.25
    assert row["交通费"] == 1470
    assert row["生活住宿费"] == 1370
    assert row["自有人工工时"] == 37
    assert row["项目类型"] == "自有人员"
    assert row["完工时间"] == "2026-06-30"
    assert row["开工时间"] == "2026-05-24", "日期没去掉时分秒"


def test_missing_columns_are_blank_not_zero(tmp_path):
    """他有、我没有的列必须**留空**。

    留空是「我不知道」，填 0 是「我说它是 0」——后者会被当成真实业务数字拿去用。
    """
    client, _ = _client(tmp_path)
    # 用**全量件**验列位：单合同件已改为竖版分析表，不再是这个横表。
    ws = _sheet(client.get("/项目成本/下载"))["信息表"]
    header = [c.value for c in ws[1]]
    for column in ("省份", "税率", "结算时间", "开票时间", "回款时间", "是否已计算提成"):
        value = ws.cell(row=2, column=header.index(column) + 1).value
        assert value in (None, ""), f"{column} 我并没有这个数，却填了 {value!r}"


def test_the_suspect_contract_is_still_excluded(tmp_path):
    """换格式不等于放开口径：合同号与权威表冲突的仍然不进表。"""
    client, _ = _client(tmp_path)
    ws = _sheet(client.get("/项目成本/下载"))["信息表"]
    keys = [ws.cell(row=r, column=3).value for r in range(2, ws.max_row + 1)]
    assert "KMX2026001-009" not in keys, "存疑合同又混进来了"


def test_the_caliber_sheet_exists_but_does_not_occupy_the_data_sheet(tmp_path):
    """口径要有（银行/税务要能看懂每个数从哪来），但只能待在第二个页签。"""
    client, _ = _client(tmp_path)
    book = _sheet(client.get("/项目成本/下载"))
    assert book.sheetnames[0] == "信息表", f"第一个页签不是数据表：{book.sheetnames}"
    assert "口径" in book.sheetnames
