"""花名册闸门：钉钉通讯录是「自己人」的唯一权威名单。

为什么必需：实测过逐格 OCR 两路完全一致、结果仍然是错的
（同一个错字在多轮里稳定复现，比如把偏旁相近的字连错两处）。一致 ≠ 正确。
所以最终由花名册仲裁：把所有 OCR 路线给出的候选一起查，唯一命中者胜出；
零命中或多命中一律判不可信，报告降级，绝不猜。
"""
from __future__ import annotations
import difflib, json, subprocess
from pathlib import Path

def fetch(dws: str, cache: Path) -> dict[str, str]:
    """遍历部门树拉全体花名册，写入 SMB 缓存。"""
    def run(args):
        p = subprocess.run([dws] + args + ["-f", "json"],
                           capture_output=True, text=True, timeout=120)
        try:
            return json.loads(p.stdout)
        except Exception:
            return None

    def dept_ids(obj, out=None):
        out = [] if out is None else out
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("deptId", "dept_id") and isinstance(v, int):
                    out.append(v)
                else:
                    dept_ids(v, out)
        elif isinstance(obj, list):
            for v in obj:
                dept_ids(v, out)
        return out

    seen, depts, queue = set(), [], [1]
    while queue:
        d = queue.pop(0)
        if d in seen:
            continue
        seen.add(d); depts.append(d)
        for i in dept_ids(run(["contact", "dept", "list-children", "--dept", str(d)])):
            if i not in seen:
                queue.append(i)

    people: dict[str, str] = {}
    def harvest(obj):
        if isinstance(obj, dict):
            uid = obj.get("userid") or obj.get("userId")
            if obj.get("name") and uid:
                people[obj["name"]] = uid
            for v in obj.values():
                harvest(v)
        elif isinstance(obj, list):
            for v in obj:
                harvest(v)
    for i in range(0, len(depts), 20):
        harvest(run(["contact", "dept", "list-members",
                     "--depts", ",".join(str(x) for x in depts[i:i + 20])]) or {})
    # 部门树是一层层爬下来的，中途任何一次请求够不着，收上来的就是半份花名册。
    # 半份的后果不是「少几个人」——是这几个人被判「不在钉钉花名册」，
    # 名字印进简报的「名单待核」里去问综合部。而且它会把缓存里好的那份盖掉，
    # 之后每天都错。所以缩水超过两成一律不落盘，宁可继续用旧的。
    prev = load(cache)
    if people and prev and len(people) < len(prev) * 0.8:
        raise RuntimeError(
            f"花名册只取到 {len(people)} 人，缓存里有 {len(prev)} 人 —— "
            f"多半是部门树爬到一半够不着钉钉，不覆盖缓存")
    if people:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(people, ensure_ascii=False, indent=1), encoding="utf-8")
    return people

def load(cache: Path) -> dict[str, str]:
    return json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}

def arbitrate(candidates: list[str], roster: dict[str, str]) -> tuple[str, str | None, str]:
    """把该格的全部 OCR 候选交给花名册仲裁。

    返回 (判决, 最终姓名 | None, 说明)：
      采信      OCR 首选就在花名册，直接用。
      修正      首选不在，但存在唯一近似（先试差 1 字，再试差 2 字），改过来。
      不在册    既不在花名册也无唯一近似 —— 这个人本来就不在钉钉
                （新入职未录入 / 外协焊工 / 已离职）。不判考勤，列入名单待核，
                **不让整份报告降级**。
      不可信    多路 OCR 对同一格给出互相矛盾且都能在花名册命中的结果，无法定夺。
    """
    cands = [c for c in dict.fromkeys(candidates) if c]
    if not cands:
        return "不可信", None, "无候选"
    first = cands[0]
    if first in roster:                       # 首选直接命中 —— 最常见的路径
        return "采信", first, ""
    hits = [c for c in cands if c in roster]
    if len(hits) == 1:
        return "修正", hits[0], f"OCR 首选 {first!r}"
    if len(hits) > 1:
        return "不可信", None, f"多个候选都在花名册: {hits}"
    # 差 1 字：3 字姓名有 2 字相同，可信
    near = list(dict.fromkeys(
        r for c in cands for r in roster
        if len(r) == len(c) and sum(a != b for a, b in zip(r, c)) == 1))
    if len(near) == 1:
        return "修正", near[0], f"与 {first!r} 差 1 字"
    if len(near) > 1:
        # 名字读得清楚、只是花名册里没有，且有多个长得像的 —— 这是「这个人不在册」，
        # 不是「读不准」。实测有个离职员工的名字会同时命中在册的两个人，
        # 若判成不可信会让整份报告无谓降级。
        return "不在册", None, f"{first} 不在花名册（近似的有 {'/'.join(near)}）"
    # 差 2 字一律不修正：3 字姓名差 2 字只剩 1 字相同，信息量不足以定人。
    # 实测这条曾把两个 3 字姓名各改成另一个在册的人 —— 宁可判不在册。
    return "不在册", None, f"{first} 不在钉钉花名册"
