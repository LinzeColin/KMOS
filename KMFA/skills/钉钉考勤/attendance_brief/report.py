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

# 钉钉 markdown 里，换行只认空行。
# 带 --title 的消息就是 markdown 类型，官方约定（dingtalk-chat skill）原话：
# 「需要稳定换行时用空行分隔段落。若以转义形式组织文本，写 \n\n，不要只写 \n。」
SEP = "\n\n"

# 分隔线不能用 markdown 的 `---`。
# 钉钉把发出去的 `\n\n` 规范化成 `  \n`（行尾两空格 + 换行），于是 `---` 总是
# **紧跟**在上一行后面 —— 而 markdown 里 `文字\n---` 是 setext 二级标题的写法，
# 上一行会被整行渲染成大标题。实测：最后一个项目行「XX项目 某某」被吃成了 H2。
# U+2500 制表符不参与任何 markdown 语法，画出来就是一条线。
RULE = "──────────"

def dingtalk(text: str) -> str:
    """把逐行写的报文转成钉钉 markdown：**行与行之间一律用空行**。

    2026-09-15 在这上面栽了两次，两次都是诊断反了：

    1. 先是按普通 markdown 的规矩写 —— 单个 `\n` 加行尾两个空格做硬换行。
       钉钉不认行尾空格，单个 `\n` 在 markdown 里本来就不换行，于是整篇糊成一段。
    2. 然后看到「空行没了」，就把空行换成全角空格（U+3000）那一行。
       结果更糟：把消息从钉钉拉回来看，`3 条␣␣\n　\n考勤异常` 被存成
       `3 条␣␣\n␣　␣考勤异常` —— 那一行空白连同它后面的换行一起被折叠成了空格，
       段落标题直接粘到正文上。**唯一有效的换行机制被亲手删掉了。**

    所以：丢掉所有空白行，剩下的每一行之间都用 `\n\n` 连接。
    视觉层次靠 markdown 自己的东西（`**粗体**` 小标题、`---` 分割线），不靠空白。
    """
    lines = [ln.rstrip() for ln in text.split("\n")]
    return SEP.join(ln for ln in lines if ln.strip())

def render(d: dict) -> tuple[str, str]:
    """返回 (会话列表标题, 正文)。"""
    day = d["业务日"]
    if d["状态"] == "无人员表":
        ok, tot = d.get("按时率", (0, 0))
        cut = d.get("截止", "17:15")
        return (f"⚠ 考勤 {day} · 人员表未按时发布",
                dingtalk(
                f"**⚠ 考勤 {day} ｜ 人员表未按时发布**\n" + RULE + "\n"
                f"{cut} 截止，生产管理群里还没有今天的人员表。\n"
                f"→ 请在 {cut} 前发出 · 今日补发\n\n"
                f"没有应到名单就判不了考勤 —— 这不等于今天没异常。\n"
                + (f"最近 {tot} 个工作日按时 {ok} 天\n" if tot else "")
                + f"明天 {cut} 自动重跑，本轮不补发。"))
    if d["状态"] == "非工作日":
        # 只有人手动点 Run 才会渲染到这里 —— 自动那条排程压根不在周末触发。
        # 他按了就得给他一个说得清的答复，而不是一句「本轮不出报」。
        return (f"考勤 {day} · 非工作日",
                dingtalk(f"**考勤 {day} ｜ 非工作日**\n" + RULE + "\n"
                f"{d.get('理由','非工作日')}，生产管理群也没有这天的人员表。\n"
                f"不点发布人的名，也不判任何人的考勤。\n\n"
                f"下一个工作日照常出报。"))
    if d["状态"] == "读不准":
        bad = d.get("不可信", [])
        return (f"⚠ 考勤 {day} · {len(bad)} 处读不准",
                dingtalk(f"**⚠ 考勤 {day} ｜ 本轮不出结论**\n" + RULE + "\n"
                f"人员表有 {len(bad)} 处识别不可信，已核对钉钉花名册仍无法确定：\n"
                + "\n".join(f"  第 {r} 行 · {t}" for r, t in bad[:6]) +
                f"\n\n宁可不报也不猜。下一轮重跑；若连续两轮读不准会单独告警。"))

    n = d["待办数"]
    abn = d["异常人数"]
    # 层次全部用 markdown 自己的东西：`**粗体**` 小标题、`---` 分割线。
    # 空白行在钉钉 markdown 里表达不了间隔（它就是换行本身），靠它排版必然糊。
    lines = [f"**考勤 {day} ｜ " + (f"要处理 {n} 条**" if n else "无待办**")]
    for label, key in (("发布纪律", "纪律"), ("考勤异常", "考勤"), ("名单待核", "名单")):
        items = d.get(key) or []
        if not items:
            continue
        lines.append(RULE)
        lines.append(f"**{label} {len(items)} 条**" if label != "考勤异常"
                     else f"**考勤异常 {len(items)} 人**")
        lines += [f"· {t}" for t in items]
    lines.append(RULE)
    lines.append("**在场**")
    lines += [
        f"开明自有员工 {d['自有员工']} 人"
        + (f"，{abn} 人考勤异常" if abn else "，考勤全部正常"),
        f"应打卡 {d['应打卡']} 人（休息 {d['休息']} 人当天不计）",
    ]
    dist = [f"{k} {v}" for k, v in d["应打卡分布"]]
    for i in range(0, len(dist), 4):
        lines.append(" · ".join(dist[i:i + 4]))
    lines.append(f"外协在场 {d['外协']} 人（流动用工）")
    lines.append(RULE)
    lines += [
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
