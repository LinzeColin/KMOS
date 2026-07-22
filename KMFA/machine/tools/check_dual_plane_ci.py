#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_dual_plane_ci.py —— 仓库级双平面合规校验（CI 入口）

对一个 repo 下的每个项目，校验双平面七文件架构是否就位并过门。
「项目」= 含 machine/tools/render_human.py 的目录，或 --projects 显式指定。

对每个项目执行：
  1. 结构门：文档/ 下 7 个文件齐全、machine/facts 与 machine/tools 存在；
     声明 machine/canonical_facts.yaml 的项目还必须恰好七文件
  2. 渲染一致门：重新渲染后 7 个文件无变化（人类平面确由机器平面生成，
     未被手工篡改）；声明 Canonical Facts 的项目还须按职责逐值投影
  3. 三道门：check_doc_budget + check_blocker_stop

任何项目任一门 FAIL -> 整体 FAIL（退出码 1）。

用法:
  python3 check_dual_plane_ci.py [--root .] [--projects a b c] [--require-projects]
  --require-projects  若未发现任何双平面项目也判 FAIL（用于已声明必须合规的 repo）
退出码: 0=全部 PASS  1=有 FAIL
"""
import argparse
import subprocess
import sys
from pathlib import Path

SEVEN = [
    "00_我在哪.md", "01_产品需求.md", "02_系统架构.md", "03_口径字典.md",
    "04_操作流程.md", "05_执行与验收.md", "06_运维手册.md",
]
# 七文件全部渲染，无手写区——渲染一致门覆盖全部七个。
RENDERED = list(SEVEN)
GENERATED_PREFIX = "<!-- 本文件由 machine/tools/render_human.py 从机器平面生成。"


def discover(root: Path):
    found = []
    for tool in root.rglob("machine/tools/render_human.py"):
        proj = tool.parents[2]
        # 跳过 kit 自身模板目录
        if (proj / "文档").is_dir() or (proj / "machine" / "facts").is_dir():
            found.append(proj)
    return sorted(set(found))


def _flatten(value):
    if value is None:
        yield "<MISSING>"
    elif isinstance(value, (str, int, float, bool)):
        yield str(value)
    elif isinstance(value, dict):
        for child in value.values():
            yield from _flatten(child)
    elif isinstance(value, list):
        for child in value:
            yield from _flatten(child)


def _missing_values(text: str, values) -> list:
    missing = []
    for raw in _flatten(values):
        escaped = raw.replace("|", r"\|").replace("\n", "<br>")
        if raw not in text and escaped not in text:
            missing.append(raw)
    return missing


def check_canonical_projection(proj: Path, docs: Path, failures: list):
    path = proj / "machine" / "canonical_facts.yaml"
    if not path.is_file():
        failures.append(f"[{proj.name}] Canonical 投影门: 缺 machine/canonical_facts.yaml")
        return
    try:
        import yaml
        canonical = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"[{proj.name}] Canonical 投影门: YAML 不可解析: {exc}")
        return
    if not isinstance(canonical, dict):
        failures.append(f"[{proj.name}] Canonical 投影门: 顶层必须是 mapping")
        return

    decisions = canonical.get("decisions", [])
    requirements = canonical.get("requirements", [])
    structure_errors = []
    if canonical.get("taskpack_version") != "1.5.2":
        structure_errors.append("taskpack_version != 1.5.2")
    for label, rows, count in (
        ("decisions", decisions, 14),
        ("requirements", requirements, 49),
        ("okrs", canonical.get("okrs", []), 4),
        ("non_goals", canonical.get("non_goals", []), 7),
    ):
        if not isinstance(rows, list) or len(rows) != count:
            structure_errors.append(f"{label} != {count}")
    if structure_errors:
        failures.append(
            f"[{proj.name}] Canonical 投影门: 固定结构错误: {', '.join(structure_errors)}"
        )
        return
    if any(not isinstance(row, dict) for row in decisions + requirements):
        failures.append(f"[{proj.name}] Canonical 投影门: decision/requirement row 必须是 mapping")
        return
    for label, rows in (("decision", decisions), ("requirement", requirements)):
        ids = [row.get("id") for row in rows]
        if any(not value for value in ids) or len(ids) != len(set(ids)):
            failures.append(f"[{proj.name}] Canonical 投影门: {label} ID 缺失或重复")
            return
    projections = {
        "00_我在哪.md": [
            canonical.get("taskpack_version"), canonical.get("status"),
            canonical.get("authorized_at"), canonical.get("product", {}).get("name"),
            canonical.get("product", {}).get("target_url"),
        ],
        "01_产品需求.md": [
            canonical.get("product", {}).get("pursuing_goal"),
            canonical.get("strategic_goal"), decisions, canonical.get("okrs", []),
            canonical.get("non_goals", []),
            [{key: row.get(key) for key in ("id", "area", "title", "statement", "priority")}
             for row in requirements],
        ],
        "02_系统架构.md": [
            canonical.get("storage_contract", {}), canonical.get("privacy_contract", {}),
        ],
        "03_口径字典.md": [
            [{"metric_id": f"metric::{row.get('id')}",
              **{key: row.get(key) for key in ("id", "metric", "baseline", "target", "window")}}
             for row in requirements],
        ],
        "04_操作流程.md": [
            canonical.get("owner_authorization", {}).get("interpretation", []),
            [{"area": row.get("area"), "id": row.get("id")} for row in requirements],
        ],
        "05_执行与验收.md": [
            [{key: row.get(key) for key in ("id", "task", "owner")}
             for row in requirements],
        ],
        "06_运维手册.md": [
            [row.get("id") for row in requirements
             if row.get("area") in {"持久化", "可靠性", "安全", "运营"}],
        ],
    }
    for name, values in projections.items():
        path = docs / name
        if not path.is_file():
            continue
        missing = _missing_values(path.read_text(encoding="utf-8"), values)
        if missing:
            preview = ", ".join(repr(value) for value in missing[:3])
            failures.append(
                f"[{proj.name}] Canonical 投影门: 文档/{name} 缺 {len(missing)} 个值"
                f"（示例: {preview}）"
            )


def check_project(proj: Path, failures: list):
    name = proj.name
    docs = proj / "文档"
    canonical_mode = (proj / "machine" / "canonical_facts.yaml").is_file()

    # 1. 结构门
    actual = sorted(path.name for path in docs.iterdir() if path.is_file()) if docs.is_dir() else []
    expected = sorted(SEVEN)
    if canonical_mode and actual != expected:
        failures.append(
            f"[{name}] 结构门: 文档/ 文件集合不是精确七文件；"
            f"缺少={sorted(set(expected) - set(actual))}，额外={sorted(set(actual) - set(expected))}"
        )
    for f in SEVEN:
        if not (docs / f).is_file():
            failures.append(f"[{name}] 结构门: 缺 文档/{f}")
        elif not (docs / f).read_text(encoding="utf-8").startswith(GENERATED_PREFIX):
            failures.append(f"[{name}] 结构门: 文档/{f} 未声明 GENERATED")
    if not (proj / "machine" / "facts").is_dir():
        failures.append(f"[{name}] 结构门: 缺 machine/facts/")

    # 2. 渲染一致门：备份渲染文件 -> 重渲染 -> 比对
    before = {}
    for f in RENDERED:
        p = docs / f
        before[f] = p.read_text(encoding="utf-8") if p.is_file() else None
    r = subprocess.run(
        [sys.executable, "machine/tools/render_human.py", "--root", "."],
        cwd=proj, capture_output=True, text=True,
    )
    if r.returncode != 0:
        failures.append(f"[{name}] 渲染失败: {r.stdout.strip()} {r.stderr.strip()}")
    for f in RENDERED:
        p = docs / f
        now = p.read_text(encoding="utf-8") if p.is_file() else None
        # 渲染时间戳行会变，比对时剔除
        def norm(t):
            if t is None:
                return None
            return "\n".join(l for l in t.splitlines() if "渲染时间" not in l)
        if norm(before[f]) != norm(now):
            failures.append(
                f"[{name}] 渲染一致门: 文档/{f} 与机器平面不一致"
                f"（人类平面被手工篡改，或事实源已变但未重渲染）")

    if canonical_mode:
        check_canonical_projection(proj, docs, failures)

    # 3. 三道门
    for tool, arg in [("check_doc_budget.py", ["--docs", "文档"]),
                      ("check_blocker_stop.py", ["--machine", "machine"])]:
        rr = subprocess.run(
            [sys.executable, f"machine/tools/{tool}"] + arg,
            cwd=proj, capture_output=True, text=True,
        )
        if rr.returncode != 0:
            first = next((l for l in rr.stdout.splitlines() if "✗" in l), rr.stdout.strip()[:120])
            failures.append(f"[{name}] {tool}: {first.strip()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--projects", nargs="*")
    ap.add_argument("--require-projects", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    projects = ([root / p for p in args.projects] if args.projects
                else discover(root))

    if not projects:
        msg = "未发现双平面项目"
        if args.require_projects:
            print(f"FAIL —— {msg}（本 repo 已声明必须合规）")
            return 1
        print(f"PASS —— {msg}（无需校验）")
        return 0

    failures: list = []
    for proj in projects:
        if not proj.is_dir():
            failures.append(f"[{proj.name}] 项目目录不存在")
            continue
        check_project(proj, failures)

    print(f"检查了 {len(projects)} 个项目：{', '.join(p.name for p in projects)}")
    if failures:
        print(f"\nFAIL —— {len(failures)} 项")
        for x in failures:
            print("  ✗ " + x)
        return 1
    print("PASS —— 全部项目双平面合规")
    return 0


if __name__ == "__main__":
    sys.exit(main())
