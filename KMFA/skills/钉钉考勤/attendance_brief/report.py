"""简报渲染。只有一个版本 —— 发给个人和发到群里是同一份内容。

写作纪律：
  · 每条待办必须能回答「谁 在什么时候前 做什么」，答不出的是统计，不发。
  · 只判自己人的考勤。外协流动性大，今天不在是正常离场，只报在场人数。
  · 数据不全时长得完全不一样，明写「这不等于没异常」，绝不用正常版式承载残缺数据。
  · 不出金额、不出出勤率、不做处罚结论。
"""
from __future__ import annotations

def _plist(pairs, sep=" · "):
    return sep.join(f"{k} {v}" for k, v in pairs)

# 段落分隔用的空行必须是「看起来空、实际有字」的一行。
# U+3000 全角空格：渲染出来是一行空白，但它不是空行。
BLANK = "\u3000"

def dingtalk(text: str) -> str:
    """钉钉那边对换行有两处会吃掉排版，两处都要绕：

    1. 单个换行会被折叠成空格，整篇糊成一段 —— 每行末尾补两个空格做硬换行。
    2. **真正的空行会被整条吃掉。** 2026-09-15 把群里 09-14 那条日报的原文拉回来看，
       源文件里 4 处空行一处都没剩：
           "…要处理 3 条  \\n考勤异常 3 人  \\n · 某员工…"
       段与段之间没有任何间隔，十几行连成一片。所以空行一律换成全角空格那一行 ——
       它渲染出来是空白，但不是空行，不会被吃掉。
    """
    return "\n".join(BLANK if not ln.strip() else ln.rstrip() + "  "
                      for ln in text.split("\n"))

def render(d: dict) -> tuple[str, str]:
    """返回 (会话列表标题, 正文)。"""
    day = d["业务日"]
    if d["状态"] == "无人员表":
        ok, tot = d.get("按时率", (0, 0))
        cut = d.get("截止", "17:15")
        return (f"⚠ 考勤 {day} · 人员表未按时发布",
                dingtalk(
                f"⚠ 考勤 {day} ｜ 人员表未按时发布\n\n"
                f"{cut} 截止，生产管理群里还没有今天的人员表。\n"
                f"→ 请在 {cut} 前发出 · 今日补发\n\n"
                f"没有应到名单就判不了考勤 —— 这不等于今天没异常。\n"
                + (f"最近 {tot} 个工作日按时 {ok} 天\n" if tot else "")
                + f"明天 {cut} 自动重跑，本轮不补发。"))
    if d["状态"] == "非工作日":
        # 只有人手动点 Run 才会渲染到这里 —— 自动那条排程压根不在周末触发。
        # 他按了就得给他一个说得清的答复，而不是一句「本轮不出报」。
        return (f"考勤 {day} · 非工作日",
                dingtalk(f"考勤 {day} ｜ 非工作日\n\n"
                f"{d.get('理由','非工作日')}，生产管理群也没有这天的人员表。\n"
                f"不点发布人的名，也不判任何人的考勤。\n\n"
                f"下一个工作日照常出报。"))
    if d["状态"] == "读不准":
        bad = d.get("不可信", [])
        return (f"⚠ 考勤 {day} · {len(bad)} 处读不准",
                dingtalk(f"⚠ 考勤 {day} ｜ 本轮不出结论\n\n"
                f"人员表有 {len(bad)} 处识别不可信，已核对钉钉花名册仍无法确定：\n"
                + "\n".join(f"  第 {r} 行 · {t}" for r, t in bad[:6]) +
                f"\n\n宁可不报也不猜。下一轮重跑；若连续两轮读不准会单独告警。"))

    n = d["待办数"]
    abn = d["异常人数"]
    lines = [f"考勤 {day} ｜ " + (f"要处理 {n} 条" if n else "无待办"), ""]
    for label, key in (("发布纪律", "纪律"), ("考勤异常", "考勤"), ("名单待核", "名单")):
        items = d.get(key) or []
        if not items:
            continue
        lines.append(f"{label} {len(items)} 条" if label != "考勤异常"
                     else f"考勤异常 {len(items)} 人")
        lines += [f"· {t}" for t in items]
        lines.append("")
    lines += [
        f"开明自有员工 {d['自有员工']} 人"
        + (f"，{abn} 人考勤异常" if abn else "，考勤全部正常"),
        f"应打卡 {d['应打卡']} 人（休息 {d['休息']} 人当天不计）",
    ]
    dist = [f"{k} {v}" for k, v in d["应打卡分布"]]
    for i in range(0, len(dist), 4):
        lines.append(" · ".join(dist[i:i + 4]))
    lines += [
        "",
        f"外协在场 {d['外协']} 人（流动用工）",
        "",
        (f"人员表 {d['人员表时间']} 发布"
         + ("（按时）" if d.get("按时") else f"（迟于 {d.get('截止','17:15')}）"))
        + (f" · 最近 {d['按时率'][1]} 个工作日按时 {d['按时率'][0]} 天"
           if d.get("按时率", (0, 0))[1] else ""),
        f"打卡截至 {day} 全天",
    ]
    title = f"考勤 {day} · " + (f"{n} 条待处理" if n else "无待办")
    if d.get("表日期"):
        # 用的不是业务日那天的表（发布人提前发了次日计划是常事）。
        # 照常出报，但必须说清楚照的是哪一天的在场表，不然读的人会默认是当天的。
        lines.append(f"本轮照的是 {d['表日期']} 的人员表")
    return title, dingtalk("\n".join(lines))
