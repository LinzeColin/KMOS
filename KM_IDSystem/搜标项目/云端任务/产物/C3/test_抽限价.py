"""离线测试：python3 -m unittest test_抽限价 -v"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from 抽限价 import 大写转数, 抽金额, 抽限价  # noqa: E402
from 评测 import 评测, 读  # noqa: E402


def 值集(文本):
    return sorted((x["标段"], x["限价元"], x["含税"]) for x in 抽限价(文本))


class 大写(unittest.TestCase):
    def test_常见(self):
        self.assertEqual(大写转数("壹佰贰拾万元整"), 1200000)
        self.assertEqual(大写转数("贰拾叁万伍仟元整"), 235000)
        self.assertEqual(大写转数("壹仟零伍拾万零捌佰元整"), 10500800)
        self.assertAlmostEqual(大写转数("叁佰肆拾伍万陆仟柒佰捌拾玖元伍角贰分"), 3456789.52)
        self.assertEqual(大写转数("壹亿贰仟万元整"), 120000000)
        self.assertEqual(大写转数("拾万元整"), 100000)
        self.assertEqual(大写转数("一百二十万元"), 1200000)


class 不该抽(unittest.TestCase):
    def test_电话日期编号(self):
        t = "项目编号：KM-2025-0012；联系电话：0371-65432100，13800138000；开标时间：2025年10月8日9:30。最高限价：36万元。"
        self.assertEqual(值集(t), [(None, 360000.0, None)])

    def test_保证金业绩注册资本(self):
        t = "投标保证金：1万元；注册资本不少于300万元；近三年单项业绩不低于200万元；最高投标限价：158万元。"
        self.assertEqual(值集(t), [(None, 1580000.0, None)])

    def test_无限价无预算(self):
        self.assertEqual(抽限价("本项目为设备检修服务，工期60日历天，质保期12个月。"), [])

    def test_分项日期标段号不当限价(self):
        self.assertEqual(值集("最高限价（含暂列金10万元）为120万元"), [(None, 1200000.0, None)])
        self.assertEqual(值集("最高限价85万元2025.10.08前递交"), [(None, 850000.0, None)])
        self.assertEqual(值集("最高限价为RMB1,000,000.00"), [(None, 1000000.0, None)])

    def test_百分比不当金额(self):
        t = "最高限价：下浮率不低于5%。"
        self.assertEqual([x for x in 抽限价(t) if x["限价元"] is not None], [])


class 类型(unittest.TestCase):
    def test_只有预算时降级(self):
        r = 抽限价("预算金额：80万元")
        self.assertEqual(r[0]["类型"], "预算(代限价)")

    def test_有限价时不返回预算(self):
        r = 抽限价("预算金额：80万元；最高限价：78万元")
        self.assertEqual([(x["类型"], x["限价元"]) for x in r], [("最高限价", 780000.0)])

    def test_单价单位(self):
        r = 抽限价("单价最高限价：1,800元/吨")
        self.assertEqual((r[0]["类型"], r[0]["单位"], r[0]["限价元"]), ("单价限价", "元/吨", 1800.0))

    def test_无单位存疑(self):
        r = 抽限价("最高限价：560000")
        self.assertIn("无单位,按元计", r[0]["存疑"])

    def test_通用抽中标价(self):
        r = 抽金额("中标金额：人民币92.8万元", {"中标价": ["中标金额"]})
        self.assertEqual(r[0]["限价元"], 928000.0)


class 样例集(unittest.TestCase):
    def test_构造样例全对(self):
        结果 = 评测(读(HERE / "构造样例.jsonl"))
        self.assertEqual(结果["分组准确率"]["全部"]["准确率"], 1.0, 结果["错例"])

    def test_复审刁钻样例(self):
        """独立复审员写的 54 条刁钻输入（只比 标段+限价元）。"""
        import json
        错 = []
        for 行 in (HERE / "复审刁钻样例.jsonl").read_text(encoding="utf-8").splitlines():
            d = json.loads(行)
            得 = sorted(((x["标段"], x["限价元"]) for x in 抽限价(d["原文"])), key=str)
            if 得 != sorted((tuple(x) for x in d["期望"]), key=str):
                错.append((d["原文"], 得))
        self.assertEqual(错, [])

    def test_盲测样例全对(self):
        结果 = 评测(读(HERE / "盲测样例.jsonl"))
        self.assertEqual(结果["分组准确率"]["全部"]["准确率"], 1.0, 结果["错例"])


if __name__ == "__main__":
    unittest.main()
