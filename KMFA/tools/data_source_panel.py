#!/usr/bin/env python3
"""数据源盘点面板。

Owner 2026-07-19 定的取数优先级：**① GitHub 私有库 → ② 本机 KMFA_MetaData → ③ 都没有才申请手动补齐**。
本工具按该顺序盘点三源，并把《下批数据需求单》12 项逐项对源命中，输出：
  · 机器面：`数据源面板.json`（可被 App / 门禁消费）
  · 人读面：`数据源面板.md`（Owner 一眼看清「哪项有、哪项缺、缺的去哪拿」）

设计要点
  · **可重跑**：不是手写会过期的文档；Owner 往任一源丢文件后重跑即刷新命中。
  · **离线容错**：`gh` 不可用时把 GitHub 源标为「未探测」，不伪造结论。
  · **命中是启发式**：文件名关键词匹配只作导航；期间/口径类要求（如「补全 2025-02 之后」）
    必须人工核期间，工具会显式标注 `需人工核期间`，不冒充已满足。

用法：
  python3 KMFA/tools/data_source_panel.py                 # 盘点并写面板
  python3 KMFA/tools/data_source_panel.py --print         # 只打印不落盘
  python3 KMFA/tools/data_source_panel.py --selftest      # 自检
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL = Path("/Users/linzezhang/Downloads/KMFA_MetaData")
INGESTED_DIR = REPO_ROOT / "KMDatabase" / "data" / "objects"
GH_REPO = "LinzeColin/Private-Database"
GH_OBJ_PREFIX = "Private-KMDatabase/objects/"
OUT_DIR = REPO_ROOT / "KMFA" / "docs" / "governance"
OBJ_NAME_RE = re.compile(r"^[0-9a-f]{64}_")
BEIJING = timezone(timedelta(hours=8))

# 《下批数据需求单》12 项。kind=file 可由文件名命中；kind=fix 为报表修正项（非新文件）。
# 匹配器刻意用「判别性关键词」——例如第 2 项不能被现有『凭证列表』误判为已满足。
ITEMS: list[dict] = [
    {"id": 1, "name": "科目余额表（带期初）", "kind": "file", "any": ["科目余额", "余额表"],
     "unlock": "四家贷款期初反推的正式验证 / 林总个人 50 万裁决", "source_hint": "金蝶：三账套全科目，期间从最早可取起"},
    {"id": 2, "name": "凭证导出（分录级借贷对应）", "kind": "file", "any": ["序时簿", "分录"],
     "unlock": "材料轴发出侧行级配对",
     "note": "现有『凭证列表』为表头级，不满足；须带分录对儿或分录序号",
     "source_hint": "金蝶：序时簿 / 凭证明细"},
    {"id": 3, "name": "湖北开明凭证列表补全（2025-02 之后）", "kind": "file", "any": ["湖北"], "all": ["凭证"],
     "unlock": "报告第 2 号遗留", "period_check": True, "source_hint": "金蝶：湖北开明账套",
     "note": "金蝶 zip 内已有『湖北开明公司_凭证列表』并已抽取，但实际覆盖不足——需补 2025-02 之后"},
    {"id": 4, "name": "曦悦明细账重导（口径一致版）", "kind": "file", "any": ["曦悦"], "all": ["明细账"],
     "unlock": "报告第 2 号双视角互证", "period_check": True, "source_hint": "金蝶：曦悦账套",
     "note": "金蝶 zip 内已有『曦悦公司25.1-26.5明细账』并已抽取，但与总量口径不一致——需按科目级一致口径重导"},
    {"id": 5, "name": "彤烨 2025 期账套（明细账 2025-01..12）", "kind": "file", "any": ["彤烨"],
     "unlock": "彤烨费用轴开跑（费用表 631 行待命）", "period_check": True,
     "note": "现有彤烨仅 2026.01-05，非 2025 期", "source_hint": "金蝶：彤烨账套 2025 全年"},
    {"id": 6, "name": "进项发票明细（价税分列）", "kind": "file", "any": ["进项"],
     "unlock": "材料轴 62 组按已双实证的价税合计形态机械展开",
     "note": "必须是进项（采购侧）；红圈『项目开票』为销项票，已入仓但不满足",
     "source_hint": "税务/发票系统：不含税额 / 税额 / 价税合计三列"},
    {"id": 7, "name": "补录两笔小额营业外收入（武汉 2025-01 记-55 ¥1,403.00 / 记-115 ¥0.50）",
     "kind": "fix", "unlock": "DT5_DATA0023"},
    {"id": 8, "name": "8 月附加税计提同步终稿（武汉 记-271，差 ¥251.73）", "kind": "fix", "unlock": "税负表+金蝶双证"},
    {"id": 9, "name": "记-49 尾差行改符号或剔除（武汉 2025-03，¥0.86）", "kind": "fix", "unlock": "DT5_DATA0042"},
    {"id": 10, "name": "修 #N/A 统一码一处（武汉 2024-11 记-275）", "kind": "fix", "unlock": "DT5_DATA0041"},
    {"id": 11, "name": "个人借支表录真凭证号（「5月」「7月」两行）", "kind": "fix", "unlock": "DT5_DATA0036"},
    {"id": 12, "name": "（可选）贷款一览表加岚丹主体行", "kind": "fix", "unlock": "DT5_DATA0044"},
]


def strip_object_name(path_or_name: str) -> str:
    """内容寻址对象名 `<64hex>_原名` → 原名；非对象名原样返回。"""
    base = path_or_name.rsplit("/", 1)[-1]
    return OBJ_NAME_RE.sub("", base)


def scan_ingested(objects_dir: Path) -> set[str]:
    if not objects_dir.is_dir():
        return set()
    return {strip_object_name(p.name) for p in objects_dir.rglob("*") if p.is_file()}


def zip_member_names(path: Path) -> list[str]:
    """列 zip 内成员名。本域 zip 多为 GBK 文件名，按 cp437→gbk 兜底解码。"""
    names: list[str] = []
    try:
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                if not (info.flag_bits & 0x800):  # 非 UTF-8 标志
                    try:
                        name = name.encode("cp437").decode("gbk")
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        pass
                names.append(name.rsplit("/", 1)[-1])
    except (zipfile.BadZipFile, OSError):
        return []
    return names


def scan_local(root: Path) -> tuple[set[str], bool, dict[str, str]]:
    """返回（文件名集合含 zip 内成员, 是否可达, 名→出处）。

    zip 内成员必须纳入：本域关键数据（如金蝶各账套凭证/明细账）都打包在 zip 里，
    只看顶层会把「有但不满足」误报成「完全没有」。
    """
    if not root.is_dir():
        return set(), False, {}
    names: set[str] = set()
    origin: dict[str, str] = {}
    for p in root.rglob("*"):
        if not p.is_file() or p.name == ".DS_Store":
            continue
        names.add(p.name)
        origin.setdefault(p.name, "本机文件")
        if p.suffix.lower() == ".zip":
            for member in zip_member_names(p):
                names.add(member)
                origin.setdefault(member, f"本机 zip 内：{p.name}")
    return names, True, origin


def scan_github(repo: str = GH_REPO, prefix: str = GH_OBJ_PREFIX) -> tuple[set[str], bool, str]:
    """经 gh 读私有库对象清单。返回（集合, 是否探测成功, 备注）。离线/无权限不伪造。"""
    try:
        out = subprocess.run(
            ["gh", "api", f"repos/{repo}/git/trees/HEAD?recursive=1",
             "--jq", '.tree[]|select(.type=="blob")|.path'],
            capture_output=True, text=True, timeout=60, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return set(), False, f"gh 调用失败：{exc}"
    if out.returncode != 0:
        return set(), False, (out.stderr or "gh 非零退出").strip().splitlines()[-1][:200]
    names = {
        strip_object_name(line) for line in out.stdout.splitlines()
        if line.startswith(prefix)
    }
    return names, True, "ok"


def match_item(item: dict, pool: set[str]) -> list[str]:
    """在文件名池里找命中。all 关键词须全含，any 关键词至少含一个。"""
    if item.get("kind") != "file":
        return []
    hits = []
    for name in pool:
        if any(k in name for k in item.get("any", [])) and all(
            k in name for k in item.get("all", [])
        ):
            hits.append(name)
    return sorted(hits)


def build_report(local_root: Path, probe_github: bool = True) -> dict:
    ingested = scan_ingested(INGESTED_DIR)
    local, local_ok, local_origin = scan_local(local_root)
    if probe_github:
        gh, gh_ok, gh_note = scan_github()
    else:
        gh, gh_ok, gh_note = set(), False, "已跳过探测（--no-github）"

    # 优先级顺序的可用池：GitHub 优先，其次本机
    pool = (gh if gh_ok else set()) | local

    items = []
    for spec in ITEMS:
        gh_hits = match_item(spec, gh) if gh_ok else []
        local_hits = match_item(spec, local)
        has_hit = bool(gh_hits or local_hits)
        if spec.get("kind") == "fix":
            status, mark = "报表修正项（非文件）——需在下批报表中改，无法靠丢文件满足", "—"
        elif has_hit and spec.get("note"):
            # 近似源存在但既有分析已判定不足：不得显示为「已满足」，否则误导 Owner
            status, mark = "已有近似源但判定不足——见备注，仍需补齐", "⚠️"
        elif has_hit:
            status = "疑似命中——需人工核期间/口径" if spec.get("period_check") else "疑似命中——需人工核内容"
            mark = "✅"
        else:
            status, mark = "缺——两源均无，需手动补齐", "❌"
        items.append({
            "id": spec["id"], "name": spec["name"], "kind": spec.get("kind"),
            "status": status, "mark": mark, "github_hits": gh_hits, "local_hits": local_hits,
            "hit_origins": sorted({local_origin.get(h, "GitHub 私有库") for h in (local_hits + gh_hits)}),
            "unlock": spec.get("unlock"), "note": spec.get("note"),
            "source_hint": spec.get("source_hint"),
        })

    return {
        "generated_at": datetime.now(BEIJING).isoformat(timespec="seconds"),
        "priority": ["① GitHub 私有库 Private-Database", "② 本机 KMFA_MetaData", "③ 手动补齐"],
        "sources": {
            "github": {"repo": GH_REPO, "path": GH_OBJ_PREFIX, "probed": gh_ok,
                       "note": gh_note, "file_count": len(gh)},
            "local": {"path": str(local_root), "reachable": local_ok, "file_count": len(local)},
            "ingested": {"path": str(INGESTED_DIR.relative_to(REPO_ROOT)), "file_count": len(ingested)},
        },
        "delta": {
            "github_not_ingested": sorted(gh - ingested) if gh_ok else [],
            "local_not_ingested": sorted(local - ingested),
            "pool_size": len(pool),
        },
        "items": items,
        "summary": {
            "missing": sum(1 for i in items if i["status"].startswith("缺")),
            "insufficient": sum(1 for i in items if i["status"].startswith("已有近似源")),
            "suspect_hit": sum(1 for i in items if i["status"].startswith("疑似")),
            "fix_only": sum(1 for i in items if i["kind"] == "fix"),
        },
    }


def render_markdown(rep: dict) -> str:
    s, d, sm = rep["sources"], rep["delta"], rep["summary"]
    gh_state = f"{s['github']['file_count']} 个" if s["github"]["probed"] else f"未探测（{s['github']['note']}）"
    lo_state = f"{s['local']['file_count']} 个" if s["local"]["reachable"] else "路径不可达"
    L = [
        "# 数据源盘点面板（机器生成，勿手改）",
        "",
        f"> 生成于 {rep['generated_at']}｜重跑：`python3 KMFA/tools/data_source_panel.py`",
        "> 取数优先级（Owner 2026-07-19 定）：**① GitHub 私有库 → ② 本机 → ③ 都没有才申请手动补齐**。",
        "",
        "## 一、三源盘点",
        "",
        "| 优先级 | 源 | 位置 | 文件数 |",
        "|---|---|---|---|",
        f"| ① | GitHub 私有库 | `{s['github']['repo']}` : `{s['github']['path']}` | {gh_state} |",
        f"| ② | 本机 | `{s['local']['path']}` | {lo_state} |",
        f"| —  | KMOS 已入仓（派生层来源） | `{s['ingested']['path']}` | {s['ingested']['file_count']} 个 |",
        "",
        "## 二、可用但未入仓（差集）",
        "",
    ]
    gnot, lnot = d["github_not_ingested"], d["local_not_ingested"]
    L.append(f"- GitHub 有、KMOS 未入仓：**{len(gnot)}** 个" + ("" if gnot else "（零新增，两侧一致）"))
    L += [f"  - `{n}`" for n in gnot[:20]]
    L.append(f"- 本机有、KMOS 未入仓：**{len(lnot)}** 个" + ("" if lnot else "（零新增）"))
    L += [f"  - `{n}`" for n in lnot[:20]]
    L += [
        "",
        "## 三、《下批数据需求单》12 项 × 源命中",
        "",
        f"**缺 {sm['missing']} 项 · 有但不足 {sm['insufficient']} 项 · 疑似命中 {sm['suspect_hit']} 项 · 报表修正 {sm['fix_only']} 项**",
        "",
        "> ⚠️ = 源里有同名近似文件（多在金蝶 zip 内、且已抽取），但既有分析判定**不满足要求**，仍需补齐。",
        "",
        "| # | 需求 | ①GitHub | ②本机 | 结论 |",
        "|---|---|---|---|---|",
    ]
    for it in rep["items"]:
        hit_mark = it.get("mark") if it.get("mark") in ("✅", "⚠️") else "✅"
        g = hit_mark if it["github_hits"] else ("—" if it["kind"] == "fix" else "❌")
        lo = hit_mark if it["local_hits"] else ("—" if it["kind"] == "fix" else "❌")
        L.append(f"| {it['id']} | {it['name']} | {g} | {lo} | {it['status']} |")
    L += ["", "### 逐项备注与去哪拿", ""]
    for it in rep["items"]:
        if it["kind"] == "fix":
            L.append(f"- **{it['id']}** {it['name']} —— 报表修正项，解锁：{it['unlock']}")
            continue
        L.append(f"- **{it['id']}** {it['name']}")
        if it.get("source_hint"):
            L.append(f"  - 去哪拿：{it['source_hint']}")
        if it.get("note"):
            L.append(f"  - 注意：{it['note']}")
        if it["github_hits"] or it["local_hits"]:
            hits = (it["local_hits"] or it["github_hits"])[:3]
            org = it.get("hit_origins") or []
            tail = ("；出处：" + " / ".join(org)) if org else ""
            L.append(f"  - 源内命中（**需人工核**）：{', '.join('`' + h + '`' for h in hits)}{tail}")
        L.append(f"  - 解锁：{it['unlock']}")
    L += [
        "",
        "> 命中为**文件名启发式**，只作导航；期间/口径必须人工核实。",
        "> 面板不改变门禁结论：真正入仓走 `ingest_data.py`，抽取走对应抽取器，复跑口令见《下批数据需求单》。",
        "",
    ]
    return "\n".join(L)


def selftest() -> int:
    assert strip_object_name("ab" * 32 + "_报表.xlsx") == "报表.xlsx", "对象名剥离失败"
    assert strip_object_name("x/y/" + "cd" * 32 + "_贷款.xls") == "贷款.xls", "带路径剥离失败"
    assert strip_object_name("普通文件.xlsx") == "普通文件.xlsx", "非对象名应原样"

    pool = {"湖北开明公司_凭证列表第2025年第1期.xlsx", "武汉开明公司-明细账.xlsx", "曦悦公司25.1-26.5明细账.xls"}
    spec3 = next(i for i in ITEMS if i["id"] == 3)
    assert match_item(spec3, pool) == ["湖北开明公司_凭证列表第2025年第1期.xlsx"], "第3项匹配异常"
    spec4 = next(i for i in ITEMS if i["id"] == 4)
    assert match_item(spec4, pool) == ["曦悦公司25.1-26.5明细账.xls"], "第4项匹配异常"

    # 判别性：现有『凭证列表』不得把第 2 项（分录级）误判为命中
    spec2 = next(i for i in ITEMS if i["id"] == 2)
    assert match_item(spec2, pool) == [], "第2项被凭证列表误命中"
    # 销项『项目开票』不得命中第 6 项（进项）
    spec6 = next(i for i in ITEMS if i["id"] == 6)
    assert match_item(spec6, {"项目开票_导出文件_303637932950.xlsx"}) == [], "第6项被销项票误命中"
    # 修正项不参与文件命中
    assert match_item(next(i for i in ITEMS if i["id"] == 7), pool) == [], "修正项不应命中文件"

    # zip 内成员必须能列举（本域关键数据都在 zip 里）；缺失 zip 须优雅返回空
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        zp = Path(td) / "t.zip"
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr("子目录/湖北开明公司_凭证列表.xlsx", b"x")
        assert "湖北开明公司_凭证列表.xlsx" in zip_member_names(zp), "zip 成员列举失败"
        assert zip_member_names(Path(td) / "missing.zip") == [], "缺失 zip 应返回空而非抛错"

    # 「有但不足」项必须带不足原因，否则命中时会被误显示为已满足
    for iid in (2, 3, 4, 5, 6):
        assert next(i for i in ITEMS if i["id"] == iid).get("note"), f"第{iid}项缺不足原因说明"

    rep = build_report(Path("/nonexistent-path-for-selftest"), probe_github=False)
    assert rep["sources"]["local"]["reachable"] is False, "不可达本机源应如实标注"
    assert rep["sources"]["github"]["probed"] is False, "跳过探测应标注未探测"
    assert len(rep["items"]) == 12, "需求单应为 12 项"
    assert render_markdown(rep).startswith("# 数据源盘点面板"), "渲染异常"
    print("selftest: 全部通过")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-root", type=Path, default=DEFAULT_LOCAL)
    ap.add_argument("--no-github", action="store_true", help="跳过 gh 探测（离线）")
    ap.add_argument("--print", dest="only_print", action="store_true", help="只打印不落盘")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    rep = build_report(args.local_root, probe_github=not args.no_github)
    md = render_markdown(rep)
    if args.only_print:
        print(md)
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "数据源面板.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "数据源面板.md").write_text(md, encoding="utf-8")
    sm = rep["summary"]
    print(f"面板已生成：缺 {sm['missing']} 项 / 疑似命中 {sm['suspect_hit']} 项 / 报表修正 {sm['fix_only']} 项")
    print(f"  → {OUT_DIR.relative_to(REPO_ROOT)}/数据源面板.md（人读）+ .json（机器）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
