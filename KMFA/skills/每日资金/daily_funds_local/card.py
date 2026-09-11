"""HTML → PNG 卡片渲染（Playwright）。

不用 matplotlib：中文字体在 matplotlib 上要单独治，且这种「大字 + 分栏 + 水位线」
的排版用 CSS 做是分钟级的事，用 matplotlib 做很别扭。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence

TEMPLATE = Path(__file__).with_name("card_template.html")


def build_payload(rows: Sequence, stale_days: int = 0) -> dict:
    """rows = store.Row 序列（已按 report_date 升序）。"""
    return {
        "series": [
            {"d": r.report_date, "b": r.bank_fen, "e": r.bill_fen,
             "imbalance": bool(r.source_imbalance or r.chain_suspect)}
            for r in rows
        ],
        "stale_days": int(stale_days),
    }


def _install_chromium() -> bool:
    """自动补装 Playwright 的浏览器。

    实测事故：2026-09-07 Playwright 升级后要一个新的浏览器构建
    （chromium_headless_shell-1223），而它没被下载过，于是 chromium.launch()
    直接失败，整轮出图挂掉。归档和读数都是好的，只倒在这一步。
    这类环境漂移不该需要人来处理——无人值守就是不能有「请手动跑一条命令」。
    """
    import subprocess
    import sys
    try:
        rc = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                            capture_output=True, text=True, timeout=900)
        return rc.returncode == 0
    except Exception:
        return False


def _shoot(payload: dict, out_png: str, scale: int) -> str:
    from playwright.sync_api import sync_playwright

    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "__PAYLOAD__", json.dumps(payload, ensure_ascii=False))
    tmp = Path(tempfile.mkdtemp(prefix="fundcard-")) / "card.html"
    tmp.write_text(html, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 900},
                                device_scale_factor=scale)
        page.goto(tmp.as_uri())
        page.wait_for_selector(".cell svg")
        page.locator("#card").screenshot(path=out_png)
        browser.close()
    return out_png


def render(payload: dict, out_png: str, *, scale: int = 1) -> str:
    if not payload.get("series"):
        raise ValueError("没有数据可画")
    try:
        return _shoot(payload, out_png, scale)
    except Exception as exc:
        # 只对「浏览器不在」这一类自愈，别的错照抛——
        # 把所有异常都当成缺浏览器会掩盖真正的渲染 bug。
        if "Executable doesn't exist" not in str(exc) and "playwright install" not in str(exc):
            raise
        if not _install_chromium():
            raise
        return _shoot(payload, out_png, scale)


def summary_text(rows: Sequence, stale_days: int = 0, due14_fen: Optional[int] = None) -> str:
    """随图的文字摘要。纯模板，不调模型——锁屏通知里不点开图也能看到关键数。"""
    if not rows:
        return "资金日报：暂无可用数据。"
    wan = lambda fen: "%.2f" % (fen / 1e6)
    last = rows[-1]
    prev = rows[-2] if len(rows) > 1 else None
    total = last.bank_fen + last.bill_fen

    lines: List[str] = ["%s 资金日报" % last.report_date, ""]
    if prev:
        d = total - (prev.bank_fen + prev.bill_fen)
        lines.append("可动用合计 %s 万，较 %s %s%s 万"
                     % (wan(total), prev.report_date[5:], "+" if d >= 0 else "−",
                        wan(abs(d))))
    else:
        lines.append("可动用合计 %s 万" % wan(total))
    pct = last.bank_fen / total * 100 if total else 0
    lines.append("  银行存款 %s 万（%.1f%%）" % (wan(last.bank_fen), pct))
    # 顺序与卡片横轴色块一致：存款 → 14 天内到期承兑 → 汇票。
    # 它是汇票的一部分，所以写「占汇票」，存款 + 汇票 仍然等于合计。
    if due14_fen is not None:
        share = due14_fen / last.bill_fen * 100 if last.bill_fen else 0
        lines.append("  14 天内到期承兑 %s 万（占汇票 %.1f%%）" % (wan(due14_fen), share))
    lines.append("  电子汇票 %s 万（%.1f%%）" % (wan(last.bill_fen), 100 - pct))
    lines.append("")

    from datetime import date, timedelta
    end = date.fromisoformat(last.report_date)
    for days in (30, 180):
        window = [r for r in rows
                  if date.fromisoformat(r.report_date) >= end - timedelta(days=days)]
        vals = [r.bank_fen + r.bill_fen for r in window]
        if vals:
            lines.append("近 %d 天区间 %s – %s 万" % (days, wan(min(vals)), wan(max(vals))))

    lines.append("")
    if stale_days >= 2:
        # 上游归档实测会一次断好几天，说成「今日的表尚未发出」会严重低估
        lines.append("※ 已 %d 天没有新表，以上为 %s 的数据。" % (stale_days, last.report_date))
    elif stale_days > 0:
        lines.append("※ 今日的表尚未发出，以上为 %s 的数据。" % last.report_date)
    return "\n".join(lines)
