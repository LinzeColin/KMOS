#!/usr/bin/env python3
"""渲染并投递付款异常消息。所有给人看的字都在这个文件里。

三条铁律，都是被真事咬出来的：

1. **时窗硬闸落在这一层。** 2026-09-09 悉尼 22:46（北京 20:46）有人手动跑生产脚本
   做「无人值守验证」，真发了出去。原因是只有下沿闸（北京 08:00 之前让路）没有上沿。
   现在判断放在真正调 dws 之前，谁调用、带什么参数、带什么环境变量都拦，
   **没有任何环境变量能绕过它**。

2. **发完必须回读确认。** 2026-09-09 那次脚本打了 `ALERT_SENT hits=5 chars=1386`，
   但群里根本没有那条消息。发送函数没抛异常 ≠ 消息落地了。
   回读确认不到就是 SEND_FAILED，台账不写，下次还能重发。

3. **钉钉按 Markdown 渲染**：单个 \n 会被吃掉（要空行分段），`|` 会触发表格语法。
"""
import datetime as dt, json, os, re, subprocess, sys
from decimal import Decimal

PRODUCTION_PAYMENT_GROUP = "cid0UmWYRhaMEbiNez2FIpDPA=="
OWNER_USER = "01256723246324629191"          # 张霖泽，失败告警只走这里，任何阶段都不进群

STALE_DAYS = {"红圈付款审批": 3, "红圈收款登记": 3, "周付款计划": 10, "下游转账凭证": 10}
DEFAULT_STALE_DAYS = 10

SEND_WINDOW_BJ = (8, 12)                     # 北京 08:00 ≤ t < 12:00
BJ = dt.timezone(dt.timedelta(hours=8))

TITLES = {
    "dup_reimbursement":  ("同收款方、同金额、同事由，7 天内报了两次", "组", "逐组认，是两笔真业务还是报重了"),
    "amount_changed":     ("申请交上去以后金额被改过", "笔", "谁改的、经谁同意的"),
    "transfer_failed":    ("钱没转出去", "笔", "财务确认补了没有，没补是为什么"),
    "same_day_duplicate": ("同一天给同一个人转了两遍", "组", "两笔都出去了，是不是多付了"),
    "status_regressed":   ("审批状态倒退成驳回或撤销", "笔", "确认是正常撤单还是被卡住了"),
    "receivable_stalled": ("客户欠款半年以上没再收到钱（余额 10 万以上）", "个合同", "财务和销售认领，按金额从大到小推"),
}
ORDER = ["transfer_failed", "receivable_stalled", "dup_reimbursement",
         "amount_changed", "same_day_duplicate", "status_regressed"]
MAX_LINES_PER_SECTION = 5


def bj_now():
    return dt.datetime.now(BJ)


def in_send_window(now=None):
    now = now or bj_now()
    return SEND_WINDOW_BJ[0] <= now.hour < SEND_WINDOW_BJ[1]


def money(x):
    return f"{Decimal(str(x)):,.2f}"


# ------------------------------------------------------------------ 渲染
def render(new_items, results, ledger_counts, sources, today=None):
    today = today or bj_now().date()
    by = {}
    for it in new_items:
        by.setdefault(it["check_id"], []).append(it)

    parts = [f"**付款异常 {today.month}月{today.day}日**"]
    n = 0
    for cid in ORDER:
        items = by.get(cid)
        if not items:
            continue
        n += 1
        title, unit, todo = TITLES[cid]
        total = sum(Decimal(str(i["amount"])) for i in items)
        parts.append(f"**{n}. {title}** {len(items)}{unit}，共 {money(total)}")
        shown = items[:MAX_LINES_PER_SECTION]
        bullets = [f"- {i['line'].replace('|', '／')}" for i in shown]
        if len(items) > len(shown):
            bullets.append(f"- 另有 {len(items) - len(shown)} 条")
        parts.append("\n".join(bullets))
        note = results.get(cid, {}).get("note")
        if note:
            parts.append(note)
        parts.append(f"**要办：**{todo}")
        parts.append("---")

    if parts[-1] == "---":
        parts.pop()

    # ---- 页脚：数据截止、增量说明、已结清、诊断 ----
    foot = []
    cut = "；".join(f"{k} {v}" for k, v in sources.items() if v)
    if cut:
        foot.append(f"数据截止：{cut}")
    stale = [(k, _stale_days(v)) for k, v in sources.items()
             if v and _stale_days(v) is not None
             and _stale_days(v) > STALE_DAYS.get(k, DEFAULT_STALE_DAYS)]
    if stale:
        who = "、".join(f"{k} 已 {d} 天没更新" for k, d in stale)
        foot.append(f"**注意：{who}**，靠它的检查只看得到截止日之前的事。")
    ans = ledger_counts.get("answered", 0)
    rep = ledger_counts.get("reported", 0)
    tail = f"本次新增 {len(new_items)} 条"
    if rep:
        tail += f"；历史 {rep} 条已上报过，不重复"
    if ans:
        tail += f"；{ans} 条群里已答复，已结清"
    foot.append(tail)
    for cid in ORDER:
        r = results.get(cid, {})
        if r.get("status") in ("error", "unavailable"):
            foot.append(f"（{TITLES[cid][0]}：本轮不可用 —— {r.get('note') or r.get('status')}）")
    if foot:
        parts.append("---")
        parts.append("\n\n".join(foot))
    return "\n\n".join(parts)


def _stale_days(datestr):
    try:
        return (bj_now().date() - dt.date.fromisoformat(str(datestr)[:10])).days
    except Exception:
        return None


# ------------------------------------------------------------------ 投递
def _dws(args, timeout=120):
    return subprocess.run(["dws"] + args, capture_output=True, text=True, timeout=timeout)


def alert_owner(text):
    """失败告警：只私聊张霖泽，任何阶段都不进群。不受发送时窗限制。"""
    r = _dws(["chat", "message", "send", "--user", OWNER_USER, "--text", text])
    return r.returncode == 0


def _readback(marker, since, group):
    """回群里把自己刚发的那条读回来。读不到就当没发出去。"""
    r = _dws(["chat", "message", "list", "--group", group,
              "--time", since.strftime("%Y-%m-%d %H:%M:%S"),
              "--direction", "newer", "--limit", "20", "-f", "json"])
    if r.returncode != 0:
        return None                      # 查不了 ≠ 没发到
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    def walk(o):
        if isinstance(o, list):
            return o
        if isinstance(o, dict):
            for k in ("items", "messages", "data", "result", "list"):
                if k in o:
                    got = walk(o[k])
                    if got is not None:
                        return got
            for v in o.values():
                got = walk(v)
                if got is not None:
                    return got
        return None
    msgs = walk(data) or []
    for m in msgs:
        c = m.get("content")
        if isinstance(c, dict):
            c = c.get("text") or json.dumps(c, ensure_ascii=False)
        if marker in str(c):
            return m.get("openMessageId") or "found"
    return False


def send(text, group=None, dry_run=False, now=None):
    """返回 (token, detail)。token ∈ SENT / OUT_OF_WINDOW / DRY_RUN / SEND_FAILED / SEND_UNVERIFIED"""
    group = group or PRODUCTION_PAYMENT_GROUP
    now = now or bj_now()

    if dry_run:
        return "DRY_RUN", text

    # ---- 硬闸：任何环境变量都绕不过 ----
    if not in_send_window(now):
        return "OUT_OF_WINDOW", f"北京 {now:%H:%M}，发布窗口是 {SEND_WINDOW_BJ[0]:02d}:00–{SEND_WINDOW_BJ[1]:02d}:00"

    marker = text.split("\n", 1)[0][:24]
    since = dt.datetime.now() - dt.timedelta(minutes=2)
    r = _dws(["chat", "message", "send", "--group", group, "--text", text])
    if r.returncode != 0:
        return "SEND_FAILED", (r.stderr or r.stdout)[:400]

    ok = _readback(marker, since, group)
    if ok is False:
        return "SEND_FAILED", "发送命令退出码 0，但回读时群里查不到这条消息"
    if ok is None:
        return "SEND_UNVERIFIED", "发送命令退出码 0，但回读接口不可用，无法确认是否落地"
    return "SENT", str(ok)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stdin", action="store_true", help="正文从标准输入读")
    a = ap.parse_args()
    text = sys.stdin.read() if a.stdin else "**付款异常 测试**\n\n测试正文"
    tok, detail = send(text, dry_run=a.dry_run)
    print(tok)
    print(detail)
    return 0 if tok in ("SENT", "DRY_RUN", "OUT_OF_WINDOW") else 3


if __name__ == "__main__":
    raise SystemExit(main())
