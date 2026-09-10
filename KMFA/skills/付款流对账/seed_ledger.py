#!/usr/bin/env python3
"""上线前回填台账：把出纳杨婷 2026-09-09 10:47 在群里答复过的条目直接标 answered。

指纹从当下真实跑出来的检查结果里取，保证与运行时完全一致 —— 手打指纹必然对不上。
证据：~/.local/share/kmfa-payment-alert/seed/group_answers_20260909.md
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from payment_checks import run_all
from payment_ledger import Ledger

ANSWERED_AT = "2026-09-09T10:47:39+08:00"
MSGID = "群内标注图 2026-09-09 10:47:39 杨婷"

# 金额 → 杨婷的原话（三笔金额在六笔里唯一，可直接锚定）
QUOTES = {
    "10168":    "账号错误没付出去，26.2.9 已重新支付",
    "12718.46": "账号错误没付出去，25.12.26 已重新支付",
    "1964":     "账号错误没付出去，26.7.31 已重新支付",
    "2000":     "账号错误没付出去，26.8.11 已重新支付",
    "2922.5":   "账号错误没付出去，26.9.3 已重新支付",
    "3130.8":   "账号错误没付出去，26.2.13 已重新支付",
}


def main():
    L = Ledger(os.environ.get("PAYMENT_LEDGER_DB"))
    res = run_all()
    n = 0
    for item in res["transfer_failed"]["items"]:
        amt = item["detail"]["amount"]
        q = QUOTES.get(amt) or QUOTES.get(amt.rstrip("0").rstrip("."))
        if not q:
            print(f"  未匹配到答复，保持未结清：{item['line']}")
            continue
        L.seed(item["fingerprint"], item["check_id"], item["line"], item,
               "answered", ANSWERED_AT, ANSWERED_AT, q, MSGID)
        print(f"  ✓ 结清 {item['line']}")
        print(f"        杨婷：{q}")
        n += 1
    L.set_meta("seeded_at", ANSWERED_AT)
    L.set_meta("last_report_scan", "2026-09-09T10:47:39+08:00")
    print(f"\n回填 {n} 条")
    print(L.counts())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
