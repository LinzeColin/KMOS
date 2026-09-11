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
from pathlib import Path
from decimal import Decimal

PRODUCTION_PAYMENT_GROUP = "cid0UmWYRhaMEbiNez2FIpDPA=="
OWNER_USER = "01256723246324629191"          # 张霖泽，失败告警只走这里，任何阶段都不进群


TITLE_PREFIX = "**付款异常 "      # 告警正文的唯一合法开头，见 send() 里的硬闸 -1
SEND_WINDOW_BJ = (8, 12)                     # 北京 08:00 ≤ t < 12:00
BJ = dt.timezone(dt.timedelta(hours=8))

TITLES = {
    "approved_not_paid":  ("领导已经打 OK，钱还没出去", "笔", "出纳说明为什么没执行"),
    "bypass_approval":    ("绕开红圈审批流先申请付款", "笔", "发起人补流程，说明为什么不能等"),
    "dup_reimbursement":  ("同收款方、同金额、同事由，7 天内报了两次", "组", "逐组认，是两笔真业务还是报重了"),
    "amount_changed":     ("申请交上去以后金额被改过", "笔", "谁改的、经谁同意的"),
    "transfer_failed":    ("钱没转出去", "笔", "财务确认补了没有，没补是为什么"),
    "same_day_duplicate": ("同一天给同一个人转了两遍", "组", "两笔都出去了，是不是多付了"),
    "status_regressed":   ("审批状态倒退成驳回或撤销", "笔", "确认是正常撤单还是被卡住了"),
    "receivable_stalled": ("客户欠款半年以上没再收到钱（余额 10 万以上）", "个合同", "财务和销售认领，按金额从大到小推"),
    "receivable_major":   ("大客户欠款压了两年以上", "家", "销售认领，按金额从大到小要回来"),
}
# 欠款怎么进：老板 2026-09-11「不是不进，是要高价值的进」。
# 按合同逐条列的那份（receivable_stalled，92 条）永远不进——一次刷 92 行没有重点，
# 而且同一家客户会被拆成十几条。进的是按客户合并、欠 50 万以上的那 9 家
# （receivable_major），合计 1,164 万，占总额一半。每家只报一次。
#
# 顺序：先说今天发生的事，再说压着的老账。
#
# 每一项都必须能回答「哪个员工该做的哪件事没做」。老板 2026-09-11：
# 「没有批准的，那么就是管理层的责任……不要把责任移嫁到管理层上面去。
#   如果是管理层把事情做了，但是员工没有做，那么就是员工的责任。」
# 所以「申请交上去没人批」这类判定已经删除——报它等于拿哨兵去追批的人。
ORDER = ["approved_not_paid", "bypass_approval",
         "transfer_failed", "dup_reimbursement",
         "amount_changed", "same_day_duplicate", "status_regressed", "receivable_major"]
DAILY_EXCLUDED = ("receivable_stalled",)
MAX_LINES_PER_SECTION = 5


def bj_now():
    return dt.datetime.now(BJ)


RUNTIME = Path(os.environ.get("PAYMENT_ALERT_DB_DIR",
                              Path.home() / ".local/share/kmfa-payment-alert"))
HOLD_FILE = RUNTIME / "SEND_HOLD"   # 存在即禁发；由老板/本人显式解除

def send_held():
    """硬闸：文件存在就绝不调用 dws。闸门在脚本里，不依赖 automation.toml。"""
    return HOLD_FILE.exists()


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
        amts = [Decimal(str(i["amount"])) for i in items
                if isinstance(i.get("amount"), (int, float, str, Decimal))
                and str(i.get("amount")).replace(".", "").replace("-", "").isdigit()]
        head = f"**{n}. {title}** {len(items)}{unit}"
        if amts and len(amts) == len(items):
            head += f"，共 {money(sum(amts))}"
        parts.append(head)
        shown = items[:MAX_LINES_PER_SECTION]
        # 明细恒为干净单行：折叠换行/多余空白，避免 \n\n 拼出三连空行。
        # 带 title 的项（如欠款）：公司名单独成行、加粗当小标题，详情另起一行。
        bullets = []
        for i in shown:
            body = " ".join(i["line"].replace("|", "／").split())
            title = i.get("title")
            if title:
                title = " ".join(str(title).replace("|", "／").split())
                if body.startswith(title):
                    body = body[len(title):].strip()
                bullets.append(f"**{title}**\n\n{body}")
            else:
                bullets.append(f"- {body}")
        if len(items) > len(shown):
            bullets.append(f"- 另有 {len(items) - len(shown)} 条")
        parts.append("\n\n".join(bullets))
        note = results.get(cid, {}).get("note")
        if note:
            parts.append(note)
        parts.append(f"**要办：**{todo}")
        parts.append("---")

    if parts[-1] == "---":
        parts.pop()

    # ---- 页脚：数据截止 + 数据源本轮不可用 ----
    foot = []
    cut = "；".join(f"{k} {v}" for k, v in sources.items() if v)
    if cut:
        foot.append(f"数据截止：{cut}")
    # 注意/本次新增不再上版（老板 2026-09-11）；台账去重仍在跑，只是不显示计数，故 ledger_counts 保留在签名上不展示。
    for cid in ORDER:
        r = results.get(cid, {})
        if r.get("status") in ("error", "unavailable"):
            foot.append(f"（{TITLES[cid][0]}：本轮不可用 —— {r.get('note') or r.get('status')}）")
    if foot:
        parts.append("---")
        parts.append("\n\n".join(foot))
    return "\n\n".join(parts)


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
    """返回 (token, detail)。token ∈ SENT / NOT_AN_ALERT / HELD / OUT_OF_WINDOW / DRY_RUN / SEND_FAILED / SEND_UNVERIFIED"""
    group = group or PRODUCTION_PAYMENT_GROUP
    now = now or bj_now()

    if dry_run:
        return "DRY_RUN", text

    # ---- 硬闸 -1：只有真正的告警正文才允许出门 ----
    #
    # 2026-09-11 07:10 我为了「实测时窗」直接调了 send('x', now=08:20)，
    # 两条 `x` 用老板的账号发进了生产付款群。和 2026-09-09 悉尼 22:46 那次
    # 同一个根因：**验证路径和生产路径是同一条**。
    # 时窗闸门拦不住它——因为我喂的时间就在窗口内。
    #
    # 所以再加一道与时间无关的闸：正文必须是真告警的形状。
    # 「x」「测试」「hello」这类东西现在物理上出不去，谁调都出不去。
    if not text.lstrip().startswith(TITLE_PREFIX):
        return "NOT_AN_ALERT", (f"正文不是告警（必须以 {TITLE_PREFIX!r} 开头），"
                                f"拒发。收到的开头是 {text.lstrip()[:20]!r}")

    # ---- 硬闸 0：显式禁发 ----
    if send_held():
        return "HELD", f"存在禁发文件 {HOLD_FILE}，本轮不发群"

    # ---- 硬闸 1：任何环境变量都绕不过 ----
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
    return 0 if tok in ("SENT", "DRY_RUN", "OUT_OF_WINDOW", "HELD", "NOT_AN_ALERT") else 3


if __name__ == "__main__":
    raise SystemExit(main())
