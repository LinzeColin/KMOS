"""把已抓取的中标/成交结果公告解析成下浮率样本（仅标准库）。

    python3 解析结果.py --缓存 本地产出/C2原文 --链接 c2_候选链接.jsonl --输出 本地产出/C2
产出：
    下浮率样本.csv   每行一个（公告, 标段）样本，列见 列名；**不含中标单位名**
    解析明细.jsonl   每个公告的解析过程/跳过原因（片段里的单位名已抹成 [单位]），供复核
下浮率 = 1 − 中标价 ÷ 限价。只在两者口径能一一配上时出样本，配不上就记跳过原因，不硬凑。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 依赖既可与本目录平级（标准布局 产物/公共、产物/C3），也可在本目录内（回件切件后 C2/公共、C2/抽限价.py）
for _p in (HERE.parent / "C3", HERE.parent / "公共", HERE / "公共", HERE):
    if _p.is_dir():
        sys.path.insert(0, str(_p))
from 抽限价 import 抽金额, 抽限价, 规整  # noqa: E402
from 抓取 import 读正文, 读索引, 读jsonl  # noqa: E402

列名 = ["公告URL", "日期", "省份", "项目类型", "评标办法", "限价", "中标价", "下浮率", "标段", "限价口径", "中标价口径", "税口径", "金额档", "质检", "来源站点"]

中标词 = ["中标（成交）金额", "中标(成交)金额", "中标（成交）价", "中标(成交)价", "中标金额", "中标价格", "中标价", "中标总价", "成交金额", "成交价格", "成交价", "成交总价", "中选金额", "中选价"]
候选报价词 = ["投标报价", "投标总价", "报价金额", "投标价格", "评标价"]

省份表 = ["北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江", "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州", "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆"]
域名省份 = {"beijing": "北京", "tianjin": "天津", "hebei": "河北", "shanxi": "山西", "nmg": "内蒙古", "nmgov": "内蒙古", "ln.": "辽宁", "liaoning": "辽宁", "jl.": "吉林", "jilin": "吉林", "hlj": "黑龙江", "shanghai": "上海", "jiangsu": "江苏", "js.": "江苏", "zj.": "浙江", "zhejiang": "浙江", "ah.": "安徽", "anhui": "安徽", "fujian": "福建", "fj.": "福建", "jiangxi": "江西", "jx.": "江西", "shandong": "山东", "sd.": "山东", "henan": "河南", "hubei": "湖北", "hunan": "湖南", "gd.": "广东", "guangdong": "广东", "gxzf": "广西", "guangxi": "广西", "hainan": "海南", "cq.": "重庆", "chongqing": "重庆", "sc.": "四川", "sichuan": "四川", "guizhou": "贵州", "gz.gov": "贵州", "yn.": "云南", "yunnan": "云南", "xizang": "西藏", "shaanxi": "陕西", "gansu": "甘肃", "qinghai": "青海", "nx.": "宁夏", "ningxia": "宁夏", "xinjiang": "新疆", "xj.": "新疆"}

类型规则 = [("改造", r"改造|技改|升级|更新改造"), ("安装", r"安装|拆装|迁装"), ("检测", r"检测|探伤|监测|无损|检验"), ("检修维修", r"检修|维修|大修|中修|小修|维保|修复|抢修|修理|保运|维护")]
评标规则 = [("综合评分法", r"综合评分|综合评估|综合打分"), ("合理低价法", r"合理低价"), ("最低评标价法", r"最低评标价|经评审的最低投标价|最低投标价法|最低价中标|最低价法"),
          ("竞争性磋商", r"竞争性磋商"), ("竞争性谈判", r"竞争性谈判"), ("询价", r"询价"), ("评定分离", r"评定分离")]

_单位名式 = re.compile(r"[一-龥（）()·A-Za-z0-9]{2,40}?(?:有限责任公司|股份有限公司|有限公司|分公司|公司|集团|研究院|研究所|工程处|厂)")


_单位标签式 = re.compile(r"((?:第[一二三四五1-5]名?)?(?:中标|成交|中选)?(?:候选人|人|单位|供应商|供应商名称|单位名称)(?:名称)?\s*[:：]\s*)[^,，;；\n。|]{1,40}")


def 抹单位(s: str) -> str:
    """片段里的单位名一律抹掉：①"中标人：xxx"类标签后的名字（不论有无公司后缀，防截断漏网）②带公司后缀的名称。"""
    return _单位名式.sub("[单位]", _单位标签式.sub(r"\1[单位]", s))


def 金额档(限价: float) -> str:
    万 = 限价 / 1e4
    if 万 < 50:
        return "<50万"
    if 万 < 200:
        return "50-200万"
    if 万 < 1000:
        return "200-1000万"
    return "≥1000万"


def 找日期(t: str) -> str:
    m = re.search(r"(?:发布|公告|公示|成交|中标)(?:时间|日期)\s*[:：]?\s*(20\d{2})[-/年.](\d{1,2})[-/月.](\d{1,2})", t)
    if not m:
        m = re.search(r"(20\d{2})[-/年.](\d{1,2})[-/月.](\d{1,2})", t)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""


def 找省份(t: str, url: str, 标题: str) -> str:
    for p in 省份表:
        if p in 标题:
            return p
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    for k, v in 域名省份.items():
        if k in host:
            return v
    头 = t[:2000]
    计 = {p: 头.count(p) for p in 省份表 if p in 头}
    return max(计, key=计.get) if 计 else ""


def 归类(文本: str, 规则) -> str:
    for 名, 式 in 规则:
        if re.search(式, 文本):
            return 名
    return ""


def 取中标价(t: str) -> list[dict]:
    """先找明确的中标/成交金额；没有则在"第一中标候选人"段里找投标报价。"""
    r = [x for x in 抽金额(t, {"中标价": 中标词}) if x["限价元"] is not None and "/" not in x["单位"]]
    if r:
        for x in r:
            x["口径"] = "中标/成交金额"
        return r
    m = re.search(r"第一(?:中标|成交)?候选人|排名第一|第一名", t)
    if m:
        止 = re.search(r"第二(?:中标|成交)?候选人|排名第二|第二名", t[m.end():])
        段 = t[m.start(): m.end() + (止.start() if 止 else 400)]
        r = [x for x in 抽金额(段, {"中标价": 候选报价词 + 中标词}) if x["限价元"] is not None and "/" not in x["单位"]]
        for x in r:
            x["口径"] = "第一候选人报价"
        return r[:1] if len({x["标段"] for x in r}) <= 1 else r
    return []


def 选限价(候选: list[dict], 中: dict) -> dict:
    """同一标段有多个限价时：①税口径与中标价一致者优先（任一方未说明视为一致）②无存疑者优先 ③金额大者优先（分项总小于总价）。"""
    def 键(x):
        税不符 = x["含税"] is not None and 中.get("含税") is not None and x["含税"] != 中["含税"]
        return (税不符, bool(x["存疑"]), -x["限价元"])
    return sorted(候选, key=键)[0]


def 配对(限价: list[dict], 中标: list[dict]):
    """返回 [(限价项, 中标项)] 与跳过原因。"""
    总价 = [x for x in 限价 if x["限价元"] is not None and x["类型"] != "单价限价"]
    if not 总价:
        return [], "无限价金额（未公布/详见文件/仅单价）"
    if not 中标:
        return [], "无中标价金额（可能为费率/下浮率报价或附件）"
    段限 = {}
    for x in 总价:
        段限.setdefault(x["标段"], []).append(x)
    段中 = {}
    for x in 中标:
        段中.setdefault(x["标段"], []).append(x)
    对 = []
    if len(段限) == 1 and len(段中) == 1:
        a = list(段限.values())[0]
        b = list(段中.values())[0]
        if len(b) != 1:
            return [], "单标段出现多个不同中标价，无法确定"
        return [(选限价(a, b[0]), b[0])], ""
    for 段, b in 段中.items():
        if 段 in 段限 and len(b) == 1:
            对.append((选限价(段限[段], b[0]), b[0]))
    return 对, ("" if 对 else "多标段无法按标段配对")


def 解析一篇(url: str, t: str, 标题: str = "") -> tuple[list[dict], dict]:
    t = 规整(t)
    标题 = 标题 or t.split("\n", 1)[0][:80]
    明细 = {"url": url, "标题": 抹单位(标题)}
    限价 = 抽限价(t)
    中标 = 取中标价(t)
    明细["限价候选"] = [{k: (抹单位(v) if k == "片段" else v) for k, v in x.items()} for x in 限价]
    明细["中标价候选"] = [{"标段": x["标段"], "金额": x["限价元"], "片段": 抹单位(x["片段"])} for x in 中标]
    对, 原因 = 配对(限价, 中标)
    if not 对:
        明细["跳过原因"] = 原因
        return [], 明细
    公共 = {
        "公告URL": url,
        "日期": 找日期(t),
        "省份": 找省份(t, url, 标题),
        "项目类型": 归类(标题, 类型规则) or 归类(t[:600], 类型规则) or "其他",
        "评标办法": 归类(t, 评标规则) or "未写明",
        "来源站点": re.sub(r"^https?://", "", url).split("/")[0],
    }
    样本 = []
    for a, b in 对:
        限, 中 = a["限价元"], b["限价元"]
        率 = 1 - 中 / 限
        质检 = "ok"
        if a["存疑"] or b.get("存疑"):
            质检 = "存疑:" + ";".join(a["存疑"] + b.get("存疑", []))
        if 率 < 0 or 率 > 0.6 or 中 <= 0:  # 异常优先于存疑：统计永远排除
            质检 = "异常:下浮率超出[0,60%]或中标价非正，疑单位或口径错"
        样本.append(dict(公共, **{
            "限价": round(限, 2), "中标价": round(中, 2), "下浮率": round(率, 4), "标段": a["标段"] or "",
            "限价口径": a["类型"], "中标价口径": b.get("口径", ""), "税口径": {True: "含税", False: "不含税", None: "未说明"}[a["含税"]],
            "金额档": 金额档(限), "质检": 质检,
        }))
    明细["样本数"] = len(样本)
    return 样本, 明细


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--缓存", required=True, type=Path, help="抓取.py 的缓存目录")
    ap.add_argument("--链接", type=Path, help="候选链接 jsonl（取 title 做标题）")
    ap.add_argument("--输出", required=True, type=Path)
    a = ap.parse_args()
    标题 = {d["url"]: d.get("title", "") for d in 读jsonl(a.链接)} if a.链接 else {}
    a.输出.mkdir(parents=True, exist_ok=True)
    全部, 计 = [], {}
    已见 = set()
    with open(a.输出 / "解析明细.jsonl", "w", encoding="utf-8") as 明细f:
        for url, 记录 in 读索引(a.缓存).items():
            if 记录["状态"] != "ok":
                计["未抓到:" + 记录["状态"]] = 计.get("未抓到:" + 记录["状态"], 0) + 1
                continue
            t = 读正文(a.缓存, url) or ""
            样本, 明细 = 解析一篇(url, t, 标题.get(url, ""))
            明细f.write(json.dumps(明细, ensure_ascii=False) + "\n")
            k = 明细.get("跳过原因") or "出样本"
            计[k] = 计.get(k, 0) + 1
            for s in 样本:
                键 = (s["公告URL"], s["标段"])
                if 键 not in 已见:
                    已见.add(键)
                    全部.append(s)
    with open(a.输出 / "下浮率样本.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=列名)
        w.writeheader()
        w.writerows(全部)
    计["样本总数"] = len(全部)
    计["质检ok样本"] = sum(1 for s in 全部 if s["质检"] == "ok")
    print(json.dumps(计, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
