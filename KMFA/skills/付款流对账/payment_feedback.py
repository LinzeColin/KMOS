#!/usr/bin/env python3
"""回应闭环：把群里的答复吃进台账，让已回应的条目永不再报。

出纳杨婷的答复方式是**把哨兵发的那条消息截图下来、在上面逐条加括号批注**再发回群里。
所以 OCR 出来的文字里同时含有哨兵自己写的原句和她的批注：

    号0374 10,168.002.6 湖北双环 164605.7元
    （账号错误没付出去，26.2.9已重新支付）

前半截是本系统自己生成的、字符串完全已知。所以匹配是**确定性的字符串锚定**，
不需要任何语义理解，也就不需要模型。

匹配不上就什么都不做。宁可这条继续挂着（首报制下本来也不会再发），
也不要错误地标成已回应，把真问题埋掉。
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

GROUP = "cid0UmWYRhaMEbiNez2FIpDPA=="
CACHE = os.path.expanduser("~/.local/share/kmfa-payment-alert/ocr_cache.json")
IMGDIR = os.path.expanduser("~/.local/share/kmfa-payment-alert/imgs")
VENV_PY = os.path.expanduser("~/.local/share/kmfa-payment-alert/venv/bin/python")

AMOUNT = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+\.\d{2}|\d{1,9}\.\d{2})(?![\d])")
TAIL = re.compile(r"尾号\s*(\d{4})")
DOCNO = re.compile(r"(FYBX-\d{8}-\d+|SK-\d{8}-\d+|\d{8}-\d{4})")
NOTE = re.compile(r"[（(]([^）)]{4,80})[）)]")
MEDIA = re.compile(r"mediaId=([^)\s]+)\)")


def _norm(s):
    """去掉空格、项目符号、全角标点和千分位 —— OCR 会到处塞这些。"""
    return re.sub(r"[\s•·・：:，,、]", "", s or "").replace(",", "")


def _dws_json(args, timeout=120):
    r = subprocess.run(["dws"] + args, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def _walk(o):
    if isinstance(o, list):
        return o
    if isinstance(o, dict):
        for k in ("items", "messages", "data", "result", "list"):
            if k in o:
                got = _walk(o[k])
                if got is not None:
                    return got
        for v in o.values():
            got = _walk(v)
            if got is not None:
                return got
    return None


def _load_cache():
    try:
        return json.load(open(CACHE, encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".tmp"
    json.dump(c, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    os.replace(tmp, CACHE)


def tokens_of(line):
    """从哨兵自己生成的那一行里抽判别性 token。金额是必须项。"""
    amts = [a.replace(",", "") for a in AMOUNT.findall(line)]
    # 行里的金额可能没有小数点后两位（渲染时一定有），再兜一层
    others = TAIL.findall(line) + DOCNO.findall(line)
    names = re.findall(r"[一-龥]{3,12}(?:有限公司|有限责任公司|中心|支行)?", line)
    return amts, others + [n for n in names if len(n) >= 3]


def match_line(line, text):
    """命中要求：金额精确出现 + 至少再有一个独立 token。返回紧随其后的括号批注。"""
    amts, others = tokens_of(line)
    if not amts:
        return None
    flat = _norm(text)
    hit_amt = None
    for a in amts:
        if _norm(a) in flat:
            hit_amt = a
            break
    if hit_amt is None:
        return None
    second = sum(1 for t in others if t and _norm(t) in flat)
    if second < 1:
        return None
    # 取金额出现位置之后的第一个括号批注
    idx = flat.find(_norm(hit_amt))
    raw_positions = []
    for m in NOTE.finditer(text):
        if _norm(text[:m.start()]).find(_norm(hit_amt)) >= 0:
            raw_positions.append(m.group(1))
    if raw_positions:
        return raw_positions[0]
    return text[max(0, idx):][:60] or "已在群内回应"


def _download(msgs):
    os.makedirs(IMGDIR, exist_ok=True)
    got = []
    for m in msgs:
        c = m.get("content")
        if isinstance(c, dict):
            c = json.dumps(c, ensure_ascii=False)
        mid = m.get("openMessageId")
        for i, media in enumerate(MEDIA.findall(str(c))):
            key = f"{mid}_{i}"
            path = os.path.join(IMGDIR, key.replace("/", "_") + ".png")
            if not os.path.exists(path):
                r = subprocess.run(
                    ["dws", "chat", "message", "download-media", "--type", "mediaId",
                     "--resource-id", media, "--message-id", mid,
                     "--open-conversation-id", GROUP, "--output", path],
                    capture_output=True, text=True, timeout=180)
                if r.returncode != 0 or not os.path.exists(path):
                    continue
            got.append((key, path, mid))
    return got


def scan(ledger, since=None, group=GROUP):
    since = since or ledger.get_meta("last_report_scan", "2026-09-06 00:00:00")
    since = str(since).replace("T", " ")[:19]
    stat = {"msgs": 0, "imgs": 0, "ocr_new": 0, "matched": 0, "unmatched": 0}

    data = _dws_json(["chat", "message", "list", "--group", group, "--time", since,
                      "--direction", "newer", "--limit", "200", "-f", "json"])
    msgs = _walk(data) or []
    stat["msgs"] = len(msgs)
    if not msgs:
        return stat

    open_items = ledger.open_items()
    if not open_items:
        return stat

    # ---- 文本通道 ----
    texts = []
    for m in msgs:
        c = m.get("content")
        if isinstance(c, dict):
            c = c.get("text") or json.dumps(c, ensure_ascii=False)
        texts.append((str(c), m.get("openMessageId")))

    # ---- 图片通道 ----
    cache = _load_cache()
    downloaded = _download(msgs)
    stat["imgs"] = len(downloaded)
    todo = [(k, p, mid) for k, p, mid in downloaded if k not in cache]
    if todo and os.path.exists(VENV_PY):
        r = subprocess.run([VENV_PY, os.path.join(HERE, "payment_ocr.py")] + [p for _, p, _ in todo],
                           capture_output=True, text=True, timeout=600)
        blocks = r.stdout.split("<<<FILE>>>")[1:]
        for (k, p, _mid), blk in zip(todo, blocks):
            body = blk.split("\n", 1)[1] if "\n" in blk else ""
            cache[k] = body
            stat["ocr_new"] += 1
        _save_cache(cache)
    for k, _p, mid in downloaded:
        if cache.get(k):
            texts.append((cache[k], mid))

    # ---- 锚定 ----
    matched_fps = set()
    for it in open_items:
        for text, mid in texts:
            q = match_line(it["rendered_line"], text)
            if q:
                if ledger.mark_answered(it["fingerprint"], q, mid):
                    stat["matched"] += 1
                    matched_fps.add(it["fingerprint"])
                break

    # ---- 明显是批注却没锚定上的，要能被看见 ----
    for text, _mid in texts:
        for note in NOTE.findall(text):
            if AMOUNT.search(note) or "支付" in note or "重复" in note:
                stat["unmatched"] += 1
    stat["unmatched"] = max(0, stat["unmatched"] - stat["matched"])
    return stat


def main():
    from payment_ledger import Ledger
    L = Ledger(os.environ.get("PAYMENT_LEDGER_DB"))
    s = scan(L)
    print(f"FEEDBACK_SCAN msgs={s['msgs']} imgs={s['imgs']} ocr_new={s['ocr_new']} "
          f"matched={s['matched']} unmatched_notes={s['unmatched']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
