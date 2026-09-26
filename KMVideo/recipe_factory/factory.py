"""配方工厂：批量抽取互不雷同的视频配方，并检查已有配方的同质化程度。

  python3 factory.py sample --n 6 --fix business=tyre --fix duration=s30 --avail footage,tts
  python3 factory.py check
  python3 factory.py show R001

规则（去同质化的三道闸）：
  1. 新配方与已有每一份配方，L0 根本因素至少有 MIN_L0_DIFF 项不同；
  2. (叙事母型, 媒介画风) 组合全库唯一；
  3. 同一批内，任一 L0 取值出现次数 ≤ ceil(n/3)（被 --fix 固定的因素除外）。
在满足三道闸的候选里，选与已有配方加权距离最远的那个（最远点采样）。
"""
import argparse
import math
import pathlib
import random
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent
RECIPES = HERE / "recipes"
MIN_L0_DIFF = 3
PAIR_KEY = ("narrative", "medium")


def load_factors():
    fs = yaml.safe_load((HERE / "factors.yaml").read_text())["factors"]
    return {f["id"]: f for f in fs}


def load_recipes():
    out = []
    for p in sorted(RECIPES.glob("R*.yaml")):
        r = yaml.safe_load(p.read_text())
        r["_path"] = p
        out.append(r)
    return out


def l0_ids(F):
    return [k for k, f in F.items() if f["layer"] == "L0"]


def distance(F, a, b):
    tot = sum(f["weight"] for f in F.values())
    diff = sum(f["weight"] for k, f in F.items() if a.get(k) != b.get(k))
    return diff / tot


def l0_diff(F, a, b):
    return sum(1 for k in l0_ids(F) if a.get(k) != b.get(k))


def value_ok(F, fid, vid, avail):
    v = next(x for x in F[fid]["values"] if x["id"] == vid)
    return all(req in avail for req in v.get("requires", []))


def passes(F, cand, pool, batch, n, fixed):
    for r in pool:
        if l0_diff(F, cand, r) < MIN_L0_DIFF:
            return False
        if all(cand[k] == r.get(k) for k in PAIR_KEY):
            return False
    cap = math.ceil(n / 3)
    for k in l0_ids(F):
        if k in fixed:
            continue
        if sum(1 for b in batch if b[k] == cand[k]) + 1 > cap:
            return False
    return True


def cmd_sample(a):
    F = load_factors()
    avail = set(filter(None, a.avail.split(",")))
    fixed = dict(kv.split("=", 1) for kv in a.fix)
    for k, v in fixed.items():
        assert k in F and any(x["id"] == v for x in F[k]["values"]), f"未知因子或取值：{k}={v}"
    rng = random.Random(a.seed)
    existing = [r["factors"] for r in load_recipes()]
    batch = []
    for _ in range(a.n):
        best, best_d = None, -1.0
        for _ in range(4000):
            cand = {}
            for k, f in F.items():
                if k in fixed:
                    cand[k] = fixed[k]
                    continue
                opts = [v["id"] for v in f["values"] if value_ok(F, k, v["id"], avail)]
                cand[k] = rng.choice(opts)
            pool = existing + batch
            if not passes(F, cand, pool, batch, a.n, fixed):
                continue
            d = min((distance(F, cand, r) for r in pool), default=1.0)
            if d > best_d:
                best, best_d = cand, d
        if best is None:
            sys.exit(f"第 {len(batch) + 1} 份找不到满足三道闸的配方：放开一些 --fix，或补充因子取值")
        batch.append(best)
    RECIPES.mkdir(exist_ok=True)
    start = len(load_recipes()) + 1
    for i, fac in enumerate(batch):
        rid = f"R{start + i:03d}"
        doc = {"id": rid, "title": "", "status": "draft", "factors": fac,
               "brief": "", "facts": [], "storyboard": "", "output": ""}
        path = RECIPES / f"{rid}.yaml"
        if a.dry:
            print(f"--- {rid}"); print(describe(F, fac))
        else:
            path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False))
            print(f"写入 {path.relative_to(HERE)}  最近距离={min((distance(F, fac, r) for r in existing + batch[:i]), default=1.0):.2f}")
            print(describe(F, fac))


def describe(F, fac):
    lines = []
    for k, f in F.items():
        v = next(x for x in f["values"] if x["id"] == fac[k])
        extra = f"  [{v['engine']}]" if "engine" in v else ""
        lines.append(f"  {f['layer']} {f['name']}: {v['label']}{extra}")
    return "\n".join(lines)


def cmd_check(a):
    F = load_factors()
    rs = load_recipes()
    bad = 0
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            x, y = rs[i]["factors"], rs[j]["factors"]
            d, l0 = distance(F, x, y), l0_diff(F, x, y)
            same_pair = all(x[k] == y[k] for k in PAIR_KEY)
            flag = l0 < MIN_L0_DIFF or same_pair
            bad += flag
            print(f"{rs[i]['id']}–{rs[j]['id']}  距离={d:.2f}  L0不同={l0}/{len(l0_ids(F))}{'  ✗ 趋同' if flag else ''}")
    print(f"{len(rs)} 份配方，{bad} 对趋同")
    sys.exit(1 if bad else 0)


def cmd_show(a):
    F = load_factors()
    r = next(r for r in load_recipes() if r["id"] == a.rid)
    print(f"{r['id']} {r.get('title', '')}  [{r.get('status')}]")
    print(describe(F, r["factors"]))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("sample")
    s.add_argument("--n", type=int, default=6)
    s.add_argument("--fix", action="append", default=[], help="固定的因子，如 business=tyre")
    s.add_argument("--avail", default="", help="已具备的条件：footage,tts,gpu_or_patience")
    s.add_argument("--seed", type=int, default=None)
    s.add_argument("--dry", action="store_true", help="只打印不写文件")
    sp.add_parser("check")
    sh = sp.add_parser("show")
    sh.add_argument("rid")
    a = ap.parse_args()
    {"sample": cmd_sample, "check": cmd_check, "show": cmd_show}[a.cmd](a)


if __name__ == "__main__":
    main()
