#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把两条 automation 的 rrule 钟点换算成北京时间，数一数有几个落在发送窗口里。

用法: slot_window.py <toml...> <出报时> <出报分> <窗口小时数>
输出: "<有效个数>|<全部槽位>|<有效槽位>"

本机是 Australia/Sydney 有夏令时，北京没有 —— 所以「19:15 就是北京 17:15」
只在半年里成立。要断言的是不变式「窗口内至少还有两趟」，不是某个具体钟点。
只用标准库，系统 python3.9 直接能跑。
"""
import datetime, pathlib, re, sys
from zoneinfo import ZoneInfo
BJ = ZoneInfo("Asia/Shanghai")
files = sys.argv[1:-3]
ph, pm, wh = int(sys.argv[-3]), int(sys.argv[-2]), int(sys.argv[-1])
lo, hi = ph * 60 + pm, ph * 60 + pm + wh * 60
today, all_slots, valid = datetime.date.today(), [], []
for f in files:
    try:
        txt = pathlib.Path(f).read_text(encoding="utf-8")
    except OSError:
        continue
    r = re.search(r'^rrule = "([^"]+)"', txt, re.M)
    if not r:
        continue
    hours = re.search(r"BYHOUR=([0-9,]+)", r.group(1))
    minute = re.search(r"BYMINUTE=([0-9]+)", r.group(1))
    if not hours:
        continue
    mm = int(minute.group(1)) if minute else 0
    for h in hours.group(1).split(","):
        bj = datetime.datetime.combine(today, datetime.time(int(h), mm)).astimezone(BJ)
        all_slots.append("%02d:%02d=BJ%s" % (int(h), mm, bj.strftime("%H:%M")))
        if lo <= bj.hour * 60 + bj.minute <= hi:
            valid.append(bj.strftime("%H:%M"))
print("%d|%s|%s" % (len(valid), " ".join(all_slots), ",".join(sorted(valid))))
