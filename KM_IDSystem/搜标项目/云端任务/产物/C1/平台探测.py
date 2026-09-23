"""平台探测：在国内网络下逐个打开平台，回填 平台普查.csv 的可访问性与日均维修类公告估计（仅标准库）。

    python3 平台探测.py --普查 平台普查.csv --输出 本地产出/C1/平台普查.csv [--间隔 3]
读取每行的 网址（首页）和 列表页URL（公告列表页，可人工补；为空则只测首页）：
    免登录看列表  是 / 否(需登录) / 打不开(原因)
    反爬          无 / 验证码 / 反爬-瑞数 / 反爬-加速乐 / JS渲染(静态无正文) / 拒绝访问(403,可能需国内IP) …
    每天维修类公告估计 = 列表页上维修类条目数 ÷ 列表页日期跨度(天)；标"估"。
    估计方法      写明：列表页 N 条、跨 D 天、维修类 M 条
需注册供应商：静态页面判断不了"投标要不要注册"，只在页面出现"供应商注册"入口时写"有注册入口"，其余保持原值。
探测失败绝不写 0：写"数不出来"+原因（来源失败 ≠ 没有公告）。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 依赖既可与本目录平级（仓库布局 产物/公共、产物/C3），也可在本目录内（回件切件后 C2/公共、C2/抽限价.py）
for _p in (HERE.parent / "C3", HERE.parent / "公共", HERE / "公共", HERE):
    if _p.is_dir():
        sys.path.insert(0, str(_p))
from 抓取 import 抓一个, 识别障碍  # noqa: E402
from 网页文本 import 解码, 转文本  # noqa: E402

维修词 = re.compile(r"检修|维修|大修|中修|维保|修复|抢修|修理|保运|维护|安装|改造|技改|探伤|检测|熔覆|堆焊")
日期式 = re.compile(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})")


def 估日量(列表文本: str, 今天: dt.date | None = None) -> tuple[float | None, str]:
    """按行找"标题…日期"条目，维修类条目数 ÷ 日期跨度。"""
    条目 = []
    for 行 in 列表文本.split("\n"):
        m = 日期式.search(行)
        if not m or len(行) < 8:
            continue
        try:
            d = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if 今天 and (d > 今天 or (今天 - d).days > 400):
            continue
        条目.append((d, bool(维修词.search(行))))
    if len(条目) < 5:
        return None, f"列表页可识别的带日期条目仅 {len(条目)} 条，数不出来"
    最早, 最晚 = min(d for d, _ in 条目), max(d for d, _ in 条目)
    跨 = (最晚 - 最早).days + 1
    修 = sum(1 for _, x in 条目 if x)
    return round(修 / 跨, 2), f"估：列表页 {len(条目)} 条、跨 {跨} 天({最早}~{最晚})、维修类 {修} 条"


def 探一个(url: str) -> dict:
    r = 抓一个(url)
    if not r["http"]:
        return {"状态": "打不开(" + r.get("错误", "连接失败")[:60] + ")", "文本": "", "原始": ""}
    原始 = 解码(r["数据"], r["ct"]) if r["数据"] else ""
    文本 = 转文本(原始) if 原始 else ""
    return {"状态": 识别障碍(r["http"], 原始, 文本, r["最终url"]), "文本": 文本, "原始": 原始}


def 回填(行: dict, 首页: dict, 列表: dict | None, 今天: dt.date) -> dict:
    行 = dict(行)
    主 = 列表 or 首页
    s = 主["状态"]
    if s == "ok":
        行["免登录看列表"] = "是" if 列表 else "首页可开(列表页未测)"
        行["反爬"] = "无(静态抓取未遇到)"
    elif s == "需登录":
        行["免登录看列表"] = "否(需登录)"
        行["反爬"] = "—"
    else:
        行["免登录看列表"] = "打不开(" + s + ")" if s.startswith(("打不开", "连接失败", "HTTP", "拒绝")) else "未知(被反爬挡住)"
        行["反爬"] = s
    if re.search(r"供应商注册|供应商入驻|注册供应商|供应商登录", 首页.get("原始", "")[:200000]):
        if 行.get("需注册供应商", "").startswith("没查"):
            行["需注册供应商"] = "有注册入口(投标大概率需注册，未逐条核)"
    if 列表 and 列表["状态"] == "ok":
        量, 法 = 估日量(列表["文本"], 今天)
        行["每天维修类公告估计"] = "" if 量 is None else str(量)
        行["估计方法"] = 法
    else:
        行["每天维修类公告估计"] = ""
        行["估计方法"] = "数不出来：" + ("未提供列表页URL" if not 列表 else "列表页" + 列表["状态"])
    行["核查状态"] = "本地已探测 " + today_str(今天)
    return 行


def today_str(d: dt.date) -> str:
    return d.isoformat()


def 排序键(行: dict):
    v = 行.get("每天维修类公告估计", "")
    try:
        return (0, -float(v))
    except ValueError:
        return (1, 行.get("类别", ""), 行.get("平台名称", ""))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--普查", required=True, type=Path)
    ap.add_argument("--输出", required=True, type=Path)
    ap.add_argument("--间隔", type=float, default=3.0)
    ap.add_argument("--只测", default="", help="只测名称包含该字样的平台（调试用）")
    a = ap.parse_args()
    with open(a.普查, encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        列 = rd.fieldnames
        行们 = list(rd)
    今天 = dt.date.today()
    新 = []
    for i, 行 in enumerate(行们, 1):
        if not 行.get("网址") or (a.只测 and a.只测 not in 行["平台名称"]):
            新.append(行)
            continue
        首页 = 探一个(行["网址"])
        time.sleep(a.间隔)
        列表 = None
        if 行.get("列表页URL"):
            列表 = 探一个(行["列表页URL"])
            time.sleep(a.间隔)
        新.append(回填(行, 首页, 列表, 今天))
        print(f"[{i}/{len(行们)}] {行['平台名称']}: {新[-1]['免登录看列表']} | {新[-1]['反爬']} | {新[-1]['每天维修类公告估计'] or '-'}", flush=True)
    新.sort(key=排序键)
    for i, 行 in enumerate(新, 1):
        行["排序"] = str(i)
    a.输出.parent.mkdir(parents=True, exist_ok=True)
    with open(a.输出, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=列)
        w.writeheader()
        w.writerows(新)
    print("写出", a.输出)


if __name__ == "__main__":
    main()
