"""生产部周报：连续在岗 + 在岗待核实 + 打卡规范。每周一一条。

写作纪律，两条硬的：

**唯一分组口径是人员表的「项目名称」列。**
钉钉考勤组的地点是滞后的 —— 实测 2026-09-14：有人钉钉考勤组挂在 A 现场，
人员表上人却在 B 现场，两地相隔数千公里。钉钉部门（车工组 / 焊工组…）也不用，
班组解决不了跨项目的排休，项目经理才能。混两个口径等于没有口径。

**报文里不做事实认定，只下排班指令。**
不出现「加班」「工时」「小时」「劳动法」等 15 个词（闸在 runtime.banned_words），
也不逐人印天数 —— 门槛写在开头一句话里，谁在名单上、为什么在，一看就懂；
把天数贴在每个人名字后面，就从「排班待办」变成了「用工强度记录」。
闸在投递前拦，不靠写文案的人自觉。
"""
from __future__ import annotations
import datetime
from collections import defaultdict
from pathlib import Path

from . import collect, extract, roster

# 钉钉考勤报表字段 id（`dws attendance report columns` 查得到）。
# 出勤/应出勤是判据，迟到/缺卡/补卡是打卡规范，审批单用来区分「请假」和「失联」。
COLS = {
    "6593377": "出勤", "6593375": "应出勤",
    "6593380": "迟到", "6593387": "上缺", "6593388": "下缺", "186335133": "补卡",
    "6593411": "审批单",
}

ONSITE = "厂内"           # 人员表上项目名为空 = 人在厂里

# 分隔线不能用 markdown 的 `---`。
# 钉钉把发出去的 `\n\n` 规范化成 `  \n`（行尾两空格 + 换行），于是 `---` 总是
# **紧跟**在上一行后面 —— 而 markdown 里 `文字\n---` 是 setext 二级标题的写法，
# 上一行会被整行渲染成大标题。实测：最后一个项目行「XX项目 某某」被吃成了 H2。
# U+2500 制表符不参与任何 markdown 语法，画出来就是一条线。
RULE = "──────────"

def dept_members(dws, root_name: str) -> dict:
    """部门全口径（含所有下级）→ {姓名: (uid, 所在组)}。

    生产部下面挂着车工组 / 焊工组 / 钳工组 / 调度组 / 车间组 / 司机组 /
    青海·山东·新疆项目组等，只查本级会漏掉一多半人。
    每轮都重新拉，一行名单都不缓存 —— 入职、离职、调岗、转外派全自动跟上。
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

def fetch(dws, uids: list, start: str, end: str) -> dict:
    """{uid: {日期: {字段: 值}}}。每批都核行数 = 人数 × 天数。

    少一行就抛。钉钉网关是阵发性失败（实测 20 次里 11 次返回空而 errorCode 为 null），
    而缺行的后果是「他这一段休过」「他没有零打卡」，两种都是错的结论，
    而且看起来完全正常。**宁可这一轮不出报。**
    query-data 一次最多 20 人、跨度不超过 32 天，这是接口的硬限制 ——
    也正好是本报需要的窗口，所以永远只有一个分片。
    """
    days = (datetime.date.fromisoformat(end) - datetime.date.fromisoformat(start)).days + 1
    if days > 32:
        raise ValueError(f"取数窗口 {days} 天超过接口上限 32 天")
    out: dict = defaultdict(dict)
    for i in range(0, len(uids), 20):
        batch = uids[i:i + 20]
        got = (dws.json(["attendance", "report", "query-data",
                         "--users", ",".join(batch), "--columns", ",".join(COLS),
                         "--start", f"{start} 00:00:00", "--end", f"{end} 23:59:59"])
               or {}).get("result") or []
        if len(got) != len(batch) * days:
            raise RuntimeError(f"考勤报表行数不对：拿到 {len(got)}，应为 {len(batch)} 人 × {days} 天"
                               f" = {len(batch) * days}。数据不全，本轮不出报")
        for x in got:
            cell = {}
            for v in x["values"]:
                name = COLS.get(v["termId"])
                if name:
                    cell[name] = v["value"]
            out[x["userId"]][_day_of(x["workDate"])] = cell
    return out

def _is(v) -> bool:
    return str(v) in ("1", "1.0")

def streak(rec: dict, end: str) -> int:
    """截至 end 的连续到岗天数。休一天即归零。

    只判「够不够门槛」，不对外报数字，所以取数窗口只要比门槛长就够：
    32 天窗口和 180 天窗口算出来的名单实测完全一致，而调用次数是 2 次对 12 次。
    """
    c = 0
    d = datetime.date.fromisoformat(end)
    while _is((rec.get(d.isoformat()) or {}).get("出勤")):
        c += 1
        d -= datetime.timedelta(days=1)
    return c

def zero_run(rec: dict, end: str) -> int:
    """在册（应出勤=1）却一次卡都没打的连续天数。"""
    c = 0
    d = datetime.date.fromisoformat(end)
    while True:
        cell = rec.get(d.isoformat()) or {}
        if not _is(cell.get("应出勤")) or _is(cell.get("出勤")):
            return c
        c += 1
        d -= datetime.timedelta(days=1)

def leave_filed(rec: dict, end: str, run: int) -> bool:
    """这段零打卡里走没走过请假流程。

    「补卡申请」不算 —— 那是补打卡，不是请假。走了流程的人不该被点名核实，
    点了就是误命中，误命中一次这条线的权威性就没了。
    """
    d = datetime.date.fromisoformat(end) - datetime.timedelta(days=run - 1)
    for _ in range(run):
        a = ((rec.get(d.isoformat()) or {}).get("审批单") or "").strip()
        if a and "补卡" not in a:
            return True
        d += datetime.timedelta(days=1)
    return False

def _projects_on(dws, cfg, day: str, wd: Path, people: dict) -> dict:
    """某一天的人员表 → {姓名: 项目}。取不到或读不准就返回空。

    姓名一律过 roster 仲裁 —— OCR 会把同音近形的姓名认错。
    仲裁返回 采信 / 修正 / 不可信 / 不在册，只有前两种带回姓名。
    """
    imgs = collect.find_table_images(dws, cfg.group_id, cfg.publishers, day, wd)
    if not imgs:
        return {}
    tab = extract.extract(str(imgs[0]))
    if not tab["类别可信"]:
        return {}
    out = {}
    for row in tab["行"]:
        if extract.is_outsourced(row) or row["类别"] == "休息人员":
            continue
        proj = " ".join((row["项目"] or "").split()) or ONSITE
        for p in row["人员"]:
            verdict, name, _ = roster.arbitrate(p["候选"], people)
            if verdict in ("采信", "修正") and name:
                out.setdefault(name, proj)
    return out

def project_map(dws, cfg, end_day: str, wd: Path, people: dict,
                need: set, back: int = 5) -> tuple:
    """{姓名: 项目} 和取到表的日期。

    从业务日往回找。周报跑在周一，业务日是周日，那天没有人员表，
    所以必须能回溯到周五 —— back 至少要 3 才够，给到 5 是留节假日的余量。
    **名单里的人全部有项目就停**，常态只解析一张表（实测一张 18 秒）。
    """
    got, days = {}, []
    d = datetime.date.fromisoformat(end_day)
    for _ in range(back):
        m = _projects_on(dws, cfg, d.isoformat(), wd, people)
        if m:
            days.append(d.isoformat())
            for k, v in m.items():
                got.setdefault(k, v)
        if need and all(n in got for n in need):
            break
        d -= datetime.timedelta(days=1)
    return got, days

def _order(proj: str, n: int) -> tuple:
    """厂内排最后，其余按人数降序 —— 外派现场排前面，那才是要协调的。"""
    return (proj == ONSITE, -n, proj)

def render(monday: str, bizday: str, roll: list, pending: list, discipline: list,
           threshold: int, prev: set | None, weeks: dict, degraded: str = "") -> tuple:
    """roll / pending = [(姓名, 项目)]；discipline = [(标签, [(姓名, 次数)])]。

    层次全部用 markdown 自己的东西：`**粗体**` 小标题、`---` 分割线。
    钉钉 markdown 里换行只认空行，空白行表达不了「间隔」—— 它就是换行本身，
    靠它排版必然糊（2026-09-15 栽过两次，见 report.dingtalk 的注释）。
    """
    md = datetime.date.fromisoformat(monday)
    bd = datetime.date.fromisoformat(bizday)
    L = [f"**生产部 · 连续在岗周报　{md.month} 月 {md.day} 日**", RULE]
    if not roll:
        L.append(f"本周无人连续到岗满 {threshold} 天。")
    else:
        names = {n for n, _ in roll}
        # 动作写成「结合现场进度择机安排」，不写成「本周请安排」：
        # 现场停不下来是常态，一条每周都下、每周都做不到的指令，累计出来的
        # 是一份「自己提了、自己没做」的记录 —— 对公司只有坏处。
        # 时机交给项目负责人，名单本身才是这条周报的产出。
        L.append(f"以下 **{len(roll)} 人**连续到岗已满 {threshold} 天，"
                 f"请项目负责人结合现场进度择机安排休息。"
                 f"休满 1 天即自动移出名单。")
        if prev is not None:
            # 这句只描述名单怎么变的，不报执行率：
            # 「已安排 N 人」是个考核计数器，做不到的那几周它就成了反面记录。
            done, add = len(prev - names), len(names - prev)
            if done and add:
                s2 = f"上周 {len(prev)} 人，其中 {done} 人本周已休息，新增 {add} 人。"
            elif done:
                s2 = f"上周 {len(prev)} 人，其中 {done} 人本周已休息。"
            elif add:
                s2 = f"上周 {len(prev)} 人全部仍在名单内，另新增 {add} 人。"
            else:
                s2 = f"名单与上周一致，仍是这 {len(prev)} 人。"
            stuck = [n for n in names if weeks.get(n, 1) >= 3]
            if stuck:
                s2 += f"名单中有 {len(stuck)} 人已连续 {max(weeks[n] for n in stuck)} 周在列。"
            L.append(s2)
        if degraded:
            L.append(degraded)
        if degraded:
            L += [n for n, _ in roll]      # 归不了类就一人一行，不拿钉钉班组凑第二个口径
        else:
            g: dict = defaultdict(list)
            for n, p in roll:
                g[p].append(n)
            for p, v in sorted(g.items(), key=lambda z: _order(z[0], len(z[1]))):
                L.append(f"**{p}**　{'、'.join(v)}")
    if pending:
        L += [RULE, "**在岗待核实**"]
        L += [f"{n}（{p}）近期没有打卡记录" for n, p in pending]
    if discipline:
        L += [RULE, f"**打卡规范　{bd.month} 月 1 日 – {bd.day} 日**"]
        L += [f"{lab} 3 次以上　" + "、".join(f"{n} {v} 次" for n, v in arr)
              for lab, arr in discipline]
    return f"生产部 · 连续在岗周报 {md.month}/{md.day}", "\n".join(L)
