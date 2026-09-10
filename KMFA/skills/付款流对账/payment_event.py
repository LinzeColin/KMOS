#!/usr/bin/env python3
"""付款事件识别：决定「今天到底该不该说话」。

老板 2026-09-11 定的口径，一字不改地执行：

    「他不是每天都有付款，有付款才发送消息，你才需要去核对，
      看付款申请群有没有申请，申请之后东西是不是齐全的，
      然后再来看生产付款群，它的回执是不是正确的，有没有错误，有没有遗漏。
      而不是他没有付款的时候你也发。」

实测（2026-08-25 ~ 09-10，16 天）：生产付款群只有 9 天出现回执，
09-01 / 09-05 / 09-06 / 09-07 / 09-10 完全没有付款。旧机制这 5 天照发不误，
发的还是 92 个合同 2307 万这条老板已经听过无数遍的历史欠款。

所以本模块只回答一个问题：**近窗口内有没有付款事件。**
没有 → 主流程直接 NO_EVENT 退出，一个字都不发。

—— 名词对照（用老板的叫法）——
  请示群 / 申请群  cidkU176W26z9HoAK9q5cb1lA==   杨婷、财务冯璐在这里提申请
  生产付款群       cid0UmWYRhaMEbiNez2FIpDPA==   杨婷在这里发转账回执
  领导             林全意、张霖泽
"""
import datetime as dt, hashlib, json, re, subprocess
from decimal import Decimal

APPLY_GROUP = "cidkU176W26z9HoAK9q5cb1lA=="
PROD_GROUP  = "cid0UmWYRhaMEbiNez2FIpDPA=="
LEADERS     = ("林全意", "张霖泽")
BJ          = dt.timezone(dt.timedelta(hours=8))

# ── 申请触发词。全部来自真实群消息，不是我编的 ──────────────────────
APPLY_TRIGGER = ("请批示", "请领导批示", "申请付款", "现申请", "请示")
# ── 催办：申请已经提了、还在等 ────────────────────────────────────
CHASE_TRIGGER = ("今天付吗", "可以付吗", "快点付", "来催了", "催一下", "还没付", "什么时候付")
# ── 授权：老板 2026-09-11「我们一般都是通过钉钉的表情回复去授权的，
#    请示群不可能有授权同意，上游授权只会发生在付款请示群，不会发生在生产付款群。」
#
#    实测 2026-08-28~09-10：请示群 93 条里 20 条带 emotionReplyList，全是领导
#    对申请打的 OK；生产付款群 47 条里只有 2 条，且都不是授权。
#    我原先在正文里找「同意/付了」这类词，找错了地方——真信号在表情里。
OK_EMOJI = ("OK", "ok", "好的", "赞", "GOOD", "Good")
# 领导在正文里也会直接下指令（「这个2790快点付了」），当补充信号，不是主信号
APPROVE_WORDS = ("付了", "快点付", "全部付", "可以付", "同意", "付承兑")
REJECT_WORDS  = ("不付", "暂时不付", "先不付", "不同意", "缓一缓", "先不")


def approved_by(msg):
    """谁给这条消息打了授权表情。没人打就返回空——那就是还没批。"""
    who = []
    for e in msg.get("emoji") or []:
        if str(e.get("emoji", "")) in OK_EMOJI:
            for u in e.get("replyUsers") or []:
                if u in LEADERS and u not in who:
                    who.append(u)
    return who
# ── 回执：钱真的出去了的证据 ──────────────────────────────────────
RECEIPT_MARK  = ("批量转账明细", "生产付款明细", "已转", "已支付", "付的承兑", "付款明细")
# ── 噪声：长得像但根本不是付款事件的东西 ──────────────────────────
NOISE = ("资金明细", "现存票据", "票据到期", "票据已贴", "票据报价", "资金日报",
         "款已到账", "已到账", "余额对账单", "赎回", "理财")

AMOUNT_YUAN = re.compile(r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*元")
AMOUNT_WAN  = re.compile(r"(\d+(?:\.\d+)?)\s*万")
IMG  = re.compile(r"\[图片消息\]")
FILE = re.compile(r"\[文件\]")


def _clean(text):
    return (text or "").replace("注意：如需下载使用dws chat message download-media命令下载", "")


def amounts_of(text):
    """从中文正文里抠金额。'4万' 算 40000，'41516.05元' 算 41516.05。"""
    out = []
    for m in AMOUNT_YUAN.finditer(text):
        out.append(Decimal(m.group(1).replace(",", "")))
    for m in AMOUNT_WAN.finditer(text):
        out.append(Decimal(m.group(1)) * 10000)
    return sorted(set(out))


def is_machine_post(sender, text):
    """我自己发的东西永远不算事件，否则哨兵会被自己的输出触发。"""
    return sender == "张霖泽" and ("资金日报" in text or text.lstrip().startswith("**付款异常"))


def _walk(o):
    if isinstance(o, list):
        return o
    if isinstance(o, dict):
        for k in ("items", "messages", "data", "result", "list"):
            if k in o:
                r = _walk(o[k])
                if r is not None:
                    return r
        for v in o.values():
            r = _walk(v)
            if r is not None:
                return r


def fetch(group, since_bj, until_bj=None, limit=100):
    """读群消息。

    `dws … --direction newer` 只有下界没有上界，会把 until 之后的消息一起吐回来。
    历史回放测试不夹上界就永远是假绿：负控窗口会读到窗口之后发生的事。
    所以上界在这里显式夹掉。

    读不到就抛，绝不静默当成「没有事件」——那会让哨兵在故障时装死。
    """
    r = subprocess.run(
        ["dws", "chat", "message", "list", "--group", group,
         "--time", since_bj.strftime("%Y-%m-%d %H:%M:%S"),
         "--direction", "newer", "--limit", str(limit), "-f", "json"],
        capture_output=True, text=True, errors="replace", timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"读群失败 {group[:12]}…: {(r.stderr or r.stdout)[:200]}")
    msgs = _walk(json.loads(r.stdout)) or []
    out = []
    for x in msgs:
        c = x.get("content")
        if isinstance(c, dict):
            c = c.get("text") or json.dumps(c, ensure_ascii=False)
        out.append({
            "time":   x.get("createTime", ""),
            "sender": x.get("sender", ""),
            "text":   _clean(str(c)),
            "msgid":  x.get("openMessageId", ""),
            "group":  group,
            "emoji":  x.get("emotionReplyList") or [],
        })
    if until_bj is not None:
        cut = until_bj.strftime("%Y-%m-%d %H:%M:%S")
        out = [m for m in out if m["time"] and m["time"] <= cut]
    out.sort(key=lambda m: m["time"])
    return out


def classify(msgs):
    """把消息分成 申请 / 催办 / 批示 / 回执 四类。归不进去的一律丢掉。"""
    apply_, chase, decide, receipt = [], [], [], []
    for m in msgs:
        t, s = m["text"], m["sender"]
        if is_machine_post(s, t):
            continue
        noisy = any(w in t for w in NOISE)
        rec = {**m, "amounts": amounts_of(t),
               "has_img": bool(IMG.search(t)), "has_file": bool(FILE.search(t))}

        if m["group"] == PROD_GROUP:
            # 生产付款群里领导说的话不是授权。老板明确讲过：上游授权只发生在
            # 付款请示群。生产群里那些是在问情况、给指令，不是审批动作。
            if s in LEADERS:
                continue
            # 生产付款群里杨婷发的转账截图/明细就是回执。
            # 但 @了领导的是对话或对告警的批注反馈（2026-09-09 10:47 杨婷那条就是），
            # 真回执从不 @人，只是把凭证甩上来。
            if noisy:
                continue
            talking = "@" in t and not rec["amounts"]
            if talking:
                continue
            if rec["has_img"] or rec["has_file"] or any(w in t for w in RECEIPT_MARK):
                receipt.append(rec)
            continue

        if noisy:
            continue
        if s in LEADERS:
            if any(w in t for w in REJECT_WORDS):
                decide.append({**rec, "verdict": "否决"})
            elif any(w in t for w in APPROVE_WORDS):
                decide.append({**rec, "verdict": "同意"})
            continue
        if any(w in t for w in CHASE_TRIGGER):
            chase.append(rec)
        elif any(w in t for w in APPLY_TRIGGER):
            apply_.append(rec)
    return {"申请": apply_, "催办": chase, "批示": decide, "回执": receipt}


def scan(days=3, now=None):
    """窗口内的付款事件全景。has_event 为假时，主流程必须闭嘴。"""
    now = now or dt.datetime.now(BJ)
    since = (now - dt.timedelta(days=days)).replace(hour=0, minute=0, second=0)
    msgs = fetch(APPLY_GROUP, since, now) + fetch(PROD_GROUP, since, now)
    ev = classify(msgs)
    ev["window"] = (since.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d %H:%M"))
    ev["has_event"] = bool(ev["申请"] or ev["催办"] or ev["回执"])
    return ev


if __name__ == "__main__":
    import sys
    d = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    e = scan(days=d)
    print(f"窗口 {e['window'][0]} → {e['window'][1]}   有事件={e['has_event']}")
    for k in ("申请", "催办", "批示", "回执"):
        print(f"\n── {k}  {len(e[k])} 条 ──")
        for x in e[k]:
            amt = "/".join(str(a) for a in x["amounts"]) or "-"
            att = ("图" if x["has_img"] else "") + ("件" if x["has_file"] else "") or "无附件"
            v = x.get("verdict", "")
            print(f"  [{x['time']}] {x['sender']:6s} 金额={amt:12s} {att:6s} {v} {x['text'][:60]}")


# ══════════════════════════════════════════════════════════════════════
#  异常判定 —— 只盯员工该做没做，不盯管理层该批没批
#
#  老板 2026-09-11 定的方向，这是本模块的第一原则：
#
#      「没有批准的，那么就是管理层的责任。我都说了，你不要把责任
#        移嫁到管理层上面去。我们整个机制的目的是要逼员工，是要维护
#        管理层的利益……如果是管理层把事情做了，但是员工没有做，
#        那么就是员工的责任。你不要逼管理层。」
#
#  所以「申请交上去没人批」这类判定**已删除**：申请挂着没批，责任在批的人，
#  报它等于拿哨兵去追老板和林总。杨婷在群里催领导也一样，不报。
#
#  留下的每一条都必须能回答同一个问题：**哪个员工，该做的哪件事没做。**
# ══════════════════════════════════════════════════════════════════════

# 领导表态同意后，员工先斩后奏也好、拖着不办也好，都归这里
MIN_DAYS = 2      # 阈值来自实测节奏：申请集中在下午提，付款集中在次日下午出。
                  # 隔一天就喊会系统性早报。

BYPASS_WORDS = ("流程未通过", "流程没通过", "未走流程", "没走流程",
                "先申请付款", "流程未过", "未通过先")


def _fmt(ts):
    return f"{int(ts[5:7])}月{int(ts[8:10])}日 {ts[11:16]}"


def _quote(text, n=42):
    t = re.sub(r"\[图片消息\]\(mediaId=[^)]*\)", "[图]", text)
    t = re.sub(r"\[文件\]\s*", "[件]", t)
    t = re.sub(r"@[^\s(]+\([^)]*\)", "", t).strip()
    t = " ".join(t.split())
    return (t[:n] + "…") if len(t) > n else (t or "[只有附件，正文没写字]")


def _days_since(ts, now):
    d = dt.datetime.strptime(ts[:10], "%Y-%m-%d").date()
    return (now.date() - d).days



SPLIT_RE = re.compile(r"(?<=请批示。)|(?<=请批示)(?=\s*\[图片消息\])")
ASKER_RE = re.compile(r"([一-龥]{1,3}(?:工|总|经理))\s*(?:那边)?\s*说")


def _split_requests(text):
    """一条消息里可能塞了两笔独立申请，按「请批示」切开分别判定。"""
    parts = [p.strip() for p in SPLIT_RE.split(text) if p and p.strip()]
    return parts or [text]


def _originator(seg):
    """「李工说这个款比较急」——发起人是李工，不是转达的人。"""
    m = ASKER_RE.search(seg)
    return m.group(1) if m else None


def findings(ev, now=None, min_days=None):
    """返回可上报的异常。每条自带 fingerprint，交给台账做首报制。

    三条，全部指向员工。老板 2026-09-11 的方向：
    「不要找老板的麻烦，你的目标是要确保员工那边的工作效率，他们的工作内容是准确的。」
    所以「领导还没批」永远不报——那是管理层的节奏，不是员工的失职。
    """
    now = now or dt.datetime.now(BJ)
    min_days = MIN_DAYS if min_days is None else min_days
    receipts = ev["回执"]
    out = []

    def receipt_after(ts):
        return [r for r in receipts if r["time"] > ts]

    # ── 1. 领导已经打了 OK，钱却没出去 ────────────────────────────
    #    授权是钉钉表情，不是正文措辞，而且只认付款请示群。
    #    领导做完授权动作之后，剩下的全是执行，这才是员工责任的正身。
    for a in ev["申请"]:
        who = approved_by(a)
        if not who or _days_since(a["time"], now) < min_days:
            continue
        if receipt_after(a["time"]):
            continue
        days = _days_since(a["time"], now)
        amt = "、".join(f"{x:,.2f}" for x in a["amounts"]) or "金额在图里"
        out.append({
            "fingerprint": f"evt:unpaid:{a['msgid']}",
            "check_id": "approved_not_paid",
            "when": a["time"], "who": a["sender"], "days": days, "amount": amt,
            "line": f"{_fmt(a['time'])} {a['sender']}提的付款请示（{amt}）"
                    f"{'、'.join(who)}已经打 OK 授权，过了 {days} 天生产付款群还没有回执",
        })

    # ── 2. 绕开红圈审批流先申请付款 ───────────────────────────────
    #    领导事后打了 OK 且钱已付 = 当场闭环，不回头要说明。
    for a in ev["申请"]:
        if approved_by(a) and receipt_after(a["time"]):
            continue
        for seg in _split_requests(a["text"]):
            if not any(w in seg for w in BYPASS_WORDS):
                continue
            amts = amounts_of(seg)
            amt = "、".join(f"{x:,.2f}" for x in amts) or "金额在图里"
            asker = _originator(seg) or a["sender"]
            relay = f"（{a['sender']}转达）" if asker != a["sender"] else ""
            out.append({
                "fingerprint": f"evt:bypass:{a['msgid']}:{hashlib.md5(seg.encode()).hexdigest()[:8]}",
                "check_id": "bypass_approval",
                "when": a["time"], "who": asker,
                "amount": str(amts[0]) if len(amts) == 1 else amt,
                "line": f"{_fmt(a['time'])} {asker}{relay}绕开红圈审批流直接申请付款"
                        f"（{amt}）：「{_quote(seg, 52)}」",
            })

    # ── 曾经有第 3 条：「申请正文不写金额，逼领导点图」。已删除。─────
    #
    # 老板 2026-09-11：「你说的不现实，杨婷只能发图片，是你的错误。」
    #
    # 他是对的。她的岗位就只能甩图，要求她额外打一行字是把流程成本推给员工；
    # 更要命的是——**金额在图里，读图本来就是本系统的活**。我手上就有 OCR，
    # 已经能把「待付款请示明细表」读成 15,000+20,000=35,000、能挑出未签字的行，
    # 却回头去怪交图的人没打字。
    #
    # 这跟本 session 早前那条「欠款方未登记」是同一类错误：
    # 把自己的解析缺口报成别人的问题。这类判定一律不许再出现。
    out.sort(key=lambda x: x["when"])
    return out


# ══════════════════════════════════════════════════════════════════════
#  申请单读取：把「正文没写金额」变成「哪两笔、多少钱、付给谁」
#
#  杨婷提申请时正文常常只有一句「领导请批示。」，金额和收款方全在图里。
#  只报「有张图挂了两天」对老板没用，他要知道是哪一笔。
#
#  用本机 Vision OCR，不调视觉模型：读错一个金额会把真问题静默抵扣掉，
#  比读不出来严重得多。读不出来就保持原样，绝不猜、绝不补一个看着像的数。
# ══════════════════════════════════════════════════════════════════════
import os, subprocess as _sp

IMGDIR = os.path.expanduser("~/.local/share/kmfa-payment-alert/apply_img")
OCR_CACHE = os.path.expanduser("~/.local/share/kmfa-payment-alert/apply_ocr.json")
VENV_PY = os.path.expanduser("~/.local/share/kmfa-payment-alert/venv/bin/python")
MEDIA_RE = re.compile(r"mediaId=([^)\s]+)\)")
NUM_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{3,9}(?:\.\d+)?)(?![\d])")
# OCR 会在公司名中间断行（「中盐内蒙古化\n工股份有限公司」），跨不过换行就只读得到一半
PAYEE_RE = re.compile(r"付([一-龥（）()A-Za-z0-9\s]{4,40}?)-{1,2}\s*公司")
SINGLE_AMT = re.compile(r"付款金额（元）\s*\n\s*([\d,]+\.\d{2})")
SINGLE_PAYEE = re.compile(r"收款单位\s*\n\s*([^\n]{4,40})")
# 「待付款请示明细表」每行末尾标签字状态：`7000 武汉 未签字`。
# 未签字 = 没走完流程，正是绕流程那几笔。比拿整张表的总合计准得多：
# 2026-09-04 那张总合计 112,100.26，但绕流程的只有 7000+8500+750=16,250，
# 而且和杨婷正文写的「武汉5,6 / 岚丹3」逐行对得上。
UNSIGNED_ROW = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s+\S{1,6}\s*未签字")


def _safe(name):
    """msgid 里有 / 和 +，不换掉会在磁盘上凭空造出目录。"""
    return re.sub(r"[^A-Za-z0-9=_.-]", "_", name)


def _total_by_arithmetic(nums):
    """找出「合计」：某个数恰好等于其余若干个数之和，就是它自己证明自己。

    实测 09-09 那张 15000+20000=35000、09-08 那张 3000+18000+91923.55+30000=142923.55，
    都能自洽。凑不出来就返回 None —— 宁可不说，也不报一个看着像总额的数。
    """
    vals = sorted(set(nums), reverse=True)
    if not vals or len(vals) > 16:
        return None, []
    for i, cand in enumerate(vals):
        rest = vals[:i] + vals[i + 1:]
        n = len(rest)
        for mask in range(1, 1 << n):
            pick = [rest[j] for j in range(n) if mask >> j & 1]
            if len(pick) >= 2 and sum(pick) == cand:
                return cand, sorted(pick, reverse=True)
    return None, []


def _ocr(paths):
    if not paths or not os.path.exists(VENV_PY):
        return {}
    try:
        cache = json.load(open(OCR_CACHE, encoding="utf-8"))
    except Exception:
        cache = {}
    todo = [p for p in paths if p not in cache]
    if todo:
        r = _sp.run([VENV_PY, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "payment_ocr.py")] + todo,
                    capture_output=True, text=True, errors="replace", timeout=600)
        for blk in r.stdout.split("<<<FILE>>>")[1:]:
            head, _, body = blk.partition("\n")
            cache[head.strip()] = body
        try:
            json.dump(cache, open(OCR_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
        except Exception:
            pass
    return {p: cache.get(p, "") for p in paths}


def read_application(msg):
    """读一条申请消息的附件，返回它能证明的东西。证不出来就返回空。"""
    os.makedirs(IMGDIR, exist_ok=True)
    paths = []
    for i, media in enumerate(MEDIA_RE.findall(msg["text"])):
        p = os.path.join(IMGDIR, f"{_safe(msg['msgid'])}_{i}.png")
        if not os.path.exists(p):
            r = _sp.run(["dws", "chat", "message", "download-media", "--type", "mediaId",
                         "--resource-id", media, "--message-id", msg["msgid"],
                         "--open-conversation-id", msg["group"], "--output", p],
                        capture_output=True, text=True, timeout=180)
            if r.returncode != 0 or not os.path.exists(p):
                continue
        paths.append(p)

    text = "\n".join(t for t in _ocr(paths).values() if t)
    if not text:
        return {}

    nums = [Decimal(m.group(1).replace(",", "")) for m in NUM_RE.finditer(text)]
    total, parts = _total_by_arithmetic(nums)
    if total is None:
        m = SINGLE_AMT.search(text)
        if m:
            total, parts = Decimal(m.group(1).replace(",", "")), []

    payees = []
    for m in PAYEE_RE.finditer(text):
        p = "".join(m.group(1).split())
        if p and p not in payees:
            payees.append(p)
    if not payees:
        m = SINGLE_PAYEE.search(text)
        if m:
            payees.append(m.group(1).strip())

    return {"total": total, "parts": parts, "payees": payees,
            "unsigned": unsigned_rows(text),
            "is_batch": "待付款请示明细表" in text, "ocr_chars": len(text)}


def unsigned_rows(text):
    """明细表里「未签字」的那几行金额——没走完流程的就是这几笔。"""
    return [Decimal(m.group(1).replace(",", "")) for m in UNSIGNED_ROW.finditer(text)]


def enrich(items, ev):
    """给绕流程那几笔补上金额。补不上就原样留着，绝不因为补不上就不报。"""
    by_id = {a["msgid"]: a for a in ev["申请"]}
    for it in items:
        if it["check_id"] != "bypass_approval":
            continue
        if "金额在图里" not in it["line"]:
            continue        # 正文已经写了金额，别再拿整条消息的 OCR 去污染它
        # 指纹是 evt:bypass:<msgid>:<段哈希>，msgid 在第 2 段。
        # 取错下标不会报错，只会静默补不上——这种失败最难发现。
        src = by_id.get(it["fingerprint"].split(":")[2])
        if not src:
            continue
        try:
            info = read_application(src)
        except Exception as exc:
            it["ocr_note"] = f"{type(exc).__name__}"
            continue
        if not info:
            continue
        rows = info.get("unsigned") or []
        if rows:
            it["amount"] = str(sum(rows))
            it["line"] = it["line"].replace(
                "（金额在图里）",
                f"（明细表里 {len(rows)} 行未签字，共 {sum(rows):,.2f}）")
        elif info.get("total") is not None:
            it["amount"] = str(info["total"])
            it["line"] = it["line"].replace("（金额在图里）", f"（共 {info['total']:,.2f}）")
    return items
