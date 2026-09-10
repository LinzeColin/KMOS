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
import datetime as dt, json, re, subprocess
from decimal import Decimal

APPLY_GROUP = "cidkU176W26z9HoAK9q5cb1lA=="
PROD_GROUP  = "cid0UmWYRhaMEbiNez2FIpDPA=="
LEADERS     = ("林全意", "张霖泽")
BJ          = dt.timezone(dt.timedelta(hours=8))

# ── 申请触发词。全部来自真实群消息，不是我编的 ──────────────────────
APPLY_TRIGGER = ("请批示", "请领导批示", "申请付款", "现申请", "请示")
# ── 催办：申请已经提了、还在等 ────────────────────────────────────
CHASE_TRIGGER = ("今天付吗", "可以付吗", "快点付", "来催了", "催一下", "还没付", "什么时候付")
# ── 批示：领导表态 ────────────────────────────────────────────────
APPROVE_WORDS = ("付了", "快点付", "全部付", "可以付", "同意", "付承兑", "好的", "好")
REJECT_WORDS  = ("不付", "暂时不付", "先不付", "不同意", "缓一缓", "先不")
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
            # 生产付款群里杨婷发的转账截图/明细就是回执。
            # 但 @了领导的是对话或对告警的批注反馈（2026-09-09 10:47 杨婷那条就是），
            # 真回执从不 @人，只是把凭证甩上来。
            if noisy or s in LEADERS:
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
#  异常判定
#
#  只写「文本本身就能证明」的两条。申请单里的金额/收款方要 OCR 才拿得到，
#  逐笔勾稽要解开「批量转账明细.pdf」，那两件没做完之前一条都不报——
#  宁可少报，也不拿半成品去消耗这个机制的可信度。
# ══════════════════════════════════════════════════════════════════════

# 判定用「自然日」而不是小时数：小时阈值是拍脑袋的，
# 「当天下班前没付」才是老板和财务共同认的那把尺。
# 申请/催办发生当天不催，隔天早上报一次；同一件事被催过就并进同一条。


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


MIN_DAYS = 2      # 阈值来自实测节奏，不是拍脑袋：申请集中在下午提，
                  # 付款也集中在次日下午出。隔一天就喊会系统性早报。


def findings(ev, now=None, min_days=None):
    """返回可上报的异常。每条自带 fingerprint，交给台账做首报制。

    只写「文本本身就能证明」的两条。申请单里的金额/收款方要 OCR 才拿得到，
    逐笔勾稽要解开「批量转账明细.pdf」，那两件没做完之前一条都不报——
    宁可少报，也不拿半成品去消耗这个机制的可信度。
    """
    now = now or dt.datetime.now(BJ)
    min_days = MIN_DAYS if min_days is None else min_days
    receipts = ev["回执"]
    out = []

    def receipt_after(ts):
        return [r for r in receipts if r["time"] > ts]

    def chases_after(ts):
        return [c for c in ev["催办"] if c["time"] > ts and not receipt_after(c["time"])]

    covered_chase = set()

    # ── 1. 申请交上去，当天过完既没批也没付 ───────────────────────
    for a in ev["申请"]:
        if _days_since(a["time"], now) < min_days:
            continue
        if receipt_after(a["time"]):
            continue
        if [d for d in ev["批示"] if d["time"] > a["time"]]:
            continue
        cs = chases_after(a["time"])
        for c in cs:
            covered_chase.add(c["msgid"])
        amt = "、".join(f"{x:,.2f}" for x in a["amounts"]) or "正文没写金额"
        days = _days_since(a["time"], now)
        tail = f"，{cs[-1]['sender']}已经催了 {len(cs)} 次" if cs else ""
        out.append({
            "fingerprint": f"evt:apply:{a['msgid']}",
            "check_id": "apply_stalled",
            "when": a["time"], "who": a["sender"], "days": days,
            "amount": amt, "chases": len(cs),
            "line": f"{_fmt(a['time'])} {a['sender']}提「{_quote(a['text'])}」（{amt}），"
                    f"挂了 {days} 天，没见批示也没见回执{tail}",
        })

    # ── 2. 催过、但催办本身找不到对应的挂起申请（申请在窗口外）─────
    for c in ev["催办"]:
        if c["msgid"] in covered_chase or _days_since(c["time"], now) < min_days:
            continue
        if receipt_after(c["time"]):
            continue
        days = _days_since(c["time"], now)
        out.append({
            "fingerprint": f"evt:chase:{c['msgid']}",
            "check_id": "chase_unpaid",
            "when": c["time"], "who": c["sender"], "days": days,
            "line": f"{_fmt(c['time'])} {c['sender']}在请示群催「{_quote(c['text'])}」，"
                    f"过了 {days} 天，生产付款群一条回执都没有",
        })

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
            "is_batch": "待付款请示明细表" in text, "ocr_chars": len(text)}


def enrich(items, ev):
    """给 apply_stalled 补上金额和收款方。补不上就原样留着，绝不因为补不上就不报。"""
    by_id = {a["msgid"]: a for a in ev["申请"]}
    for it in items:
        if it["check_id"] != "apply_stalled":
            continue
        src = by_id.get(it["fingerprint"].split(":")[-1])
        if not src:
            continue
        try:
            info = read_application(src)
        except Exception as exc:
            it["ocr_note"] = f"{type(exc).__name__}"
            continue
        if not info or info.get("total") is None:
            continue
        n = len(info["parts"]) or 1
        who = "、".join(info["payees"][:3])
        if len(info["payees"]) > 3:
            who += f" 等 {len(info['payees'])} 家"
        detail = f"{n} 笔共 {info['total']:,.2f}"
        if info["parts"]:
            detail += "（" + " + ".join(f"{p:,.0f}" for p in info["parts"]) + "）"
        it["amount"] = str(info["total"])
        it["line"] = (f"{_fmt(it['when'])} {it['who']}提的付款请示：{detail}"
                      + (f"，付{who}" if who else "")
                      + f"，挂了 {it['days']} 天，没见批示也没见回执"
                      + (f"，{it['who']}已经催了 {it['chases']} 次" if it.get("chases") else ""))
    return items
