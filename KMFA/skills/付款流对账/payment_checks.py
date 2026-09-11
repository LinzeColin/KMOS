#!/usr/bin/env python3
"""付款异常六项检查。

口径全部在 2026-09-11 用真实数据 + 出纳杨婷 09-09 的群内答复重新验过。
被推翻的旧口径写在每项的注释里，别再回去。

一律 Decimal，不用 float。
"""
import datetime as dt, json, os, re, sqlite3, sys, zipfile
from decimal import Decimal, InvalidOperation

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from xlsx_raw import read_sheet, column_map  # noqa: E402

RUNTIME = os.environ.get("PAYMENT_ALERT_DB_DIR",
                         os.path.expanduser("~/.local/share/kmfa-payment-alert/db"))
P2 = os.path.join(RUNTIME, "p2", "payment_reconciliation.sqlite3")
P3 = os.path.join(RUNTIME, "p3", "payment_reconciliation_downstream.sqlite3")
BUSINESS_RAW = "/Volumes/share/03_资料库/MetaData/KMFA_MetaData/财务/一级原始数据/业务原始"

RECEIVABLE_MIN = Decimal("100000")
RECEIVABLE_DAYS = 180


def D(x):
    try:
        return Decimal(str(x or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def money(x):
    return f"{x:,.2f}"


def _conn(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def _snapshots(db):
    return [r[0] for r in db.execute(
        "SELECT source_md5 FROM approval GROUP BY source_md5 "
        "ORDER BY MAX(ingested_at) DESC, MAX(source_file) DESC")]


# ---------------------------------------------------------------- 1 重复报销
def dup_reimbursement(db):
    """同收款方 + 同金额 + 7 天内 + 费用说明相同 + 组内已支付 ≥2 笔。

    2026-09-09 出纳杨婷推翻了旧口径的两组：
      · 0959/0960 知识产权保护中心 135 元 —— 0959 未支付、0960 全部支付，
        银行只付了一次。所以「已支付 ≥2 笔」是硬条件。
      · 1402/1403 武汉科信达 1250 元 —— 一笔湖北曦悦、一笔武汉彤烨代账费。
        这两条的 payment_content 都是空的，数据里没有区分依据，
        所以「费用说明非空且相同」也是硬条件：判不了就不报。
    """
    snaps = _snapshots(db)
    if not snaps:
        return "unavailable", [], "approval 表没有任何快照"
    rows = [dict(r) for r in db.execute(
        "SELECT payment_id, application_date, requested_amount, payment_status,"
        "       payee_account, payment_content, creator"
        "  FROM approval WHERE source_md5=? AND payee_account<>''"
        "    AND TRIM(COALESCE(payment_content,''))<>''", (snaps[0],))]
    paid = lambda s: bool(s) and "支付" in s and s != "未支付"
    key = {}
    for r in rows:
        key.setdefault((r["payee_account"], D(r["requested_amount"]), r["payment_content"]), []).append(r)
    out = []
    for (acct, amt, content), grp in key.items():
        if len(grp) < 2:
            continue
        grp.sort(key=lambda r: r["application_date"] or "")
        for i in range(len(grp) - 1):
            a, b = grp[i], grp[i + 1]
            if not (a["application_date"] and b["application_date"]):
                continue
            try:
                gap = (dt.date.fromisoformat(b["application_date"][:10])
                       - dt.date.fromisoformat(a["application_date"][:10])).days
            except ValueError:
                continue
            if gap > 7:
                continue
            if not (paid(a["payment_status"]) and paid(b["payment_status"])):
                continue          # 只真付了一笔 → 撤回重报，不是重复
            ids = "/".join(sorted([a["payment_id"], b["payment_id"]]))
            out.append({
                "check_id": "dup_reimbursement",
                "fingerprint": f"dup:{acct}:{amt}:{ids}",
                "amount": amt * 2,
                "line": f"{acct[:22]} {money(amt)} ×2 {a['application_date']} 单号 {ids}",
                "detail": {"payee": acct, "amount": str(amt), "ids": ids, "content": content[:60]},
            })
    return ("hit" if out else "clear"), out, ""


# ---------------------------------------------------------------- 2 金额被改
def amount_changed(db):
    """两份导出快照之间，同一单号的**申请金额**被改了。

    旧口径拿「申请支付金额 vs 实际支付金额」作差，是错的：
    实际支付金额是「已付了多少」，未支付就是 0、部分支付就小于申请额，
    1268 行里 83 行会无脑命中。2026-09-11 实测，按正确口径命中 0。
    """
    snaps = _snapshots(db)
    if len(snaps) < 2:
        return "unavailable", [], "只有一份快照，无从比对（需要两次不同日期的全历史导出）"
    new = {r["payment_id"]: dict(r) for r in db.execute(
        "SELECT payment_id, requested_amount, approval_status, creator, payment_content"
        "  FROM approval WHERE source_md5=?", (snaps[0],))}
    old = {r["payment_id"]: dict(r) for r in db.execute(
        "SELECT payment_id, requested_amount FROM approval WHERE source_md5=?", (snaps[1],))}
    out = []
    for pid, n in new.items():
        o = old.get(pid)
        if not o:
            continue
        was, now = D(o["requested_amount"]), D(n["requested_amount"])
        if abs(now - was) <= Decimal("0.01"):
            continue
        out.append({
            "check_id": "amount_changed",
            "fingerprint": f"amt:{pid}:{was}:{now}",
            "amount": abs(now - was),
            "line": f"{pid} {n.get('creator') or '?'} {money(was)} → {money(now)}",
            "detail": {"payment_id": pid, "was": str(was), "now": str(now)},
        })
    return ("hit" if out else "clear"), out, ""


# ---------------------------------------------------------------- 3 钱没转出去
def transfer_failed(db3):
    """银行回单状态是「交易失败」的明细。

    杨婷 09-09 答复：现有 6 笔全部是「账号错误没付出去，X 月 X 日已重新支付」。
    本系统查不到那些补付 —— transfer 只有 313 行 / 23 个批次，补付所在的批次
    回单没归档进来。所以**不自证补付**，靠台账结清：她答过的永不再报。
    """
    rows = [dict(r) for r in db3.execute(
        "SELECT source_md5, source_row, payee_name, payee_account, amount, transaction_time, purpose"
        "  FROM transfer WHERE transaction_status='交易失败'")]
    blind = db3.execute(
        "SELECT COUNT(*) FROM transfer WHERE COALESCE(transaction_status,'')=''").fetchone()[0]
    out = []
    for r in rows:
        amt = D(r["amount"])
        tail = (r["payee_account"] or "")[-4:]
        out.append({
            "check_id": "transfer_failed",
            "fingerprint": f"fail:{r['payee_name']}:{amt}:{(r['transaction_time'] or '')[:10]}",
            "amount": amt,
            "line": f"{r['payee_name']} {money(amt)} 尾号{tail} {(r['transaction_time'] or '')[:10]}",
            "detail": {"payee": r["payee_name"], "amount": str(amt),
                       "time": r["transaction_time"], "purpose": (r["purpose"] or "")[:40]},
        })
    note = f"另有 {blind} 笔回单是老格式没有状态栏，查不了" if blind else ""
    return ("hit" if out else "clear"), out, note


# ---------------------------------------------------------------- 4 同日重付
def same_day_duplicate(db3):
    """同一个人、同一天、同一金额，**且在同一个批次里**付了两遍。

    杨婷 09-09 推翻了旧口径：张红 1505×2、汪松涛 1085×2 都在 2026-02-06，
    但一笔是江西赣锋工资（单号 20260206-0289）、一笔是池州恒鑫工资
    （20260205-0281），分属两个批次。一人跨多项目发工资是常态，
    所以「同一批次」是硬条件。2026-09-11 实测，按正确口径命中 0。
    """
    rows = [dict(r) for r in db3.execute(
        "SELECT source_md5, payee_name, amount, transaction_time"
        "  FROM transfer WHERE transaction_status='交易成功'")]
    key = {}
    for r in rows:
        k = (r["source_md5"], r["payee_name"], D(r["amount"]), (r["transaction_time"] or "")[:10])
        key.setdefault(k, []).append(r)
    out = []
    for (md5, name, amt, day), grp in key.items():
        if len(grp) < 2 or not day:
            continue
        out.append({
            "check_id": "same_day_duplicate",
            "fingerprint": f"same:{md5}:{name}:{amt}:{day}",
            "amount": amt * len(grp),
            "line": f"{name} {money(amt)} ×{len(grp)} {day}（同一批次内）",
            "detail": {"payee": name, "amount": str(amt), "date": day, "times": len(grp)},
        })
    return ("hit" if out else "clear"), out, ""


# ---------------------------------------------------------------- 5 审批状态倒退
def status_regressed(db):
    """两份快照之间，审批状态从「审批中/已通过」倒退成「已驳回/已撤销」。

    旧口径报「驳回停滞 N 天」是算不出来的：导出表里根本没有驳回日期这一列
    （表头只有 申请日期 / 支付日期），上次那个「停了 24 天」就是拿申请日期
    冒充驳回日期算出来的。所以这里只报**状态发生倒退**这个可证的事实，不报天数。
    """
    snaps = _snapshots(db)
    if len(snaps) < 2:
        return "unavailable", [], "只有一份快照，无从比对"
    BAD = {"已驳回", "已撤销"}
    new = {r["payment_id"]: dict(r) for r in db.execute(
        "SELECT payment_id, approval_status, requested_amount, creator, payment_content"
        "  FROM approval WHERE source_md5=?", (snaps[0],))}
    old = {r["payment_id"]: r["approval_status"] for r in db.execute(
        "SELECT payment_id, approval_status FROM approval WHERE source_md5=?", (snaps[1],))}
    out = []
    for pid, n in new.items():
        was = old.get(pid)
        if was is None or n["approval_status"] not in BAD or was in BAD:
            continue
        amt = D(n["requested_amount"])
        out.append({
            "check_id": "status_regressed",
            "fingerprint": f"reg:{pid}:{was}->{n['approval_status']}",
            "amount": amt,
            "line": f"{pid} {n.get('creator') or '?'} {money(amt)} {was} → {n['approval_status']}",
            "detail": {"payment_id": pid, "was": was, "now": n["approval_status"]},
        })
    return ("hit" if out else "clear"), out, ""


# ---------------------------------------------------------------- 6 客户欠款
# 归档按上海月份写到 业务原始/<YYYYMM>/红圈/<对象>/。2026-09-11 查实旧写法错在两处：
# 月份目录写死（10 月起会永远读 9 月）；按文件名字典序取最后一个——「红圈主合同 2026-09-09.xlsx」
# 排在「20260911_红圈主合同_…_任务303902702477.xlsx」后面（汉字大于数字），读到的是两天前的主合同。
# 所以：跨月份目录扫；日期只从文件名取（先去掉归档撞名时加的 md5 后缀，按日期区间导出的只是一部分数据、不算）；
# 最新那天的件打不开就退到前一天；同一天几份按工作簿自带生成时间（换成 UTC）比，有一份读不到就改按任务号。
# 共享盘 mtime 不可信，一律不看。
_NAME_DATE8 = re.compile(r"(?<!\d)(20[12]\d)(\d{2})(\d{2})(?!\d)")
_NAME_DATE10 = re.compile(r"(?<!\d)(20[12]\d)-(\d{2})-(\d{2})(?!\d)")
_NAME_TASK = re.compile(r"任务(\d+)")
_MD5_SUFFIX = re.compile(r"_[0-9a-f]{12}(?=\.xlsx$)")
_DATE_RANGE = re.compile(r"(?<!\d)20[12]\d{5}至20[12]\d{5}(?!\d)")
_CORE_CREATED = re.compile(r"<dcterms:created[^>]*>\s*([^<\s]+)\s*<")
_W3CDTF = re.compile(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?$")
CORE_XML_MAX_BYTES = 64 * 1024


def name_date(name):
    """文件名里最晚的日期（20260911 或 2026-09-11）。

    先去掉归档撞名时加的 `_<md5前12位>` 后缀——它可能碰巧长得像日期（`_20261231abcd`）；
    数字串必须独立成段，任务号里截不出日期。
    """
    name = _MD5_SUFFIX.sub("", name)
    days = []
    for pattern in (_NAME_DATE8, _NAME_DATE10):
        for y, m, d in pattern.findall(name):
            try:
                days.append(dt.date(int(y), int(m), int(d)))
            except ValueError:
                pass
    return max(days) if days else None


def _readable_workbook(path):
    """zip 完整、确实是工作簿才参与排序；PK 开头但写到一半的件跳过，好让更早的可读件顶上。"""
    try:
        with zipfile.ZipFile(path) as book:
            return "xl/workbook.xml" in book.namelist()
    except Exception:
        return False


def _created_utc(path):
    """工作簿自己记的生成时间（docProps/core.xml 的 dcterms:created）换算成 UTC；读不到、太大或不认识返回 None。"""
    try:
        with zipfile.ZipFile(path) as book:
            info = book.getinfo("docProps/core.xml")
            if info.file_size > CORE_XML_MAX_BYTES:
                return None
            text = book.read(info).decode("utf-8", "ignore")
    except Exception:          # 截断的 zip 会抛 zlib.error、EOFError 等，一律当读不到
        return None
    found = _CORE_CREATED.search(text)
    stamp = _W3CDTF.match(found.group(1)) if found else None
    if not stamp:
        return None
    y, mo, d, h, mi, sec, frac, zone = stamp.groups()
    try:
        moment = dt.datetime(int(y), int(mo), int(d), int(h), int(mi), int(sec or 0),
                             int(round(float(frac) * 1_000_000)) if frac else 0)
    except ValueError:
        return None
    if zone and zone != "Z":
        sign = 1 if zone[0] == "+" else -1
        moment -= sign * dt.timedelta(hours=int(zone[1:3]), minutes=int(zone[4:6]))
    return moment


def latest_hongquan(obj, must_contain="", root=None):
    """业务原始/*/红圈/<obj>/ 里最新的一份完整导出；一份都没有返回 None。"""
    root = root or BUSINESS_RAW
    try:
        months = sorted(os.listdir(root))
    except OSError:
        return None
    ranked = []
    for month in months:
        folder = os.path.join(root, month, "红圈", obj)
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in names:
            if (name.startswith("._") or not name.endswith(".xlsx") or must_contain not in name
                    or _DATE_RANGE.search(name)):
                continue
            day = name_date(name)
            if day is None:
                continue
            task = _NAME_TASK.search(name)
            ranked.append((day, int(task.group(1)) if task else -1, os.path.join(folder, name)))
    for day in sorted({day for day, _, _ in ranked}, reverse=True):
        same_day = [(task, path) for d, task, path in ranked if d == day and _readable_workbook(path)]
        if not same_day:
            continue                                   # 这一天的件全坏：退到前一天的可读件
        if len(same_day) == 1:
            return same_day[0][1]
        stamped = [(_created_utc(path), task, path) for task, path in same_day]
        if all(created is not None for created, _, _ in stamped):
            return max(stamped)[2]
        return max((task, created or dt.datetime.min, path) for created, task, path in stamped)[2]
    return None


def receivable_stalled(receipt_path=None, contract_path=None, today=None):
    """合同余额 ≥10 万、且末次收款已超 180 天。

    欠款方名字必须解得出来才报。2026-09-11 实测：收款登记的「付款单位」
    有 71.8% 的行是空的，按行取必然取到空 —— 旧口径报出来的
    「73 个欠款方未登记」全是本系统自己没 join 的锅，人家早登记了。
    正确做法：按合同编号聚合取任一非空；再取不到就 join 主合同的「甲方」；
    还取不到就**剔除出正文**，只在诊断行计数。绝不把自己的解析缺口当成别人的问题。
    """
    today = today or dt.date.today()
    receipt = receipt_path or latest_hongquan("收款登记", "全历史导出")
    contract = contract_path or latest_hongquan("主合同")
    if not receipt:
        return "unavailable", [], "找不到红圈收款登记全历史导出"

    h, rows = read_sheet(receipt)
    m = column_map(h, ["收款编号", "付款单位", "收款日期", "剩余未收款金额", "合同编号", "合同名称"])
    need = {"收款编号", "付款单位", "收款日期", "剩余未收款金额", "合同编号"}
    if not need <= set(m):
        return "unavailable", [], f"收款登记缺列：{sorted(need - set(m))}"

    party = {}
    if contract:
        hc, rc = read_sheet(contract)
        mc = column_map(hc, ["合同编号", "甲方"])
        if {"合同编号", "甲方"} <= set(mc):
            for r in rc:
                k, v = r.get(mc["合同编号"], "").strip(), r.get(mc["甲方"], "").strip()
                if k and v:
                    party[k] = v

    groups = {}
    for r in rows:
        k = r.get(m["合同编号"], "").strip()
        if not k:
            continue
        g = groups.setdefault(k, {"payers": set(), "last": "", "seq": "", "bal": None, "name": ""})
        p = r.get(m["付款单位"], "").strip()
        if p:
            g["payers"].add(p)
        d = r.get(m["收款日期"], "").strip()
        if d > g["last"]:
            g["last"] = d
        sq = r.get(m["收款编号"], "")
        if sq > g["seq"]:                      # 收款编号编码录入顺序，最后一条才是当前余额
            g["seq"] = sq
            g["bal"] = D(r.get(m["剩余未收款金额"], "0"))
        if not g["name"]:
            g["name"] = r.get(m.get("合同名称", ""), "").strip()

    out, excluded = [], 0
    for k, g in groups.items():
        if g["bal"] is None or g["bal"] < RECEIVABLE_MIN or not g["last"]:
            continue
        try:
            last = dt.date.fromisoformat(g["last"][:10])
        except ValueError:
            continue
        days = (today - last).days
        if days < RECEIVABLE_DAYS:
            continue
        name = (sorted(g["payers"])[0] if g["payers"] else "") or party.get(k, "")
        if not name:
            excluded += 1
            continue                            # 解不出名字就不报
        out.append({
            "check_id": "receivable_stalled",
            "fingerprint": f"recv:{k}",   # 只按合同：余额变动不算新事件，宁可少报
            "amount": g["bal"],
            "line": f"{name} 欠 {money(g['bal'])} 末次收款 {g['last'][:10]}（{days} 天）",
            "detail": {"contract": k, "party": name, "balance": str(g["bal"]),
                       "last": g["last"][:10], "days": days},
        })
    out.sort(key=lambda x: -x["amount"])
    note = f"另有 {excluded} 个合同因本系统未能解析欠款方已排除" if excluded else ""
    return ("hit" if out else "clear"), out, note


RECEIVABLE_MAJOR = Decimal("500000")     # 高价值线：欠 50 万以上的 9 家占了总额一半


def receivable_major(receipt_path=None, contract_path=None, today=None):
    """按欠款方合并的高价值长期欠款。

    老板 2026-09-11：「不是不进，是要高价值的进。」

    为什么按客户不按合同：同一家跨多个合同 —— 青海发投碱业 17 个、
    日照钢铁 3 个、山东鲁泰 4 个。按合同报会把一家拆成十几条刷屏，
    而且老板追的是这家客户，不是合同编号。

    为什么是 50 万：实测 92 个合同归到 60 家，欠 50 万以上的 9 家
    合计 1,164 万，占总额 23,071,351.64 的一半。再往下放到 30 万就是 22 家，
    一次报 22 家等于没有重点。

    首报制照旧按欠款方发指纹：报过一次就不再重复，除非这家的欠款
    又涨过一个 50 万台阶（台阶写进指纹，涨了才算新事件）。
    """
    status, rows, upstream_note = receivable_stalled(receipt_path, contract_path, today)
    if status not in ("hit", "clear"):
        return status, [], upstream_note

    by_party = {}
    for r in rows:
        d = r["detail"]
        g = by_party.setdefault(d["party"], {"amt": Decimal(0), "n": 0, "days": 0, "last": ""})
        g["amt"] += Decimal(d["balance"])
        g["n"] += 1
        if d["days"] > g["days"]:
            g["days"], g["last"] = d["days"], d["last"]

    out = []
    for party, g in by_party.items():
        if g["amt"] < RECEIVABLE_MAJOR:
            continue
        step = int(g["amt"] // RECEIVABLE_MAJOR)      # 涨过一个台阶才算新事件
        span = f"{g['n']} 个合同" if g["n"] > 1 else "1 个合同"
        out.append({
            "check_id": "receivable_major",
            "fingerprint": f"recvmajor:{party}:{step}",
            "amount": g["amt"],
            "line": f"{party} 欠 {money(g['amt'])}（{span}），最久一笔 {g['last']} 收到钱",
            "detail": {"party": party, "balance": str(g["amt"]),
                       "contracts": g["n"], "days": g["days"], "last": g["last"]},
        })
    out.sort(key=lambda x: -x["amount"])
    small = len(by_party) - len(out)
    # 诊断分行写：钉钉里每条独占一行（单个 \n 会被吃掉，要空行分段）
    note_lines = [
        f"另有 {small} 家欠款不足 {RECEIVABLE_MAJOR:,.0f}",
        f"全部 {len(rows)} 个合同合计 {money(sum(Decimal(r['detail']['balance']) for r in rows))}",
    ]
    # 上游因解析不出欠款方而剔除的合同必须留在诊断行里，不能在合并这一步悄悄丢掉
    if upstream_note:
        note_lines.append(upstream_note)
    note = "\n\n".join(note_lines)
    return ("hit" if out else "clear"), out, note


# ---------------------------------------------------------------- 汇总
CHECKS = [
    ("dup_reimbursement", "同收款方、同金额、同事由，7 天内报了两次"),
    ("amount_changed", "申请交上去以后金额被改过"),
    ("transfer_failed", "钱没转出去"),
    ("same_day_duplicate", "同一天给同一个人转了两遍"),
    ("status_regressed", "审批状态倒退成驳回或撤销"),
    ("receivable_stalled", "客户欠款半年以上没再收到钱（余额 10 万以上）"),
    ("receivable_major", "大额客户欠款（按客户合并，欠 50 万以上）"),
]


def run_all(today=None):
    results = {}
    try:
        db2 = _conn(P2)
    except FileNotFoundError as e:
        db2 = None
        err2 = str(e)
    try:
        db3 = _conn(P3)
    except FileNotFoundError as e:
        db3 = None
        err3 = str(e)

    def guard(cid, fn):
        try:
            st, items, note = fn()
        except Exception as exc:                       # 一项炸了不许拖垮其余五项
            st, items, note = "error", [], f"{type(exc).__name__}: {exc}"
        results[cid] = {"status": st, "items": items, "note": note}

    guard("dup_reimbursement", lambda: dup_reimbursement(db2) if db2 else ("unavailable", [], err2))
    guard("amount_changed", lambda: amount_changed(db2) if db2 else ("unavailable", [], err2))
    guard("transfer_failed", lambda: transfer_failed(db3) if db3 else ("unavailable", [], err3))
    guard("same_day_duplicate", lambda: same_day_duplicate(db3) if db3 else ("unavailable", [], err3))
    guard("status_regressed", lambda: status_regressed(db2) if db2 else ("unavailable", [], err2))
    guard("receivable_stalled", lambda: receivable_stalled(today=today))
    guard("receivable_major", lambda: receivable_major(today=today))
    return results


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--today")
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.today) if a.today else None
    res = run_all(today)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, default=str))
        return 0
    healthy = [c for c in res.values() if c["status"] in ("hit", "clear")]
    broken = [c for c in res.values() if c["status"] in ("error", "unavailable")]
    for cid, title in CHECKS:
        r = res[cid]
        n = len(r["items"])
        tot = sum((i["amount"] for i in r["items"]), Decimal("0"))
        print(f"{r['status']:<12} {cid:<20} {n:>4} 条  {money(tot):>18}  {title}")
        if r["note"]:
            print(f"{'':<12} └ {r['note']}")
    if not healthy:
        print("CHECKS_FAILED 六项全部不可用")
        return 2
    print(f"CHECKS_OK healthy={len(healthy)} broken={len(broken)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
