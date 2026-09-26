"""由 搜索记录/*.jsonl 按统一规则生成 平台普查.csv 初版（可复现；仅标准库）。

    python3 生成普查初版.py
统一规则（2026-09-23 复审后定）：
  证据级别  一手 = 网址是平台自有域名，且原样出现在搜索结果链接里
            二手 = 仅搜索摘要文字/子 agent 备注提及，或来源为第三方页面
  镜像      只搜到第三方镜像/技术支持域名的，网址留空、镜像放 证据URL，不计入"有网址平台"
  可访问性  免登录/注册/反爬/日均 在云端一律"没查"（出网被拦），由 平台探测.py 本地回填
人工修正逐条列在 修正 里，并写明依据。
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
列 = ["排序", "平台名称", "所属", "行业", "类别", "网址", "列表页URL", "免登录看列表", "需注册供应商", "反爬", "每天维修类公告估计", "估计方法", "证据URL", "证据级别", "核查状态", "备注"]
没查 = "没查（云端出网被拦，待本地探测）"
类别序 = {"公开招标门户": 0, "省ggzy": 1, "省工程交易中心": 2, "省政府采购网": 3, "集团SRM": 4}

# 名称 → 覆盖字段；依据写在 _依据
修正 = {
    "国家能源集团电子商务平台": {"name": "国家能源集团招标平台（国能e招）", "url": "https://www.chnenergybidding.com.cn/", "source_level": "一手",
                         "evidence_url": "https://www.chnenergybidding.com.cn/bidweb/001/001005/7313.html", "mirror": "https://e-chnenergy.dlzbxx.com/",
                         "_依据": "原记录为镜像 e-chnenergy.dlzbxx.com；C2 搜索结果原样出现官方域名 chnenergybidding.com.cn 的公告链接（C2/候选链接.jsonl 第21、36行）"},
    "易派客": {"url": "https://bidding.epec.com/", "source_level": "二手",
            "_依据": "原记录 url 误写为 ouyeel.com（欧冶，属宝武）；子 agent 备注称搜索结果显示 bidding.epec.com / ebidding.sinopec.com，未原样核"},
    "安徽省公共资源交易电子服务平台": {"url": "", "mirror": "https://ahggzy.dljczb.com/", "_依据": "只搜到第三方技术支持域名，按镜像规则留空"},
    "金川集团电子招标投标交易平台": {"source_level": "二手", "_依据": "域名仅由搜索摘要文字给出，未在链接列表中原样出现"},
    "山东黄金供应链管理系统招标采购平台": {"source_level": "二手", "_依据": "同上"},
    "河北省政府采购网": {"url": "http://www.ccgp-hebei.gov.cn/hd/hd/", "status": "查了有", "source_level": "一手",
                   "_依据": "官方 ccgp-hebei.gov.cn 链接原样出现在搜索结果中，与其余 6 个 ccgp-省 同一标准收录；首页未核"},
    "上海市建设工程交易服务中心（上海公共资源交易相关）": {"category": "省工程交易中心", "_依据": "是建设工程交易中心，不是省 ggzy；上海 ggzy 统一入口未搜到"},
    "广东省政府采购中心/公共资源交易平台": {"category": "省政府采购网", "_依据": "gpcgd 为省政府采购中心"},
    "欧冶云商": {"_依据": "存疑：欧冶云商主要是钢材交易平台，宝武设备维修采购是否在此发布未核"},
}
镜像名 = {"亚泰电子招标采购平台", "中国华电集团电子商务平台"}  # 原记录已留空 url、证据为镜像


def 主机(u: str) -> str:
    return re.sub(r"^https?://", "", u).split("/")[0].lower()


def main() -> None:
    记录 = []
    for f in ("集团平台.jsonl", "省级与全国平台.jsonl"):
        记录 += [json.loads(x) for x in (HERE / "搜索记录" / f).read_text(encoding="utf-8").splitlines() if x.strip()]
    有, 无, 见 = [], [], set()
    for r in 记录:
        改 = 修正.get(r["name"], {})
        r = {**r, **{k: v for k, v in 改.items() if not k.startswith("_")}}
        依据 = 改.get("_依据", "")
        备注 = "；".join(x for x in (r.get("note", ""), ("修正：" + 依据) if 依据 else "") if x)
        if r.get("url") and 主机(r["url"]) not in 见:
            见.add(主机(r["url"]))
            有.append((r, 备注))
        elif r.get("url"):
            无.append((r, 备注 + "；与已收录平台同域名，合并", "同域名已收录"))
        else:
            if r["name"] in 镜像名 or r.get("mirror"):
                状态 = "查了有平台，但只搜到第三方镜像、没搜到官方网址（镜像见证据URL）"
            else:
                状态 = "查了没有（搜索未找到自建平台网址）"
            无.append((r, 备注, 状态))
    有.sort(key=lambda x: (类别序.get(x[0]["category"], 9), x[0]["industry"], x[0]["name"]))
    with open(HERE / "平台普查.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=列)
        w.writeheader()
        i = 0
        for r, 备注 in 有:
            i += 1
            w.writerow({"排序": i, "平台名称": r["name"], "所属": r["owner"], "行业": r["industry"], "类别": r["category"], "网址": r["url"], "列表页URL": "",
                        "免登录看列表": 没查, "需注册供应商": 没查, "反爬": 没查, "每天维修类公告估计": "", "估计方法": "数不出来：云端无法打开页面",
                        "证据URL": r["evidence_url"], "证据级别": r["source_level"] + ("（搜索结果原样出现，未打开）" if r["source_level"] == "一手" else "（未原样核）"),
                        "核查状态": "网址来自搜索结果；可访问性没查", "备注": 备注})
        for r, 备注, 状态 in 无:
            i += 1
            w.writerow({"排序": i, "平台名称": r["name"], "所属": r["owner"], "行业": r["industry"], "类别": r["category"], "网址": "", "列表页URL": "",
                        "证据URL": r.get("mirror") or r.get("evidence_url", ""), "证据级别": "二手（镜像/第三方）" if "镜像" in 状态 else "",
                        "核查状态": 状态, "备注": 备注})
    from collections import Counter
    print(f"有网址 {len(有)}；无官方网址 {len(无)}")
    print("类别", dict(Counter(r["category"] for r, _ in 有)))
    print("集团行业", dict(Counter(r["industry"] for r, _ in 有 if r["category"] == "集团SRM")))
    print("证据级别", dict(Counter(r["source_level"] for r, _ in 有)))


if __name__ == "__main__":
    main()
