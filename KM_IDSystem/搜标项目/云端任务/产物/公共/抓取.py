"""礼貌抓取器（仅标准库）：限速、超时、字节上限、本地缓存、断点续跑、访问障碍识别。

用法：
    python3 抓取.py --输入 链接.jsonl --缓存 本地产出/原文 [--间隔 3] [--上限 0]
输入每行一个 JSON，至少含 "url"。结果写到 <缓存>/索引.jsonl（每 URL 一行，追加写，已抓过的跳过）。
访问障碍（登录/验证码/JS 挑战/403 等）会如实记为 状态，绝不当作"没有公告"。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from 网页文本 import 解码, 转文本  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
最大字节 = 5 * 1024 * 1024

# 反爬/访问障碍特征：键为状态名，值为特征正则（在前 20KB 原始 HTML 中找）
障碍特征 = {
    "反爬-瑞数": r"\$_ts\s*=|FSSBBIl1UgzbN7N|_\$[a-z]{2}\(",
    "反爬-加速乐": r"__jsl_clearance|document\.cookie\s*=.*?__jsl",
    "反爬-阿里云WAF": r"acw_sc__v2|aliyun_waf|_waf_bd8ce2ce37",
    "限流": r"访问过于频繁|请求过于频繁|访问频率过|操作过于频繁|稍后再试|too many requests|rate limit",
    "验证码": r"验证码|captcha|geetest|滑块|slider-?verify|nc_1_wrapper|安全验证|人机验证",
    "需登录": r"请先登录|用户登录|登录后查看|请登录|login\.html|/login\b|sso/login",
}


def 键(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def 识别障碍(http状态: int, 原始: str, 正文: str, 最终url: str) -> str:
    """把"拿到了 HTTP 200 但其实没内容"的情况都识别出来——宁可报障碍，不可当 ok（ok 会被下游当成"没有公告/没有限价"）。"""
    if http状态 in (412, 521):
        return "反爬-JS挑战(HTTP%d)" % http状态
    if http状态 == 429:
        return "限流(HTTP429)"
    if http状态 == 403:
        return "拒绝访问(403,可能需国内IP)"
    if http状态 >= 400:
        return "HTTP%d" % http状态
    头 = 原始[:20000]
    for 名 in ("反爬-瑞数", "反爬-加速乐", "反爬-阿里云WAF"):
        # 非 200（如瑞数的 202）带特征即判挡；200 时需正文很少才判（正常页也可能嵌这些脚本）
        if re.search(障碍特征[名], 头, re.I) and (http状态 != 200 or len(正文) < 400):
            return 名
    for 名 in ("限流", "验证码"):
        if re.search(障碍特征[名], 头, re.I) and len(正文) < 400:
            return 名
    if re.search(障碍特征["需登录"], 最终url, re.I) or (len(正文) < 400 and re.search(障碍特征["需登录"], 头, re.I)):
        return "需登录"
    if len(正文) < 150 and "<script" in 原始.lower():
        return "JS渲染(静态无正文)"
    if len(正文) < 30:
        return "空页(静态无正文)"
    return "ok"


def 抓一个(url: str, 超时: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=超时) as r:
            数据 = r.read(最大字节 + 1)
            return {"http": r.status, "最终url": r.geturl(), "ct": r.headers.get("Content-Type", ""), "数据": 数据[:最大字节]}
    except urllib.error.HTTPError as e:
        try:
            数据 = e.read(200000)
        except Exception:
            数据 = b""
        return {"http": e.code, "最终url": url, "ct": e.headers.get("Content-Type", "") if e.headers else "", "数据": 数据}
    except Exception as e:  # DNS/超时/TLS 等
        return {"http": 0, "最终url": url, "ct": "", "数据": b"", "错误": f"{type(e).__name__}: {e}"[:200]}


def 读索引(缓存: Path) -> dict:
    已有 = {}
    f = 缓存 / "索引.jsonl"
    if f.exists():
        for 行 in f.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(行)
                已有[d["url"]] = d
            except Exception:
                continue
    return 已有


def 读正文(缓存: Path, url: str) -> str | None:
    p = 缓存 / (键(url) + ".txt")
    return p.read_text(encoding="utf-8") if p.exists() else None


def 批量抓取(链接: list[dict], 缓存: Path, 间隔: float = 3.0, 上限: int = 0, 重试失败: bool = False) -> dict:
    缓存.mkdir(parents=True, exist_ok=True)
    已有 = 读索引(缓存)
    计数 = {"新抓": 0, "跳过": 0}
    with open(缓存 / "索引.jsonl", "a", encoding="utf-8") as idx:
        for 条 in 链接:
            url = 条["url"]
            旧 = 已有.get(url)
            if 旧 and (旧["状态"] == "ok" or not 重试失败):
                计数["跳过"] += 1
                continue
            if 上限 and 计数["新抓"] >= 上限:
                break
            if 附件型(url):
                记录 = {"url": url, "状态": "附件(PDF/DOC,需人工或另行解析)", "http": None, "字数": 0, "时间": time.strftime("%Y-%m-%d %H:%M:%S")}
            else:
                r = 抓一个(url)
                原始 = 解码(r["数据"], r["ct"]) if r["数据"] else ""
                正文 = 转文本(原始) if 原始 else ""
                状态 = 识别障碍(r["http"], 原始, 正文, r["最终url"]) if r["http"] else "连接失败:" + r.get("错误", "")
                if 原始:
                    (缓存 / (键(url) + ".html")).write_text(原始, encoding="utf-8")
                    (缓存 / (键(url) + ".txt")).write_text(正文, encoding="utf-8")
                记录 = {"url": url, "状态": 状态, "http": r["http"], "最终url": r["最终url"], "字数": len(正文), "时间": time.strftime("%Y-%m-%d %H:%M:%S")}
            idx.write(json.dumps(记录, ensure_ascii=False) + "\n")
            idx.flush()  # 流式落盘：被杀进程也只丢当前一条
            计数["新抓"] += 1
            计数[记录["状态"]] = 计数.get(记录["状态"], 0) + 1
            print(f"[{计数['新抓']}] {记录['状态']} {url}", flush=True)
            time.sleep(间隔)
    return 计数


def 附件型(url: str) -> bool:
    return bool(re.search(r"\.(pdf|docx?|xlsx?|zip|rar)(\?|$)", url, re.I))


def 读jsonl(路径: Path) -> list[dict]:
    return [json.loads(x) for x in 路径.read_text(encoding="utf-8").splitlines() if x.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--输入", required=True, type=Path)
    ap.add_argument("--缓存", required=True, type=Path)
    ap.add_argument("--间隔", type=float, default=3.0, help="每次请求间隔秒数（默认 3，别调太小）")
    ap.add_argument("--上限", type=int, default=0, help="本轮最多新抓多少条，0=不限")
    ap.add_argument("--重试失败", action="store_true", help="对之前非 ok 的 URL 再试一次")
    a = ap.parse_args()
    计数 = 批量抓取(读jsonl(a.输入), a.缓存, a.间隔, a.上限, a.重试失败)
    print(json.dumps(计数, ensure_ascii=False))


if __name__ == "__main__":
    main()
