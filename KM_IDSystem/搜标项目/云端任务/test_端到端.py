"""端到端离线测试：本机起一个假网站，把 C1/C2/C3 三条本地流水线从头跑一遍。

    cd 云端任务 && python3 -m unittest test_端到端 -v
不访问外网。页面内容全部是构造的（非真实公告）。
"""
import csv
import datetime as dt
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
产物 = ROOT / "产物"
for p in ("公共", "C1", "C2", "C3"):
    sys.path.insert(0, str(产物 / p))

今天 = dt.date.today()
d = [(今天 - dt.timedelta(days=i)).isoformat() for i in range(3)]

页面 = {
    "/r1": ("utf-8", 200, f"""<html><head><meta charset="utf-8"><title>回转窑检修</title></head><body>
<h1>某水泥有限公司回转窑托轮检修项目中标结果公告</h1><p>发布时间：2026-03-12</p><p>项目地点：河南省</p>
<p>评标办法：综合评分法</p><p>最高限价：120万元（含税）</p><p>中标人：某某机械设备有限公司</p><p>中标金额：108.6万元</p></body></html>"""),
    "/r2": ("gbk", 200, """<html><head><meta charset="gbk"></head><body>
<p>立磨减速机大修中标候选人公示</p><p>公示时间：2026年5月8日</p><p>招标控制价：人民币560,000.00元</p><p>评标办法：经评审的最低投标价法</p>
<p>第一中标候选人：甲工程有限公司，投标报价：498,000.00元</p><p>第二中标候选人：乙公司，投标报价：505,000.00元</p></body></html>"""),
    "/r3": ("utf-8", 200, """<html><body><p>辊压机及除尘器改造项目成交结果公告</p><p>发布日期：2026-06-01</p>
<p>标段一最高限价：80万元；标段二最高限价：50万元。</p><p>采购方式：竞争性磋商</p>
<p>标段一成交金额：72万元；标段二成交金额：46.5万元。</p></body></html>"""),
    "/r4": ("utf-8", 200, """<html><body><p>探伤检测服务中标结果</p><p>发布时间：2026-07-01</p><p>最高限价：30万元</p><p>中标价：下浮率8%</p></body></html>"""),
    "/ruishu": ("utf-8", 412, "<html><script>var $_ts=window['$_ts'];</script></html>"),
    "/login": ("utf-8", 200, "<html><body><form>用户登录 请先登录</form></body></html>"),
    "/captcha": ("utf-8", 200, "<html><body>安全验证 请输入验证码<script></script></body></html>"),
    "/list": ("utf-8", 200, "<html><body><table>" + "".join(
        f"<tr><td>{t}</td><td>{dd}</td></tr>" for t, dd in [
            ("1#窑检修项目招标公告", d[0]), ("办公用品采购", d[0]), ("球磨机维修服务", d[1]), ("食堂外包", d[1]),
            ("电除尘改造工程", d[1]), ("车辆保险", d[2]), ("减速机齿轮修复", d[2]), ("劳保用品", d[2])]) + "</table>供应商注册</body></html>"),
    "/jg_1": ("utf-8", 200, "<html><body><ul>"
        "<li><a href='/r1'>某水泥公司回转窑托轮检修项目中标结果公告</a></li>"
        "<li><a href='r3' title='辊压机及除尘器改造项目成交结果公告'>辊压机及除尘器改造...</a></li>"
        "<li><a href='/x9'>食堂外包服务中标结果公告</a></li>"
        "<li><a href='/t1'>水泥磨检修招标公告</a></li>"
        "<li><a href='javascript:void(0)'>下一页</a></li></ul></body></html>"),
    "/jg_2": ("utf-8", 200, "<html><body><a href='/r2'>立磨减速机大修中标候选人公示</a><a href='/r1'>某水泥公司回转窑托轮检修项目中标结果公告</a></body></html>"),
    "/t1": ("utf-8", 200, """<html><body><p>水泥磨检修招标公告</p><p>本项目分两个标段，标段一最高限价：人民币柒拾伍万元整；标段二最高限价：40万元（含税）。</p>
<p>投标保证金：1万元。</p></body></html>"""),
}


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        enc, code, body = 页面.get(self.path, ("utf-8", 404, "nf"))
        b = body.encode(enc)
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


def 跑(*args, 期望码=0):
    env = dict(os.environ, NO_PROXY="*", no_proxy="*")
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, env=env)
    if r.returncode != 期望码:
        raise AssertionError(f"{args} rc={r.returncode}\n{r.stdout}\n{r.stderr}")
    return r.stdout


class 端到端(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def 写链接(self, 名, 路径们):
        p = self.tmp / 名
        p.write_text("".join(json.dumps({"url": self.base + x, "title": ""}) + "\n" for x in 路径们), encoding="utf-8")
        return p

    def test_C2_抓取解析统计(self):
        链 = self.写链接("c2.jsonl", ["/r1", "/r2", "/r3", "/r4", "/ruishu"])
        缓存 = self.tmp / "c2raw"
        跑(产物 / "公共/抓取.py", "--输入", 链, "--缓存", 缓存, "--间隔", "0")
        状态 = {json.loads(x)["url"].rsplit("/", 1)[1]: json.loads(x)["状态"] for x in (缓存 / "索引.jsonl").read_text(encoding="utf-8").splitlines()}
        self.assertEqual(状态["ruishu"], "反爬-JS挑战(HTTP412)")
        self.assertEqual(状态["r2"], "ok")
        # 断点续跑：第二次全部跳过
        self.assertIn('"跳过": 5', 跑(产物 / "公共/抓取.py", "--输入", 链, "--缓存", 缓存, "--间隔", "0"))
        出 = self.tmp / "c2out"
        跑(产物 / "C2/解析结果.py", "--缓存", 缓存, "--链接", 链, "--输出", 出)
        with open(出 / "下浮率样本.csv", encoding="utf-8-sig") as f:
            样本 = list(csv.DictReader(f))
        率 = sorted((s["公告URL"].rsplit("/", 1)[1], s["标段"], s["下浮率"], s["评标办法"]) for s in 样本)
        self.assertEqual(率, [
            ("r1", "", "0.095", "综合评分法"),
            ("r2", "", "0.1107", "最低评标价法"),
            ("r3", "1", "0.1", "竞争性磋商"),
            ("r3", "2", "0.07", "竞争性磋商"),
        ])
        全文 = (出 / "下浮率样本.csv").read_text(encoding="utf-8-sig") + (出 / "解析明细.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("某某机械", 全文)  # 中标单位名不得出现
        self.assertNotIn("甲工程", 全文)
        self.assertIn("费率", (出 / "解析明细.jsonl").read_text(encoding="utf-8"))  # r4 记跳过原因
        r1 = next(s for s in 样本 if s["公告URL"].endswith("/r1"))
        self.assertEqual((r1["省份"], r1["日期"], r1["项目类型"], r1["税口径"]), ("河南", "2026-03-12", "检修维修", "含税"))
        跑(产物 / "C2/统计分布.py", "--样本", 出 / "下浮率样本.csv", "--输出", 出 / "下浮率分布.csv")
        with open(出 / "下浮率分布.csv", encoding="utf-8-sig") as f:
            总 = next(r for r in csv.DictReader(f) if r["评标办法"] == r["项目类型"] == r["金额档"] == "(全部)")
        self.assertEqual((总["样本数"], 总["P50"]), ("4", "0.0975"))

    def test_公共_列表抽链接(self):
        出 = self.tmp / "抽链.jsonl"
        跑(产物 / "公共/列表抽链接.py", "--列表页", self.base + "/jg_{页}", "--页", "1-2", "--必含", "中标|成交|候选人|结果",
           "--且含", "检修|维修|大修|改造", "--输出", 出, "--间隔", "0")
        行 = [json.loads(x) for x in 出.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sorted(x["url"].rsplit("/", 1)[1] for x in 行), ["r1", "r2", "r3"])  # 去重、过滤食堂和招标公告
        self.assertEqual(next(x for x in 行 if x["url"].endswith("r3"))["title"], "辊压机及除尘器改造项目成交结果公告")  # 用 title 属性补全截断标题
        # 再跑一次不重复追加
        跑(产物 / "公共/列表抽链接.py", "--列表页", self.base + "/jg_1", "--必含", "中标|成交", "--且含", "检修|改造", "--输出", 出, "--间隔", "0")
        self.assertEqual(len(出.read_text(encoding="utf-8").splitlines()), 3)

    def test_C3_切片段与校验(self):
        链 = self.写链接("c3.jsonl", ["/t1"])
        缓存 = self.tmp / "c3raw"
        跑(产物 / "公共/抓取.py", "--输入", 链, "--缓存", 缓存, "--间隔", "0")
        待 = self.tmp / "待标注.jsonl"
        跑(产物 / "C3/生成待标注.py", "--缓存", 缓存, "--输出", 待)
        行 = [json.loads(x) for x in 待.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(行), 1)
        self.assertTrue({"multi_lot", "capital", "tax"} <= set(行[0]["难点标签"]))
        # 模拟人工标注：一条正确、一条编造数字
        好 = dict(行[0], 正确答案=[{"标段": "1", "限价元": 750000, "含税": None}, {"标段": "2", "限价元": 400000, "含税": True}], 标注状态="已标注")
        编 = dict(行[0], id="x", 原文片段=行[0]["原文片段"][:-1], 正确答案=[{"标段": "1", "限价元": 123456, "含税": None}], 标注状态="已标注")
        待.write_text(json.dumps(好, ensure_ascii=False) + "\n" + json.dumps(编, ensure_ascii=False) + "\n", encoding="utf-8")
        出 = self.tmp / "难例.jsonl"
        out = 跑(产物 / "C3/标注校验.py", "--待标注", 待, "--输出", 出, "--至少", "1")
        self.assertIn("疑似编造", out)
        self.assertEqual(len(出.read_text(encoding="utf-8").splitlines()), 1)
        评 = json.loads(跑(产物 / "C3/评测.py", 出))
        self.assertEqual(评["分组准确率"]["全部"]["准确率"], 1.0)

    def test_C1_平台探测(self):
        普 = self.tmp / "普查.csv"
        列 = ["排序", "平台名称", "所属", "行业", "类别", "网址", "列表页URL", "免登录看列表", "需注册供应商", "反爬", "每天维修类公告估计", "估计方法", "证据URL", "证据级别", "核查状态", "备注"]
        行们 = [
            {"平台名称": "甲", "网址": self.base + "/list", "列表页URL": self.base + "/list", "需注册供应商": "没查"},
            {"平台名称": "乙", "网址": self.base + "/ruishu", "需注册供应商": "没查"},
            {"平台名称": "丙", "网址": self.base + "/login", "需注册供应商": "没查"},
            {"平台名称": "丁", "网址": self.base + "/captcha", "需注册供应商": "没查"},
            {"平台名称": "戊", "网址": "", "需注册供应商": ""},
        ]
        with open(普, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=列)
            w.writeheader()
            w.writerows(行们)
        出 = self.tmp / "普查出.csv"
        跑(产物 / "C1/平台探测.py", "--普查", 普, "--输出", 出, "--间隔", "0")
        with open(出, encoding="utf-8-sig") as f:
            r = {x["平台名称"]: x for x in csv.DictReader(f)}
        self.assertEqual(r["甲"]["排序"], "1")  # 有估计量的排最前
        self.assertEqual(r["甲"]["每天维修类公告估计"], "1.33")  # 3 天 4 条维修类
        self.assertEqual(r["甲"]["免登录看列表"], "是")
        self.assertTrue(r["甲"]["需注册供应商"].startswith("有注册入口"))
        self.assertEqual(r["乙"]["反爬"], "反爬-JS挑战(HTTP412)")
        self.assertEqual(r["丙"]["免登录看列表"], "否(需登录)")
        self.assertEqual(r["丁"]["反爬"], "验证码")
        self.assertTrue(r["乙"]["估计方法"].startswith("数不出来"))


if __name__ == "__main__":
    unittest.main()
