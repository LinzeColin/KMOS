"""KMDY-RF 配方工坊：按车道抽取 / 演化互不雷同的视频配方，并检查全库同质化。

  python3 factory.py sample --lane TYPE --n 3                   # 在 TYPE 车道抽 3 份新配方
  python3 factory.py sample --lane TOON --fix business=rotary_kiln --fix duration=s30
  python3 factory.py evolve --lane TOON                          # 从车道最高分配方演化出下一代
  python3 factory.py evolve --lane TOON --parent R001 --keep value_core,twist
  python3 factory.py check                                       # 全库趋同检查，有趋同则退出码 1
  python3 factory.py status                                      # 各车道进度与剩余组合空间
  python3 factory.py show TOON-002

去同质化的四道闸（全部通过才写入）：
  1. 与库里每一份配方（含 EXT 车道登记的 Blender 工作间成片）L0 至少 MIN_L0_DIFF 项不同；
  2. (叙事母型, 惊喜机制, 画风) 三元组全库唯一；
  3. 同车道最近 window 部片子里，叙事母型与惊喜机制都不重复；
  4. 同一批内，任一未固定的 L0 取值出现次数 ≤ ceil(n/3)。
在通过闸门的候选里选与全库加权距离最远的一个（最远点采样）。
配方目录取 workspace.yaml 的 paths.recipes；该目录不存在时用本目录下的 recipes/。环境变量 RF_RECIPES 可覆盖。
"""
import argparse
import contextlib
import math
import os
import pathlib
import random
import sys
import time

import yaml

HERE = pathlib.Path(__file__).resolve().parent
MIN_L0_DIFF = 3
TRIPLE = ("narrative", "twist", "medium")
TRIES = 4000


def load_yaml(p):
    return yaml.safe_load(pathlib.Path(p).read_text())


WS = load_yaml(HERE / "workspace.yaml")
FAC = load_yaml(HERE / "factors.yaml")
LANES_DOC = load_yaml(HERE / "lanes.yaml")
F = {f["id"]: f for f in FAC["factors"]}
ENGINES = FAC["engines"]
LANES = {l["id"]: l for l in LANES_DOC["lanes"]}
WINDOW = LANES_DOC["window"]
CAPS = {k for k, v in WS["capabilities"].items() if v}
L0 = [k for k, f in F.items() if f["layer"] == "L0"]


def recipes_dir():
    if os.environ.get("RF_RECIPES"):
        return pathlib.Path(os.environ["RF_RECIPES"])
    p = pathlib.Path(WS["paths"]["recipes"].replace("{root}", WS["paths"]["root"])).expanduser()
    return p if p.exists() else HERE / "recipes"


RECIPES = recipes_dir()


@contextlib.contextmanager
def lock():
    """mkdir 在 SMB 上是原子操作，用它做跨机器的写锁；超过 10 分钟的锁视为遗留并接管。"""
    d = RECIPES / ".lock"
    for _ in range(600):
        try:
            d.mkdir(parents=True)
            break
        except FileExistsError:
            if time.time() - d.stat().st_mtime > 600:
                d.rmdir()
                continue
            time.sleep(1)
    else:
        sys.exit("拿不到配方库写锁")
    try:
        yield
    finally:
        d.rmdir()


def load_recipes():
    out = []
    for p in sorted(RECIPES.glob("*/*.yaml")):
        r = load_yaml(p)
        r["_path"], r["_lane"] = p, p.parent.name
        out.append(r)
    return out


def value(fid, vid):
    return next(x for x in F[fid]["values"] if x["id"] == vid)


def available(fid, v):
    if v.get("retired"):
        return False
    need = set(v.get("requires", []))
    if "engine" in v:
        need |= set(ENGINES[v["engine"]]["requires"])
    return need <= CAPS


def options(fid, lane):
    vals = [v for v in F[fid]["values"] if available(fid, v)]
    if fid == "medium":
        vals = [v for v in vals if v["id"] in lane["media"]]
    return [v["id"] for v in vals]


def distance(a, b):
    tot = sum(f["weight"] for f in F.values())
    return sum(f["weight"] for k, f in F.items() if a.get(k) != b.get(k)) / tot


def l0_diff(a, b):
    return sum(1 for k in L0 if a.get(k) != b.get(k))


def lane_tail(recipes, lane_id, extra=()):
    rs = [r["factors"] for r in recipes if r["_lane"] == lane_id] + list(extra)
    return rs[-WINDOW:]


def gate(cand, pool, tail, batch, n, fixed):
    for r in pool:
        if l0_diff(cand, r) < MIN_L0_DIFF:
            return "L0 差异不足"
        if all(cand[k] == r.get(k) for k in TRIPLE):
            return "三元组重复"
    for r in tail:
        if cand["narrative"] == r.get("narrative") or cand["twist"] == r.get("twist"):
            return "车道窗口内叙事/惊喜重复"
    cap = math.ceil(n / 3)
    for k in L0:
        if k not in fixed and sum(1 for b in batch if b[k] == cand[k]) + 1 > cap:
            return "批内取值超限"
    return None


def draw(rng, lane, fixed):
    cand = {}
    for k in F:
        if k in fixed:
            cand[k] = fixed[k]
            continue
        opts = options(k, lane)
        tilt = set(lane.get("tilt", {}).get(k, []))
        cand[k] = rng.choices(opts, weights=[2 if o in tilt else 1 for o in opts])[0]
    return cand


def generate(lane_id, n, fixed, seed):
    lane = LANES[lane_id]
    if lane.get("external"):
        sys.exit(f"{lane_id} 是外部登记车道，只能手工登记成片，不在此抽样")
    for k, v in fixed.items():
        assert k in F and any(x["id"] == v for x in F[k]["values"]), f"未知因子或取值：{k}={v}"
    if not options("medium", lane):
        need = sorted(set(ENGINES[lane["engine"]]["requires"]) - CAPS)
        sys.exit(f"{lane_id} 车道的引擎 {lane['engine']} 未就绪：workspace.yaml 里把 {need} 改成 true")
    rng = random.Random(seed)
    existing = load_recipes()
    pool = [r["factors"] for r in existing]
    batch, reasons = [], {}
    for _ in range(n):
        best, best_d = None, -1.0
        for _ in range(TRIES):
            cand = draw(rng, lane, fixed)
            why = gate(cand, pool + batch, lane_tail(existing, lane_id, batch), batch, n, fixed)
            if why:
                reasons[why] = reasons.get(why, 0) + 1
                continue
            d = min((distance(cand, r) for r in pool + batch), default=1.0)
            if d > best_d:
                best, best_d = cand, d
        if best is None:
            sys.exit(f"第 {len(batch) + 1} 份找不到满足闸门的配方（被拒原因：{reasons}）。"
                     "放开 --fix / --keep，或给本车道补充新的因子取值（见 README「衍变」）")
        batch.append(best)
    return batch


def next_rid(lane_id, k):
    d = RECIPES / lane_id
    nums = [int(p.stem.split("-")[1]) for p in d.glob(f"{lane_id}-*.yaml")] if d.exists() else []
    return f"{lane_id}-{max(nums, default=0) + 1 + k:03d}"


def write(lane_id, batch, dry, parent=None):
    existing = [r["factors"] for r in load_recipes()]
    for i, fac in enumerate(batch):
        rid = next_rid(lane_id, i)
        doc = {"id": rid, "lane": lane_id, "parent": parent, "title": "", "status": "draft",
               "score": None, "factors": fac, "brief": "", "facts": [], "storyboard": "",
               "output": "", "qc": "", "metrics": {}}
        d = min((distance(fac, r) for r in existing + batch[:i]), default=1.0)
        print(f"--- {rid}  与全库最近距离={d:.2f}{'  (dry)' if dry else ''}")
        print(describe(fac))
        if not dry:
            p = RECIPES / lane_id / f"{rid}.yaml"
            p.parent.mkdir(parents=True, exist_ok=True)
            text = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
            p.write_text(text)
            assert p.read_text() == text, f"写入读回不一致：{p}"


def parse_fix(kvs):
    return dict(kv.split("=", 1) for kv in kvs)


def cmd_sample(a):
    with lock():
        write(a.lane, generate(a.lane, a.n, parse_fix(a.fix), a.seed), a.dry)


def cmd_evolve(a):
    with lock():
        rs = [r for r in load_recipes() if r["_lane"] == a.lane]
        if a.parent:
            par = next(r for r in load_recipes() if r["id"] == a.parent)
        else:
            scored = [r for r in rs if isinstance(r.get("score"), (int, float))]
            if not scored and not rs:
                sys.exit(f"{a.lane} 车道还没有配方，先 sample 或用 --parent 指定种子")
            par = max(scored, key=lambda r: r["score"]) if scored else rs[-1]
        keep = [k for k in a.keep.split(",") if k]
        assert len(keep) <= len(L0) - MIN_L0_DIFF, f"保留基因最多 {len(L0) - MIN_L0_DIFF} 个"
        fixed = {k: par["factors"][k] for k in keep}
        fixed.update(parse_fix(a.fix))
        print(f"父本 {par['id']}（score={par.get('score')}），保留基因：{fixed}")
        write(a.lane, generate(a.lane, a.n, fixed, a.seed), a.dry, parent=par["id"])


def describe(fac):
    lines = []
    for k, f in F.items():
        v = value(k, fac[k])
        extra = f"  [{v['engine']}]" if "engine" in v else ""
        lines.append(f"  {f['layer']} {f['name']}: {v['label']}{extra}")
    return "\n".join(lines)


def cmd_check(a):
    rs = load_recipes()
    bad = 0
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            x, y = rs[i]["factors"], rs[j]["factors"]
            l0 = l0_diff(x, y)
            same = all(x[k] == y[k] for k in TRIPLE)
            if l0 < MIN_L0_DIFF or same:
                bad += 1
                print(f"✗ {rs[i]['id']}–{rs[j]['id']}  L0不同={l0}/{len(L0)}{'  三元组重复' if same else ''}")
    for lane_id in LANES:
        seq = [r for r in rs if r["_lane"] == lane_id and not LANES[lane_id].get("external")]
        for i in range(1, len(seq)):
            for prev in seq[max(0, i - WINDOW):i]:
                for k in ("narrative", "twist"):
                    if seq[i]["factors"][k] == prev["factors"][k]:
                        bad += 1
                        print(f"✗ {prev['id']}→{seq[i]['id']}  车道窗口内 {k} 重复")
    ds = [distance(rs[i]["factors"], rs[j]["factors"]) for i in range(len(rs)) for j in range(i + 1, len(rs))]
    print(f"{len(rs)} 份配方，{bad} 处趋同；两两距离 最小={min(ds, default=0):.2f} 平均={sum(ds) / max(len(ds), 1):.2f}")
    sys.exit(1 if bad else 0)


def cmd_status(a):
    rs = load_recipes()
    used = {tuple(r["factors"][k] for k in TRIPLE) for r in rs}
    print(f"配方库：{RECIPES}\n能力：{', '.join(sorted(CAPS))}\n")
    print("车道 | 引擎 | 配方数 | 各状态 | 可用画风 | 剩余三元组")
    for lid, lane in LANES.items():
        mine = [r for r in rs if r["_lane"] == lid]
        st = {}
        for r in mine:
            st[r.get("status")] = st.get(r.get("status"), 0) + 1
        media = options("medium", lane) if not lane.get("external") else lane["media"]
        free = sum(1 for n in options("narrative", lane) for t in options("twist", lane) for m in media
                   if (n, t, m) not in used)
        print(f"{lid} | {lane['engine']} | {len(mine)} | {st or '-'} | {len(media)}/{len(lane['media'])} | {free}")


def cmd_show(a):
    r = next(r for r in load_recipes() if r["id"] == a.rid)
    print(f"{r['id']} {r.get('title', '')}  [{r.get('status')}]  车道={r['_lane']}  父本={r.get('parent')}")
    print(describe(r["factors"]))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("sample", "evolve"):
        s = sp.add_parser(name)
        s.add_argument("--lane", required=True, choices=list(LANES))
        s.add_argument("--n", type=int, default=1)
        s.add_argument("--fix", action="append", default=[], help="固定的因子，如 business=rotary_kiln")
        s.add_argument("--seed", type=int, default=None)
        s.add_argument("--dry", action="store_true", help="只打印不写文件")
        if name == "evolve":
            s.add_argument("--parent", default="")
            s.add_argument("--keep", default="value_core", help="从父本继承的 L0 基因，逗号分隔")
    sp.add_parser("check")
    sp.add_parser("status")
    sh = sp.add_parser("show")
    sh.add_argument("rid")
    a = ap.parse_args()
    {"sample": cmd_sample, "evolve": cmd_evolve, "check": cmd_check,
     "status": cmd_status, "show": cmd_show}[a.cmd](a)


if __name__ == "__main__":
    main()
