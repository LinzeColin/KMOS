#!/usr/bin/env python3
"""付款异常哨兵回归测试。

守的是历史上真出过的事故，每条断言后面都写清楚它防的是哪一次。
零参数、零环境变量就能跑 —— 定时任务走的就是这条路径。
"""
import datetime as dt, os, sys, tempfile
from decimal import Decimal
import payment_checks as PC

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BJ = dt.timezone(dt.timedelta(hours=8))
FAILED = []


def check(name, cond, extra=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{extra}]" if extra else ""))
    if not cond:
        FAILED.append(name)


def main():
    import payment_send as S
    from payment_checks import run_all, CHECKS
    from payment_ledger import Ledger
    from payment_feedback import match_line

    print("== 一、发送时窗硬闸（2026-09-09 悉尼 22:46 那次误发）==")
    for h, want in ((5, False), (7, False), (8, True), (11, True), (12, False), (20, False), (23, False)):
        got = S.in_send_window(dt.datetime(2026, 9, 11, h, 30, tzinfo=BJ))
        check(f"北京 {h:02d}:30 {'放行' if want else '拦下'}", got == want)
    src = open(os.path.join(HERE, "payment_send.py"), encoding="utf-8").read()
    gate = src[src.index("def send("):]
    check("send() 里时窗判断在调 dws 之前", gate.index("in_send_window") < gate.index('"send"'))
    check("没有任何环境变量能绕过时窗", "environ" not in gate.split("def main")[0])

    print("\n== 二、各项检查（零参数可跑，一项坏了不许拖垮其余）==")
    res = run_all()
    check("注册表里每一项都有结果", len(res) == len(CHECKS), f"{len(res)} vs {len(CHECKS)}")
    for cid, _t in CHECKS:
        check(f"{cid} 不是 error", res[cid]["status"] != "error", res[cid]["note"][:60])
    healthy = [c for c in res.values() if c["status"] in ("hit", "clear")]
    check("至少一项健康", len(healthy) >= 1, f"healthy={len(healthy)}")

    print("\n== 三、被杨婷 2026-09-09 推翻的三条旧口径，不许复活 ==")
    check("重复报销 0 命中（0959/0960 只真付一笔；1402/1403 费用说明为空判不了）",
          len(res["dup_reimbursement"]["items"]) == 0,
          f"{len(res['dup_reimbursement']['items'])}")
    check("同日重付 0 命中（张红/汪松涛分属两个批次）",
          len(res["same_day_duplicate"]["items"]) == 0,
          f"{len(res['same_day_duplicate']['items'])}")
    check("金额被改按快照差异算，0 命中（旧口径拿已付额当被改额，83 行会无脑命中）",
          len(res["amount_changed"]["items"]) == 0,
          f"{len(res['amount_changed']['items'])}")

    print("\n== 四、客户欠款：不许把自己的解析缺口报成别人的问题 ==")
    rv = res["receivable_stalled"]
    check("客户欠款可用", rv["status"] in ("hit", "clear"), rv["note"][:60])
    check("正文里没有「未登记」字样", all("未登记" not in i["line"] for i in rv["items"]))
    check("每一条都有真实欠款方", all(len(i["detail"]["party"]) >= 2 for i in rv["items"]))
    check("排除数为 0（join 主合同后应当全部解得出）", "已排除" not in (rv["note"] or ""), rv["note"][:40])

    print("\n== 五、首报制台账 ==")
    with tempfile.TemporaryDirectory() as td:
        L = Ledger(os.path.join(td, "t.sqlite3"))
        items = [i for r in res.values() for i in r["items"]][:5]
        check("首次全是新的", len(L.unreported(items)) == len(items))
        L.record_reported(items)
        check("第二次一条不剩", len(L.unreported(items)) == 0)
        fp = items[0]["fingerprint"]
        check("能标记已回应", L.mark_answered(fp, "测试原话", "msg1"))
        check("已回应的不会再出现在待办里", fp not in [x["fingerprint"] for x in L.open_items()])
        check("重复标记已回应返回 False", not L.mark_answered(fp, "又一次", "msg2"))

    print("\n== 六、回应锚定（用杨婷 09-09 那三张真图）==")
    seed = os.path.expanduser("~/.local/share/kmfa-payment-alert/seed")
    cache_txt = ""
    venv = os.path.expanduser("~/.local/share/kmfa-payment-alert/venv/bin/python")
    imgs = sorted(f for f in os.listdir(seed) if f.endswith(".png")) if os.path.isdir(seed) else []
    if imgs and os.path.exists(venv):
        import subprocess
        r = subprocess.run([venv, os.path.join(HERE, "payment_ocr.py")]
                           + [os.path.join(seed, f) for f in imgs],
                           capture_output=True, text=True, timeout=600)
        cache_txt = r.stdout
    if cache_txt:
        cases = [("王玉鹤 10,168.00 尾号0374 2026-02-06", "26.2.9"),
                 ("张红 12,718.46 尾号0087 2025-12-26", "25.12.26"),
                 ("刘文亮 2,000.00 尾号6363 2026-08-10", "26.8.11"),
                 ("刘文亮 2,922.50 尾号6363 2026-09-02", "26.9.3")]
        for line, want in cases:
            q = match_line(line, cache_txt) or ""
            check(f"锚定 {line[:22]}", want in q, q[:40])
        check("负控：金额差 1 分就匹配不上",
              match_line("王玉鹤 10,168.01 尾号0374 2026-02-06", cache_txt) is None)
        check("负控：只有名字没有金额不算命中",
              match_line("王玉鹤 尾号0374", cache_txt) is None)
    else:
        check("锚定测试有素材可用", False, "seed 图或 venv 缺失")

    print("\n== 七、消息模板 ==")
    ev_items = [{
        "fingerprint": "evt:bypass:TEST:abcd1234", "check_id": "bypass_approval",
        "when": "2026-09-08 11:39:52", "who": "李工", "amount": "41516.05",
        "line": "9月8日 11:39 李工（杨婷转达）绕开红圈审批流直接申请付款（41,516.05）",
    }]
    text = S.render(ev_items, res, {"reported": 1, "answered": 6},
                    {"红圈付款审批": "2026-09-04"}, today=dt.date(2026, 9, 11))
    check("有分节编号", "**1. " in text)
    check("段落之间是空行（钉钉按 Markdown 渲染，单换行会被吃掉）", "\n\n" in text)
    check("有要办", "**要办：**" in text)
    check("正文不含裸竖线（会被当表格语法）", "|" not in text.replace("／", ""))
    check("写了数据截止", "数据截止" in text)
    check("停更有提示", "停更" in text or "没更新" in text)
    check("说明了是增量", "本次新增" in text)
    check("金额齐全时给出小计", "，共 41,516.05" in text)

    print("\n== 八、欠款怎么进：按客户合并、只进高价值 ==")
    # 老板 2026-09-11：「不是不进，是要高价值的进。」
    # 按合同逐条那份（92 条）永远不进——一次刷 92 行没有重点，同一家会被拆成十几条。
    check("按合同逐条的那份被排除", "receivable_stalled" in S.DAILY_EXCLUDED)
    check("按合同逐条的那份不在渲染顺序里", "receivable_stalled" not in S.ORDER)
    check("按客户合并的高价值那份要进", "receivable_major" in S.ORDER)
    recv = res["receivable_stalled"]["items"][:3]
    leaked = S.render(recv, res, {"reported": 0, "answered": 0},
                      {"红圈付款审批": "2026-09-04"}, today=dt.date(2026, 9, 11))
    check("拿逐条欠款去渲染也渲不出正文", "**1. " not in leaked)

    maj = res["receivable_major"]
    check("高价值欠款查得出来", maj["status"] == "hit" and len(maj["items"]) >= 5)
    check("每家一条，不按合同拆", all(it["fingerprint"].startswith("recvmajor:") for it in maj["items"]))
    check("同一家的多个合同已合并", any(it["detail"]["contracts"] > 1 for it in maj["items"]))
    check("门槛以下的不进正文",
          all(Decimal(it["detail"]["balance"]) >= PC.RECEIVABLE_MAJOR for it in maj["items"]))
    check("脚注交代了没进正文的部分", "全部" in maj["note"] and "合计" in maj["note"])
    parties = [it["detail"]["party"] for it in maj["items"]]
    check("欠款方都有真名字", all(p and "未登记" not in p and "未知" not in p for p in parties))
    check("按金额从大到小", [Decimal(i["detail"]["balance"]) for i in maj["items"]]
          == sorted([Decimal(i["detail"]["balance"]) for i in maj["items"]], reverse=True))
    fps = [it["fingerprint"] for it in maj["items"]]
    check("同一家只出现一次", len(fps) == len(set(fps)))

    print("\n== 九、事件闸门（没有付款就不说话）==")
    import payment_event as EV
    qnow = dt.datetime(2026, 9, 6, 23, 59, tzinfo=EV.BJ)      # 窗口 09-05 → 09-06，两天全空
    quiet = EV.scan(days=1, now=qnow)
    check("09-05~09-06 两天没有任何付款事件", quiet["has_event"] is False)
    check("安静日一条异常都不产", EV.findings(quiet, now=qnow) == [])
    check("上界被夹住了（--direction newer 没有上界，不夹就假绿）",
          all(m["time"] <= "2026-09-06 23:59:00"
              for m in EV.fetch(EV.APPLY_GROUP, dt.datetime(2026, 9, 1, tzinfo=EV.BJ), qnow)))
    busy = EV.scan(days=1, now=dt.datetime(2026, 9, 4, 23, 59, tzinfo=EV.BJ))
    check("09-04 真有付款，识别得到", busy["has_event"] is True and len(busy["回执"]) >= 3)
    chase = EV.scan(days=1, now=dt.datetime(2026, 9, 10, 23, 59, tzinfo=EV.BJ))
    check("09-10 只有催办也算事件", chase["has_event"] is True and len(chase["催办"]) == 1)
    check("自己发的资金日报不算事件", EV.is_machine_post("张霖泽", "2026-09-09 资金日报\n可动用合计"))
    check("自己发的付款异常不算事件", EV.is_machine_post("张霖泽", "**付款异常 9月8日**"))
    check("领导真批示不会被误当机器发言", not EV.is_machine_post("张霖泽", "新都化工钢筋采购费41516.05元付承兑"))
    check("金额解析：4万 = 40000", EV.amounts_of("宜宾华福双三水泥材料款4万（付承兑）") == [Decimal("40000")])
    check("金额解析：41516.05元", Decimal("41516.05") in EV.amounts_of("新都化工钢筋采购费41516.05元付承兑"))
    check("噪声不算申请：资金明细", EV.classify([
        {"time": "2026-09-09 10:19:17", "sender": "杨婷", "text": "[图片消息](mediaId=x)9.8资金明细",
         "msgid": "m1", "group": EV.APPLY_GROUP}])["申请"] == [])
    check("噪声不算回执：款已到账", EV.classify([
        {"time": "2026-09-04 14:50:34", "sender": "杨婷", "text": "[图片消息](mediaId=x)票据到期，款已到账。",
         "msgid": "m2", "group": EV.APPLY_GROUP}])["申请"] == [])

    print("\n== 九之二、只追员工，不追管理层 ==")
    # 老板 2026-09-11：「没有批准的，那么就是管理层的责任……不要把责任移嫁到管理层上面去。」
    # 「申请交上去没人批」「催了领导还不批」这两类判定必须永久消失。
    src = open(os.path.join(HERE, "payment_event.py"), encoding="utf-8").read()
    check("「申请挂着没人批」这类判定已删除", "apply_stalled" not in src)
    check("「催了领导还不批」这类判定已删除", "chase_unpaid" not in src)
    check("模板里也没有这两项", "apply_stalled" not in S.ORDER and "chase_unpaid" not in S.ORDER)
    wide = EV.scan(days=14, now=dt.datetime(2026, 9, 11, 8, 20, tzinfo=EV.BJ))
    fs = EV.findings(wide, now=dt.datetime(2026, 9, 11, 8, 20, tzinfo=EV.BJ))
    check("报出来的每一条都指向员工",
          all(f["check_id"] in ("approved_not_paid", "bypass_approval", "application_unclear")
              for f in fs), str(fs)[:80])

    print("\n== 九之三、授权是钉钉表情，而且只在付款请示群 ==")
    # 老板 2026-09-11：「我们一般都是通过钉钉的表情回复去授权的，请示群不可能有
    # 授权同意，上游授权只会发生在付款请示群，不会发生在生产付款群。」
    #
    # 我先前在正文里找「同意/付了」，找错了地方；还一度把生产付款群里领导说的
    # 「新都化工钢筋采购费41516.05元付承兑」当成授权来源——那是在下指令，不是审批。
    ok = [a for a in wide["申请"] if EV.approved_by(a)]
    check("授权读的是 emotionReplyList 里的 OK", len(ok) >= 10, f"{len(ok)} 笔已授权")
    check("09-08 16:04 那笔有林全意的 OK",
          any(a["time"].startswith("2026-09-08 16:04") and "林全意" in EV.approved_by(a)
              for a in wide["申请"]))
    check("09-09 16:35 那笔没有任何 OK —— 没批就是没批",
          all(EV.approved_by(a) == [] for a in wide["申请"]
              if a["time"].startswith("2026-09-09 16:35")))
    # 09-09 那笔没批，绝不能因为「挂着没人批」被点名。
    # （它会出现在「正文不写金额」的统计里，那是提交质量，跟批没批无关。）
    check("没打 OK 的一律不报「没人批/没付款」（那是管理层的节奏，不是员工失职）",
          not any(f["when"].startswith("2026-09-09 16:35")
                  and f["check_id"] in ("approved_not_paid", "bypass_approval") for f in fs))
    check("生产付款群不产生授权",
          all(d["group"] == EV.APPLY_GROUP for d in wide["批示"]) if wide["批示"] else True)
    check("非领导打的 OK 不算授权",
          EV.approved_by({"emoji": [{"emoji": "OK", "replyUsers": ["杨婷"]}]}) == [])
    check("领导打的 OK 才算", EV.approved_by(
          {"emoji": [{"emoji": "OK", "replyUsers": ["林全意"]}]}) == ["林全意"])
    check("没有表情字段时不炸", EV.approved_by({}) == [])
    unpaid = [a for a in ok if not [r for r in wide["回执"] if r["time"] > a["time"]]]
    check("已授权的申请全部都有后续回执，所以「批了没付」是 0 条",
          unpaid == [] and not any(f["check_id"] == "approved_not_paid" for f in fs),
          f"{len(unpaid)} 笔已批未付")

    print("\n== 九之四、请示正文不写金额（真正该管的员工侧问题）==")
    # 实测 17 笔申请里 10 笔正文只有「领导请批示。」，金额和事由全埋在图里，
    # 领导每批一笔就要点开一张图。10 笔全是同一个人交的，财务冯璐每次都写在正文。
    q = [f for f in fs if f["check_id"] == "application_unclear"]
    check("这条查得出来", len(q) == 1, str([f["check_id"] for f in fs]))
    check("按人聚合成一条，不是一笔一条", q and q[0]["count"] >= 3)
    check("一周只报一次（指纹带周序号）", q and "W" in q[0]["fingerprint"].split(":")[-1])
    check("偶尔一次不算问题（少于 3 笔不报）",
          EV.findings({"申请": [{"time": "2026-09-09 16:35:29", "sender": "某人", "text": "[图]领导请批示。",
                                "msgid": "z1", "amounts": [], "emoji": []}],
                       "催办": [], "批示": [], "回执": []},
                      now=dt.datetime(2026, 9, 11, 8, 20, tzinfo=EV.BJ)) == [])

    print("\n== 十、申请单 OCR 解析（把「有张图」变成「哪两笔多少钱」）==")
    from decimal import Decimal as D
    t, parts = EV._total_by_arithmetic([D("15000"), D("20000"), D("35000"), D("5000"), D("3")])
    check("09-09 那张：15000+20000=35000 自证", t == D("35000") and sorted(parts) == [D("15000"), D("20000")])
    t2, p2 = EV._total_by_arithmetic([D("3000"), D("18000"), D("91923.55"), D("30000"),
                                      D("142923.55"), D("111923.55")])
    check("09-08 那张：四笔加总 = 142923.55", t2 == D("142923.55") and len(p2) == 4)
    t3, _ = EV._total_by_arithmetic([D("1000"), D("2000"), D("4500")])
    check("凑不出合计就返回 None，不硬报一个像总额的数", t3 is None)
    check("msgid 里的 / 不会在磁盘上凭空造目录", "/" not in EV._safe("msg6J8L+mrM/a94O8qdeH5VrA=="))
    ocr = EV._ocr([])
    check("没有图时 OCR 不炸", ocr == {})
    payees = EV.PAYEE_RE.findall("付中盐内蒙古化\n工股份有限公司--公司")
    check("公司名被 OCR 断行也读得全", payees and "".join(payees[0].split()) == "中盐内蒙古化工股份有限公司")
    stub = [{"check_id": "apply_stalled", "fingerprint": "evt:apply:NOPE",
             "when": "2026-09-09 16:35:29", "who": "杨婷", "days": 2, "chases": 0,
             "line": "原样"}]
    EV.enrich(stub, {"申请": []})
    check("补不上金额时原样保留，不吞掉真异常", stub[0]["line"] == "原样")
    rows = EV.unsigned_rows("2273 武汉 已签字\n7000 武汉 未签字\n8500 武汉 未签字\n750 岚丹 未签字")
    check("按签字状态取绕流程那几笔（09-04 那张：7000+8500+750）",
          rows == [D("7000"), D("8500"), D("750")] and sum(rows) == D("16250"))
    check("已签字的行不算绕流程",
          EV.unsigned_rows("15000 武汉 已签字现金\n20000 武汉 已签字 现金") == [])

    print(f"\n{'='*54}")
    if FAILED:
        print(f"失败 {len(FAILED)} 条：")
        for f in FAILED:
            print(f"  - {f}")
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
