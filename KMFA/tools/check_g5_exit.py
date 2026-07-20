#!/usr/bin/env python3
"""G5 出口门禁检查单 + 证据包清单（TSK.KMFA.PROD.0018）。

任务包第 29 行原文：
  「S24 review 通过；App 真数据端到端 PASS 并入 CI；.app parity；性能达标；
    渲染门持续真绿。失败动作：remain_in_stage。**Approver：Owner**。」

本检查器只核**技术判据**并出证据包清单。**它不宣布 G5 通过**——
Approver 是 Owner，技术判据全绿 ≠ 门禁通过。结论字段为此分成两个：
  technical_checks_all_green（机器可判）与 g5_passed。

g5_passed 的唯一翻真途径：审批台账 metadata/approvals/control_events.jsonl 里存在
Owner 本人的 g5_signoff 事件（由 sign-g5 workflow_dispatch 落痕，GitHub 验身份）。
检查器只**识别**已记录的签名，不制造签名——签名不存在时恒 false。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KMFA = ROOT / "KMFA"
ART = KMFA / "stage_artifacts"

TASKS = [f"PROD.{n:04d}" for n in range(1, 19)]
EVIDENCE = {
    "PROD.0001": "DT6_PROD0001_sqlite_state", "PROD.0002": "DT6_PROD0002_backend_api",
    "PROD.0003": "DT6_PROD0003_access_security", "PROD.0004": "DT6_PROD0004_home",
    "PROD.0005": "DT6_PROD0005_source_board", "PROD.0006": "DT6_PROD0006_project_cost",
    "PROD.0007": "DT6_PROD0007_workbench", "PROD.0008": "DT6_PROD0008_impact_rerun",
    "PROD.0009": "DT6_PROD0009_report_center", "PROD.0010": "DT6_PROD0010_aging",
    "PROD.0011": "DT6_PROD0011_invoice_tax", "PROD.0012": "DT6_PROD0012_s24_review",
    "PROD.0013": "DT6_PROD0013_e2e", "PROD.0014": "DT6_PROD0014_erpnext_gap",
    "PROD.0015": "DT6_PROD0015_app_entry", "PROD.0016": "DT6_PROD0016_perf",
    "PROD.0017": "DT6_PROD0017_docs", "PROD.0018": "DT6_PROD0018_g5",
}
G5_ITEMS = [
    ("S24 review 通过", "DT6_PROD0012_s24_review"),
    ("App 真数据端到端 PASS 并入 CI", "DT6_PROD0013_e2e"),
    (".app parity", "DT6_PROD0015_app_entry"),
    ("性能达标", "DT6_PROD0016_perf"),
    ("渲染门持续真绿", "DT6_PROD0017_docs"),
]


def _dir_digest(p: Path) -> dict:
    """目录内容哈希：文件名 + 内容一起进摘要，改一个字节就变。"""
    if not p.is_dir():
        return {"存在": False}
    h, files = hashlib.sha256(), []
    for f in sorted(p.rglob("*")):
        if f.is_file():
            rel = f.relative_to(p).as_posix()
            h.update(rel.encode())
            h.update(f.read_bytes())
            files.append(rel)
    return {"存在": True, "文件数": len(files), "内容哈希": "sha256:" + h.hexdigest()}


def _render_gate() -> dict:
    """渲染门要现场跑，不能引用一句「上次是绿的」。"""
    out = {}
    for name, script in (("渲染", "machine/tools/render_human.py"),
                         ("三道门", "machine/tools/check_doc_budget.py"),
                         ("阻塞重审门", "machine/tools/check_blocker_stop.py")):
        r = subprocess.run(["python3", script], cwd=str(KMFA), capture_output=True, text=True)
        out[name] = {"退出码": r.returncode, "尾行": (r.stdout.strip().splitlines() or [""])[-1][:80]}
    return out


APPROVER = "LinzeColin"
SIGNOFF_LEDGER = KMFA / "metadata" / "approvals" / "control_events.jsonl"


def _find_signoff() -> dict | None:
    """在审批台账里找 Owner 的 g5_signoff 事件。只认字段齐全的，不认残缺行。"""
    if not SIGNOFF_LEDGER.exists():
        return None
    for line in SIGNOFF_LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (ev.get("event_type") == "g5_signoff"
                and ev.get("task_id") == "TSK.KMFA.PROD.0018"
                and ev.get("approver") == APPROVER
                and ev.get("approval_channel") == "github-actions workflow_dispatch"
                and ev.get("workflow_run_url")):
            return ev
    return None


def main() -> int:
    bundle = {t: {"证据目录": EVIDENCE[t], **_dir_digest(ART / EVIDENCE[t])} for t in TASKS}
    missing = [t for t, v in bundle.items() if not v.get("存在")]
    g5 = [{"项": n, "判据目录": d, "具备": (ART / d).is_dir() and any((ART / d).glob("*.md"))}
          for n, d in G5_ITEMS]
    gate = _render_gate()

    tech_green = (not missing and all(x["具备"] for x in g5)
                  and all(v["退出码"] == 0 for v in gate.values()))
    report = {
        "record_type": "g5_exit_checklist",
        "task_id": "TSK.KMFA.PROD.0018",
        "十八项证据包": {"合计": len(TASKS), "齐备": len(TASKS) - len(missing),
                         "缺": missing, "逐项": bundle},
        "G5检查单": {"合计": len(g5), "具备": len([x for x in g5 if x["具备"]]), "逐项": g5},
        "渲染门现场复跑": gate,
        "technical_checks_all_green": tech_green,
    }
    signoff = _find_signoff()
    report["g5_passed"] = bool(tech_green and signoff)
    if signoff:
        report["签核记录"] = {
            "事件号": signoff.get("event_id"), "签核人": signoff.get("approver"),
            "时间": signoff.get("event_time"), "运行": signoff.get("workflow_run_url"),
            "网站内容已亲验": signoff.get("site_content_verified_by_owner"),
        }
        if not tech_green:
            report["why_not_passed"] = "已有签核记录，但技术判据当前不全绿——签名不豁免技术判据。"
    else:
        report["why_not_passed"] = (
            "Approver 是 Owner（任务包第 29 行）。技术判据全绿不等于门禁通过，"
            "本检查器不代签。失败动作 remain_in_stage。")
        report["owner_待办"] = [
            "签核 G5：仓库 Actions → sign-g5 → Run workflow，输入确认语（GitHub 验身份，一次点击）",
            "登录 kmfa.linzezhang.com 亲验真实经营数据与页眉三徽章（可在同一 workflow 勾「已亲验网站」一并落痕）",
            "为 ERPNext 三条 gap 排序（PROD.0014 登记表）",
        ]
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if tech_green else 1


if __name__ == "__main__":
    raise SystemExit(main())
