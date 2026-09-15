"""生产部出勤累计：越线通知（事件式）+ 月报（每周一）。

两条报文共用一次取数。写作纪律跟日报一致，另加一条硬的：
**报文里不出现「加班」「工时」「小时」。** 说时长等于书面记录公司自己的用工强度，
压力给到公司而不是员工；这条线要的是「谁该调休、谁该守打卡纪律」。
闸在 runtime.banned_words()，投递前拦，不靠写文案的人自觉。
"""
from __future__ import annotations
import datetime
from collections import defaultdict

# 钉钉考勤报表的字段 id（`dws attendance report columns` 查得到）。
# 只取这六个：出勤天数是门槛判据，其余四个是打卡纪律，应出勤用来认「在不在考勤组」。
COLS = {
    "6593377": "出勤", "6593375": "应出勤",
    "6593380": "迟到", "6593387": "上缺", "6593388": "下缺", "186335133": "补卡",
}

def dept_members(dws, root_name: str) -> dict:
    """部门全口径（含所有下级）→ {姓名: (uid, 所在组)}。

    生产部下面还挂着车工组 / 焊工组 / 钳工组 / 调度组 / 车间组 / 司机组 /
    青海·山东·新疆项目组等，只查生产部本级会漏掉一多半人。
    """
    root = None
    for x in (dws.json(["contact", "dept", "list-children", "--dept", "1"]) or {}).get("result") or []:
        if x.get("deptName") == root_name:
            root = x["deptId"]
    if root is None:
        raise RuntimeError(f"通讯录顶层找不到「{root_name}」部门")
    out, seen, queue = {}, set(), [(root, root_name)]
    while queue:
        did, dname = queue.pop(0)
        if did in seen:
            continue
        seen.add(did)
        for x in (dws.json(["contact", "dept", "list-children", "--dept", str(did)]) or {}).get("result") or []:
            queue.append((x["deptId"], x["deptName"]))
        def harvest(o):
            if isinstance(o, dict):
                uid = o.get("userid") or o.get("userId")
                if o.get("name") and uid:
                    out[o["name"]] = (str(uid), dname)
                for v in o.values():
                    harvest(v)
            elif isinstance(o, list):
                for v in o:
                    harvest(v)
        harvest(dws.json(["contact", "dept", "list-members", "--depts", str(did)]))
    return out

def _day_of(wd) -> str:
    """两个接口的 workDate 形状不一样：report query-data 给 "2026-08-01"，
    attendance check result 给 epoch 毫秒。两种都要认。"""
    if isinstance(wd, str):
        return wd[:10]
    return datetime.datetime.fromtimestamp(int(wd) / 1000).strftime("%Y-%m-%d")

def fetch(dws, uids: list, start: str, end: str) -> tuple:
    """返回 (逐日出勤 {uid: {day: 天数}}, 月累计 {uid: {字段: 合计}})。

    每批都核行数 = 人数 × 天数。少一行就抛 —— 钉钉网关是阵发性失败，
    而缺行的后果是「他这个月没越线」「他一次卡都没打」，两种都是错的结论，
    而且看起来完全正常。**宁可这一轮不出报。**
    query-data 一次最多 20 人、跨度不超过 32 天，这是接口的硬限制。
    """
    days = (datetime.date.fromisoformat(end) - datetime.date.fromisoformat(start)).days + 1
    rows = []
    for i in range(0, len(uids), 20):
        batch = uids[i:i + 20]
        got = (dws.json(["attendance", "report", "query-data",
                         "--users", ",".join(batch), "--columns", ",".join(COLS),
                         "--start", f"{start} 00:00:00", "--end", f"{end} 23:59:59"])
               or {}).get("result") or []
        if len(got) != len(batch) * days:
            raise RuntimeError(f"考勤报表行数不对：拿到 {len(got)}，应为 {len(batch)} 人 × {days} 天"
                               f" = {len(batch) * days}。数据不全，本轮不出报")
        rows += got
    daily, agg = defaultdict(dict), defaultdict(lambda: defaultdict(float))
    for x in rows:
        u = x["userId"]
        for v in x["values"]:
            name = COLS.get(v["termId"])
            if not name:
                continue
            try:
                f = float(v["value"])
            except (TypeError, ValueError):
                continue
            agg[u][name] += f
            if name == "出勤":
                daily[u][_day_of(x["workDate"])] = f
    return daily, agg

def crossings(daily: dict, threshold: float) -> dict:
    """{uid: 越线那一天}。

    判的是「跨过去」这个动作，不写死任何数字：
        昨天累计 <= 门槛  且  今天累计 > 门槛  →  今天越线
    半天班（钉钉记 0.5 天）、补录、数据跳一格都不会让它失灵；
    门槛换成别的数，或者按当月天数浮动，这里一个字都不用改。
    """
    out = {}
    for u, days in daily.items():
        prev = 0.0
        for d in sorted(days):
            cur = prev + days[d]
            if prev <= threshold < cur:
                out[u] = d
                break
            prev = cur
    return out

def render_cross(day: str, names: list, month_total: int, headcount: int,
                 threshold: float) -> tuple:
    """越线通知。

    一人一行，不把二十个名字塞进一个段落 —— 挤成一片谁都看不下去。
    每人只印姓名和组：越线当天所有人的出勤天数必然一样，印出来没有区分度；
    要人做的事只有一件，安排调休。
    """
    thr = f"{threshold:g}"
    title = f"考勤 {day} · 出勤超 {thr} 天 {len(names)} 人"
    lines = [f"考勤 {day} ｜ 生产部本月出勤已超 {thr} 天", f"{len(names)} 人", ""]
    lines += [f"· {n}（{g}）" for n, g in names]
    lines += ["", "→ 请合理安排休息与调休", "",
              f"生产部在册 {headcount} 人 · 本月累计 {month_total} 人",
              "同一个人本月不再重复通知"]
    return title, "\n".join(lines)

def _名次(pairs) -> str:
    return "3 次以上：" + ("、".join(f"{n} {int(v)} 次" for n, v in pairs) if pairs else "无")

def render_month(month: str, rows: list, threshold: float) -> tuple:
    """月报。rows = [(姓名, 组, 累计字段 dict)]，只含在考勤组里的人。

    一人一行。上一版把二十个人挤成三行长句，手机上就是一堵墙。
    """
    thr = f"{threshold:g}"
    over = sorted([r for r in rows if r[2]["出勤"] > threshold], key=lambda z: (-z[2]["出勤"], z[1], z[0]))
    late = sorted([(r[0], r[2]["迟到"]) for r in rows if r[2]["迟到"] >= 3], key=lambda z: -z[1])
    miss = sorted([(r[0], r[2]["上缺"] + r[2]["下缺"]) for r in rows
                   if r[2]["上缺"] + r[2]["下缺"] >= 3], key=lambda z: -z[1])
    fix  = sorted([(r[0], r[2]["补卡"]) for r in rows if r[2]["补卡"] >= 3], key=lambda z: -z[1])
    zero = [r for r in rows if r[2]["出勤"] == 0]
    y, m = month.split("-")
    lines = [f"考勤月报 {y} 年 {int(m)} 月", f"生产部在册 {len(rows)} 人", "",
             f"本月出勤超 {thr} 天 {len(over)} 人", "→ 请合理安排休息与调休", ""]
    lines += [f"· {n}（{g}）{int(a['出勤'])} 天" for n, g, a in over]
    lines += ["", "打卡纪律（本月累计）", ""]
    lines += [f"· 迟到 {_名次(late)}", f"· 缺卡 {_名次(miss)}", f"· 补卡 {_名次(fix)}"]
    for n, g, a in zero:
        # 应出勤不为 0 说明他在考勤组里、系统认为他该打卡，而他一次都没打。
        lines += ["", f"· {n} 本月人员表天天在场、钉钉一次卡都没打",
                  "  → 综合部核实在岗与打卡状态 · 本周内"]
    return f"考勤月报 {y}-{m} · 生产部 {len(rows)} 人", "\n".join(lines)
